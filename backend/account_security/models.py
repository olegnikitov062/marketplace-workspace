import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django_otp.models import Device, ThrottlingMixin, TimestampMixin
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex

from .crypto import EncryptedTextField


class AccountSecurity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, primary_key=True)
    version = models.PositiveBigIntegerField(default=1)
    recovery_required = models.BooleanField(default=False)


class LoginChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.PositiveBigIntegerField()
    credential_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)


class Authenticator(TimestampMixin, ThrottlingMixin, Device):
    """Storage adapter: verification/replay/throttling are upstream django-otp."""

    key = EncryptedTextField(default=random_hex)
    step = models.PositiveSmallIntegerField(default=30)
    t0 = models.BigIntegerField(default=0)
    digits = models.PositiveSmallIntegerField(default=6)
    tolerance = models.PositiveSmallIntegerField(default=1)
    drift = models.SmallIntegerField(default=0)
    last_t = models.BigIntegerField(default=-1)
    revoked_at = models.DateTimeField(null=True)
    enrollment_hash = models.CharField(max_length=64, blank=True)
    enrollment_version = models.PositiveBigIntegerField(default=1)
    expires_at = models.DateTimeField(null=True)

    bin_key = TOTPDevice.bin_key
    config_url = TOTPDevice.config_url
    get_throttle_factor = TOTPDevice.get_throttle_factor

    def verify_token(self, token):
        if self.revoked_at is not None:
            return False
        return TOTPDevice.verify_token(self, token)

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding and kwargs.get("update_fields") is None:
            # Upstream verify_token calls save(); encrypted identity is insert-only.
            kwargs["update_fields"] = ["confirmed", "last_t", "drift", "revoked_at", "expires_at",
                "last_used_at", "throttling_failure_timestamp", "throttling_failure_count"]
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=Q(confirmed=True, revoked_at__isnull=True), name="security_one_active_totp"),
        ]


class TrustedDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    authenticator = models.ForeignKey(Authenticator, on_delete=models.PROTECT)
    token_hash = models.CharField(max_length=64, unique=True)
    credential_hash = models.CharField(max_length=64)
    version = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)


class AccountSession(models.Model):
    class Level(models.TextChoices):
        FULL = "full"
        ENROLL = "enroll"
        RECOVER = "recover"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    session_hash = models.CharField(max_length=64, unique=True)
    credential_hash = models.CharField(max_length=64)
    version = models.PositiveBigIntegerField()
    level = models.CharField(max_length=10, choices=Level.choices)
    authenticator = models.ForeignKey(Authenticator, null=True, on_delete=models.PROTECT)
    trusted_device = models.ForeignKey(TrustedDevice, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    last_seen = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True)
    password_confirmed_at = models.DateTimeField(null=True)
    factor_confirmed_at = models.DateTimeField(null=True)


class RecoveryCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    verifier = models.CharField(max_length=256)
    created_at = models.DateTimeField(default=timezone.now)
    used_at = models.DateTimeField(null=True)


class RecoveryPermit(models.Model):
    """Only the separately authorized operator can INSERT this capability."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    token_hash = models.CharField(max_length=64, unique=True)
    version = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)


class ExportPermit(models.Model):
    """Live authorization for a synthetic download, not business export rights."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    organization = models.ForeignKey("ownership.Organization", on_delete=models.PROTECT)
    session = models.ForeignKey(AccountSession, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)


class SecurityEvent(models.Model):
    occurred_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=40)
    # No submitted values, peer, user agent, cookies or credential fingerprints.
