"""Проверки BaseWork только в новом локальном синтетическом кластере."""
import argparse
import json
import os
from pathlib import Path

PROJECT = 'basework-stage3-pg-20261027'
TABLES = ('basework_identitybinding', 'basework_federatedsession', 'basework_applicationaccess')


def expect(value, code):
    if not value:
        raise AssertionError(code)


def marker():
    expect(os.name == 'posix' and os.environ.get('BASEWORK_PG_REHEARSAL') == PROJECT, 'маркер_окружения')
    path = Path('/run/basework-pg/manifest.json')
    expect(path.is_file() and not path.is_symlink(), 'файл_маркера')
    expect(json.loads(path.read_text()) == {'project': PROJECT, 'synthetic_only': True}, 'содержимое_маркера')


def bootstrap():
    import psycopg
    import runpy
    marker()
    args = dict(host='postgres', dbname='mw_beta', user='mw_beta_bootstrap',
                password=Path('/run/secrets/db_bootstrap_password').read_text().strip(), connect_timeout=5)
    with psycopg.connect(**args) as conn:
        expect(conn.execute("SELECT current_database(),session_user,current_setting('cluster_name')").fetchone()
               == ('mw_beta', 'mw_beta_bootstrap', PROJECT), 'кластер_bootstrap')
        expect(conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone() == (0,), 'пустая_база')
        expect(conn.execute("SELECT count(*) FROM pg_roles WHERE rolname IN ('mw_beta_web','mw_beta_migrator')").fetchone() == (0,), 'новые_роли')
        conn.execute('REVOKE TEMPORARY ON DATABASE mw_beta FROM PUBLIC')
    runpy.run_module('tools.bootstrap_roles', run_name='__main__')
    with psycopg.connect(**args) as conn:
        expect(conn.execute("SELECT current_setting('cluster_name')").fetchone() == (PROJECT,), 'кластер_схемы')
        conn.execute('CREATE SCHEMA mw_isolation AUTHORIZATION mw_beta_migrator')


def guard():
    marker()
    expect(os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings') == 'config.settings', 'настройки')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.db import connection
    from django.conf import settings
    from account_security.operator import require_operator_process
    require_operator_process()
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('cluster_name'),current_setting('server_version_num')::int")
        cluster, version = cursor.fetchone()
        expect(cluster == PROJECT and 170000 <= version < 180000, 'кластер_PostgreSQL17')
    expect(settings.ISOLATION_ENABLED and settings.BASEWORK_ENABLED, 'защита_включена')


def configure():
    guard()
    from django.core.management import call_command
    from django.db import connection, transaction
    from tools import access_web_grants as acl
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.django_migrations')")
        expect(cursor.fetchone() == (None,), 'только_новая_схема')
    call_command('migrate', interactive=False, verbosity=0)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM mw_beta_web')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM mw_beta_web')
        for table in (*acl.READ_TABLES, *TABLES):
            cursor.execute(f'GRANT SELECT ON public.{table} TO mw_beta_web')
        acl.apply_fresh(cursor, acl.MAIN_ROLE)
        from tools.isolation_web_contract import apply
        apply(cursor, Path('/run/secrets/isolation_signing_key').read_bytes())
        from tools.financial_web_contract import apply as finance
        finance(cursor)
    contract()


