import secrets

from django.db import connection, transaction, IntegrityError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from ownership.models import Organization, User, Membership
from access_control.models import Grant


class AccessMigrationTests(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor != 'sqlite':
            return super()._fixture_teardown()
        # SQLite flush uses DELETE; only in the disposable test database remove
        # history guards after assertions, flush, then restore the exact schema.
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([('access_control', '0001_initial')])
            super()._fixture_teardown()
        finally:
            MigrationExecutor(connection).migrate(latest)

    def test_reverse_forward_guards_preserve_revoked_grants(self):
        org = Organization.objects.create(name='synthetic-migration')
        user = User.objects.create_user('synthetic-migration', secrets.token_urlsafe(24))
        member = Membership.objects.create(user=user, organization=org, role='observer')
        grant = Grant.objects.create(organization=org, membership=member, resource='synthetic_record', action='view')
        Grant.objects.filter(pk=grant.pk).update(revoked_at=timezone.now())
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([('access_control', '0001_initial')])
            self.assertTrue(Grant.objects.get(pk=grant.pk).revoked_at is not None)
        finally:
            MigrationExecutor(connection).migrate(latest)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Grant.objects.filter(pk=grant.pk).update(revoked_at=None)

    def test_initial_reverse_only_empty_access_schema_preserves_ownership(self):
        org = Organization.objects.create(name='synthetic-retained')
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([('access_control', None)])
            self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
