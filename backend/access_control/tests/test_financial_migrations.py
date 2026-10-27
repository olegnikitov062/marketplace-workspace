import secrets
from unittest import skipUnless
from django.db import connection, transaction, IntegrityError
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase

from ownership.models import User, Organization, Membership, Cabinet
from access_control.models import Grant, SyntheticRecord, SyntheticFinance


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL financial ACL/RLS/migrations')
class FinancialMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_original_data_grants_and_guard_definitions(self):
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([('access_control','0002_access_guards'),
                                                   ('data_isolation','0001_statement_and_row_policies')])
            org = Organization.objects.create(name='synthetic-upgrade')
            user = User.objects.create_user('synthetic-upgrade', secrets.token_urlsafe(24))
            member = Membership.objects.create(organization=org, user=user, role='observer')
            cab = Cabinet.objects.create(organization=org, name='synthetic-upgrade', marketplace='synthetic')
            record = SyntheticRecord.objects.create(organization=org, cabinet=cab, value=42)
            grant = Grant.objects.create(organization=org, membership=member, cabinet=cab,
                                         resource='synthetic_record', action='view')
            before = list(Grant.objects.values())
            with connection.cursor() as cursor:
                cursor.execute("SELECT tgname,pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal "
                               "AND tgrelid='public.access_control_grant'::regclass ORDER BY tgname")
                old_guards = dict(cursor.fetchall())
            MigrationExecutor(connection).migrate(latest)
            self.assertEqual(list(Grant.objects.values()), before)
            self.assertEqual(SyntheticRecord.objects.get(pk=record.pk).value, 42)
            self.assertFalse(SyntheticFinance.objects.exists())
            self.assertFalse(Grant.objects.filter(resource='synthetic_finance').exists())
            with connection.cursor() as cursor:
                cursor.execute("SELECT tgname,pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal "
                               "AND tgrelid='public.access_control_grant'::regclass ORDER BY tgname")
                now = dict(cursor.fetchall())
                self.assertTrue(all(now[k] == v for k,v in old_guards.items()))
        finally:
            MigrationExecutor(connection).migrate(latest)

    def test_financial_rows_and_grants_refuse_downgrade(self):
        org = Organization.objects.create(name='synthetic-financial-retained')
        user = User.objects.create_user('synthetic-financial-retained', secrets.token_urlsafe(24))
        member = Membership.objects.create(organization=org,user=user,role='observer')
        cab = Cabinet.objects.create(organization=org,name='synthetic',marketplace='synthetic')
        record = SyntheticRecord.objects.create(organization=org,cabinet=cab)
        SyntheticFinance.objects.create(record=record,organization=org,cabinet=cab,revenue=10,cost=1,expenses=2,payout=8)
        Grant.objects.create(organization=org,membership=member,resource='synthetic_finance',action='view')
        with self.assertRaises(IrreversibleError), transaction.atomic():
            MigrationExecutor(connection).migrate([('data_isolation','0001_statement_and_row_policies')])
        self.assertEqual(SyntheticFinance.objects.get(record=record).revenue, 10)
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM django_migrations WHERE app='data_isolation' AND name='0002_financial_operations'")
            self.assertEqual(cursor.fetchone(), (1,))
        other = Organization.objects.create(name='synthetic-other')
        with self.assertRaises(IntegrityError), transaction.atomic():
            SyntheticFinance.objects.filter(record=record).update(organization=other)
