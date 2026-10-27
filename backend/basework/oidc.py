"""Одноразовое состояние OIDC и завершение прежнего локального MFA."""
import json
import re
import secrets
import uuid
from contextlib import contextmanager
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from account_security import services as security
from account_security.crypto import seal
from accounts.limits import allow_attempt
from data_isolation.context import StatementSigner, scope
from .models import OIDCAttempt, IdentityBinding
from .oidc_configuration import CALLBACK_PATH, current, fingerprint
from . import oidc_client

COOKIE = '__Host-basework_oidc'


def enabled():
    if not getattr(settings, 'BASEWORK_OIDC_ENABLED', False) or connection.vendor != 'postgresql':
        raise PermissionDenied()


def browser(request):
    value = request.COOKIES.get(COOKIE, '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
        raise PermissionDenied()
    return security.digest(value)


@contextmanager
def phase():
    if connection.in_atomic_block:
        raise PermissionDenied()
    marker = scope.set(None)
    try:
        with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)):
            yield
    finally:
        scope.reset(marker)


def transition(operation, **values):
    with connection.cursor() as cursor:
        cursor.execute('SELECT basework_oidc_transition(%s,%s::jsonb)', [operation, json.dumps(values)])
        result = cursor.fetchone()[0]
    if result is None:
        raise PermissionDenied()
    return result


def begin(request):
    enabled()
    if not allow_attempt('oidc_start', request.META.get('REMOTE_ADDR', '')):
        raise PermissionDenied()
    state, raw_browser, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
    url = oidc_client.client().create_authorization_url(current().redirect_uri, state=state, nonce=nonce, code_verifier=verifier)['url']
    transition('create', id=str(uuid.uuid4()), state_hash=security.digest(state), browser_hash=security.digest(raw_browser),
               provider_hash=fingerprint(), nonce=seal(nonce), verifier=seal(verifier))
    return url, raw_browser


def prepare_callback(request):
    """Commit погашения до сети; сбой любой последующей фазы не возрождает state."""
    enabled()
    if request.method != 'GET' or any(len(v) != 1 for _, v in request.GET.lists()):
        raise PermissionDenied()
    state, code = request.GET.get('state', ''), request.GET.get('code', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
        raise PermissionDenied()
    browser_hash = browser(request)
    attempt = None
    with phase():
        if allow_attempt('oidc_callback', request.META.get('REMOTE_ADDR', '')):
            try:
                attempt_id = transition('claim', state_hash=security.digest(state), browser_hash=browser_hash, provider_hash=fingerprint())
                attempt = OIDCAttempt.objects.get(pk=attempt_id)
            except PermissionDenied:
                pass  # Отказ не откатывает счётчик ограничения попыток.
    if attempt is None:
        raise PermissionDenied()
    if ('error' in request.GET or not 1 <= len(code) <= 2048
            or request.GET.get('iss', current().issuer) != current().issuer):
        raise PermissionDenied()
    # Authlib и сетевой транспорт не могут обращаться к БД или сохранять токены.
    identity = oidc_client.exchange(attempt, code)
    request.basework_oidc_result = (attempt_id, identity)


def pending(request):
    return OIDCAttempt.objects.filter(browser_hash=browser(request), ready_at__isnull=False,
        finished_at__isnull=True, expires_at__gt=timezone.now(), provider_hash=fingerprint()).first()


def finish(request, attempt, token=None):
    binding = IdentityBinding.objects.get(pk=attempt.binding_id)
    user, state = security.locked_user(binding.user_id)
    # Повторное чтение после общей блокировки user сериализует MFA/отзыв/выход.
    attempt = pending(request)
    if attempt is None or attempt.binding_id != binding.pk:
        raise PermissionDenied()
    binding.refresh_from_db()
    if (binding.revoked_at or state.recovery_required or state.version != attempt.version
            or not constant_time_compare(user.get_session_auth_hash(), attempt.credential_hash)):
        raise PermissionDenied()
    device = security.authenticator(user)
    if device:
        if token is None:
            return 'mfa'
        device = security.verify_factor(user.pk, token, device.pk)
        if device is None:
            return 'invalid_factor'  # Не откатывать счётчики django-otp.
    elif security.required(user):
        return 'setup_required'  # Настройка фактора — через прежний локальный вход.
    record = security.register_session(request, user, state, 'full', device=device,
                                       factor=bool(device), password_confirmed=False)
    transition('finish', id=str(attempt.pk), browser_hash=browser(request), session_id=str(record.pk))
    security.event(user, 'basework_oidc_login')
    return 'complete'


def callback(request):
    result = getattr(request, 'basework_oidc_result', None)
    if result is None:
        raise PermissionDenied()
    attempt_id, (issuer, subject) = result
    from .services import resolve_identity
    binding = resolve_identity(issuer, subject)
    user, state = security.locked_user(binding.user_id)
    binding.refresh_from_db()
    if binding.revoked_at or state.recovery_required:
        raise PermissionDenied()
    transition('ready', id=str(attempt_id), browser_hash=browser(request), binding_id=str(binding.pk),
               version=state.version, credential_hash=user.get_session_auth_hash())
    return finish(request, OIDCAttempt.objects.get(pk=attempt_id))