def contract():
    guard()
    from django.db import connection
    from tools.financial_web_contract import verify
    with connection.cursor() as cursor:
        verify(cursor)
        for table in TABLES:
            cursor.execute("SELECT c.relrowsecurity,c.relforcerowsecurity,r.rolname FROM pg_class c "
                           "JOIN pg_roles r ON r.oid=c.relowner WHERE c.oid=%s::regclass", [table])
            expect(cursor.fetchone() == (True, True, 'mw_beta_migrator'), 'RLS_' + table)
            cursor.execute("SELECT policyname,cmd,roles,qual,with_check FROM pg_policies "
                           "WHERE schemaname='public' AND tablename=%s ORDER BY policyname", [table])
            expect(cursor.fetchall() == [('basework_operator', 'ALL', ['mw_beta_migrator'], 'true', 'true'),
                                         ('basework_read', 'SELECT', ['public'], '(mw_isolation.claims() IS NOT NULL)', None)], 'политики_' + table)
            cursor.execute("SELECT has_table_privilege('mw_beta_web',%s,'SELECT'), "
                           "has_table_privilege('mw_beta_web',%s,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'), "
                           "EXISTS(SELECT 1 FROM pg_attribute a WHERE a.attrelid=%s::regclass AND a.attnum>0 "
                           "AND NOT a.attisdropped AND has_column_privilege('mw_beta_web',a.attrelid,a.attnum,'INSERT,UPDATE,REFERENCES'))", [table]*3)
            expect(cursor.fetchone() == (True, False, False), 'ACL_' + table)
            cursor.execute("SELECT tgname,tgenabled,p.proname FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid "
                           "WHERE tgrelid=%s::regclass AND NOT tgisinternal ORDER BY tgname", [table])
            expected = [('basework_immutable', 'O', 'security_immutable'), ('basework_no_delete', 'O', 'basework_no_delete')]
            expected.append(('basework_session_binding', 'O', 'basework_session_binding') if table == 'basework_federatedsession'
                            else ('basework_revoke', 'O', table + '_revoke'))
            expect(cursor.fetchall() == expected, 'триггеры_' + table)
        cursor.execute("SELECT p.proname,p.prosecdef,p.proconfig,r.rolname, "
                       "has_function_privilege('mw_beta_web',p.oid,'EXECUTE'), "
                       "EXISTS(SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0) "
                       "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner "
                       "WHERE n.nspname='public' AND p.proname IN ('basework_no_delete','basework_session_binding',"
                       "'basework_identitybinding_revoke','basework_applicationaccess_revoke')")
        functions = cursor.fetchall()
        expect(len(functions) == 4, 'число_функций_BaseWork')
        for name, definer, config, owner, executable, public in functions:
            expect(owner == 'mw_beta_migrator' and not executable and not public
                   and definer == name.endswith('_revoke')
                   and config == ['search_path=pg_catalog' if name == 'basework_no_delete' else 'search_path=pg_catalog, public'], 'защита_функций_BaseWork')
        cursor.execute("SELECT version()")
        print(json.dumps({'контракт': 'PASS', 'PostgreSQL': cursor.fetchone()[0], 'BaseWork_FORCE_RLS': 3}, ensure_ascii=False))


