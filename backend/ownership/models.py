"""Ownership only. Role templates are not cabinet grants or global permissions."""
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ArchiveQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Archive records instead of deleting history.")


class ArchivedRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    archived_at = models.DateTimeField(null=True, blank=True, editable=False)
    objects = ArchiveQuerySet.as_manager()

    class Meta:
        abstract = True

    def archive(self):
        if self.archived_at is None:
            self.archived_at = timezone.now()
            self.save(update_fields=["archived_at"])

    def delete(self, *args, **kwargs):
        raise ValidationError("Archive records instead of deleting history.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class UserManager(BaseUserManager.from_queryset(ArchiveQuerySet)):
    def create_user(self, username, password=None, **extra_fields):
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(ArchivedRecord, AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    USERNAME_FIELD = "username"
    objects = UserManager()

    # No PermissionsMixin, global role, superuser, staff or real contact data.
    def archive(self):
        self.is_active = False
        if self.archived_at is None:
            self.archived_at = timezone.now()
        self.save(update_fields=["is_active", "archived_at"])


class Organization(ArchivedRecord):
    name = models.CharField(max_length=200)


class TenantRecord(ArchivedRecord):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not self._state.adding:
            previous = type(self).objects.filter(pk=self.pk).values_list("organization_id", flat=True).first()
            if previous is not None and previous != self.organization_id:
                raise ValidationError("Organization ownership is immutable.")
        for field in self._meta.fields:
            if field.is_relation and field.name not in {"organization", "user"}:
                related = getattr(self, field.name, None)
                if related is not None and related.organization_id != self.organization_id:
                    raise ValidationError({field.name: "Related object belongs to another organization."})


class Membership(TenantRecord):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        OBSERVER = "observer", "Observer"
        CABINET_USER = "cabinet_user", "Cabinet user"

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices)
    state = models.CharField(max_length=20, choices=State.choices, default=State.ACTIVE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="membership_user_org_unique"),
            models.CheckConstraint(condition=Q(role__in=["owner", "observer", "cabinet_user"]), name="membership_role_valid"),
            models.CheckConstraint(condition=Q(state__in=["active", "suspended"]), name="membership_state_valid"),
        ]


class LegalEntity(TenantRecord):
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "id"], name="legal_org_id_unique")]


class Brand(TenantRecord):
    name = models.CharField(max_length=200)
    # Name is neither a unique global identifier nor an ownership/access rule.


class Cabinet(TenantRecord):
    name = models.CharField(max_length=200)
    marketplace = models.CharField(max_length=80)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "id"], name="cabinet_org_id_unique")]


class SourceConnection(TenantRecord):
    cabinet = models.ForeignKey(Cabinet, on_delete=models.PROTECT)
    source_type = models.CharField(max_length=80)
    seller_identity = models.CharField(max_length=200)
    secret_reference = models.CharField(max_length=200, blank=True)
    # Opaque reference only; credentials are not stored or resolved in E2-04.


class CabinetLegalEntity(TenantRecord):
    cabinet = models.ForeignKey(Cabinet, on_delete=models.PROTECT, related_name="legal_entity_history")
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.PROTECT)
    observed_from = models.DateTimeField(default=timezone.now, editable=False)
    observed_until = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cabinet"], condition=Q(observed_until__isnull=True), name="cabinet_one_current_legal"),
            models.CheckConstraint(condition=Q(observed_until__isnull=True) | Q(observed_until__gt=models.F("observed_from")), name="cabinet_legal_positive_interval"),
        ]

    def clean(self):
        super().clean()
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            immutable = ["organization_id", "cabinet_id", "legal_entity_id", "observed_from"]
            if any(getattr(old, key) != getattr(self, key) for key in immutable):
                raise ValidationError("Historical attribution is immutable.")
            if old.observed_until is not None and old.observed_until != self.observed_until:
                raise ValidationError("A closed historical interval is immutable.")
