"""Explicit synthetic recovery probe, only on beta's isolated test cluster.

Run seed, then pg_dump/pg_restore through postgres-test, then verify.
Does not dump, delete databases, change main beta or read external sources.
"""
import argparse
import os

import django
import psycopg
from psycopg import sql

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if os.environ["DJANGO_SETTINGS_MODULE"] != "config.settings":
    raise SystemExit("Recovery probe requires the guarded runtime settings")
django.setup()

from django.conf import settings
from django.db import connections, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from ownership.models import (
    Organization, User, Membership, Cabinet, LegalEntity, Brand,
    SourceConnection, CabinetLegalEntity,
)
from ownership.services import observe_legal_entity, membership_role

SOURCE = "mw_beta_test_e2_04_recovery"
RESTORE = "mw_beta_test_e2_04_restore"
TABLES = [
    "ownership_user", "ownership_organization", "ownership_membership",
    "ownership_cabinet", "ownership_legalentity", "ownership_brand",
    "ownership_sourceconnection", "ownership_cabinetlegalentity",
]
database = settings.DATABASES["default"]
if settings.EFFECTIVE != {
    "environment": "beta", "mode": "test", "DB_HOST": "postgres-test",
    "DB_PORT": "5432", "DB_NAME": "mw_beta_test", "DB_USER": "mw_beta_test_runner",
}:
    raise SystemExit("Only guarded beta test configuration is allowed")


def select_database(name):
    if name not in {SOURCE, RESTORE}:
        raise RuntimeError("Unknown synthetic recovery database")
    connection = connections["default"]
    connection.close()
    connection.settings_dict["NAME"] = name
    return connection


def seed():
    # Maintenance CONNECT/CREATEDB exists only for this own isolated test role.
    with psycopg.connect(
        host=database["HOST"], port=database["PORT"], dbname="postgres",
        user=database["USER"], password=database["PASSWORD"],
        autocommit=True, connect_timeout=5,
    ) as admin:
        existing = admin.execute("SELECT datname FROM pg_database WHERE datname = ANY(%s)", [[SOURCE, RESTORE]]).fetchall()
        if existing:
            raise SystemExit("Recovery database already exists; preserve it and choose a reviewed new run")
        for name in [SOURCE, RESTORE]:
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER mw_beta_test_runner").format(sql.Identifier(name)))
            admin.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name)))
    connection = select_database(SOURCE)
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    with transaction.atomic():
        a = Organization.objects.create(name="synthetic-recovery-a")
        b = Organization.objects.create(name="synthetic-recovery-b")
        user = User.objects.create_user("synthetic-recovery-user")
        Membership.objects.create(organization=a, user=user, role="owner")
        Membership.objects.create(organization=b, user=user, role="observer")
        cabinet = Cabinet.objects.create(organization=a, name="synthetic-recovery-a", marketplace="synthetic")
        Cabinet.objects.create(organization=b, name="synthetic-recovery-b", marketplace="synthetic")
        first = LegalEntity.objects.create(organization=a, name="synthetic-first")
        second = LegalEntity.objects.create(organization=a, name="synthetic-second")
        LegalEntity.objects.create(organization=b, name="synthetic-foreign")
        Brand.objects.create(organization=a, name="synthetic-brand")
        SourceConnection.objects.create(organization=a, cabinet=cabinet, source_type="synthetic", seller_identity="synthetic-seller")
        observe_legal_entity(cabinet, first)
        observe_legal_entity(cabinet, second)
        first.archive()
        cabinet.archive()
    print("Synthetic recovery databases created and source seeded; neither was deleted")


def snapshot(name):
    connection = select_database(name)
    result = {}
    with connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(f"SELECT * FROM {table} ORDER BY id")
            result[table] = cursor.fetchall()
        cursor.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
        result["migrations"] = cursor.fetchall()
    return result


def verify():
    before, after = snapshot(SOURCE), snapshot(RESTORE)
    if before != after or len(after["ownership_cabinetlegalentity"]) != 2:
        raise SystemExit("Synthetic restore contents mismatch")
    for name in [SOURCE, RESTORE]:
        select_database(name)
        a = Organization.objects.get(name="synthetic-recovery-a")
        b = Organization.objects.get(name="synthetic-recovery-b")
        user = User.objects.get(username="synthetic-recovery-user")
        if membership_role(user, a) != "owner" or membership_role(user, b) != "observer":
            raise SystemExit("Restored membership scopes differ")
        cabinet = Cabinet.objects.get(organization=a)
        foreign = Cabinet.objects.get(organization=b)
        if not cabinet.archived_at or CabinetLegalEntity.objects.filter(observed_until__isnull=True).count() != 1:
            raise SystemExit("Restored archive/history mismatch")
        try:
            with transaction.atomic():
                SourceConnection.objects.bulk_create([
                    SourceConnection(organization=a, cabinet=foreign, source_type="synthetic", seller_identity="synthetic")
                ])
        except IntegrityError:
            pass
        else:
            raise SystemExit("Composite FK not enforced after restore")
        historical = CabinetLegalEntity.objects.get(observed_until__isnull=False)
        current = CabinetLegalEntity.objects.get(observed_until__isnull=True)
        try:
            with transaction.atomic():
                CabinetLegalEntity.objects.filter(pk=historical.pk).update(legal_entity_id=current.legal_entity_id)
        except IntegrityError:
            pass
        else:
            raise SystemExit("History trigger not enforced after restore")
        try:
            with transaction.atomic(), connections["default"].cursor() as cursor:
                cursor.execute("DELETE FROM ownership_cabinetlegalentity WHERE id = %s", [historical.pk])
        except IntegrityError:
            pass
        else:
            raise SystemExit("Archive/delete trigger not enforced after restore")
    print("Synthetic dump/restore equal; membership, archive, composite FK and history guards passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["seed", "verify"])
    phase = parser.parse_args().phase
    {"seed": seed, "verify": verify}[phase]()


if __name__ == "__main__":
    main()
