"""Same-origin API оболочки с прежним реестром сессий и CSRF."""
from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from account_security import services as security
from account_security.models import AccountSession
from .services import catalog
from . import faq


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
