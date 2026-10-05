import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class PlatformRoleAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('ownership.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(blank=True, null=True)
    # Operator procedure is the only writer; no HTTP assignment endpoint.
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user'], condition=Q(revoked_at__isnull=True),
                                               name='access_one_platform_assignment')]


class Grant(models.Model):
    class Resource(models.TextChoices):
        MEMBERSHIPS = 'memberships'
        RECORD = 'synthetic_record'

    class Action(models.TextChoices):
        VIEW = 'view'
        EXPORT = 'export'
        CHANGE = 'change'
        MANAGE = 'manage_access'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('ownership.Organization', on_delete=models.PROTECT)
    cabinet = models.ForeignKey('ownership.Cabinet', blank=True, null=True, on_delete=models.PROTECT)
    membership = models.ForeignKey('ownership.Membership', blank=True, null=True, on_delete=models.PROTECT)
    platform = models.ForeignKey(PlatformRoleAssignment, blank=True, null=True, on_delete=models.PROTECT)
    resource = models.CharField(max_length=24, choices=Resource.choices)
    action = models.CharField(max_length=16, choices=Action.choices)
    created_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=(Q(membership__isnull=False, platform__isnull=True) |
                                               Q(membership__isnull=True, platform__isnull=False)), name='access_one_subject'),
            models.CheckConstraint(condition=(Q(resource='memberships', action__in=['view', 'manage_access'], cabinet__isnull=True) |
                Q(resource='synthetic_record', action__in=['view', 'export', 'change', 'manage_access'])), name='access_known_operation'),
        ]


class SyntheticRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('ownership.Organization', on_delete=models.PROTECT)
    cabinet = models.ForeignKey('ownership.Cabinet', on_delete=models.PROTECT)
    value = models.IntegerField(default=0)
    archived_at = models.DateTimeField(blank=True, null=True)


class SupportWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grant = models.ForeignKey(Grant, on_delete=models.PROTECT)
    session = models.ForeignKey('account_security.AccountSession', on_delete=models.PROTECT)
    # Enumerated reason prevents free-form personal data entering the journal.
    reason = models.CharField(max_length=24, choices=[('synthetic_diagnostic', 'Synthetic diagnostic')])
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(blank=True, null=True)


class ExportBinding(models.Model):
    permit = models.OneToOneField('account_security.ExportPermit', primary_key=True, on_delete=models.PROTECT)
    grant = models.ForeignKey(Grant, on_delete=models.PROTECT)
    record = models.ForeignKey(SyntheticRecord, on_delete=models.PROTECT)
