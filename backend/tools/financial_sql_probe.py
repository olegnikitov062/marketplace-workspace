"""Guarded caller only: real web LOGIN/HTTP, no emitted payloads or credentials."""
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.conf import settings
from django.db import connection, transaction, DatabaseError
from django.utils import timezone
from data_isolation.context import StatementSigner, record_scope, scope, signing_key, signature, serialize
from tools.financial_rehearsal import expect, PROJECT


def denied(statement, params=None, signed=False):
    from contextlib import nullcontext
    refused = False
    try:
        with transaction.atomic():
            wrapper = connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)) if signed else nullcontext()
            with wrapper, connection.cursor() as cursor:
                cursor.execute(statement,params)
                transaction.set_rollback(True)
    except DatabaseError as error:
        refused = getattr(error.__cause__,'sqlstate',None)=='42501'
    expect(refused)


def run(case):
    from account_security.models import AccountSession
    from account_security.services import digest
    with connection.cursor() as cursor:
        cursor.execute("SELECT session_user,current_user,current_database(),current_setting('cluster_name')")
        expect(cursor.fetchone()==('mw_beta_web','mw_beta_web','mw_beta',PROJECT))
    # This credential cannot access financial columns even with a genuine signed SQL.
    for statement in ('SELECT * FROM access_control_syntheticfinance',
                      'SELECT sum(cost) FROM access_control_syntheticfinance',
                      'UPDATE access_control_syntheticfinance SET cost=0',
                      'ALTER TABLE access_control_syntheticfinance DISABLE ROW LEVEL SECURITY',
                      'SELECT mw_isolation.finance_allowed(NULL)',
                      'UPDATE access_control_exportbinding SET finance_grant_id=NULL',
                      'SET ROLE mw_beta_migrator'):
        denied(statement)
        denied(statement,signed=True)
    sql='SELECT * FROM mw_isolation.finance_read(%s::uuid[],NULL::uuid)'
    args=[[case.ra.pk]]
    denied(sql,args)
    denied(sql,args,signed=True)  # Trusted control envelope is still insufficient.
    issued={}
    def issue(resource,action,cabinet=case.ca):
        response=case.post(case.org_url('grants/'), dict(membership_id=str(case.mm.pk),
            resource=resource,action=action,cabinet_id=str(cabinet.pk)))
        expect(response.status_code==201)
        return response.json()['grant_id']
    issue('synthetic_record','view')
    with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)):
        session=AccountSession.objects.get(session_hash=digest(case.member_client.cookies[settings.SESSION_COOKIE_NAME].value))
    with record_scope(case.member,session,case.a,case.ca,'view'):
        denied(sql,args,signed=True)  # Ordinary view is not financial authority.
    expect(case.member_client.get(case.url(),secure=True).json()['finance_visibility']=='restricted')
    for action in ('view','export','change'):
        issued[action]=issue('synthetic_finance',action)
    with record_scope(case.member,session,case.a,case.ca,'view'):
        original = scope.get()
        for field, value in (('user',None),('session',None),('organization',None),('cabinet',None),
                             ('resource','synthetic_finance'),('action','manage_access'),('session','invalid')):
            marker = scope.set({**original,field:value})
            try:
                denied(sql,args,signed=True)
            finally:
                scope.reset(marker)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            denied(sql,args,signed=True)
    data=case.member_client.get(case.url(),secure=True).json()
    expect(data['finance']['profit']=='50.00')
    listing=case.member_client.get(case.list_url(),secure=True).json()
    expect(listing['finance_totals']['profit']=='50.00' and listing['finance_totals']['scope']=='returned_records')
    expect(case.member_client.get(case.url(case.rb),secure=True).json()['finance_visibility']=='restricted')
    for query in ('fields=cost','sort=profit','group_by=payout','cost__gt=1','resource=synthetic_finance'):
        expect(case.member_client.get(case.list_url()+'?'+query,secure=True).status_code==403)
    with transaction.atomic(), record_scope(case.member,session,case.a,case.ca,'view'):
        with connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)), connection.cursor() as cursor:
            cursor.execute(sql,[[case.ra.pk,case.ra2.pk,case.rb.pk]])
            expect([r[0] for r in cursor.fetchall()]==[case.ra.pk])
        denied('SELECT mw_isolation.finance_write(%s,1,1,1,1)',[case.ra.pk],signed=True)
    # Same connection after savepoint failure; following unsigned query must deny.
    with transaction.atomic(), record_scope(case.member,session,case.a,case.ca,'view'), \
            connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)):
        try:
            with transaction.atomic(),connection.cursor() as cursor:
                cursor.execute('SELECT 1/0')
        except DatabaseError:
            pass
        with connection.cursor() as cursor:
            cursor.execute(sql,args)
            expect(len(cursor.fetchall())==1)
    denied(sql,args)
    # No change survives an exception/rollback, even with financial change authority.
    with transaction.atomic(),record_scope(case.member,session,case.a,case.ca,'change'):
        with connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)),connection.cursor() as cursor:
            cursor.execute('SELECT mw_isolation.finance_write(%s,5,1,1,1)',[case.ra.pk])
        transaction.set_rollback(True)
    expect(case.member_client.get(case.url(),secure=True).json()['finance']['revenue']=='100.00')
    path=case.url(suffix='finance/change/')
    expect(case.post(path,case.change_values(),case.member_client,csrf=False).status_code==403)
    expect(case.post(path,case.change_values(),case.member_client).json()=={'status':'ok'})
    # Independent backend/transaction identities: one permitted cabinet, one denied.
    params=connection.get_connection_params(); params.pop('cursor_factory',None); params.pop('context',None)
    barrier=Barrier(2); key=signing_key()
    def independent(cab):
        import psycopg
        with psycopg.connect(**params,cursor_factory=psycopg.ClientCursor) as conn:
            cur=conn.cursor()
            cur.execute('SELECT pg_backend_pid(),txid_current()::text,current_database(),session_user')
            pid,xid,database,role=cur.fetchone()
            statement=cur.mogrify(sql,args)
            if isinstance(statement,bytes): statement=statement.decode()
            claims=dict(kind='record',resource='synthetic_record',action='view',user=str(case.member.pk),
                session=str(session.pk),organization=str(case.a.pk),cabinet=str(cab.pk),pid=pid,xid=xid,
                database=database,role=role,request=uuid.uuid4().hex,expires=int(timezone.now().timestamp())+10,
                statement=hashlib.sha256(statement.encode()).hexdigest())
            payload=serialize(claims)
            cur.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true)",
                        [payload,signature(key,payload)])
            barrier.wait(timeout=5)
            try:
                cur.execute(statement)
                return [row[0] for row in cur.fetchall()]==[case.ra.pk]
            except psycopg.errors.InsufficientPrivilege:
                conn.rollback()
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        expect(list(pool.map(independent,[case.ca,case.ca2]))==[True,False])
    permit=case.export()
    expect(b'profit' in case.download(permit).content)
    expect(case.post(case.org_url(f"grants/{issued['export']}/revoke/")).status_code==200)
    issue('synthetic_finance','export')
    expect(case.download(permit).status_code==403)
    expect(case.download(case.export()).status_code==200)
    expect(case.post(case.org_url(f"grants/{issued['view']}/revoke/")).status_code==200)
    with record_scope(case.member,session,case.a,case.ca,'view'):
        denied(sql,args,signed=True)
    expect(case.member_client.get(case.list_url(),secure=True).json()['finance_visibility']=='restricted')
    expect(scope.get() is None)
    print('Financial real web LOGIN, fields/formulas/totals, SQL denial/reuse/concurrency and irreversible links PASS')
