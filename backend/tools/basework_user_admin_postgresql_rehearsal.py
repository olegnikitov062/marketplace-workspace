"""Новый локальный PostgreSQL: управление пользователями через настоящий web LOGIN."""
import argparse
import json
import secrets
import traceback
import uuid
import threading
import time
from unittest.mock import patch
from pathlib import Path

from tools import basework_postgresql_rehearsal as base

PROJECT = 'basework-user-admin-pg-20261102'
base.PROJECT = PROJECT


def scenario():
    base.guard()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection, transaction, DatabaseError
    from django.test import Client
    from django.test.utils import setup_test_environment
    from django.utils import timezone
    from account_security import services as security
    from account_security.models import AccountSecurity, AccountSession, Authenticator
    from access_control.models import PlatformRoleAssignment
    from basework import personal_access as personal
    from basework.models import Administrator, ApplicationAccess
    from basework.tests.test_user_admin import login, post, ROOT
    from ownership.models import User, Membership, Organization
    from accounts.models import AccountContact
    from tools.basework_user_admin_contract import verify
    from data_isolation.context import scope, StatementSigner
    from basework import user_admin
    import psycopg

    setup_test_environment()
    settings.ALLOWED_HOSTS = ['testserver', 'localhost']
    migrator = connection.settings_dict['PASSWORD']
    web = Path('/run/secrets/db_web_password').read_text().strip()
    checks = []
    def check(value, name):
        base.expect(value, name)
        checks.append(name)
        print(json.dumps({'проверка': name, 'результат': 'PASS'}, ensure_ascii=False), flush=True)
    def switch(role):
        base.expect(not connection.in_atomic_block, 'вне_транзакции')
        connection.close()
        connection.settings_dict.update(USER='mw_beta_' + role, PASSWORD=web if role == 'web' else migrator)
        with connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_setting('cluster_name')")
            base.expect(cursor.fetchone() == ('mw_beta_' + role, PROJECT), 'реальный_LOGIN_своего_кластера')
    entry = next(iter(personal.guard().values()))
    actor_id = entry['id']
    personal.execute('create', actor_id, output=str(personal.OUTPUT / 'initial.txt'))
    password = secrets.token_urlsafe(32)
    personal.use_code((personal.OUTPUT / 'initial.txt').read_text().strip(), password, password)
    personal.execute('grant-admin', actor_id)
    personal.execute('issue-access', actor_id, output=str(personal.OUTPUT / 'admin.txt'))
    personal.use_code((personal.OUTPUT / 'admin.txt').read_text().strip(), password, password)
    actor = User.objects.get(pk=actor_id)
    check(Administrator.objects.filter(user=actor, revoked_at__isnull=True).exists()
          and PlatformRoleAssignment.objects.filter(user=actor, revoked_at__isnull=True).exists(), 'явное_назначение_администратора_оператором')
    client = Client(enforce_csrf_checks=True)
    switch('web')
    check(login(client, actor, password).status_code == 302, 'первый_вход_требует_настройки_MFA')
    check(client.get(ROOT, secure=True).status_code == 403, 'до_MFA_нет_управления')
    switch('migrator')
    factor = Authenticator.objects.create(user=actor, name='fixture', confirmed=True)
    ordinary = User.objects.create_user('ordinary-' + uuid.uuid4().hex[:8], password)
    ApplicationAccess.objects.create(user=ordinary, application='rooms')
    switch('web')
    client = Client(enforce_csrf_checks=True)
    check(login(client, actor, password, factor).status_code == 302, 'вход_с_паролем_и_MFA')
    check(client.get('/api/v1/basework/bootstrap', secure=True).json()['canManageUsers'], 'серверная_ссылка_администратору')
    check(client.get(ROOT, secure=True).status_code == 200, 'страница_управления_под_web_LOGIN')
    denied = Client(enforce_csrf_checks=True)
    check(login(denied, ordinary, password).status_code == 302, 'обычный_парольный_вход')
    check(denied.get(ROOT, secure=True).status_code == 403, 'rooms_не_даёт_управление_пользователями')
    switch('migrator')
    ordinary_session = AccountSession.objects.get(user=ordinary, revoked_at__isnull=True)
    admin_session = AccountSession.objects.get(user=actor, level='full', revoked_at__isnull=True)
    switch('web')
    def signed_denied(user, session, target, app, label):
        marker = scope.set({'kind': 'control', 'user': str(user.pk), 'session': str(session.pk)})
        try:
            try:
                with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)), connection.cursor() as cursor:
                    cursor.execute('SELECT public.basework_set_application(%s,%s,%s)', [target, app, True])
                    transaction.set_rollback(True)
            except DatabaseError as error:
                check(getattr(error.__cause__, 'sqlstate', None) == '42501', label)
            else:
                raise AssertionError(label)
        finally:
            scope.reset(marker)
    signed_denied(ordinary, ordinary_session, actor.pk, 'faq', 'подписанный_обычный_пользователь_не_назначает_права')
    signed_denied(actor, admin_session, actor.pk, 'faq', 'подписанный_администратор_не_меняет_себя')
    signed_denied(actor, admin_session, ordinary.pk, 'faq', 'подписанный_администратор_не_меняет_старые_аккаунты')
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM basework_administrator')
        check(cursor.fetchone() == (0,), 'RLS_без_подписи_скрывает_назначения_администраторов')
    for sql, params, label in [
        ('SELECT public.basework_authorize_admin(%s)', [actor.pk], 'функция_без_подписи_запрещена'),
        ('SELECT public.basework_set_application(%s,%s,%s)', [ordinary.pk, 'faq', True], 'назначение_без_подписи_запрещено'),
        ('UPDATE basework_applicationaccess SET revoked_at=CURRENT_TIMESTAMP', [], 'прямое_DML_прав_запрещено'),
        ('UPDATE basework_administrator SET revoked_at=CURRENT_TIMESTAMP', [], 'прямое_DML_администраторов_запрещено'),
    ]:
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql, params)
                transaction.set_rollback(True)
        except DatabaseError as error:
            check(getattr(error.__cause__, 'sqlstate', None) == '42501', label)
        else:
            raise AssertionError(label)
    def create_data(name):
        page = client.get(ROOT + 'new/', secure=True)
        return {'ticket': page.context['form']['ticket'].value(), 'username': name, 'applications': ['faq', 'rooms']}
    name = 'member-' + uuid.uuid4().hex[:8]
    data = create_data(name)
    check(post(client, ROOT + 'new/', data, csrf=False).status_code == 403, 'CSRF_до_изменения')
    check(post(denied, ROOT + 'new/', data).status_code == 403, 'обычный_аккаунт_не_создаёт_пользователя')
    response = post(client, ROOT + 'new/', data)
    check(response.status_code == 200, 'создание_через_web_LOGIN')
    created = response.context['account']
    code = response.context['invitation'].split('Код доступа: ')[1].split('\n')[0]
    check('Логин: ' + name in response.context['invitation'] and 'no-store' in response['Cache-Control'], 'приглашение_с_логином_без_кэша')
    check(post(client, ROOT + 'new/', data).status_code == 409, 'повтор_создания_не_дублирует_аккаунт')
    check(post(client, ROOT + 'new/', create_data(name)).status_code == 409, 'повтор_логина_запрещён')
    switch('migrator')
    check(not any(model.objects.exists() for model in (Membership, Organization, AccountContact)), 'нет_фиктивных_контактов_и_организаций')
    check(set(ApplicationAccess.objects.filter(user=created, revoked_at__isnull=True).values_list('application', flat=True)) == {'faq', 'rooms'}, 'ровно_два_назначения')
    switch('web')
    signed_denied(actor, admin_session, created.pk, 'marketplace', 'подписанный_администратор_не_выдаёт_другие_разделы')
    member = Client(enforce_csrf_checks=True)
    member_password = secrets.token_urlsafe(32)
    result = post(member, '/auth/basework/access', {'code': code, 'new_password1': member_password, 'new_password2': member_password})
    check(result.status_code == 200 and name in result.content.decode(), 'пользователь_видит_логин_после_активации')
    check(login(member, created, member_password).status_code == 302, 'вход_созданного_пользователя')
    cookie = member.cookies[settings.SESSION_COOKIE_NAME].value
    check({x['id'] for x in member.get('/api/v1/basework/bootstrap', secure=True).json()['applications']} == {'faq', 'rooms'}, 'права_видны_пользователю')
    detail = ROOT + str(created.pk) + '/'
    page = client.get(detail, secure=True)
    version = page.context['version']
    change = {'action': 'access', 'version': version, 'applications': ['faq']}
    check(post(client, detail, change).status_code == 302, 'изменение_прав_через_узкую_функцию')
    check(member.get('/api/v1/basework/bootstrap', secure=True).status_code == 401, 'отзыв_прав_завершает_сессию')
    check(post(client, detail, change).status_code == 409, 'устаревшая_форма_409')
    version = client.get(detail, secure=True).context['version']
    check(post(client, detail, {'action': 'access', 'version': version, 'applications': ['faq', 'rooms']}).status_code == 302, 'возврат_прав')
    member.cookies[settings.SESSION_COOKIE_NAME] = cookie
    check(member.get('/api/v1/basework/bootstrap', secure=True).status_code == 401, 'возврат_прав_не_оживляет_сессию')
    version = client.get(detail, secure=True).context['version']
    request = {'action': 'code', 'version': version}
    result = post(client, detail, request)
    check(result.status_code == 200, 'перевыпуск_кода')
    latest_code = result.context['invitation'].split('Код доступа: ')[1].split('\n')[0]
    check(post(client, detail, request).status_code == 409, 'повтор_перевыпуска_не_меняет_новый_код')
    check(post(member, '/auth/basework/access', {'code': latest_code, 'new_password1': member_password,
          'new_password2': member_password}).status_code == 200, 'после_повтора_первый_перевыпущенный_код_действует')
    check(code not in client.get(detail, secure=True).content.decode(), 'GET_не_возвращает_код')
    started, done, failures = threading.Event(), threading.Event(), []
    def concurrent_revoke():
        try:
            with psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_migrator', password=migrator,
                    connect_timeout=5, options='-c statement_timeout=5000 -c lock_timeout=4000') as conn:
                base.expect(conn.execute("SELECT current_setting('cluster_name')").fetchone() == (PROJECT,), 'кластер_конкурентного_отзыва')
                started.set()
                conn.execute('UPDATE basework_administrator SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=%s AND revoked_at IS NULL', [actor.pk])
            done.set()
        except Exception as error:
            failures.append(type(error).__name__)
    revoke_thread = threading.Thread(target=concurrent_revoke)
    original = user_admin.set_applications
    def during_change(*args):
        revoke_thread.start()
        base.expect(started.wait(2), 'отзыв_начался')
        time.sleep(.15)
        check(not done.is_set(), 'конкурентный_отзыв_ждёт_начатую_операцию')
        return original(*args)
    race_data = create_data('race-' + uuid.uuid4().hex[:8])
    with patch('basework.user_admin.set_applications', side_effect=during_change):
        race_result = post(client, ROOT + 'new/', race_data)
    revoke_thread.join(6)
    check(race_result.status_code == 200 and done.is_set() and not failures, 'операция_завершена_затем_отзыв_подтверждён')
    check(client.get(ROOT, secure=True).status_code == 401, 'после_конкурентного_отзыва_управление_закрыто')
    switch('migrator')
    personal.execute('revoke-admin', actor_id)
    switch('web')
    check(client.get(ROOT, secure=True).status_code == 401, 'отзыв_администратора_завершает_сессию')
    switch('migrator')
    personal.execute('grant-admin', actor_id)
    switch('web')
    check(client.get(ROOT, secure=True).status_code == 401, 'возврат_администратора_не_оживляет_сессию')
    switch('migrator')
    with connection.cursor() as cursor:
        verify(cursor)
    base.contract()
    call_command('makemigrations', check=True, dry_run=True, verbosity=0)
    print(json.dumps({'результат': 'PASS', 'проверок': len(checks), 'данные': 'только синтетические'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['bootstrap', 'configure', 'scenario'])
    action = parser.parse_args().action
    try:
        {'bootstrap': base.bootstrap, 'configure': base.configure, 'scenario': scenario}[action]()
    except Exception as error:
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name} for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'результат': 'FAIL', 'тип': type(error).__name__, 'sqlstate': getattr(error.__cause__, 'sqlstate', None), 'место': frames}, ensure_ascii=False))
        raise SystemExit(1) from None
