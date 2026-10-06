from unittest import skipUnless
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase
from ownership.models import Organization
from data_isolation.sql import TABLES


@skipUnless(connection.vendor == 'postgresql', 'Requires actual PostgreSQL RLS and migration transactions')
class IsolationMigrationTests(TransactionTestCase):
    def test_policies_forced_and_populated_reverse_refused_without_data_loss(self):
        org = Organization.objects.create(name='synthetic-isolation-retained')
        with connection.cursor() as cursor:
            cursor.execute("SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                           "WHERE n.nspname='public' AND c.relrowsecurity AND c.relforcerowsecurity")
            self.assertEqual({r[0] for r in cursor.fetchall()}, set(TABLES))
        with self.assertRaises(IrreversibleError), transaction.atomic():
            MigrationExecutor(connection).migrate([('data_isolation',None)])
        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM django_migrations WHERE app='data_isolation'")
            self.assertEqual(cursor.fetchone(), (1,))

    def test_empty_schema_reverse_forward(self):
        targets = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([('data_isolation',None)])
        finally:
            MigrationExecutor(connection).migrate(targets)
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_class WHERE relrowsecurity AND relforcerowsecurity")
            self.assertEqual(cursor.fetchone(), (len(TABLES),))
