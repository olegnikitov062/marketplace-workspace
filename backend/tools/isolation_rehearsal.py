"""E2-08 isolated rehearsal; never accepts a main-beta cluster or old fixture.

Default: print a non-secret plan. All mutation requires an explicit action and
the new project's marker, PostgreSQL cluster identity and actual SQL identity.
"""
import argparse
import json
import os
from pathlib import Path

PROJECT = 'marketplace-e208-20261006-01a1105a'
ROOT = Path('/run/rehearsal-state')


def expect(value):
    if not value:
        raise RuntimeError('access_rehearsal_precondition')


def marker():
    expect(os.name == 'posix' and os.environ.get('E208_REHEARSAL') == PROJECT)
    path = ROOT / 'manifest.json'
    expect(path.is_file() and not path.is_symlink())
    expect(json.loads(path.read_text()) == {'project': PROJECT, 'synthetic_only': True})


def bootstrap():
    import psycopg
    import runpy
    marker()
    password = Path('/run/secrets/db_bootstrap_password').read_text().strip()
    with psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_bootstrap', password=password, connect_timeout=5) as conn:
        expect(conn.execute("SELECT current_database(), session_user, current_setting('cluster_name')").fetchone() == ('mw_beta', 'mw_beta_bootstrap', PROJECT))
        expect(conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone() == (0,))
        expect(conn.execute("SELECT count(*) FROM pg_roles WHERE rolname IN ('mw_beta_web','mw_beta_migrator')").fetchone() == (0,))
        conn.execute('REVOKE TEMPORARY ON DATABASE mw_beta FROM PUBLIC')
    runpy.run_module('tools.bootstrap_roles', run_name='__main__')
    # Main migrator intentionally lacks database CREATE; provision only this
    # empty schema, without broadening its database-level privilege.
    with psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_bootstrap', password=password, connect_timeout=5) as conn:
        expect(conn.execute("SELECT current_setting('cluster_name')").fetchone() == (PROJECT,))
        conn.execute('CREATE SCHEMA mw_isolation AUTHORIZATION mw_beta_migrator')


def test_database():
    import psycopg
    marker()
    password = Path('/run/secrets/db_bootstrap_password').read_text().strip()
    with psycopg.connect(host='postgres', dbname='mw_beta', user='mw_beta_bootstrap', password=password,
                         connect_timeout=5, autocommit=True) as conn:
        expect(conn.execute("SELECT current_setting('cluster_name')").fetchone() == (PROJECT,))
        expect(conn.execute("SELECT count(*) FROM pg_database WHERE datname='test_mw_beta'").fetchone() == (0,))
        conn.execute('CREATE DATABASE test_mw_beta OWNER mw_beta_migrator')
        conn.execute('REVOKE ALL ON DATABASE test_mw_beta FROM PUBLIC')


