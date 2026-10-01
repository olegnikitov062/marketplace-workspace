from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import IntegrityError, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from ownership.models import Organization, Cabinet, LegalEntity, CabinetLegalEntity
from ownership.services import observe_legal_entity


class OwnershipMigrationTests(TransactionTestCase):
    """Runs only in Django's disposable test database, never the base beta DB."""

    def test_guard_reverse_forward_preserves_archived_history(self):
        org = Organization.objects.create(name="synthetic-migration")
        cabinet = Cabinet.objects.create(organization=org, name="synthetic", marketplace="synthetic")
        legal = LegalEntity.objects.create(organization=org, name="synthetic")
        history = observe_legal_entity(cabinet, legal)
        cabinet.archive()
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("ownership", "0001_initial")])
            self.assertEqual(CabinetLegalEntity.objects.get(pk=history.pk).legal_entity_id, legal.pk)
            self.assertIsNotNone(Cabinet.objects.get(pk=cabinet.pk).archived_at)
        finally:
            MigrationExecutor(connection).migrate(latest)
        self.assertEqual(CabinetLegalEntity.objects.get(pk=history.pk).cabinet_id, cabinet.pk)
        if connection.vendor == "postgresql":
            foreign = Organization.objects.create(name="synthetic-foreign")
            foreign_cabinet = Cabinet.objects.create(organization=foreign, name="synthetic", marketplace="synthetic")
            with self.assertRaises(IntegrityError), transaction.atomic():
                CabinetLegalEntity.objects.bulk_create([
                    CabinetLegalEntity(organization=org, cabinet=foreign_cabinet, legal_entity=legal)
                ])

    def test_empty_test_schema_zero_forward(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("ownership", None)])
            self.assertNotIn("ownership_organization", connection.introspection.table_names())
        finally:
            MigrationExecutor(connection).migrate(latest)
        self.assertIn("ownership_organization", connection.introspection.table_names())
        Organization.objects.create(name="synthetic-after-forward")

    @skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL row locks and concurrent connections")
    def test_concurrent_attribution_changes_are_serialized(self):
        org = Organization.objects.create(name="synthetic-concurrent")
        cabinet = Cabinet.objects.create(organization=org, name="synthetic", marketplace="synthetic")
        first = LegalEntity.objects.create(organization=org, name="synthetic-first")
        replacements = [LegalEntity.objects.create(organization=org, name=f"synthetic-{i}") for i in range(2)]
        observe_legal_entity(cabinet, first)
        barrier = Barrier(2)

        def change(legal):
            try:
                barrier.wait(timeout=5)
                return observe_legal_entity(cabinet, legal).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(change, legal) for legal in replacements]
            for future in futures:
                future.result(timeout=15)
        history = list(CabinetLegalEntity.objects.filter(cabinet=cabinet).order_by("observed_from"))
        self.assertEqual(len(history), 3)
        self.assertEqual(sum(item.observed_until is None for item in history), 1)
        self.assertEqual(history[0].legal_entity_id, first.pk)
        for previous, following in zip(history, history[1:]):
            self.assertEqual(previous.observed_until, following.observed_from)
