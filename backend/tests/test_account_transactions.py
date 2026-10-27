"""PostgreSQL tests are explicitly skipped offline, never counted as passed."""
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.core import mail
from django.db import IntegrityError, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from accounts import services
from accounts.limits import allow_attempt
from accounts.models import AccountContact, Invitation
from ownership.models import Membership, Organization, User


class AccountMigrationTests(TransactionTestCase):
    def test_guard_reverse_forward_preserves_enrollment(self):
        org = Organization.objects.create(name="synthetic-migration")
        owner = User.objects.create_user("synthetic-owner")
        Membership.objects.create(user=owner, organization=org, role="owner")
        invitation = services.issue_invitation(owner, org.pk, "synthetic-pending", "pending@example.invalid", "observer")
        before = list(Invitation.objects.values())
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("accounts", "0001_initial")])
            self.assertTrue(before == list(Invitation.objects.values()))
        finally:
            MigrationExecutor(connection).migrate(latest)
        self.assertTrue(before == list(Invitation.objects.values()))
        self.assertTrue(AccountContact.objects.filter(user_id=invitation.membership.user_id).exists())

    def test_empty_account_schema_zero_forward_leaves_ownership(self):
        org = Organization.objects.create(name="synthetic-retained")
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("accounts", None)])
            self.assertNotIn("accounts_invitation", connection.introspection.table_names())
            self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
        self.assertIn("accounts_invitation", connection.introspection.table_names())


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL triggers and row locks")
class AccountPostgreSQLTests(TransactionTestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="synthetic-concurrent")
        self.owner = User.objects.create_user("synthetic-owner")
        Membership.objects.create(user=self.owner, organization=self.org, role="owner")
        self.invitation = services.issue_invitation(self.owner, self.org.pk, "synthetic-new", "new@example.invalid", "observer")
        self.token = json.loads(mail.outbox[-1].body)["token"]
        self.password = secrets.token_urlsafe(24)

    def race(self, operations):
        barrier = Barrier(len(operations))

        def run(operation):
            try:
                barrier.wait(timeout=10)
                try:
                    operation()
                    return True
                except services.AccountRejected:
                    return False
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return [f.result(timeout=30) for f in [pool.submit(run, op) for op in operations]]

    def test_concurrent_accept_is_single_use(self):
        operation = lambda: services.accept_invitation(self.token, self.password, self.password)
        self.assertEqual(sum(self.race([operation, operation])), 1)

    def test_concurrent_reinvite_replaces_only_once(self):
        operation = lambda: services.reinvite(self.owner, self.invitation.pk)
        self.assertEqual(sum(self.race([operation, operation])), 1)
        self.assertEqual(Invitation.objects.filter(used_at__isnull=True, revoked_at__isnull=True).count(), 1)

    def test_concurrent_recovery_is_single_use(self):
        services.accept_invitation(self.token, self.password, self.password)
        user = User.objects.get(pk=self.invitation.membership.user_id)
        services.request_recovery(user.username)
        token = json.loads(mail.outbox[-1].body)["token"]
        operation = lambda: services.confirm_recovery(user.pk, token, self.password, self.password)
        self.assertEqual(sum(self.race([operation, operation])), 1)

    def test_block_racing_accept_always_finishes_blocked(self):
        self.race([
            lambda: services.accept_invitation(self.token, self.password, self.password),
            lambda: services.block_account(self.invitation.membership.user_id),
        ])
        user = User.objects.get(pk=self.invitation.membership.user_id)
        self.assertFalse(user.is_active or user.has_usable_password())
        self.assertFalse(services.request_recovery(user.username))

    @override_settings(ACCOUNT_PEER_LIMIT=3)
    def test_first_use_counter_race_is_atomic(self):
        results = []
        self.race([lambda: results.append(allow_attempt("login", "synthetic-peer")) for _ in range(6)])
        self.assertEqual(sum(results), 3)

    def test_invitation_identity_cannot_be_rebound_by_raw_update(self):
        other_org = Organization.objects.create(name="synthetic-foreign")
        foreign = Membership.objects.create(user=self.owner, organization=other_org, role="observer")
        for field, value in [("membership_id", foreign.pk), ("scope_digest", "f" * 64), ("token_hash", "f" * 64), ("expires_at", timezone.now())]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Invitation.objects.filter(pk=self.invitation.pk).update(**{field: value})

    def test_terminal_invitation_cannot_be_revived(self):
        services.revoke_invitation(self.owner, self.invitation.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invitation.objects.filter(pk=self.invitation.pk).update(revoked_at=None)

    def test_contact_cannot_be_reassigned_or_changed(self):
        contact = AccountContact.objects.get(user_id=self.invitation.membership.user_id)
        for field, value in [("user_id", self.owner.pk), ("email", "other@example.invalid")]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                AccountContact.objects.filter(pk=contact.pk).update(**{field: value})
