"""Личный вход: новый локальный PostgreSQL, отдельные вымышленные данные источников."""
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
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from wsgiref.simple_server import make_server, WSGIRequestHandler

from tools import basework_postgresql_rehearsal as base

PROJECT = 'basework-personal-pg-20261102'
base.PROJECT = PROJECT


def scenario():
    base.guard()
    from django.conf import settings
    from django.core.exceptions import PermissionDenied
    from django.core.management import call_command
    from django.db import connection, transaction, DatabaseError
    from django.test import Client
    from ownership.models import User, Organization, Membership
    from accounts.models import AccountContact
    from basework import personal_access as personal
    from basework.tests.test_faq import DOCUMENT

    checks = []
    def check(value, name):
        base.expect(value, name)
        checks.append(name)
        print(json.dumps({'проверка': name, 'результат': 'PASS'}, ensure_ascii=False), flush=True)

    migrator = connection.settings_dict['PASSWORD']
    web = Path('/run/secrets/db_web_password').read_text().strip()
    def switch(role):
        base.expect(not connection.in_atomic_block, 'вне_транзакции')
        connection.close()
        connection.settings_dict.update(USER='mw_beta_' + role, PASSWORD=web if role == 'web' else migrator)
        with connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_setting('cluster_name')")
            base.expect(cursor.fetchone() == ('mw_beta_' + role, PROJECT), 'реальный_LOGIN_своего_кластера')

    entry = next(iter(personal.guard().values()))
    actor = entry['id']
    output = personal.OUTPUT / 'initial.txt'
    personal.execute('create', actor, output=str(output))
    code = output.read_text().strip()
    check(output.stat().st_mode & 0o777 == 0o600, 'код_только_в_закрытом_файле')
    check(not User.objects.get(pk=actor).has_usable_password(), 'начальный_пароль_отключён')
    check(not any(model.objects.exists() for model in (Organization, Membership, AccountContact)), 'без_фиктивной_организации_и_почты')
    settings.ALLOWED_HOSTS = ['testserver', 'localhost']
    settings.BASEWORK_ROOMS_WRITES = True
    client = Client(enforce_csrf_checks=True)
    password = secrets.token_urlsafe(32)
    def post(path, data):
        csrf = client.get('/auth/csrf', secure=True).json()['csrfToken']
        return client.post(path, urlencode(data), content_type='application/x-www-form-urlencoded',
                           secure=True, HTTP_ORIGIN='https://testserver', HTTP_X_CSRFTOKEN=csrf)
    def activate(value):
        return post('/auth/basework/access', {'code': value, 'new_password1': password, 'new_password2': password})
    def login():
        client.get('/auth/basework/login', secure=True)
        return post('/auth/basework/login', {'base_work_login-current_step': 'auth',
                    'auth-username': entry['username'], 'auth-password': password})
    def bootstrap():
        return client.get('/api/v1/basework/bootstrap', secure=True)

    switch('web')
    try:
        personal.guard()
    except PermissionDenied:
        check(True, 'оператор_недоступен_web')
    else:
        raise AssertionError('оператор_доступен_web')
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM basework_applicationaccess')
        check(cursor.fetchone() == (0,), 'RLS_без_подписи_не_читает_права')
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('UPDATE basework_applicationaccess SET revoked_at=CURRENT_TIMESTAMP')
    except DatabaseError:
        check(True, 'web_не_назначает_права')
    else:
        raise AssertionError('web_изменяет_права')
    check(activate(code).status_code == 200, 'активация_через_настоящий_web_LOGIN')
    check(activate(code).status_code == 400, 'повторный_код_отклонён')
    check(login().status_code == 302, 'парольный_вход_без_организации')
    check(bootstrap().json()['applications'] == [], 'нет_неявных_прав')
    check(client.get('/api/v1/basework/faq/items', secure=True).status_code == 403, 'FAQ_без_права_403')
    switch('migrator')
    personal.execute('grant', actor)
    switch('web')
    check({x['id'] for x in bootstrap().json()['applications']} == {'faq', 'rooms'}, 'только_два_раздела')

    with tempfile.TemporaryDirectory(prefix='personal-synthetic-') as tmp:
        directory = Path(tmp)
        key = directory / 'bridge.key'
        key.write_bytes(secrets.token_bytes(32))
        bindings = directory / 'bindings.json'
        os.environ.update(DATA_DIR=tmp, DEV_MODE='1', BASEWORK_BRIDGE_KEY_FILE=str(key), BASEWORK_BRIDGE_BINDINGS_FILE=str(bindings))
        sys.path.insert(0, '/rooms-source')
        import server as source
        import storage
        native = storage.add_user('personal-fixture', 'Вымышленный администратор', secrets.token_urlsafe(32), role='admin', must_change=False)
        bindings.write_text(json.dumps({'bindings': {actor: native['id']}}))
        class Quiet(WSGIRequestHandler):
            def log_message(self, *args): pass
        rooms_http = make_server('127.0.0.1', 0, source.application, handler_class=Quiet)
        class FAQ(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                body = json.dumps(DOCUMENT).encode()
                self.send_response(200 if self.path == '/api/items' else 404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        faq_http = ThreadingHTTPServer(('127.0.0.1', 0), FAQ)
        servers = [rooms_http, faq_http]
        threads = [threading.Thread(target=http.serve_forever, daemon=True) for http in servers]
        for thread in threads: thread.start()
        settings.BASEWORK_ROOMS_URL = f'http://127.0.0.1:{rooms_http.server_port}/api/basework'
        settings.BASEWORK_ROOMS_KEY_FILE = str(key)
        settings.BASEWORK_FAQ_URL = f'http://127.0.0.1:{faq_http.server_port}/api/items'
        endpoint = '/api/v1/basework/rooms/events'
        query = '?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z'
        def write(method, body, event=''):
            csrf = client.get('/auth/csrf', secure=True).json()['csrfToken']
            return getattr(client, method)(endpoint + ('/' + event if event else ''), json.dumps(body),
                content_type='application/json', secure=True, HTTP_ORIGIN='https://testserver',
                HTTP_X_CSRFTOKEN=csrf, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        try:
            result = client.get('/api/v1/basework/faq/items?q=отчет', secure=True)
            check(result.status_code == 200 and result.json()['version'] == 7 and len(result.json()['items']) == 1, 'FAQ_чтение_поиск_версия_фикстуры')
            check(client.get(endpoint + query, secure=True).status_code == 200, 'переговорки_чтение_со_своей_привязкой')
            body = {'roomId': 'big', 'title': 'Вымышленная встреча', 'start': '2026-11-02T09:00:00+03:00', 'end': '2026-11-02T10:00:00+03:00'}
            result = write('post', body)
            check(result.status_code == 201, 'создание_личным_аккаунтом')
            event = client.get(endpoint + query, secure=True).json()['events'][0]
            check(write('put', {**body, 'title': 'Изменённая вымышленная встреча', 'expectedRevision': event['revision']}, event['id']).status_code == 200, 'изменение_личным_аккаунтом')
            event = client.get(endpoint + query, secure=True).json()['events'][0]
            check(write('delete', {'expectedRevision': event['revision']}, event['id']).status_code == 200, 'отмена_личным_аккаунтом')
            settings.BASEWORK_ROOMS_WRITES = False
            check(write('post', body).status_code == 403, 'выключенная_запись_403')
            switch('migrator')
            personal.execute('revoke', actor)
            revoked = time.monotonic()
            switch('web')
            check(bootstrap().status_code == 401 and client.get(endpoint + query, secure=True).status_code == 401, 'отзыв_сессии_и_разделов')
            check(time.monotonic() - revoked < 60, 'отзыв_менее_60_секунд')
            switch('migrator')
            personal.execute('grant', actor)
            switch('web')
            check(bootstrap().status_code == 401, 'возврат_прав_не_оживляет_сессию')
            check(login().status_code == 302 and bootstrap().status_code == 200, 'новая_сессия_после_возврата_прав')
            switch('migrator')
            recovery = personal.OUTPUT / 'recovery.txt'
            personal.execute('issue-access', actor, output=str(recovery))
            switch('web')
            check(bootstrap().status_code == 401, 'восстановление_отзывает_старую_сессию')
            check(activate(recovery.read_text().strip()).status_code == 200, 'восстановление_через_web_LOGIN')
            check(bootstrap().status_code == 401, 'восстановление_не_входит_автоматически')
            check(login().status_code == 302 and bootstrap().status_code == 200, 'вход_после_восстановления')
            switch('migrator')
            race = personal.OUTPUT / 'concurrent.txt'
            personal.execute('issue-access', actor, output=str(race))
            race_code = race.read_text().strip()
            switch('web')
            barrier = threading.Barrier(2)
            def concurrent_activation(_):
                local = Client(enforce_csrf_checks=True)
                try:
                    csrf = local.get('/auth/csrf', secure=True).json()['csrfToken']
                    barrier.wait(timeout=5)
                    result = local.post('/auth/basework/access', urlencode({'code': race_code,
                        'new_password1': password, 'new_password2': password}),
                        content_type='application/x-www-form-urlencoded', secure=True,
                        HTTP_ORIGIN='https://testserver', HTTP_X_CSRFTOKEN=csrf)
                    return result.status_code
                finally:
                    connection.close()
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses = list(pool.map(concurrent_activation, range(2)))
            check(sorted(statuses) == [200, 400], 'одновременное_использование_кода_только_один_успех')
        finally:
            for http in servers: http.shutdown(); http.server_close()
            for thread in threads: thread.join(3)
            switch('migrator')
    call_command('makemigrations', check=True, dry_run=True, verbosity=0)
    base.contract()
    print(json.dumps({'результат': 'PASS', 'проверок': len(checks), 'данные': 'только синтетические'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['bootstrap', 'configure', 'contract', 'scenario'])
    action = parser.parse_args().action
    try:
        {'bootstrap': base.bootstrap, 'configure': base.configure, 'contract': base.contract, 'scenario': scenario}[action]()
    except Exception as error:
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name} for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'результат': 'FAIL', 'тип': type(error).__name__, 'sqlstate': getattr(error.__cause__, 'sqlstate', None), 'место': frames}, ensure_ascii=False))
        raise SystemExit(1) from None
