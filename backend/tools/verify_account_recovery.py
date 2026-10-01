"""Guarded synthetic E2-05 dump/restore probe. Never changes main beta.

Requires separate authorization. Fails if either fixed database exists.
No credentials, payloads or row values are printed; no databases are deleted.
"""
import argparse
import json
import os
import secrets

import django
import psycopg
from psycopg import sql

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if os.environ["DJANGO_SETTINGS_MODULE"] != "config.settings":
    raise SystemExit("Recovery requires guarded runtime settings")
django.setup()

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.db import connections, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from accounts import services
from accounts.limits import allow_attempt
from accounts.models import AccountContact, Invitation
from ownership.models import Membership, Organization, User
from ownership.services import membership_role

SOURCE = "mw_beta_test_e2_05_recovery"
RESTORE = "mw_beta_test_e2_05_restore"
TABLES = [
    "ownership_user", "ownership_organization", "ownership_membership",
    "ownership_cabinet", "ownership_legalentity", "ownership_brand",
    "ownership_sourceconnection", "ownership_cabinetlegalentity",
    "accounts_accountcontact", "accounts_invitation", "accounts_attemptbucket",
    "accounts_authdenial", "django_session",
]


def guard():
    if settings.EFFECTIVE != {
        "environment": "beta", "mode": "test", "DB_HOST": "postgres-test",
        "DB_PORT": "5432", "DB_NAME": "mw_beta_test", "DB_USER": "mw_beta_test_runner",
    }:
        raise SystemExit("Only isolated beta test cluster is permitted")


def select_database(name):
    if name not in {SOURCE, RESTORE}:
        raise RuntimeError("Unexpected probe database")
    connection = connections["default"]
    connection.close()
    connection.settings_dict["NAME"] = name
    return connection


def seed():
    database = settings.DATABASES["default"]
    with psycopg.connect(
        host=database["HOST"], port=database["PORT"], dbname="postgres",
        user=database["USER"], password=database["PASSWORD"],
        autocommit=True, connect_timeout=5,
    ) as admin:
        if admin.execute("SELECT datname FROM pg_database WHERE datname = ANY(%s)", [[SOURCE, RESTORE]]).fetchall():
            raise RuntimeError("Probe database exists; preserve and review before another run")
        for name in [SOURCE, RESTORE]:
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER mw_beta_test_runner").format(sql.Identifier(name)))
            admin.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name)))
    connection = select_database(SOURCE)
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    with transaction.atomic():
        a = Organization.objects.create(name="synthetic-e2-05-a")
        b = Organization.objects.create(name="synthetic-e2-05-b")
        owner = User.objects.create_user("synthetic-e2-05-owner")
        Membership.objects.create(user=owner, organization=a, role="owner")
        Membership.objects.create(user=owner, organization=b, role="observer")
        for state in ["active", "pending", "blocked", "revoked"]:
            invitation = services.issue_invitation(owner, a.pk, f"synthetic-e2-05-{state}", f"{state}@example.invalid", "observer")
            if state == "active":
                token = json.loads(mail.outbox[-1].body)["token"]
                password = secrets.token_urlsafe(24)
                services.accept_invitation(token, password, password)
            elif state == "blocked":
                services.block_account(invitation.membership.user_id)
            elif state == "revoked":
                services.revoke_invitation(owner, invitation.pk)
        allow_attempt("login", "synthetic-peer", "synthetic-principal")
    mail.outbox.clear()
    print("Synthetic account source and empty restore databases prepared; neither deleted")


def snapshot(name):
    connection = select_database(name)
    result = {}
    with connection.cursor() as cursor:
        for table in TABLES:
            # All names are source constants. Whole rows compared in memory only.
            primary = {"accounts_accountcontact": "user_id", "accounts_attemptbucket": "key", "django_session": "session_key"}.get(table, "id")
            cursor.execute(f"SELECT * FROM {table} ORDER BY {primary}")
            result[table] = cursor.fetchall()
        cursor.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
        result["migrations"] = cursor.fetchall()
    return result


def verify():
    before = snapshot(SOURCE)
    if before != snapshot(RESTORE) or len(before["accounts_invitation"]) != 4:
        raise RuntimeError("Restored account snapshot mismatch")
    for name in [SOURCE, RESTORE]:
        select_database(name)
        # Behavioral checks roll back; preserved copies keep their seeded state.
        with transaction.atomic():
            owner = User.objects.get(username="synthetic-e2-05-owner")
            a = Organization.objects.get(name="synthetic-e2-05-a")
            b = Organization.objects.get(name="synthetic-e2-05-b")
            if membership_role(owner, a) != "owner" or membership_role(owner, b) != "observer":
                raise RuntimeError("Membership scopes changed")
            pending = Invitation.objects.get(membership__user__username="synthetic-e2-05-pending")
            replacement = services.reinvite(owner, pending.pk)
            token = json.loads(mail.outbox[-1].body)["token"]
            password = secrets.token_urlsafe(24)
            services.accept_invitation(token, password, password)
            if replacement.membership_id != pending.membership_id:
                raise RuntimeError("Invitation scope changed")
            try:
                services.accept_invitation(token, password, password)
            except services.AccountRejected:
                pass
            else:
                raise RuntimeError("Restored single-use guard failed")
            user = User.objects.get(pk=pending.membership.user_id)
            client = Client()
            if not client.login(username=user.username, password=password):
                raise RuntimeError("Restored Django authentication failed")
            services.request_recovery(user.username)
            reset = json.loads(mail.outbox[-1].body)["token"]
            services.confirm_recovery(user.pk, reset, password, password)
            user.refresh_from_db()
            if default_token_generator.check_token(user, reset):
                raise RuntimeError("Restored reset single-use guard failed")
            services.block_account(user.pk)
            if client.get("/auth/session").status_code != 401 or services.request_recovery(user.username):
                raise RuntimeError("Restored blocking failed")
            for attempt in [
                lambda: Invitation.objects.filter(pk=pending.pk).update(revoked_at=None),
                lambda: Invitation.objects.filter(pk=pending.pk).update(membership_id=Membership.objects.get(user=owner, organization=b).pk),
                lambda: AccountContact.objects.filter(user=user).update(email="other@example.invalid"),
            ]:
                try:
                    with transaction.atomic():
                        attempt()
                except IntegrityError:
                    pass
                else:
                    raise RuntimeError("Restored immutable guard failed")
            transaction.set_rollback(True)
    if before != snapshot(SOURCE) or before != snapshot(RESTORE):
        raise RuntimeError("Verification changed preserved snapshots")
    mail.outbox.clear()
    print("Synthetic dump/restore equality, login, recovery, blocking and immutable scopes passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["seed", "verify"])
    phase = parser.parse_args().phase
    guard()
    try:
        {"seed": seed, "verify": verify}[phase]()
    except Exception:
        # Do not emit SQL parameters, credentials, mail, identity or traceback.
        raise SystemExit("E2-05 recovery probe failed; preserve artifacts and investigate locally") from None


if __name__ == "__main__":
    main()
