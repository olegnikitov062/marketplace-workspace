"""Trusted application signer, never an HTTP or SQL signing endpoint.

The web SQL credential alone is deliberately insufficient. Each capability binds
the *rendered, parameterized* statement, transaction, backend and database. Auth
queries retain their existing narrow consumers; this is not a blanket auth GUC.
Application code/key compromise is outside this trust boundary.
"""
import hashlib
import hmac
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.views.decorators.debug import sensitive_variables
from django.utils import timezone


scope = ContextVar('isolation_scope', default=None)


def serialize(claims):
    return json.dumps(claims, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def signature(key, payload):
    return hmac.new(key, payload.encode('utf-8'), hashlib.sha256).hexdigest()


@sensitive_variables()
def signing_key():
    if getattr(settings, 'ISOLATION_OFFLINE', False):
        return settings.ISOLATION_TEST_KEY
    path = getattr(settings, 'ISOLATION_KEY_FILE', None)
    if path != '/run/secrets/isolation_signing_key':
        raise ImproperlyConfigured('Isolation signing key mount required')
    try:
        key = Path(path).read_bytes()
    except OSError:
        raise ImproperlyConfigured('Isolation signing key unavailable') from None
    if len(key) != 32:
        raise ImproperlyConfigured('Isolation signing key invalid')
    return key


@contextmanager
def record_scope(actor, session, organization, cabinet, action):
    if action not in {'view', 'export', 'change'}:
        raise PermissionDenied()
    claims = {'kind': 'record', 'user': str(actor.pk), 'session': str(session.pk),
              'organization': str(organization.pk), 'cabinet': str(cabinet.pk),
              'resource': 'synthetic_record', 'action': action}
    marker = scope.set(claims)
    try:
        yield
    finally:
        scope.reset(marker)


class StatementSigner:
    """Installed only around one HTTP request, before session middleware.

    Never sign SQL supplied by a client. Raw SQL/admin tools do not install this
    wrapper. Unknown routes, streaming responses and executemany fail closed.
    """
    def __init__(self, connection, request_id):
        self.connection = connection
        self.request_id = request_id
        self.key = signing_key()

    @sensitive_variables()
    def __call__(self, execute, sql, params, many, context):
        # Recovery from an aborted savepoint must not issue SELECT/set_config
        # before ROLLBACK. These fixed Django transaction-control statements
        # cannot access rows and need no capability.
        if isinstance(sql, str) and not params and re.fullmatch(
                r'(?:SAVEPOINT|RELEASE SAVEPOINT|ROLLBACK TO SAVEPOINT) "s[0-9]+_x[0-9]+"', sql):
            return execute(sql, params, many, context)
        if self.connection.vendor != 'postgresql':
            if not getattr(settings, 'ISOLATION_OFFLINE', False):
                raise ImproperlyConfigured('Isolation requires PostgreSQL')
            return execute(sql, params, many, context)
        if many or not self.connection.in_atomic_block:
            raise PermissionDenied()
        # Use the same client-side adapter that executes the query. Binding is
        # completed once; the exact resulting text is both signed and executed.
        raw = context['cursor'].cursor
        if not hasattr(raw, 'mogrify'):
            raise ImproperlyConfigured('Isolation requires client-side SQL binding')
        statement = raw.mogrify(sql, params)
        if isinstance(statement, bytes):
            statement = statement.decode('utf-8')
        with self.connection.connection.cursor() as control:
            control.execute('SELECT pg_backend_pid(), txid_current()::text, current_database(), session_user')
            pid, xid, database, role = control.fetchone()
            claims = dict(scope.get() or {'kind': 'control'})
            claims.update(pid=pid, xid=xid, database=database, role=role,
                          request=self.request_id, expires=int(timezone.now().timestamp()) + 10,
                          statement=hashlib.sha256(statement.encode('utf-8')).hexdigest())
            payload = serialize(claims)
            control.execute("SELECT set_config('mw.isolation_payload', %s, true), "
                            "set_config('mw.isolation_signature', %s, true)",
                            [payload, signature(self.key, payload)])
        # A different statement cannot use the capability, even in this same
        # transaction. Transaction-local GUCs expire at commit or rollback.
        return execute(statement, None, False, context)