def guard():
    marker()
    expect(os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings') == 'config.settings')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.db import connection
    from django.conf import settings
    from account_security.operator import require_operator_process
    require_operator_process()
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('cluster_name')")
        expect(cursor.fetchone() == (PROJECT,))
    expect(settings.ACCESS_CONTROL_ENABLED)
    expect(settings.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend')


def configure():
    guard()
    from django.core.management import call_command
    from django.db import connection, transaction
    from tools import access_web_grants as acl
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.django_migrations')")
        expect(cursor.fetchone() == (None,))
    call_command('migrate', interactive=False, verbosity=0)
    with transaction.atomic(), connection.cursor() as cursor:
        # This fresh isolated cluster has no earlier ACL/work to preserve.
        cursor.execute('REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM mw_beta_web')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM mw_beta_web')
        for table in acl.READ_TABLES:
            cursor.execute(f'GRANT SELECT ON public.{table} TO mw_beta_web')
        acl.apply_fresh(cursor, acl.MAIN_ROLE)
        from tools.isolation_web_contract import apply
        apply(cursor, Path('/run/secrets/isolation_signing_key').read_bytes())


def scenario():
    guard()
    from django.conf import settings
    from django.db import connection, transaction
    from django.test import Client
    from ownership.models import User, Organization
    from access_control.tests.test_http import AccessHTTPTests
    from access_control.models import Grant
    from tools import access_web_grants as acl
    expect(not User.objects.exists() and not Organization.objects.exists())
    settings.ALLOWED_HOSTS = ['testserver', 'localhost', 'web']
    case = AccessHTTPTests('test_default_deny_and_four_independent_actions')
    # Fixture is operator-created; all requests below reconnect as real web LOGIN.
    case.setUp()
    from django.core.management import call_command
    from account_security.models import Authenticator
    from accounts.models import AccountContact
    from access_control.models import PlatformRoleAssignment
    from django.utils import timezone
    platform_user = User.objects.create_user('synthetic-platform-runtime', case.password)
    AccountContact.objects.create(user=platform_user, email='platform-runtime@example.invalid', activated_at=timezone.now())
    Authenticator.objects.create(user=platform_user, name='synthetic', confirmed=True)
    # Actual guarded migrator command, not a patched operator guard.
    call_command('manage_access_operator', 'assign-platform', str(platform_user.pk), verbosity=0)
    assignment = PlatformRoleAssignment.objects.get(user=platform_user, revoked_at__isnull=True)
    call_command('manage_access_operator', 'grant-platform', str(assignment.pk),
        organization_id=str(case.a.pk), resource='synthetic_record', action='view', cabinet_id=str(case.ca.pk), verbosity=0)
    support_grant = Grant.objects.get(platform=assignment)
    Grant.objects.create(organization=case.b,membership=case.mb,cabinet=case.cb,
                         resource='synthetic_record',action='view')
    factors = {str(u.pk): Authenticator.objects.filter(user=u, confirmed=True, revoked_at__isnull=True).first()
               for u in (case.owner, case.member, platform_user)}
    settings.SECURITY_DOWNLOAD_PROBE = True
    connection.close()
    connection.settings_dict['USER'] = 'mw_beta_web'
    connection.settings_dict['PASSWORD'] = Path('/run/secrets/db_web_password').read_text().strip()
    with connection.cursor() as cursor:
        cursor.execute('SELECT session_user,current_user')
        expect(cursor.fetchone() == ('mw_beta_web', 'mw_beta_web'))
        acl.verify_privileges(cursor, acl.MAIN_ROLE, True)
        acl.verify_guards(cursor, acl.MAIN_ROLE, True)
    case.client = Client(enforce_csrf_checks=True)
    case.member_client = Client(enforce_csrf_checks=True)
    def synthetic_login(user, client):
        from unittest.mock import patch
        result = case.start_login(user, client)
        factor = factors[str(user.pk)]
        if factor is not None:
            code, now = case.otp(factor)
            with patch('django_otp.plugins.otp_totp.models.time.time', return_value=now):
                result = case.post('/auth/mfa/login/', {'personal_login-current_step': 'token',
                    'token-otp_token': code, 'token-remember': ''}, client)
        expect(result.status_code == 302)
        expect(client.get('/auth/session', secure=True).status_code == 200)
    synthetic_login(case.owner, case.client)
    synthetic_login(case.member, case.member_client)
    expect(case.member_client.get(case.url(), secure=True).status_code == 403)
    data = {'membership_id': str(case.mm.pk), 'resource': 'synthetic_record', 'action': 'export', 'cabinet_id': str(case.ca.pk)}
    response = case.post(case.org_url('grants/'), data)
    expect(response.status_code == 201)
    grant_id = response.json()['grant_id']
    permit = case.export()
    expect(case.download(permit).status_code == 200)
    expect(case.member_client.get(case.url(), secure=True).status_code == 403)
    expect(case.post(case.org_url(f'grants/{grant_id}/revoke/')).status_code == 200)
    expect(case.post(case.org_url('grants/'), data).status_code == 201)
    expect(case.download(permit).status_code == 403)
    expect(case.post(case.url(suffix='change/'), {'value': '3'}, csrf=False).status_code == 403)
    platform_client = Client(enforce_csrf_checks=True)
    synthetic_login(platform_user, platform_client)
    expect(platform_client.get(case.url(), secure=True).status_code == 403)
    opened = case.post(case.org_url('support/'), {'grant_id': str(support_grant.pk), 'reason': 'synthetic_diagnostic'}, platform_client)
    expect(opened.status_code == 201)
    expect(platform_client.get(case.url(), secure=True).status_code == 200)
    expect(case.post(case.url(suffix='export/'), client=platform_client).status_code == 403)
    expect(case.post(case.org_url('support/' + opened.json()['support_id'] + '/close/'), client=platform_client).status_code == 200)
    expect(platform_client.get(case.url(), secure=True).status_code == 403)
    negatives = [
        'CREATE TABLE access_forbidden(id integer)',
        'CREATE TEMP TABLE access_forbidden(id integer)',
        'UPDATE ownership_user SET is_active=false',
        'UPDATE ownership_membership SET organization_id=organization_id',
        'UPDATE access_control_grant SET action=action',
        'UPDATE access_control_platformroleassignment SET revoked_at=CURRENT_TIMESTAMP',
        'DELETE FROM access_control_grant',
        'TRUNCATE access_control_grant CASCADE',
        'UPDATE django_migrations SET name=name',
        'SET ROLE mw_beta_migrator',
    ]
    from django.db import DatabaseError
    for statement in negatives:
        rejected = False
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(statement)
                # An unexpected success must still roll back the probe.
                transaction.set_rollback(True)
        except DatabaseError as error:
            rejected = getattr(error.__cause__, 'sqlstate', None) == '42501'
        expect(rejected)
    with connection.cursor() as cursor:
        acl.verify_privileges(cursor, acl.MAIN_ROLE, True)
    from tools.isolation_sql_probe import run
    run(case)
    print(json.dumps({'limited_login_http': 'PASS', 'sql_denials': len(negatives), 'old_link_stays_revoked': True}))


def quarantine():
    guard()
    from account_security.services import quarantine_restored_access
    quarantine_restored_access()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'bootstrap', 'test_database', 'configure', 'scenario', 'quarantine'], nargs='?', default='plan')
    args = parser.parse_args()
    if args.action == 'plan':
        print(json.dumps({'project': PROJECT, 'default': 'no operations', 'server_authorization_required': True}))
    else:
        try:
            globals()[args.action]()
        except Exception:
            raise SystemExit('E2-08 isolated operation failed; preserve resources; no details disclosed') from None
        print('E2-08 isolated operation completed')
