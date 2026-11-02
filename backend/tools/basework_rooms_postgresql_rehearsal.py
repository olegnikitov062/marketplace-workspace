"""Переговорки: отдельный PostgreSQL 17 и настоящий источник на временной SQLite."""
import argparse
import json
import os
import secrets
import sys
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from unittest.mock import patch
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
from socketserver import ThreadingMixIn

from tools import basework_postgresql_rehearsal as base

PROJECT = 'basework-stage5-rooms-pg-20261031'
base.PROJECT = PROJECT


def scenario():
    base.guard()
    import psycopg
    from django.conf import settings
    from django.db import connection, transaction, DatabaseError
    from django.test import Client
    from django.utils import timezone
    from accounts.models import AccountContact
    from ownership.models import User, Organization, Membership
    from basework.models import ApplicationAccess
    from basework import rooms
    from basework.tests.test_password_login import PasswordLoginTests
    from account_security.models import AccountSession

    checks, timings = [], {}
    def check(value, name):
        base.expect(value, name)
        checks.append(name)
        print(json.dumps({'проверка': name, 'результат': 'PASS'}, ensure_ascii=False), flush=True)

    migrator = connection.settings_dict['PASSWORD']
    web = Path('/run/secrets/db_web_password').read_text().strip()
    def switch(role):
        base.expect(not connection.in_atomic_block, 'переключение_вне_транзакции')
        connection.close()
        connection.settings_dict.update(USER='mw_beta_' + role, PASSWORD=web if role == 'web' else migrator)
        with connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_setting('cluster_name')")
            base.expect(cursor.fetchone() == ('mw_beta_' + role, PROJECT), 'реальный_LOGIN_своего_кластера')

    def revoke(access):
        with psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_migrator', password=migrator,
                connect_timeout=5, options='-c statement_timeout=5000 -c lock_timeout=2000') as conn:
            base.expect(conn.execute("SELECT current_setting('cluster_name')").fetchone() == (PROJECT,), 'кластер_отзыва')
            conn.execute('UPDATE basework_applicationaccess SET revoked_at=CURRENT_TIMESTAMP WHERE id=%s', [access.pk])
        return time.monotonic()

    def new_case(label):
        case = PasswordLoginTests('test_password_opens_basework_without_oidc_and_logout_revokes_session')
        case.password = secrets.token_urlsafe(32)
        suffix = uuid.uuid4().hex[:10]
        case.user = User.objects.create_user('rooms-' + label + '-' + suffix, case.password)
        AccountContact.objects.create(user=case.user, email=suffix+'@example.invalid', activated_at=timezone.now())
        org = Organization.objects.create(name='synthetic-rooms-'+suffix)
        Membership.objects.create(user=case.user, organization=org, role='observer')
        case.client = Client(enforce_csrf_checks=True)
        return case

    reader, denied, other, race, writer = [new_case(label) for label in ('reader','denied','other','race','writer')]
    access = {str(c.user.pk): ApplicationAccess.objects.create(user=c.user, application='rooms') for c in (reader,other,race,writer)}
    settings.ALLOWED_HOSTS = ['testserver','localhost']
    settings.BASEWORK_ROOMS_WRITES = True
    check(not settings.BASEWORK_OIDC_ENABLED, 'парольный_вход_без_OIDC')

    with tempfile.TemporaryDirectory(prefix='rooms-pg-synthetic-') as tmp:
        directory = Path(tmp)
        key_file = directory/'bridge.key'; key_file.write_bytes(secrets.token_bytes(32))
        bindings_file = directory/'bindings.json'
        os.environ.update(DATA_DIR=tmp, DEV_MODE='1', BASEWORK_BRIDGE_KEY_FILE=str(key_file),
                          BASEWORK_BRIDGE_BINDINGS_FILE=str(bindings_file))
        sys.path.insert(0, '/rooms-source')
        import server as source
        import storage
        native = {str(c.user.pk): storage.add_user('fixture-'+str(i), 'Вымышленный '+str(i), secrets.token_urlsafe(32), must_change=False)['id']
                  for i,c in enumerate((reader,other,race,writer))}
        bindings_file.write_text(json.dumps({'bindings':native}))
        class Quiet(WSGIRequestHandler):
            def log_message(self, *args): pass
        class Threaded(ThreadingMixIn, WSGIServer):
            daemon_threads = True
        http = make_server('127.0.0.1', 0, source.application, Threaded, Quiet)
        thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
        settings.BASEWORK_ROOMS_URL = f'http://127.0.0.1:{http.server_port}/api/basework'
        settings.BASEWORK_ROOMS_KEY_FILE = str(key_file)
        endpoint = '/api/v1/basework/rooms/events'
        query = '?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z'
        body = {'roomId':'big','title':'Вымышленная встреча','start':'2026-11-02T09:00:00+03:00','end':'2026-11-02T10:00:00+03:00'}
        calls = []
        original = rooms.exchange
        def observed(actor, method, *args):
            if method == 'GET':
                base.expect(not connection.in_atomic_block and not connection.execute_wrappers, 'чтение_вне_SQL_транзакции')
                base.expect(connection.connection.info.transaction_status == psycopg.pq.TransactionStatus.IDLE, 'PG_IDLE')
            else:
                base.expect(connection.in_atomic_block, 'запись_в_защищённой_транзакции')
            calls.append(method)
            return original(actor, method, *args)
        def get(case): return case.client.get(endpoint+query, secure=True)
        def write(case, payload=body, method='post', event='', operation=None, csrf=True):
            headers = {'HTTP_ORIGIN':'https://testserver', 'HTTP_IDEMPOTENCY_KEY':operation or str(uuid.uuid4())}
            if csrf: headers['HTTP_X_CSRFTOKEN'] = case.client.get('/auth/csrf', secure=True).json()['csrfToken']
            return getattr(case.client,method)(endpoint+('/'+event if event else ''), data=json.dumps(payload), content_type='application/json', secure=True, **headers)
        try:
            switch('web')
            with connection.cursor() as cursor:
                cursor.execute('SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user')
                check(cursor.fetchone() == (False,False,False,False), 'web_ограниченный_LOGIN')
            for case in (reader,denied,other,race,writer):
                check(case.login().status_code == 302, 'вход_'+case.user.username.split('-')[1])
            with patch('basework.rooms.exchange', side_effect=observed):
                check(Client().get(endpoint+query,secure=True).status_code == 401, 'анонимный_401')
                check(get(denied).status_code == 403 and write(denied).status_code == 403 and not calls, 'без_права_до_источника')
                check(get(reader).status_code == 200, 'чтение_через_настоящий_HTTP')
                before = len(calls)
                check(write(reader,csrf=False).status_code == 403 and len(calls)==before, 'CSRF_до_источника')
                settings.BASEWORK_ROOMS_WRITES = False
                check(write(reader).status_code == 403 and len(calls)==before, 'переключатель_только_чтения')
                settings.BASEWORK_ROOMS_WRITES = True
                operation = str(uuid.uuid4())
                created = write(reader,operation=operation)
                check(created.status_code == 201, 'создание_через_PostgreSQL_web')
                check(write(reader,operation=operation).json()==created.json(), 'повтор_без_дубликата')
                check(write(reader).status_code == 409, 'пересечение_409')
                doc = get(reader).json(); ev = doc['events'][0]
                check(len(doc['events']) == 1 and ev['mine'] and 'owner' not in ev and 'no-store' in get(reader)['Cache-Control'], 'владелец_и_без_утечки_идентификаторов')
                check(write(other,{'expectedRevision':ev['revision']},'delete',ev['id']).status_code == 403, 'чужая_бронь_защищена')
                check(write(reader,{**body,'title':'Изменено','expectedRevision':ev['revision']},'put',ev['id']).status_code == 200, 'изменение_своей_брони')
                check(write(reader,{'expectedRevision':ev['revision']},'delete',ev['id']).status_code == 409, 'устаревшая_версия_409')
                ev=get(reader).json()['events'][0]
                check(write(reader,{'expectedRevision':ev['revision']},'delete',ev['id']).status_code == 200, 'удаление_своей_брони')
                for table in base.TABLES:
                    with connection.cursor() as cursor:
                        cursor.execute(f'SELECT count(*) FROM {table}')
                        check(cursor.fetchone()==(0,), 'RLS_без_подписи_'+table)
                    try:
                        with transaction.atomic(),connection.cursor() as cursor:
                            cursor.execute(f'DELETE FROM {table}')
                            transaction.set_rollback(True)
                        refused=False
                    except DatabaseError as error:
                        refused=getattr(error.__cause__,'sqlstate',None)=='42501'
                    check(refused,'ACL_запрет_записи_'+table)
                cookie=reader.client.cookies[settings.SESSION_COOKIE_NAME].value
                committed=revoke(access[str(reader.user.pk)])
                check(get(reader).status_code==401,'отзыв_сессии_внешним_SQL')
                timings['commit_to_denied_seconds']=round(time.monotonic()-committed,6)
                check(timings['commit_to_denied_seconds']<60,'отзыв_быстрее_60с')
                before=len(calls)
                for _ in range(3):
                    reader.client.cookies[settings.SESSION_COOKIE_NAME]=cookie
                    base.expect(get(reader).status_code==401,'отозванная_cookie')
                check(len(calls)==before,'повтор_cookie_не_читает_источник')
                switch('migrator')
                check(not AccountSession.objects.filter(user=reader.user,revoked_at__isnull=True).exists(),'триггер_отозвал_все_сессии')
                ApplicationAccess.objects.create(user=reader.user,application='rooms')
                switch('web')
                reader.client.cookies[settings.SESSION_COOKIE_NAME]=cookie
                check(get(reader).status_code==401,'новое_право_не_оживляет_cookie')
                check(reader.login().status_code==302 and get(reader).status_code==200,'новый_вход_после_синтетического_назначения')
                def during_read(*args):
                    result=observed(*args)
                    revoke(access[str(race.user.pk)])
                    return result
                with patch('basework.rooms.exchange',side_effect=during_read):
                    result=get(race)
                check(result.status_code==401 and 'events' not in result.json(),'отзыв_между_чтением_и_выдачей')

                started=threading.Event(); done=threading.Event(); errors=[]
                def revoker():
                    started.set()
                    try: timings['writer_revoke_commit']=revoke(access[str(writer.user.pk)])
                    except Exception as error: errors.append(type(error).__name__)
                    finally: done.set()
                revoke_thread=threading.Thread(target=revoker)
                def during_write(*args):
                    revoke_thread.start(); base.expect(started.wait(1),'отзыв_начат')
                    time.sleep(.15)
                    check(not done.is_set(),'отзыв_ждёт_уже_начатую_запись')
                    return observed(*args)
                with patch('basework.rooms.exchange',side_effect=during_write):
                    result=write(writer)
                revoke_thread.join(6)
                check(result.status_code==201 and done.is_set() and not errors,'запись_затем_коммит_отзыва')
                check(get(writer).status_code==401 and write(writer).status_code==401,'после_отзыва_чтение_и_запись_запрещены')
                timings['writer_commit_to_denied_seconds']=round(time.monotonic()-timings.pop('writer_revoke_commit'),6)
                check(timings['writer_commit_to_denied_seconds']<60,'конкурентный_отзыв_быстрее_60с')
                check(get(other).status_code==200,'другой_пользователь_сохранил_доступ')
        finally:
            http.shutdown(); http.server_close(); thread.join(3)
            switch('migrator')
    base.contract()
    print(json.dumps({'результат':'PASS','проверок':len(checks),'время':timings,'данные':'только синтетические'},ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['bootstrap','configure','contract','legacy','scenario'])
    action=parser.parse_args().action
    try:
        {'bootstrap':base.bootstrap,'configure':base.configure,'contract':base.contract,'legacy':base.scenario,'scenario':scenario}[action]()
    except Exception as error:
        frames=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'результат':'FAIL','тип':type(error).__name__,'sqlstate':getattr(error.__cause__,'sqlstate',None),'место':frames},ensure_ascii=False))
        raise SystemExit(1) from None
    print(json.dumps({'операция':action,'результат':'PASS'},ensure_ascii=False))
