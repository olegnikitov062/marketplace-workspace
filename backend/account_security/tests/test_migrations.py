import secrets

from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from ownership.models import Organization, User, Membership
from account_security.models import Authenticator, AccountSecurity


class SecurityMigrationTests(TransactionTestCase):
    def test_guards_reverse_forward_preserve_ciphertext_and_ownership(self):
        user = User.objects.create_user("synthetic-migration", secrets.token_urlsafe(24))
        org = Organization.objects.create(name="synthetic-migration")
        membership = Membership.objects.create(user=user, organization=org, role="owner")
        state = AccountSecurity.objects.create(user=user)
        device = Authenticator.objects.create(user=user, name="default", confirmed=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT key FROM account_security_authenticator WHERE id=%s", [device.pk])
            encrypted = cursor.fetchone()[0]
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("account_security", "0001_initial")])
        finally:
            MigrationExecutor(connection).migrate(latest)
        with connection.cursor() as cursor:
            cursor.execute("SELECT key FROM account_security_authenticator WHERE id=%s", [device.pk])
            self.assertTrue(cursor.fetchone()[0] == encrypted)
        self.assertTrue(Authenticator.objects.get(pk=device.pk).key == device.key)
        self.assertTrue(Membership.objects.filter(pk=membership.pk, user=user, organization=org, role="owner").exists())
        AccountSecurity.objects.filter(user=user).update(version=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountSecurity.objects.filter(user=user).update(version=1)

    def test_empty_security_zero_forward_preserves_ownership(self):
        org = Organization.objects.create(name="synthetic-retained")
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("account_security", None)])
            self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
