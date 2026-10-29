import uuid

from django.conf import settings
from django.db import connection, transaction
from django.http import JsonResponse
from django.urls import Resolver404, resolve
from django.utils.cache import patch_cache_control

from .context import StatementSigner, scope


class IsolationBoundary:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return JsonResponse({'status': 'not_found'}, status=404)
        view = getattr(match.func, 'view_class', match.func)
        if view.__module__ not in {'accounts.views', 'account_security.views',
                                  'access_control.views', 'config.urls', 'basework.views', 'basework.oidc_views',
                                  'basework.password_views'}:
            return JsonResponse({'status': 'denied'}, status=403)
        if request.path_info == '/auth/basework/oidc/callback' and getattr(settings, 'BASEWORK_OIDC_ENABLED', False):
            # Погашение state коммитится отдельно. Внешний обмен не удерживает
            # SQL-транзакцию; итоговая фаза проходит обычные session/MFA middleware.
            from basework.oidc import prepare_callback
            from django.core.exceptions import PermissionDenied
            try:
                if not request.is_secure():
                    raise PermissionDenied()
                prepare_callback(request)
            except Exception as error:
                response = JsonResponse({'status': 'oidc_denied' if isinstance(error, PermissionDenied) else 'oidc_unavailable'},
                                        status=403 if isinstance(error, PermissionDenied) else 503)
                patch_cache_control(response, private=True, no_store=True, no_cache=True)
                response['Referrer-Policy'] = 'no-referrer'
                return response
        response = self.transactional_response(request)
        if getattr(request, '_basework_faq_pending', False) and response.status_code == 200:
            from basework.faq import read_source, SourceUnavailable
            try:
                request._basework_faq_result = read_source()
            except SourceUnavailable:
                request._basework_faq_result = None
            # Повторная авторизация использует свежие user/session и те же SQL-подписи.
            for name in ('_cached_user', '_acached_user'):
                if hasattr(request, name):
                    delattr(request, name)
            return self.transactional_response(request)
        return response

    def transactional_response(self, request):
        marker = scope.set(None)
        try:
            with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)):
                response = self.get_response(request)
                if response.streaming:
                    transaction.set_rollback(True)
                    response = JsonResponse({'status': 'denied'}, status=503)
                elif response.status_code >= 500:
                    transaction.set_rollback(True)
                    if request.path.startswith('/api/v1/basework/'):
                        # При откате отзыва нельзя подтверждать выход очисткой cookie.
                        response.cookies.pop(settings.SESSION_COOKIE_NAME, None)
                        response.cookies.pop(getattr(settings, 'SECURITY_TRUST_COOKIE', ''), None)
                patch_cache_control(response, private=True, no_store=True, no_cache=True)
                if request.path.startswith('/auth/basework/oidc/'):
                    response['Referrer-Policy'] = 'no-referrer'
                    response['X-Frame-Options'] = 'DENY'
                return response
        finally:
            scope.reset(marker)


class ActorContext:
    """After SessionGate: add server-derived identity and URL tenant bounds.

    Pre-login queries run before this layer, bound to their exact statement.
    Query-string organization/cabinet/action fields never define this context.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        match = resolve(request.path_info)
        claims = {'kind': 'control'}
        if request.user.is_authenticated:
            claims['user'] = str(request.user.pk)
            session = getattr(request, 'security_session', None)
            if session is not None:
                claims['session'] = str(session.pk)
        if 'organization_id' in match.kwargs:
            claims['organization'] = str(match.kwargs['organization_id'])
        marker = scope.set(claims)
        try:
            return self.get_response(request)
        finally:
            scope.reset(marker)
