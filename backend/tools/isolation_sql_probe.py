"""Real web LOGIN probes, invoked only by the guarded fresh E2-08 rehearsal.

Synthetic identities and claims stay in memory. Never prints SQL parameters,
cookies, capabilities or row data. Every unexpected write rolls back.
"""
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.conf import settings
from django.db import connection, transaction, DatabaseError
from django.utils import timezone

from data_isolation.context import StatementSigner, record_scope, scope, serialize, signature, signing_key
from data_isolation.sql import CONTROL_TABLES
from tools.isolation_web_contract import verify


def require(value):
    if not value:
        raise RuntimeError('isolation_probe_failed')


def run(case):
    from account_security.models import AccountSession
    from account_security.services import digest
    import psycopg
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),session_user,current_user,current_setting('cluster_name')")
        require(cursor.fetchone() == ('mw_beta','mw_beta_web','mw_beta_web','marketplace-e208-20261007-01a1105a-r2'))
        verify(cursor)
        for table in (*CONTROL_TABLES, 'access_control_syntheticrecord'):
            cursor.execute(f'SELECT count(*) FROM public.{table}')
            require(cursor.fetchone() == (0,))
    # Missing, malformed and caller-written identity GUCs never identify a user.
    for payload in ('', '{}', '{invalid', '{"kind":"control"}'):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true),set_config('mw.user_id',%s,true)",
                           [payload, '0'*64, str(case.owner.pk)])
            cursor.execute('SELECT count(*) FROM ownership_user')
            require(cursor.fetchone() == (0,))
    # Even a cryptographically valid but incomplete envelope is not an
    # identity. Exercise SQL NULL semantics rather than assuming HMAC suffices.
    for missing in ('pid','xid','database','role','expires','statement','kind','request'):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT pg_backend_pid(),txid_current()::text,current_database(),session_user')
            pid,xid,database,role=cursor.fetchone()
            statement='SELECT count(*) FROM ownership_user'
            claims=dict(pid=pid,xid=xid,database=database,role=role,expires=int(timezone.now().timestamp())+10,
                        statement=hashlib.sha256(statement.encode()).hexdigest(),kind='control',request=uuid.uuid4().hex)
            claims[missing]=None
            payload=serialize(claims)
            cursor.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true)",
                           [payload,signature(signing_key(),payload)])
            cursor.execute(statement)
            require(cursor.fetchone() == (0,))
    for sql in ('SELECT secret FROM mw_isolation.key',
                "SELECT mw_isolation.hmac('x',decode(repeat('00',32),'hex'))",
                'ALTER TABLE access_control_syntheticrecord DISABLE ROW LEVEL SECURITY',
                'SET ROLE mw_beta_migrator'):
        refused = False
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql)
                transaction.set_rollback(True)
        except DatabaseError as error:
            refused = getattr(error.__cause__, 'sqlstate', None) == '42501'
        require(refused)
    issued = {}
    for action in ('view','change'):
        result = case.post(case.org_url('grants/'), {'membership_id':str(case.mm.pk),
            'resource':'synthetic_record','action':action,'cabinet_id':str(case.ca.pk)})
        require(result.status_code == 201)
        issued[action] = result.json()['grant_id']
    with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)):
        session = AccountSession.objects.get(session_hash=digest(case.member_client.cookies[settings.SESSION_COOKIE_NAME].value))
    # A single personal session can use two independently granted organizations.
    require(case.member_client.get(case.url(case.rb),secure=True).json() == {'value':11})
    with transaction.atomic(), record_scope(case.member,session,case.b,case.cb,'view'):
        with connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)), connection.cursor() as cursor:
            cursor.execute('SELECT id FROM access_control_syntheticrecord ORDER BY id')
            require(cursor.fetchall() == [(case.rb.pk,)])
    marker=scope.set({'kind':'control','user':str(case.member.pk),'session':str(session.pk),'organization':str(case.a.pk)})
    try:
        with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)), connection.cursor() as cursor:
            cursor.execute('SELECT id FROM ownership_cabinet ORDER BY id')
            require({row[0] for row in cursor.fetchall()} == {case.ca.pk,case.ca2.pk})
    finally:
        scope.reset(marker)
    with transaction.atomic():
        with record_scope(case.member, session, case.a, case.ca, 'view'):
            with connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)), connection.cursor() as cursor:
                cursor.execute('SELECT id FROM access_control_syntheticrecord ORDER BY id')
                require(cursor.fetchall() == [(case.ra.pk,)])
                # View cannot write even when a separate change grant exists.
                cursor.execute('UPDATE access_control_syntheticrecord SET value=123')
                require(cursor.rowcount == 0)
        with connection.cursor() as cursor:
            cursor.execute('SELECT id FROM access_control_syntheticrecord ORDER BY id')
            require(cursor.fetchall() == [])  # Last signed statement was UPDATE.
        with record_scope(case.member, session, case.a, case.ca, 'change'):
            with connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)), connection.cursor() as cursor:
                cursor.execute('UPDATE access_control_syntheticrecord SET value=123')
                require(cursor.rowcount == 1)
        transaction.set_rollback(True)
    # A transaction's capability cannot survive rollback or authenticate a new
    # transaction, even if explicitly restored as a session-level setting.
    saved = None
    with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)), connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM ownership_user')
        require(cursor.fetchone()[0] > 0)
        # Raw cursor avoids signing the inspection and replacing the capability.
        with connection.connection.cursor() as raw:
            raw.execute("SELECT current_setting('mw.isolation_payload'),current_setting('mw.isolation_signature')")
            saved = raw.fetchone()
        transaction.set_rollback(True)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true)", saved)
        cursor.execute('SELECT count(*) FROM ownership_user')
        require(cursor.fetchone() == (0,))
    # Recover an aborted savepoint under the real wrapper, then keep using the
    # same connection; no closed/poisoned connection is silently substituted.
    with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)):
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute('SELECT 1/0')
        except DatabaseError:
            pass
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM ownership_user')
            require(cursor.fetchone()[0] > 0)
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM ownership_user')
        require(cursor.fetchone() == (0,))
    params = connection.get_connection_params()
    params.pop('cursor_factory',None)
    params.pop('context',None)
    barrier = Barrier(2)
    key = signing_key()
    def independent(cabinet):
        with psycopg.connect(**params, cursor_factory=psycopg.ClientCursor) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT pg_backend_pid(),txid_current()::text,current_database(),session_user')
                pid,xid,database,role = cur.fetchone()
                statement = 'SELECT id FROM access_control_syntheticrecord ORDER BY id'
                claims = dict(kind='record',resource='synthetic_record',action='view', user=str(case.member.pk),
                    session=str(session.pk),organization=str(case.a.pk),cabinet=str(cabinet.pk),
                    pid=pid,xid=xid,database=database,role=role,request=uuid.uuid4().hex,
                    expires=int(timezone.now().timestamp())+10,statement=hashlib.sha256(statement.encode()).hexdigest())
                payload=serialize(claims)
                cur.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true)", [payload,signature(key,payload)])
                barrier.wait(timeout=5)
                cur.execute(statement)
                return cur.fetchall()
    with ThreadPoolExecutor(max_workers=2) as pool:
        require(list(pool.map(independent,[case.ca,case.ca2])) == [[(case.ra.pk,)],[]])
    require(case.member_client.get(case.url(),secure=True).json() == {'value':7})
    require(case.post(case.org_url(f"grants/{issued['view']}/revoke/")).status_code == 200)
    # Same live session, correctly signed capability, revoked view grant:
    # the SQL predicate must still deny. Signing is not an authorization cache.
    with transaction.atomic(), record_scope(case.member,session,case.a,case.ca,'view'):
        with connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)), connection.cursor() as cursor:
            cursor.execute('SELECT id FROM access_control_syntheticrecord')
            require(cursor.fetchall() == [])
    require(case.member_client.get(case.url(),secure=True).status_code == 403)
