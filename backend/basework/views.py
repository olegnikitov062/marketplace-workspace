"""Same-origin API оболочки с прежним реестром сессий и CSRF."""
from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from account_security import services as security
from account_security.models import AccountSession
from .services import catalog
from . import faq
from . import rooms


@never_cache
@require_GET
def auth_options(request):
    return JsonResponse({'oidcEnabled': bool(getattr(settings, 'BASEWORK_OIDC_ENABLED', False))})


def guarded(view=None, *, full=True):
    if view is None:
        return lambda target: guarded(target, full=full)
    @never_cache
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                expired = bool(request.COOKIES.get(settings.SESSION_COOKIE_NAME))
                return JsonResponse({'status': 'session_expired' if expired else 'anonymous'}, status=401)
            record = AccountSession.objects.filter(pk=getattr(request.security_session, 'pk', None),
                                                  user=request.user).first()
            if record is None or not security.record_valid(record, request.user, security.state_for(request.user)):
                return JsonResponse({'status': 'session_expired'}, status=401)
            if full and record.level != 'full':
                return JsonResponse({'status': 'mfa_required'}, status=403)
            return view(request, *args, **kwargs)
        except PermissionDenied:
            return JsonResponse({'status': 'denied'}, status=403)
        except DatabaseError:
            return JsonResponse({'status': 'access_unavailable'}, status=503)
    return wrapped


@require_GET
@guarded
def bootstrap(request):
    return JsonResponse({
        'session': {'status': 'authenticated', 'user': {
            'id': str(request.user.pk), 'displayName': request.user.username}},
        'applications': catalog(request.user),
        'csrfToken': get_token(request),
    })


@require_GET
@guarded
def application(request, application_id):
    if not any(item['id'] == application_id for item in catalog(request.user)):
        return JsonResponse({'status': 'denied'}, status=403)
    return JsonResponse({'status': 'module_unavailable'}, status=503)


@require_GET
@guarded
def faq_items(request):
    if not any(item['id'] == 'faq' for item in catalog(request.user)):
        return JsonResponse({'status': 'denied'}, status=403)
    if set(request.GET) - {'q', 'category'} or any(len(values) != 1 for _, values in request.GET.lists()):
        return JsonResponse({'status': 'invalid_request'}, status=400)
    query, category = request.GET.get('q', '').strip(), request.GET.get('category', '').strip()
    if len(query) > 300 or len(category) > 1000:
        return JsonResponse({'status': 'invalid_request'}, status=400)
    if not hasattr(request, '_basework_faq_result'):
        # IsolationBoundary завершит транзакцию до сети и повторит этот guard после неё.
        request._basework_faq_pending = True
        return JsonResponse({'status': 'source_pending'})
    if request._basework_faq_result is None:
        return JsonResponse({'status': 'source_unavailable'}, status=503)
    return JsonResponse(faq.search(request._basework_faq_result, query, category))


@require_POST
@csrf_protect
@guarded(full=False)
def logout(request, all_sessions=False):
    if request.body:
        return JsonResponse({'status': 'invalid_request'}, status=400)
    security.logout(request, all_sessions=all_sessions)
    response = JsonResponse({'status': 'ok', 'providerLogout': 'not_performed'})
    if all_sessions:
        response.delete_cookie(settings.SECURITY_TRUST_COOKIE, path='/auth/')
    return response


@require_http_methods(['GET', 'POST', 'PUT', 'DELETE'])
@csrf_protect
@guarded
def rooms_events(request, event_id=None):
    import json
    import re
    import uuid
    from datetime import datetime, timedelta
    from urllib.parse import urlencode
    from .models import ApplicationAccess
    if not ApplicationAccess.objects.filter(user=request.user, application='rooms', revoked_at__isnull=True).exists():
        return JsonResponse({'status': 'denied'}, status=403)
    if event_id is not None and not re.fullmatch('[a-f0-9]{32}', event_id):
        return JsonResponse({'status': 'invalid_request'}, status=400)
    if (request.method in ('GET', 'POST') and event_id is not None) or (request.method in ('PUT', 'DELETE') and event_id is None):
        return JsonResponse({'status': 'invalid_request'}, status=400)
    if request.method == 'GET':
        try:
            if set(request.GET) != {'from', 'to'} or any(len(v) != 1 for _, v in request.GET.lists()):
                raise ValueError()
            start, end = [datetime.fromisoformat(request.GET[k].replace('Z', '+00:00')) for k in ('from', 'to')]
            if start.tzinfo is None or end.tzinfo is None or not timedelta(0) < end - start <= timedelta(days=35):
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({'status': 'invalid_request'}, status=400)
        if not hasattr(request, '_basework_rooms_result'):
            request._basework_rooms_pending = (str(request.user.pk), str(request.security_session.pk),
                '/api/events?' + urlencode({k: request.GET[k] for k in ('from', 'to')}))
            return JsonResponse({'status': 'source_pending'})
        actor, session, _ = request._basework_rooms_pending
        if actor != str(request.user.pk) or session != str(request.security_session.pk):
            return JsonResponse({'status': 'session_expired'}, status=401)
        status, result = request._basework_rooms_result
        return JsonResponse(result, status=status)
    if not getattr(settings, 'BASEWORK_ROOMS_WRITES', False):
        return JsonResponse({'status': 'read_only'}, status=403)
    operation = rooms.operation_id(request.headers.get('Idempotency-Key'))
    try:
        if not operation or request.GET or request.content_type != 'application/json' or len(request.body) > 490_000:
            raise ValueError()
        body = json.loads(request.body)
        if not isinstance(body, dict):
            raise ValueError()
    except (ValueError, UnicodeError):
        return JsonResponse({'status': 'invalid_request'}, status=400)
    # Отзыв и внешняя запись сериализуются прежней блокировкой пользователя.
    # Сетевой запрос ограничен по времени; данные не копируются в PostgreSQL.
    user, state = security.locked_user(request.user.pk)
    record = AccountSession.objects.get(pk=request.security_session.pk, user=user)
    if not security.record_valid(record, user, state):
        return JsonResponse({'status': 'session_expired'}, status=401)
    if not ApplicationAccess.objects.filter(user=user, application='rooms', revoked_at__isnull=True).exists():
        return JsonResponse({'status': 'denied'}, status=403)
    try:
        status, result = rooms.exchange(user.pk, request.method, '/api/events' + ('/' + event_id if event_id else ''), body, operation)
    except rooms.SourceUnavailable:
        # Ответ потерян: браузер сохраняет тот же ключ и тело для проверки результата.
        return JsonResponse({'status': 'operation_unknown'}, status=503)
    return JsonResponse(result, status=status)
