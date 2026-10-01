from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from ownership.models import (
    User, Organization, Membership, LegalEntity, Brand, Cabinet,
    SourceConnection, CabinetLegalEntity,
)
from ownership.services import can_manage_memberships, membership_role, observe_legal_entity


class OwnershipTests(TestCase):
    def setUp(self):
        self.a = Organization.objects.create(name="synthetic-a")
        self.b = Organization.objects.create(name="synthetic-b")
        self.user = User.objects.create_user("synthetic-user")
        self.owner = Membership.objects.create(user=self.user, organization=self.a, role="owner")
        self.observer = Membership.objects.create(user=self.user, organization=self.b, role="observer")
        self.ca = Cabinet.objects.create(organization=self.a, name="synthetic-a", marketplace="synthetic")
        self.cb = Cabinet.objects.create(organization=self.b, name="synthetic-b", marketplace="synthetic")
        self.la = LegalEntity.objects.create(organization=self.a, name="synthetic-a")
        self.lb = LegalEntity.objects.create(organization=self.b, name="synthetic-b")

    def test_different_live_organization_rights(self):
        self.assertEqual(membership_role(self.user, self.a), "owner")
        self.assertEqual(membership_role(self.user, self.b), "observer")
        self.assertTrue(can_manage_memberships(self.user, self.a))
        self.assertFalse(can_manage_memberships(self.user, self.b))
        self.owner.state = "suspended"
        self.owner.save()
        self.assertFalse(can_manage_memberships(self.user, self.a))
        self.assertEqual(membership_role(self.user, self.b), "observer")
        self.observer.archive()
        self.assertIsNone(membership_role(self.user, self.b))
        self.assertEqual(Membership.objects.count(), 2)

    def test_absent_member_and_archived_user_or_organization_deny(self):
        stranger = User.objects.create_user("synthetic-stranger")
        self.assertIsNone(membership_role(stranger, self.a))
        self.a.archive()
        self.assertFalse(can_manage_memberships(self.user, self.a))
        self.user.archive()
        self.assertIsNone(membership_role(self.user, self.b))

    def test_local_links_and_token_reference_rotation_keep_cabinet(self):
        for org, cabinet, legal in [(self.a, self.ca, self.la), (self.b, self.cb, self.lb)]:
            connection_record = SourceConnection.objects.create(
                organization=org, cabinet=cabinet, source_type="synthetic",
                seller_identity="synthetic-seller", secret_reference="synthetic-reference-v1",
            )
            connection_record.secret_reference = "synthetic-reference-v2"
            connection_record.save()
            connection_record.refresh_from_db()
            self.assertEqual(connection_record.cabinet_id, cabinet.pk)
            version = observe_legal_entity(cabinet, legal)
            self.assertEqual(version.organization_id, org.pk)
            self.assertEqual(observe_legal_entity(cabinet, legal).pk, version.pk)
        for org in [self.a, self.b]:
            Brand.objects.create(organization=org, name="same-synthetic-brand")
        self.assertEqual(Brand.objects.count(), 2)

    def test_model_rejects_cross_organization_links(self):
        for org, cabinet, legal in [(self.a, self.cb, self.la), (self.a, self.ca, self.lb)]:
            with self.assertRaises(ValidationError):
                CabinetLegalEntity.objects.create(organization=org, cabinet=cabinet, legal_entity=legal)
        with self.assertRaises(ValidationError):
            SourceConnection.objects.create(organization=self.a, cabinet=self.cb, source_type="synthetic", seller_identity="synthetic")
        with self.assertRaises(ValidationError):
            observe_legal_entity(self.ca, self.lb)
        self.assertFalse(CabinetLegalEntity.objects.exists())
        self.ca.organization = self.b
        with self.assertRaises(ValidationError):
            self.ca.save()

    def test_history_versions_archive_and_delete_protection(self):
        first = observe_legal_entity(self.ca, self.la)
        replacement = LegalEntity.objects.create(organization=self.a, name="synthetic-replacement")
        second = observe_legal_entity(self.ca, replacement)
        first.refresh_from_db()
        self.assertEqual(first.observed_until, second.observed_from)
        self.assertEqual(first.legal_entity_id, self.la.pk)
        first.legal_entity = replacement
        with self.assertRaises(ValidationError):
            first.save()
        source = SourceConnection.objects.create(organization=self.a, cabinet=self.ca, source_type="synthetic", seller_identity="synthetic")
        brand = Brand.objects.create(organization=self.a, name="synthetic")
        for record in [self.la, replacement, self.ca, source, brand, second, self.a]:
            record.archive()
            record.refresh_from_db()
            self.assertIsNotNone(record.archived_at)
            with self.assertRaises(ValidationError):
                record.delete()
        self.assertEqual(CabinetLegalEntity.objects.filter(cabinet=self.ca).count(), 2)
        self.assertEqual(SourceConnection.objects.get(pk=source.pk).cabinet_id, self.ca.pk)
        with self.assertRaises(ValidationError):
            Cabinet.objects.all().delete()
        with self.assertRaises(ValidationError):
            observe_legal_entity(self.ca, self.la)

    def test_duplicate_membership_and_unknown_role(self):
        with self.assertRaises(ValidationError):
            Membership.objects.create(user=self.user, organization=self.a, role="observer")
        with self.assertRaises(ValidationError):
            Membership.objects.create(user=self.user, organization=self.b, role="global-admin")

    def test_database_role_state_and_current_version_constraints(self):
        for update in [{"role": "global-admin"}, {"state": "unknown"}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Membership.objects.filter(pk=self.owner.pk).update(**update)
        observe_legal_entity(self.ca, self.la)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CabinetLegalEntity.objects.bulk_create([
                CabinetLegalEntity(organization=self.a, cabinet=self.ca, legal_entity=self.la)
            ])

    @skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL composite FK and triggers")
    def test_postgresql_bypassed_model_writes_reject_foreign_links(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SourceConnection.objects.bulk_create([
                SourceConnection(organization=self.a, cabinet=self.cb, source_type="synthetic", seller_identity="synthetic")
            ])
        for cabinet, legal in [(self.cb, self.la), (self.ca, self.lb)]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                CabinetLegalEntity.objects.bulk_create([
                    CabinetLegalEntity(organization=self.a, cabinet=cabinet, legal_entity=legal)
                ])
        source = SourceConnection.objects.create(organization=self.a, cabinet=self.ca, source_type="synthetic", seller_identity="synthetic")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SourceConnection.objects.filter(pk=source.pk).update(cabinet=self.cb)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SourceConnection.objects.filter(pk=source.pk).update(organization=self.b)

    @skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL ownership/history triggers")
    def test_postgresql_raw_updates_and_deletes_preserve_history(self):
        version = observe_legal_entity(self.ca, self.la)
        replacement = LegalEntity.objects.create(organization=self.a, name="synthetic-replacement")
        for model, pk in [(Cabinet, self.ca.pk), (LegalEntity, self.la.pk), (Brand, Brand.objects.create(organization=self.a, name="synthetic").pk), (Membership, self.owner.pk), (CabinetLegalEntity, version.pk)]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.filter(pk=pk).update(organization=self.b)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CabinetLegalEntity.objects.filter(pk=version.pk).update(legal_entity=replacement)
        observe_legal_entity(self.ca, replacement)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CabinetLegalEntity.objects.filter(pk=version.pk).update(observed_until=None)
        for table, pk in [("ownership_user", self.user.pk), ("ownership_organization", self.b.pk), ("ownership_cabinetlegalentity", version.pk)]:
            with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table} WHERE id = %s", [pk])
