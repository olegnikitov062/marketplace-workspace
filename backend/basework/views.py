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
