"""FAQ на отдельном локальном PostgreSQL: парольный вход, RLS и конкурентный отзыв."""
import argparse
import json
import secrets
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from tools import basework_postgresql_rehearsal as base

PROJECT = 'basework-stage4-faq-pg-20261029'
# Переиспользуем прежний строгий контракт, закрепляя отдельный кластер этой приёмки.
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
    from basework import faq
    from basework.tests.test_password_login import PasswordLoginTests
    from account_security.models import AccountSession

    checks, timings = [], {}
    def check(value, name):
        base.expect(value, name)
        checks.append(name)
        print(json.dumps({'проверка': name, 'результат': 'PASS'}, ensure_ascii=False), flush=True)

    migrator_password = connection.settings_dict['PASSWORD']
    web_password = Path('/run/secrets/db_web_password').read_text().strip()
    def switch(role):
        base.expect(not connection.in_atomic_block, 'переключение_вне_транзакции')
        connection.close()
        connection.settings_dict.update(USER='mw_beta_' + role,
            PASSWORD=web_password if role == 'web' else migrator_password)
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_user,session_user,current_database(),current_setting(\'cluster_name\')')
            base.expect(cursor.fetchone() == ('mw_beta_' + role, 'mw_beta_' + role, 'mw_beta', PROJECT), 'реальный_LOGIN')

    @contextmanager
    def operator():
        switch('migrator')
        try:
            yield
        finally:
            switch('web')

    def separate_operator():
        conn = psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_migrator',
            password=migrator_password, connect_timeout=5,
            options='-c statement_timeout=5000 -c lock_timeout=2000')
        base.expect(conn.execute("SELECT current_setting('cluster_name'),session_user").fetchone()
            == (PROJECT, 'mw_beta_migrator'), 'отдельное_соединение_только_своего_кластера')
        return conn

    def new_case(label):
        case = PasswordLoginTests('test_password_opens_basework_without_oidc_and_logout_revokes_session')
        case.password = secrets.token_urlsafe(32)
        suffix = uuid.uuid4().hex[:10]
        case.user = User.objects.create_user('faq-' + label + '-' + suffix, case.password)
        AccountContact.objects.create(user=case.user, email=suffix + '@example.invalid', activated_at=timezone.now())
        organization = Organization.objects.create(name='synthetic-faq-' + suffix)
        Membership.objects.create(user=case.user, organization=organization, role='observer')
        case.client = Client(enforce_csrf_checks=True)
        return case

    reader, denied, other, race = [new_case(label) for label in ('reader', 'denied', 'other', 'race')]
    access = ApplicationAccess.objects.create(user=reader.user, application='faq')
    ApplicationAccess.objects.create(user=other.user, application='faq')
    race_access = ApplicationAccess.objects.create(user=race.user, application='faq')
    settings.ALLOWED_HOSTS = ['testserver', 'localhost']
    base.expect(not settings.BASEWORK_OIDC_ENABLED, 'OIDC_отключён')
    switch('web')
    with connection.cursor() as cursor:
        cursor.execute('SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user')
        check(cursor.fetchone() == (False, False, False, False), 'web_не_superuser_не_BYPASSRLS_без_создания_ролей_и_БД')
        cursor.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                       "WHERE n.nspname='public' AND c.relrowsecurity AND c.relforcerowsecurity")
        force_rls = cursor.fetchone()[0]
        check(force_rls >= 30, 'FORCE_RLS_включён_на_таблицах')

    for case in (reader, denied, other, race):
        response = case.login()
        check(response.status_code == 302 and response['Location'] == '/basework/', 'парольный_вход_' + case.user.username.split('-')[1])

    document = {'version': 11, 'updatedAt': '2026-10-29T12:00:00+03:00',
        'people': [{'name': 'Синтетический сотрудник', 'role': 'Склад'}],
        'items': [{'id': 'q-1', 'cat': 'Поставки', 'q': 'Кому передать отчёт?',
                   'contacts': [['Синтетический сотрудник', 'После сверки']]},
                  {'id': 'q-2', 'cat': 'Другое', 'q': 'Вопрос без ответственного', 'contacts': []}]}
    state = {'requests': 0, 'during_read': None, 'status': 200, 'headers_safe': True}
    class Source(BaseHTTPRequestHandler):
        def do_GET(self):
            state['requests'] += 1
            state['headers_safe'] &= not any(self.headers.get(key) for key in ('Cookie', 'Authorization', 'X-Admin-Key'))
            try:
                if state['during_read']:
                    state['during_read']()
                payload = json.dumps(document).encode()
                self.send_response(state['status'])
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as error:
                state['source_error'] = type(error).__name__
                self.send_error(500)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Source)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    settings.BASEWORK_FAQ_URL = f'http://127.0.0.1:{server.server_port}/api/items'
    endpoint = '/api/v1/basework/faq/items'
    original_read = faq.read_source
    observations = []
    def observed_read():
        base.expect(not connection.in_atomic_block and connection.get_autocommit(), 'сеть_без_транзакции')
        base.expect(not connection.execute_wrappers, 'сеть_без_SQL_signer')
        base.expect(connection.connection.info.transaction_status == psycopg.pq.TransactionStatus.IDLE, 'PostgreSQL_IDLE_при_чтении')
        observations.append(True)
        return original_read()
    def get(case, query=''):
        return case.client.get(endpoint + query, secure=True)
    def no_data(response):
        return 'items' not in response.json() and 'people' not in response.json()
    def raw_revoke(access_id):
        with separate_operator() as conn:
            conn.execute('UPDATE basework_applicationaccess SET revoked_at=CURRENT_TIMESTAMP WHERE id=%s', [access_id])
        return time.monotonic()

    try:
        with patch('basework.faq.read_source', side_effect=observed_read):
            check(Client().get(endpoint, secure=True).status_code == 401, 'анонимный_401')
            denied_response = get(denied)
            check(denied_response.status_code == 403 and no_data(denied_response) and state['requests'] == 0,
                  'без_права_403_до_источника')
            response = get(reader)
            check(response.status_code == 200 and response.json() == faq.search(document), 'FAQ_полное_совпадение_через_PostgreSQL_web')
            check('no-store' in response['Cache-Control'], 'данные_не_кэшируются')
            check(get(reader, '?q=ОТЧЕТ').json()['items'] == [document['items'][0]], 'поиск_е_ё_регистр')
            check(get(reader, '?q=сверки&category=Поставки').json()['items'] == [document['items'][0]], 'поиск_контактов_и_категории')
            check(get(reader, '?q=несуществующий').json()['items'] == [], 'пустая_выдача')
            token = reader.client.get('/auth/csrf', secure=True).json()['csrfToken']
            before = state['requests']
            for method in ('post', 'put', 'patch', 'delete'):
                result = getattr(reader.client, method)(endpoint, data='{}', content_type='application/json', secure=True,
                    HTTP_ORIGIN='https://testserver', HTTP_X_CSRFTOKEN=token)
                check(result.status_code == 405, 'запрет_' + method.upper() + '_с_CSRF')
            check(state['requests'] == before, 'запись_не_обращается_к_источнику')

            for table in base.TABLES:
                with connection.cursor() as cursor:
                    cursor.execute(f'SELECT count(*) FROM {table}')
                    check(cursor.fetchone() == (0,), 'без_подписи_RLS_' + table)
                for sql in (f'INSERT INTO {table} DEFAULT VALUES', f'DELETE FROM {table}',
                            f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY'):
                    refused = False
                    try:
                        with transaction.atomic(), connection.cursor() as cursor:
                            cursor.execute(sql)
                            transaction.set_rollback(True)
                    except DatabaseError as error:
                        refused = getattr(error.__cause__, 'sqlstate', None) == '42501'
                    base.expect(refused, 'ACL_запрет_мутации_или_отключения_RLS')
                check(True, 'ACL_без_записи_и_отключения_RLS_' + table)

            old_cookie = reader.client.cookies[settings.SESSION_COOKIE_NAME].value
            committed = raw_revoke(access.pk)
            result = get(reader)
            latency = time.monotonic() - committed
            timings['commit_to_faq_denied_seconds'] = round(latency, 6)
            check(result.status_code == 401 and no_data(result) and latency < 60, 'отзыв_из_другого_соединения_менее_60с')
            before = state['requests']
            for _ in range(3):
                reader.client.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
                result = get(reader)
                base.expect(result.status_code == 401 and no_data(result), 'повтор_cookie_закрыт')
            check(state['requests'] == before, 'три_повтора_отозванной_cookie_без_чтения')
            with operator():
                check(AccountSession.objects.filter(user=reader.user, revoked_at__isnull=True).count() == 0,
                      'триггер_PostgreSQL_отозвал_сессии')
            check(reader.login().status_code == 302 and get(reader).status_code == 403, 'новый_парольный_вход_не_возвращает_право')
            check(get(other).status_code == 200, 'другой_пользователь_сохранил_доступ')
            with operator():
                ApplicationAccess.objects.create(user=reader.user, application='faq')
            reader.client.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
            check(get(reader).status_code == 401, 'повторное_назначение_не_оживляет_отозванную_сессию')
            check(reader.login().status_code == 302 and get(reader).status_code == 200, 'новый_вход_с_новым_синтетическим_правом')

            race_cookie = race.client.cookies[settings.SESSION_COOKIE_NAME].value
            state['during_read'] = lambda: timings.update(race_commit=raw_revoke(race_access.pk))
            result = get(race)
            timings['during_read_commit_to_denied_seconds'] = round(time.monotonic() - timings.pop('race_commit'), 6)
            check('source_error' not in state and result.status_code == 401 and no_data(result),
                  'отзыв_во_время_HTTP_чтения_запрещает_выдачу')
            check(timings['during_read_commit_to_denied_seconds'] < 60, 'конкурентный_отзыв_менее_60с')
            state['during_read'] = None
            race.client.cookies[settings.SESSION_COOKIE_NAME] = race_cookie
            check(get(race).status_code == 401, 'cookie_после_конкурентного_отзыва_не_работает')

            state['status'] = 500
            result = get(other)
            check(result.status_code == 503 and result.json() == {'status': 'source_unavailable'}, 'ошибка_источника_503_без_данных')
            state['status'] = 200
            check(get(other).status_code == 200, 'восстановление_источника_без_расширения_прав')
            check(len(observations) >= 8, 'все_чтения_вне_транзакции_с_PostgreSQL_IDLE')
            check(state['headers_safe'], 'источнику_не_переданы_ключи_или_cookie')
            with separate_operator() as conn:
                conn.execute('UPDATE ownership_user SET is_active=false WHERE id=%s', [other.user.pk])
            check(get(other).status_code == 401, 'блокировка_пользователя_в_другом_соединении')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        switch('migrator')
    base.contract()
    print(json.dumps({'результат': 'PASS', 'проверок': len(checks), 'FORCE_RLS_tables': force_rls,
        'измерения': timings, 'источник': 'синтетический_HTTP', 'Chrome': 'не проверялся'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['bootstrap', 'configure', 'contract', 'legacy', 'faq'])
    args = parser.parse_args()
    try:
        actions = {'bootstrap': base.bootstrap, 'configure': base.configure, 'contract': base.contract,
                   'legacy': base.scenario, 'faq': scenario}
        actions[args.action]()
    except Exception as error:
        print(json.dumps({'результат': 'FAIL', 'тип': type(error).__name__,
            'sqlstate': getattr(error.__cause__, 'sqlstate', None),
            'место': [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                      for frame in traceback.extract_tb(error.__traceback__)]}, ensure_ascii=False), flush=True)
        raise SystemExit(1) from None
    print(json.dumps({'операция': args.action, 'результат': 'PASS'}, ensure_ascii=False), flush=True)
