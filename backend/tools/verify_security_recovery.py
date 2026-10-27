"""Explicit new-database E2-06 recovery rehearsal; never main beta or old probes."""
import argparse
import os
import secrets
from datetime import timedelta
from unittest.mock import patch

SOURCE = "mw_beta_test_e2_06_recovery"
RESTORE = "mw_beta_test_e2_06_restore"
TABLES = (
    "ownership_user", "ownership_organization", "ownership_membership", "ownership_legalentity",
    "ownership_brand", "ownership_cabinet", "ownership_sourceconnection", "ownership_cabinetlegalentity",
    "accounts_accountcontact", "accounts_invitation", "accounts_attemptbucket", "accounts_authdenial",
    "django_session", "account_security_accountsecurity", "account_security_authenticator",
    "account_security_accountsession", "account_security_trusteddevice", "account_security_recoverycode",
    "account_security_recoverypermit", "account_security_exportpermit", "account_security_securityevent",
    "account_security_loginchallenge", "django_migrations",
)


def guard(settings, connection):
    if connection.vendor != "postgresql" or settings.EFFECTIVE != {
        "environment": "beta", "mode": "test", "DB_HOST": "postgres-test", "DB_PORT": "5432",
        "DB_NAME": "mw_beta_test", "DB_USER": "mw_beta_test_runner",
    }:
        raise RuntimeError("isolated_postgresql_test_required")


def select_database(name):
    from django.db import connection
    if name not in {SOURCE, RESTORE}:
        raise RuntimeError("unexpected_recovery_database")
    connection.close()
    connection.settings_dict["NAME"] = name
    return connection


def seed(settings, connection):
    import psycopg
    from psycopg import sql
    from django.db.migrations.executor import MigrationExecutor
    from django.contrib.auth.hashers import make_password
    from django.contrib.auth.models import AnonymousUser
    from django.test import RequestFactory, override_settings
    from django.utils import timezone
    from account_security import services
    from account_security.models import Authenticator, RecoveryCode, LoginChallenge
    from account_security.session_backend import SessionStore
    from ownership.models import User, Organization
    from tools.security_role_scenario import seed as seed_fixture, code_for
    guard(settings, connection)
    config = connection.settings_dict
    with psycopg.connect(host="postgres-test", port=5432, dbname="postgres", user="mw_beta_test_runner",
                         password=config["PASSWORD"], autocommit=True, connect_timeout=5) as admin:
        if admin.execute("SELECT datname FROM pg_database WHERE datname=ANY(%s)", [[SOURCE, RESTORE]]).fetchall():
            raise RuntimeError("recovery_name_already_occupied")
        for name in (SOURCE, RESTORE):
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER mw_beta_test_runner").format(sql.Identifier(name)))
            admin.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name)))
            admin.execute(sql.SQL("COMMENT ON DATABASE {} IS 'marketplace-workspace E2-06 synthetic recovery'").format(sql.Identifier(name)))
    connection = select_database(SOURCE)
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    fixture = seed_fixture()
    user = User.objects.get(pk=fixture["user_id"])
    state = services.state_for(user)
    device = Authenticator.objects.create(user=user, name="default", confirmed=True)
    code, now = code_for(device)
    with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
        if services.verify_factor(user.pk, code, device.pk) is None:
            raise RuntimeError("synthetic_totp_seed_failed")
    RecoveryCode.objects.create(user=user, verifier=make_password(secrets.token_urlsafe(24)))
    RecoveryCode.objects.create(user=user, verifier=make_password(secrets.token_urlsafe(24)), used_at=timezone.now())
    challenge = LoginChallenge.objects.create(user=user, version=state.version,
        credential_hash=user.get_session_auth_hash(), expires_at=timezone.now()+timedelta(minutes=5))
    request = RequestFactory().post("/auth/mfa/login/", secure=True)
    request.session = SessionStore()
    request.user = AnonymousUser()
    services.complete_login(request, user.pk, challenge.pk, device.pk, remember=True)
    with override_settings(SECURITY_DOWNLOAD_PROBE=True):
        services.issue_export_probe(user, Organization.objects.get(pk=fixture["a"]), request.security_session)
    print("E2-06 recovery seed PASS: new synthetic source and empty restore target; preserve both")


def snapshot(name):
    connection = select_database(name)
    with connection.cursor() as cursor:
        return _rows(cursor)


def _rows(cursor):
    from psycopg import sql
    result = {}
    for table in TABLES:
        cursor.execute(sql.SQL("SELECT * FROM {} ORDER BY 1").format(sql.Identifier(table)))
        result[table] = cursor.fetchall()
    return result


def verify(settings, connection):
    from cryptography.fernet import Fernet
    from django.core.exceptions import ImproperlyConfigured
    from django.db import transaction
    from django.test import override_settings
    from account_security import services
    from account_security.models import Authenticator, AccountSession, RecoveryCode, TrustedDevice, AccountSecurity
    from ownership.models import Membership
    from tools.security_role_scenario import code_for
    guard(settings, connection)
    original = snapshot(SOURCE)
    if original != snapshot(RESTORE):
        raise RuntimeError("restored_rows_or_migrations_differ")
    for name in (SOURCE, RESTORE):
        select_database(name)
        with transaction.atomic():
            device = Authenticator.objects.get(confirmed=True, revoked_at__isnull=True)
            with override_settings(MFA_TEST_KEY=Fernet.generate_key()):
                try:
                    Authenticator.objects.get(pk=device.pk)
                except ImproperlyConfigured:
                    pass
                else:
                    raise RuntimeError("wrong_key_did_not_fail_closed")
            code, now = code_for(device)
            with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
                if services.verify_factor(device.user_id, code, device.pk) is None:
                    raise RuntimeError("restored_totp_failed")
                if services.verify_factor(device.user_id, code, device.pk) is not None:
                    raise RuntimeError("restored_totp_replay")
            before = list(Membership.objects.order_by("pk").values_list("id", "user_id", "organization_id", "role", "state"))
            services.quarantine_restored_access()
            if (AccountSession.objects.filter(revoked_at__isnull=True).exists()
                    or TrustedDevice.objects.filter(revoked_at__isnull=True).exists()
                    or RecoveryCode.objects.filter(used_at__isnull=True).exists()
                    or AccountSecurity.objects.filter(recovery_required=False).exists()
                    or before != list(Membership.objects.order_by("pk").values_list("id", "user_id", "organization_id", "role", "state"))):
                raise RuntimeError("restore_quarantine_failed")
            transaction.set_rollback(True)
    if snapshot(SOURCE) != original or snapshot(RESTORE) != original:
        raise RuntimeError("recovery_probe_changed_preserved_snapshots")
    print("E2-06 restore PASS: rows/migrations equal; separate-key decryption, replay denial and quarantine verified; snapshots preserved")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["seed", "verify"])
    action = parser.parse_args().action
    if os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings") != "config.settings":
        raise SystemExit("Guarded runtime settings required")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    try:
        {"seed": seed, "verify": verify}[action](settings, connection)
    except Exception as error:
        raise SystemExit(f"E2-06 recovery FAIL: {type(error).__name__}; preserve resources; values omitted") from None


if __name__ == "__main__":
    main()