def http_smoke():
    guard()
    import urllib.request
    import urllib.error
    from django.core.management import call_command
    call_command('migrate', check_unapplied=True, interactive=False, verbosity=0)
    call_command('makemigrations', check=True, dry_run=True, verbosity=0)
    for path, status, expected in (
        ('/api/v1/health/live', 200, 'ok'),
        ('/api/v1/health/ready', 200, 'ready'),
        ('/api/v1/basework/bootstrap', 401, 'anonymous'),
        ('/api/v1/basework/applications/marketplace', 401, 'anonymous'),
    ):
        try:
            response = urllib.request.urlopen('http://web:8000' + path, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            expect(response.status == status and json.load(response)['status'] == expected, 'HTTP_' + path)
            expect('no-store' in response.headers.get('Cache-Control', ''), 'HTTP_без_кэша')
        print(json.dumps({'HTTP': path, 'результат': 'PASS', 'код': status}, ensure_ascii=False))


def scenario():
    guard()
    import hashlib
    import time
    import uuid
    from contextlib import contextmanager
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from unittest.mock import patch
    import psycopg
    from django.conf import settings
    from django.db import connection, transaction, DatabaseError, IntegrityError
    from django.test import Client
    from django.utils import timezone
    from ownership.models import User, Membership
    from accounts.models import AccountContact
    from account_security.models import AccountSession, Authenticator, ExportPermit
    from account_security import services as security
    from access_control.tests.test_http import AccessHTTPTests
    from basework.models import IdentityBinding, FederatedSession, ApplicationAccess
    from basework import services
    from data_isolation.context import StatementSigner, serialize, signature, signing_key

    checks = []
    def check(value, name):
        expect(value, name)
        checks.append(name)
        print(json.dumps({'проверка': name, 'результат': 'PASS'}, ensure_ascii=False), flush=True)

    settings.ALLOWED_HOSTS = ['testserver', 'localhost', 'web']
    settings.SECURITY_DOWNLOAD_PROBE = True
    # Каждый повтор создаёт новые синтетические учётные записи; история не удаляется.
    prefix = uuid.uuid4().hex[:10]
    create_user, create_contact = User.objects.create_user, AccountContact.objects.create
    def new_user(username, *args, **kwargs):
        return create_user(prefix + '-' + username, *args, **kwargs)
    def new_contact(**kwargs):
        kwargs['email'] = prefix + '-' + kwargs['email']
        return create_contact(**kwargs)
    case = AccessHTTPTests('test_default_deny_and_four_independent_actions')
    with patch.object(User.objects, 'create_user', side_effect=new_user), patch.object(AccountContact.objects, 'create', side_effect=new_contact):
        case.setUp()
    owner_factor = Authenticator.objects.get(user=case.owner, confirmed=True, revoked_at__isnull=True)
    migrator_password = connection.settings_dict['PASSWORD']
    web_password = Path('/run/secrets/db_web_password').read_text().strip()

    def switch(role):
        expect(not connection.in_atomic_block, 'переключение_вне_транзакции')
        connection.close()
        connection.settings_dict['USER'] = 'mw_beta_' + role
        connection.settings_dict['PASSWORD'] = web_password if role == 'web' else migrator_password
        with connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_user,current_database(),current_setting('cluster_name')")
            expect(cursor.fetchone() == ('mw_beta_' + role, 'mw_beta_' + role, 'mw_beta', PROJECT), 'реальный_LOGIN_' + role)

    @contextmanager
    def operator():
        switch('migrator')
        try:
            yield
        finally:
            switch('web')

    def login(user, client, factor=None):
        result = case.start_login(user, client)
        if factor is not None:
            with operator():
                factor.refresh_from_db()
            code, now = case.otp(factor)
            with patch('django_otp.plugins.otp_totp.models.time.time', return_value=now):
                result = case.post('/auth/mfa/login/', {'personal_login-current_step': 'token',
                    'token-otp_token': code, 'token-remember': ''}, client)
        expect(result.status_code == 302, 'вход_HTTP')
        expect(client.get('/auth/session', secure=True).status_code == 200, 'сессия_HTTP')

    def bootstrap(client=None):
        return (client or case.member_client).get('/api/v1/basework/bootstrap', secure=True)

    def denied_sql(statement, params=None, sqlstate='42501'):
        refused = False
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(statement, params)
                transaction.set_rollback(True)
        except DatabaseError as error:
            refused = getattr(error.__cause__, 'sqlstate', None) == sqlstate
        expect(refused, 'запрещённый_SQL')

    switch('web')
    case.client, case.member_client = Client(enforce_csrf_checks=True), Client(enforce_csrf_checks=True)
    login(case.owner, case.client, owner_factor)
    login(case.member, case.member_client)
    check(bootstrap().status_code == 200 and bootstrap().json()['session']['user']['id'] == str(case.member.pk), 'bootstrap_реальный_web_LOGIN')
    check(bootstrap().json()['applications'] == [], 'меню_запрещено_по_умолчанию')
    with operator():
        binding = IdentityBinding.objects.create(user=case.member, issuer='https://issuer.example.invalid', subject=prefix)
        record = case.session_record(case.member_client)
        owner_record = case.session_record(case.client)
        services.attach_identity(record, binding)
        access = ApplicationAccess.objects.create(user=case.member, application='marketplace')
        faq = ApplicationAccess.objects.create(user=case.member, application='faq')
        view_grant = case.grant('view', case.ca)
        case.grant('export', case.ca)
    check({a['id'] for a in bootstrap().json()['applications']} == {'marketplace', 'faq'}, 'меню_с_живыми_правами')
    check(case.member_client.get(case.url(), secure=True).status_code == 200, 'прямой_API_с_правом')
    check(all(case.member_client.get(case.url(obj), secure=True).status_code == 403 for obj in (case.ra2, case.rb)), 'чужие_кабинет_и_организация')
    check(case.member_client.get('/api/v1/basework/applications/faq', secure=True).status_code == 503, 'неподключённый_адаптер')
    permit = case.export()
    check(case.download(permit).status_code == 200, 'файл_до_отзыва')

    for table in TABLES:
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT count(*) FROM {table}')
            check(cursor.fetchone() == (0,), 'RLS_без_подписи_' + table)
        column = 'session_id' if table == 'basework_federatedsession' else 'id'
        for statement in (f'INSERT INTO {table} DEFAULT VALUES', f'UPDATE {table} SET {column}={column}',
                          f'DELETE FROM {table}', f'TRUNCATE {table} CASCADE',
                          f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY'):
            denied_sql(statement)
        check(True, 'пять_запретов_SQL_' + table)
    for statement in ('SET ROLE mw_beta_migrator', 'SELECT secret FROM mw_isolation.key',
                      'CREATE TABLE basework_forbidden(id integer)', 'CREATE TEMP TABLE basework_forbidden(id integer)'):
        denied_sql(statement)
    check(True, 'нет_повышения_прав_ключа_и_DDL')

    # Одна подпись привязана к тексту SQL, транзакции, соединению и сроку.
    statement = 'SELECT count(*) FROM basework_identitybinding'
    saved = None
    with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)), connection.cursor() as cursor:
        cursor.execute(statement)
        check(cursor.fetchone()[0] > 0, 'RLS_точный_подписанный_SQL')
        with connection.connection.cursor() as raw:
            raw.execute("SELECT current_setting('mw.isolation_payload'),current_setting('mw.isolation_signature')")
            saved = raw.fetchone()
            raw.execute(statement + ' WHERE revoked_at IS NULL')
            check(raw.fetchone() == (0,), 'подпись_не_подходит_другому_SQL')
        transaction.set_rollback(True)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true)", saved)
        cursor.execute(statement)
        check(cursor.fetchone() == (0,), 'повтор_подписи_после_rollback_запрещён')
    for expired in (False, True):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT pg_backend_pid(),txid_current()::text,current_database(),session_user')
            pid, xid, database, role = cursor.fetchone()
            claims = dict(pid=pid,xid=xid,database=database,role=role,kind='control',request=uuid.uuid4().hex,
                          expires=int(time.time()) + (-1 if expired else 10),statement=hashlib.sha256(statement.encode()).hexdigest())
            payload = serialize(claims)
            cursor.execute("SELECT set_config('mw.isolation_payload',%s,true),set_config('mw.isolation_signature',%s,true)",
                           [payload, signature(signing_key(), payload) if expired else '0'*64])
            cursor.execute(statement)
            check(cursor.fetchone() == (0,), 'истёкшая_подпись' if expired else 'поддельная_подпись')

    with operator():
        for table, column, value in ((TABLES[0], 'subject', 'changed'), (TABLES[2], 'application', 'rooms')):
            denied_sql(f'UPDATE {table} SET {column}=%s WHERE id=%s', [value, binding.pk if table == TABLES[0] else access.pk], '23514')
        for table in TABLES:
            denied_sql(f'DELETE FROM {table}', sqlstate='23514')
        refused = False
        try:
            with transaction.atomic():
                FederatedSession.objects.create(binding=binding, session=owner_record)
        except IntegrityError:
            refused = True
        check(refused, 'чужая_сессия_не_перепривязывается')
        check(True, 'неизменяемая_история_и_запрет_удаления')
        with transaction.atomic():
            services.revoke_identity(binding.pk)
            record.refresh_from_db()
            check(record.revoked_at is not None, 'отзыв_внутри_транзакции')
            transaction.set_rollback(True)
        binding.refresh_from_db()
        record.refresh_from_db()
        check(binding.revoked_at is None and record.revoked_at is None, 'откат_отзыва_атомарен')
    check(bootstrap().status_code == 200 and case.download(permit).status_code == 200, 'доступ_сохранён_после_отката')

    cookie = case.member_client.cookies[settings.SESSION_COOKIE_NAME].value
    check(case.member_client.post('/api/v1/basework/logout', secure=True).status_code == 403, 'выход_требует_CSRF')
    original_logout = security.logout
    def failure(request, **kwargs):
        original_logout(request, **kwargs)
        raise DatabaseError()
    with patch('basework.views.security.logout', side_effect=failure):
        response = case.post('/api/v1/basework/logout', client=case.member_client)
    check(response.status_code == 503 and settings.SESSION_COOKIE_NAME not in response.cookies, 'ошибка_выхода_не_подтверждает_успех')
    check(bootstrap().status_code == 200, 'ошибка_выхода_откатила_отзыв')
    with patch('basework.services.ApplicationAccess.objects.filter', side_effect=DatabaseError()):
        check(bootstrap().status_code == 503, 'ошибка_реестра_не_открывает_доступ')

    # Отдельное соединение удерживает незавершённый сырой отзыв. HTTP проверяется
    # в другом соединении до commit, затем повторяется с прежней cookie после commit.
    ready, release = Event(), Event()
    def concurrent_revoke():
        with psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_migrator',
                             password=migrator_password, connect_timeout=5,
                             options='-c statement_timeout=5000 -c lock_timeout=2000') as conn:
            expect(conn.execute("SELECT current_setting('cluster_name'),session_user").fetchone() == (PROJECT, 'mw_beta_migrator'), 'конкурентный_кластер')
            conn.execute('UPDATE basework_identitybinding SET revoked_at=CURRENT_TIMESTAMP WHERE id=%s', [binding.pk])
            ready.set()
            expect(release.wait(10), 'ожидание_commit')
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(concurrent_revoke)
        try:
            expect(ready.wait(8), 'отзыв_начат')
            check(bootstrap().status_code == 200, 'незавершённый_отзыв_не_виден_другому_соединению')
        finally:
            release.set()
        pending.result(timeout=8)
    committed = time.monotonic()
    check(bootstrap().status_code == 401, 'отзыв_commit_закрыл_старую_cookie')
    for url, expected in (('/auth/session', 401), (case.url(), 403), (f'/auth/security/probe/{permit}/', 302)):
        case.member_client.cookies[settings.SESSION_COOKIE_NAME] = cookie
        response = case.member_client.get(url, secure=True)
        check(response.status_code == expected and (expected != 302 or response['Location'].startswith(settings.LOGIN_URL + '?')),
              'отзыв_закрыл_' + ('файл' if 'probe/' in url else 'сессию' if url == '/auth/session' else 'прямой_API'))
    latency = time.monotonic() - committed
    check(latency < 60, 'отзыв_проверенных_путей_менее_60с')
    with operator():
        record.refresh_from_db()
        check(record.revoked_at is not None and ExportPermit.objects.get(pk=permit).revoked_at is not None, 'SQL_триггер_отозвал_сессию_и_файл')
        denied_sql('UPDATE basework_identitybinding SET revoked_at=NULL WHERE id=%s', [binding.pk], '23514')
    check(bootstrap(case.client).status_code == 200, 'отзыв_не_затронул_другого_пользователя')

    case.member_client = Client(enforce_csrf_checks=True)
    login(case.member, case.member_client)
    check(case.download(permit).status_code == 403, 'новый_вход_не_восстановил_старый_файл')
    with operator():
        services.revoke_application(faq.pk)
    check(bootstrap().status_code == 401, 'операторский_отзыв_приложения_закрыл_сессию')
    case.member_client = Client(enforce_csrf_checks=True)
    login(case.member, case.member_client)
    check({a['id'] for a in bootstrap().json()['applications']} == {'marketplace'}, 'повторный_вход_не_вернул_отозванное_меню')
    with operator():
        view_grant.revoked_at = timezone.now()
        view_grant.save(update_fields=['revoked_at'])
    check(bootstrap().json()['applications'] == [] and case.member_client.get(case.url(), secure=True).status_code == 403, 'отзыв_прикладного_права_меню_и_API')
    with operator():
        case.grant('view', case.ca)
        Membership.objects.filter(pk=case.mm.pk).update(state='suspended')
    check(bootstrap().json()['applications'] == [] and case.member_client.get(case.url(), secure=True).status_code == 403, 'приостановка_членства_меню_и_API')
    with operator():
        User.objects.filter(pk=case.member.pk).update(is_active=False)
    check(bootstrap().status_code == 401, 'блокировка_пользователя_старой_cookie')

    second_owner = Client(enforce_csrf_checks=True)
    login(case.owner, second_owner, owner_factor)
    owner_cookie = case.client.cookies[settings.SESSION_COOKIE_NAME].value
    check(case.post('/api/v1/basework/logout', client=case.client).status_code == 200, 'обычный_выход_полной_сессии')
    case.client.cookies[settings.SESSION_COOKIE_NAME] = owner_cookie
    check(bootstrap(case.client).status_code == 401 and bootstrap(second_owner).status_code == 200, 'обычный_выход_отзывает_только_свою_сессию')
    case.client = Client(enforce_csrf_checks=True)
    login(case.owner, case.client, owner_factor)
    check(case.post('/api/v1/basework/logout-all', client=case.client).status_code == 200, 'выход_везде_полной_сессии')
    check(bootstrap(second_owner).status_code == 401, 'выход_везде_отозвал_вторую_сессию')

    # Незавершённый MFA не получает профиль; ошибка/откат не повышают уровень.
    with operator():
        Authenticator.objects.filter(user=case.owner).update(revoked_at=timezone.now())
    partial = Client(enforce_csrf_checks=True)
    case.start_login(case.owner, partial)
    check(bootstrap(partial).status_code == 403 and bootstrap(partial).json()['status'] == 'mfa_required', 'MFA_не_завершён_профиль_запрещён')
    with patch('basework.views.security.logout', side_effect=failure):
        check(case.post('/api/v1/basework/logout', client=partial).status_code == 503, 'MFA_ошибка_выхода')
    check(bootstrap(partial).json()['status'] == 'mfa_required', 'rollback_не_повысил_MFA')
    check(case.post('/api/v1/basework/logout', client=partial).status_code == 200 and bootstrap(partial).status_code == 401, 'выход_незавершённого_MFA')
    switch('migrator')
    contract()
    print(json.dumps({'проверок': len(checks), 'результат': 'PASS',
                      'commit_до_отказа_трёх_путей_секунд': round(latency, 3),
                      'SSO_и_неподключённые_приложения': 'не проверялись'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['bootstrap', 'configure', 'contract', 'scenario', 'http_smoke'])
    args = parser.parse_args()
    try:
        globals()[args.action]()
    except Exception as error:
        # Только тип/SQLSTATE: исключение БД может содержать значения SQL-параметров.
        import traceback
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                  for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'результат': 'FAIL', 'тип': type(error).__name__,
                          'sqlstate': getattr(error.__cause__, 'sqlstate', None), 'место': frames}, ensure_ascii=False))
        raise SystemExit(1) from None
    print(json.dumps({'операция': args.action, 'результат': 'PASS'}, ensure_ascii=False))
