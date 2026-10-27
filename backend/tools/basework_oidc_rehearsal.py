"""Проверки OIDC через HTTPS на синтетическом провайдере локального стенда."""
import argparse
import json
from pathlib import Path
from tools.basework_postgresql_rehearsal import guard, expect


def configure():
    guard()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection, transaction
    expect(settings.BASEWORK_OIDC_ENABLED, 'OIDC_стенд')
    call_command('migrate', interactive=False, verbosity=0)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('GRANT SELECT ON basework_oidcattempt TO mw_beta_web')
        cursor.execute('GRANT EXECUTE ON FUNCTION basework_oidc_transition(text,jsonb) TO mw_beta_web')
        from tools.basework_oidc_contract import verify
        verify(cursor)
        from tools.financial_web_contract import verify as previous
        previous(cursor)
    call_command('makemigrations', dry_run=True, check=True, verbosity=0)


def scenario():
    guard()
    import time
    import uuid
    import hashlib
    import re
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import parse_qs, urlsplit, urlencode
    from unittest.mock import patch
    import requests
    from django.conf import settings
    from django.db import connection, transaction, DatabaseError
    from django.utils import timezone
    from accounts.models import AccountContact, AttemptBucket
    from ownership.models import User, Membership
    from account_security.models import AccountSession, Authenticator
    from account_security import services as security
    from access_control.tests.test_http import AccessHTTPTests
    from basework.models import IdentityBinding, OIDCAttempt, FederatedSession, ApplicationAccess
    from basework.oidc_configuration import current
    provider = current()
    ISSUER, CA, CALLBACK = provider.issuer, provider.ca_file, provider.redirect_uri
    from basework.oidc import COOKIE
    from data_isolation.context import StatementSigner
    from tools.basework_oidc_contract import verify
    from datetime import timedelta

    checks = []
    def check(value, name):
        expect(value, name)
        checks.append(name)
        print(json.dumps({'проверка': name, 'результат': 'PASS'}, ensure_ascii=False), flush=True)

    with connection.cursor() as cursor:
        verify(cursor)
    # Новый прогон получает новое окно лимитов только в синтетической базе.
    AttemptBucket.objects.update(window_start=timezone.now()-timedelta(minutes=16))
    settings.ALLOWED_HOSTS = ['testserver','web','localhost']
    settings.SECURITY_DOWNLOAD_PROBE = True
    prefix = uuid.uuid4().hex[:10]
    create_user, create_contact = User.objects.create_user, AccountContact.objects.create
    def new_user(username, *args, **kwargs):
        return create_user(prefix+'-'+username, *args, **kwargs)
    def new_contact(**kwargs):
        kwargs['email'] = prefix+'-'+kwargs['email']
        return create_contact(**kwargs)
    case = AccessHTTPTests('test_default_deny_and_four_independent_actions')
    with patch.object(User.objects, 'create_user', side_effect=new_user), patch.object(AccountContact.objects, 'create', side_effect=new_contact):
        case.setUp()
    member_binding = IdentityBinding.objects.create(user=case.member, issuer=ISSUER, subject=prefix+'-member')
    owner_binding = IdentityBinding.objects.create(user=case.owner, issuer=ISSUER, subject=prefix+'-owner')
    ApplicationAccess.objects.create(user=case.member, application='marketplace')
    case.grant('view', case.ca)
    users_before = User.objects.count()
    base = CALLBACK.removesuffix('/auth/basework/oidc/callback')
    login_url = base+'/auth/basework/oidc/login'

    def session():
        s = requests.Session()
        s.trust_env = False
        s.verify = CA
        return s

    def req(s, method, url, **kwargs):
        return s.request(method, url, allow_redirects=False, timeout=12, **kwargs)

    def start(subject=None, mode='valid'):
        s = session()
        response = req(s, 'GET', login_url)
        expect(response.status_code == 200, 'страница_входа')
        response = req(s, 'POST', login_url, headers={'Origin': base, 'X-CSRFToken': s.cookies.get('csrftoken')})
        expect(response.status_code == 302, 'начало_OIDC')
        q = parse_qs(urlsplit(response.headers['Location']).query)
        expect(q['redirect_uri'] == [CALLBACK] and q['response_type'] == ['code']
               and q['scope'] == ['openid'] and q['code_challenge_method'] == ['S256'], 'параметры_Authorization_Code')
        expect('Secure' in response.headers['Set-Cookie'] and 'HttpOnly' in response.headers['Set-Cookie']
               and 'SameSite=Lax' in response.headers['Set-Cookie'], 'cookie_попытки')
        authorize_url=response.headers['Location']
        if mode == 'pkce':
            altered={**q,'code_challenge':['0'*43]}
            authorize_url=authorize_url.split('?')[0]+'?'+urlencode(altered,doseq=True)
        url = authorize_url+'&'+urlencode({'test_subject': subject or member_binding.subject, 'test_mode': mode})
        response = req(s, 'GET', url)
        expect(response.status_code == 302, 'провайдер_код')
        attempt = OIDCAttempt.objects.get(state_hash=security.digest(q['state'][0]))
        return s, response.headers['Location'], attempt

    def callback(s, url):
        return req(s, 'GET', url)

    def bootstrap(s):
        return req(s, 'GET', base+'/api/v1/basework/bootstrap')

    def browser_proof(s):
        return next(c.value for c in s.cookies if c.name == COOKIE)

    from dataclasses import replace
    from django.test import override_settings
    from basework.oidc_client import RestrictedSession
    from requests.exceptions import SSLError
    with override_settings(BASEWORK_OIDC_CONFIG=replace(provider, ca_file=None)), RestrictedSession() as transport:
        denied = False
        try:
            transport.request('GET', provider.discovery, withhold_token=True)
        except SSLError:
            denied = True
        check(denied, 'TLS_неизвестный_CA_отвергнут_реальным_транспортом')

    s = session()
    check(req(s, 'GET', base+'/api/v1/health/ready').status_code == 200, 'runtime_ready_с_OIDC_контрактом')
    check(req(s, 'POST', login_url).status_code == 403, 'начало_входа_требует_CSRF')
    s, url, attempt = start()
    response = callback(s, url)
    check(response.status_code == 302 and response.headers['Location'] == '/basework/profile', 'полный_HTTPS_вход_через_Authlib')
    data = bootstrap(s)
    check(data.status_code == 200 and data.json()['session']['user']['id'] == str(case.member.pk), 'OIDC_сохраняет_существующий_UUID')
    record = AccountSession.objects.get(session_hash=security.digest(s.cookies.get(settings.SESSION_COOKIE_NAME)))
    check(FederatedSession.objects.filter(session=record, binding=member_binding).exists(), 'OIDC_привязал_ровно_свою_сессию')
    check(record.password_confirmed_at is None and not security.fresh(record, factor=False), 'OIDC_не_подменяет_локальное_подтверждение_пароля')
    check(req(s,'GET',base+case.url()).status_code == 200 and req(s,'GET',base+case.url(case.rb)).status_code == 403, 'OIDC_сохраняет_прикладную_изоляцию')
    check(callback(s,url).status_code == 403, 'последовательный_повтор_callback_закрыт')
    check('no-store' in response.headers.get('Cache-Control','') and response.headers.get('Referrer-Policy') == 'no-referrer', 'callback_без_кэша_и_referrer')

    wrong, url, attempt = start()
    stranger = session()
    check(callback(stranger,url).status_code == 403, 'callback_чужого_браузера_закрыт')
    attempt.refresh_from_db()
    check(attempt.claimed_at is None, 'чужой_браузер_не_погасил_попытку')
    altered=parse_qs(urlsplit(url).query)
    altered['state']=['x'*43]
    check(callback(wrong,CALLBACK+'?'+urlencode(altered,doseq=True)).status_code == 403, 'неизвестный_state_отвергнут')
    check(callback(wrong,url).status_code == 302, 'исходный_браузер_может_закончить_попытку')

    duplicate, url, attempt = start()
    check(callback(duplicate,url+'&state=duplicate').status_code == 403, 'двойной_state_запрещён')
    attempt.refresh_from_db()
    check(attempt.claimed_at is None, 'неоднозначный_callback_не_погасил_state')
    cancelled, url, attempt = start()
    check(callback(cancelled,url+'&error=access_denied').status_code == 403, 'отказ_пользователя_на_провайдере')
    attempt.refresh_from_db()
    check(attempt.claimed_at is not None and callback(cancelled,url).status_code == 403, 'отмена_не_возрождает_state')

    import secrets
    from basework.oidc_configuration import fingerprint
    expired_state, proof = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expired_attempt = OIDCAttempt.objects.create(state_hash=security.digest(expired_state), browser_hash=security.digest(proof),
        provider_hash=fingerprint(), nonce='synthetic', verifier='synthetic', expires_at=timezone.now()-timedelta(seconds=1))
    expired_client=session()
    expired_response=req(expired_client,'GET',CALLBACK+'?'+urlencode({'state':expired_state,'code':'synthetic'}),
                         headers={'Cookie':COOKIE+'='+proof})
    expired_attempt.refresh_from_db()
    check(expired_response.status_code == 403 and expired_attempt.claimed_at is None, 'истёкшая_попытка_отвергнута_до_обмена')

    interrupted, url, attempt = start()
    with transaction.atomic():
        User.objects.select_for_update().get(pk=case.member.pk)
        response=callback(interrupted,url)
    attempt.refresh_from_db()
    check(response.status_code == 503 and attempt.claimed_at is not None and attempt.ready_at is None,
          'блокировка_БД_после_обмена_не_возрождает_попытку')
    check(bootstrap(interrupted).status_code == 401 and callback(interrupted,url).status_code == 403,
          'сбой_финализации_без_сессии_и_повторного_обмена')

    AttemptBucket.objects.update(window_start=timezone.now()-timedelta(minutes=16))
    for mode in ('pkce','issuer','audience','nonce','missing_nonce','expired','signature','outage','redirect','timeout','cancel'):
        bad, url, attempt = start(mode=mode)
        response = callback(bad,url)
        check(response.status_code in (403,503) and bootstrap(bad).status_code == 401, 'отказ_' + mode)
        attempt.refresh_from_db()
        check(attempt.claimed_at is not None and attempt.ready_at is None and callback(bad,url).status_code == 403, 'попытка_не_возрождается_' + mode)

    AttemptBucket.objects.update(window_start=timezone.now()-timedelta(minutes=16))

    control = ISSUER.split('/login')[0]+'/__test__/discovery'
    for mode in ('issuer', 'token', 'authorize', 'jwks', 'pkce', 'algorithm', 'auth', 'redirect', 'inline'):
        control_session = session()
        expect(req(control_session, 'POST', control, data=mode).status_code == 200, 'режим_discovery')
        try:
            bad, url, attempt = start()
            response = callback(bad, url)
            if mode == 'inline':
                check(response.status_code == 302 and bootstrap(bad).status_code == 200,
                      'discovery_не_подменяет_JWKS_секрет_TLS_и_scope')
            else:
                attempt.refresh_from_db()
                check(response.status_code == 403 and bootstrap(bad).status_code == 401
                      and attempt.claimed_at is not None and attempt.ready_at is None
                      and callback(bad, url).status_code == 403, 'discovery_отказ_'+mode)
        finally:
            expect(req(control_session, 'POST', control, data='valid').status_code == 200, 'сброс_discovery')
            control_session.close()
    rotated, url, attempt = start(mode='rotation')
    check(callback(rotated, url).status_code == 302 and bootstrap(rotated).status_code == 200, 'новый_ключ_из_закреплённого_JWKS')
    AttemptBucket.objects.update(window_start=timezone.now()-timedelta(minutes=16))

    unknown, url, attempt = start(subject=case.member.username)
    check(callback(unknown,url).status_code == 403 and User.objects.count() == users_before, 'username_не_создаёт_и_не_связывает_пользователя')

    race, url, attempt = start()
    proof = browser_proof(race)
    def racing_callback():
        r = session()
        r.cookies.set(COOKIE, proof, domain='web.local', path='/', secure=True)
        return r.get(url, headers={'Cookie': COOKIE+'='+proof}, allow_redirects=False, timeout=12).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: racing_callback(), range(2)))
    check(sorted(statuses) == [302,403], 'два_параллельных_callback_ровно_один_успех')
    attempt.refresh_from_db()
    check(attempt.finished_at is not None, 'конкурентная_попытка_завершена_однократно')

    owner, url, attempt = start(subject=owner_binding.subject)
    response = callback(owner,url)
    check(response.status_code == 302 and response.headers['Location'].endswith('/oidc/mfa') and bootstrap(owner).status_code == 401, 'OIDC_не_обходим_локальный_MFA')
    factor = Authenticator.objects.get(user=case.owner,confirmed=True,revoked_at__isnull=True)
    token, _ = case.otp(factor)
    wrong_token = str((int(token)+1)%1000000).zfill(6)
    mfa_url = base+'/auth/basework/oidc/mfa'
    req(owner,'GET',mfa_url)
    headers={'Origin':base,'X-CSRFToken':owner.cookies.get('csrftoken')}
    check(req(owner,'POST',mfa_url,data={'token':token}).status_code == 403, 'MFA_требует_CSRF')
    check(req(owner,'POST',mfa_url,data={'token':wrong_token},headers=headers).status_code == 400, 'неверный_локальный_TOTP_отвергнут')
    factor.refresh_from_db()
    check(factor.throttling_failure_count > 0 and bootstrap(owner).status_code == 401, 'счётчик_MFA_сохранён_без_сессии')
    time.sleep(1.1)
    def finish_mfa():
        browser_session=session()
        browser_session.cookies.update(owner.cookies)
        response=req(browser_session,'POST',mfa_url,data={'token':token},headers=headers)
        return response.status_code,browser_session
    with ThreadPoolExecutor(max_workers=2) as pool:
        finished=list(pool.map(lambda _: finish_mfa(),range(2)))
    check(sorted(status for status,_ in finished) == [302,403], 'конкурентное_завершение_MFA_однократно')
    owner=next(browser_session for status,browser_session in finished if status == 302)
    check(bootstrap(owner).status_code == 200, 'верный_MFA_завершает_OIDC')
    check(req(owner,'POST',mfa_url,data={'token':token},headers=headers).status_code == 403, 'повтор_завершения_MFA_закрыт')

    waiting, url, attempt = start(subject=owner_binding.subject)
    check(callback(waiting,url).status_code == 302 and bootstrap(waiting).status_code == 401, 'ожидающий_MFA_ещё_без_сессии')
    from basework.services import revoke_identity
    revoke_identity(owner_binding.pk)
    check(req(waiting,'POST',mfa_url,data={'token':token},headers={'Origin':base,'X-CSRFToken':waiting.cookies.get('csrftoken')}).status_code == 403
          and bootstrap(owner).status_code == 401, 'отзыв_между_callback_и_MFA_закрывает_вход')
    Authenticator.objects.filter(user=case.owner,revoked_at__isnull=True).update(revoked_at=timezone.now())
    setup_binding=IdentityBinding.objects.create(user=case.owner,issuer=ISSUER,subject=prefix+'-setup')
    setup_client,url,attempt=start(subject=setup_binding.subject)
    response=callback(setup_client,url)
    check(response.status_code == 403 and response.json()['status'] == 'local_mfa_setup_required'
          and bootstrap(setup_client).status_code == 401, 'обязательный_ненастроенный_MFA_не_обходится')

    blocked, url, attempt = start()
    User.objects.filter(pk=case.member.pk).update(is_active=False)
    check(callback(blocked,url).status_code == 403 and bootstrap(blocked).status_code == 401, 'блокировка_между_началом_и_callback')
    User.objects.filter(pk=case.member.pk).update(is_active=True)
    revoked, url, attempt = start()
    revoke_identity(member_binding.pk)
    check(callback(revoked,url).status_code == 403 and bootstrap(s).status_code == 401, 'отзыв_привязки_закрывает_callback_и_старую_сессию')

    with connection.cursor() as cursor:
        verify(cursor)
        cursor.execute('SELECT nonce,verifier FROM basework_oidcattempt WHERE id=%s',[attempt.pk])
        encrypted=cursor.fetchone()
        check(all(value.startswith('gAAAA') for value in encrypted), 'nonce_PKCE_в_БД_зашифрованы')
    check(User.objects.count() == users_before, 'нет_автоматических_новых_пользователей')
    AttemptBucket.objects.update(window_start=timezone.now()-timedelta(minutes=16))
    limited=session()
    req(limited,'GET',login_url)
    headers={'Origin':base,'X-CSRFToken':limited.cookies.get('csrftoken')}
    statuses=[req(limited,'POST',login_url,headers=headers).status_code for _ in range(31)]
    check(statuses == [302]*30+[403], 'штатный_лимит_30_начал_входа')

    # Настоящий web LOGIN без signer не может читать или менять автомат попытки.
    connection.close()
    connection.settings_dict['USER']='mw_beta_web'
    connection.settings_dict['PASSWORD']=Path('/run/secrets/db_web_password').read_text().strip()
    with connection.cursor() as cursor:
        cursor.execute('SELECT session_user,current_user')
        check(cursor.fetchone() == ('mw_beta_web','mw_beta_web'), 'реальный_web_LOGIN_для_SQL')
        cursor.execute('SELECT count(*) FROM basework_oidcattempt')
        check(cursor.fetchone() == (0,), 'реестр_попыток_невидим_без_подписи')
    for sql in ('INSERT INTO basework_oidcattempt DEFAULT VALUES', 'UPDATE basework_oidcattempt SET claimed_at=NULL',
                'DELETE FROM basework_oidcattempt', "SELECT basework_oidc_transition('claim','{}'::jsonb)"):
        denied=False
        try:
            with transaction.atomic(),connection.cursor() as cursor:
                cursor.execute(sql)
                transaction.set_rollback(True)
        except DatabaseError as error:
            denied=getattr(error.__cause__,'sqlstate',None)=='42501'
        check(denied,'SQL_запрет_'+sql.split()[0])
    with transaction.atomic(),connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)),connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM basework_oidcattempt')
        check(cursor.fetchone()[0]>0,'реестр_читается_с_точной_подписью')
    print(json.dumps({'проверок':len(checks),'результат':'PASS','transport':'HTTPS + PostgreSQL + Gunicorn 2 workers'},ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['configure','scenario'])
    args=parser.parse_args()
    try:
        globals()[args.action]()
    except Exception as error:
        import traceback
        frames=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'результат':'FAIL','тип':type(error).__name__,'sqlstate':getattr(error.__cause__,'sqlstate',None),'место':frames},ensure_ascii=False))
        raise SystemExit(1) from None
    print(json.dumps({'операция':args.action,'результат':'PASS'},ensure_ascii=False))
