"""Идентичности и разрешения оболочки; прикладные права остаются в источниках."""
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone
from account_security.crypto import EncryptedTextField


APPLICATIONS = ('marketplace', 'reports', 'sources', 'airflow', 'bloggers', 'faq', 'rooms')


class OIDCAttempt(models.Model):
    """Одноразовая попытка; токены провайдера здесь никогда не сохраняются."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state_hash = models.CharField(max_length=64, unique=True)
    browser_hash = models.CharField(max_length=64, unique=True)
    provider_hash = models.CharField(max_length=64)
    nonce = EncryptedTextField()
    verifier = EncryptedTextField()
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    claimed_at = models.DateTimeField(null=True)
    ready_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    binding = models.ForeignKey('IdentityBinding', null=True, on_delete=models.PROTECT)
    version = models.PositiveBigIntegerField(null=True)
    credential_hash = models.CharField(max_length=64, default='')


class IdentityBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issuer = models.CharField(max_length=512)
    subject = models.CharField(max_length=255)
    user = models.ForeignKey('ownership.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['issuer', 'subject'], name='basework_identity_unique'),
            models.CheckConstraint(condition=~Q(issuer='') & ~Q(subject=''), name='basework_identity_nonempty'),
        ]


class FederatedSession(models.Model):
    session = models.OneToOneField('account_security.AccountSession', on_delete=models.PROTECT, primary_key=True)
    binding = models.ForeignKey(IdentityBinding, on_delete=models.PROTECT)


class ApplicationAccess(models.Model):
    """Только вход в раздел оболочки. Не заменяет Grant или native admin."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('ownership.User', on_delete=models.PROTECT)
    application = models.CharField(max_length=24, choices=[(value, value) for value in APPLICATIONS])
    created_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(application__in=APPLICATIONS), name='basework_known_application'),
            models.UniqueConstraint(fields=['user', 'application'], condition=Q(revoked_at__isnull=True),
                                    name='basework_one_application_access'),
        ]
