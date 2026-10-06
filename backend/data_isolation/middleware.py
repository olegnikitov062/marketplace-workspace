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
                                  'access_control.views', 'config.urls'}:
            return JsonResponse({'status': 'denied'}, status=403)
        marker = scope.set(None)
        try:
            with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)):
                response = self.get_response(request)
                if response.streaming:
                    transaction.set_rollback(True)
                    response = JsonResponse({'status': 'denied'}, status=503)
                elif response.status_code >= 500:
                    transaction.set_rollback(True)
                patch_cache_control(response, private=True, no_store=True, no_cache=True)
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
