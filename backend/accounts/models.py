import uuid

from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class AccountContact(models.Model):
    """Optional E2-05 enrollment; existing ownership users are not rewritten."""

    user = models.OneToOneField("ownership.User", on_delete=models.PROTECT, primary_key=True)
    email = models.EmailField(unique=True)
    activated_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(email__endswith="@example.invalid") & Q(email=models.functions.Lower("email")),
                name="account_synthetic_email_only",
            ),
        ]


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # A single FK supplies both tenant and user: no second organization FK to mix.
    membership = models.ForeignKey("ownership.Membership", on_delete=models.PROTECT)
    scope_digest = models.CharField(max_length=64, editable=False)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField(editable=False)
    used_at = models.DateTimeField(null=True, editable=False)
    revoked_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membership"], condition=Q(used_at__isnull=True, revoked_at__isnull=True), name="invitation_one_pending"),
            models.CheckConstraint(condition=Q(expires_at__gt=F("created_at")), name="invitation_positive_lifetime"),
            models.CheckConstraint(condition=Q(used_at__isnull=True) | Q(revoked_at__isnull=True), name="invitation_one_terminal_state"),
        ]


class AttemptBucket(models.Model):
    # HMAC, never a raw login, IP, invitation or reset token.
    key = models.CharField(max_length=64, primary_key=True)
    window_start = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)


class AuthDenial(models.Model):
    occurred_at = models.DateTimeField(default=timezone.now)
    # Fixed event category only; no request body, identity, IP or token.
    kind = models.CharField(max_length=32)
