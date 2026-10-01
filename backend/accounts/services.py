import hashlib
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.debug import sensitive_variables

from ownership.models import Membership, Organization, User
from ownership.services import can_manage_memberships
from .delivery import deliver, synthetic_address
from .models import AccountContact, Invitation


class AccountRejected(Exception):
    """Intentionally contains no identity or credential details."""


def scope_digest(membership):
    value = f"{membership.pk}:{membership.user_id}:{membership.organization_id}:{membership.role}"
    return hashlib.sha256(value.encode()).hexdigest()


def active(user):
    return user.is_active and user.archived_at is None


def require_owner(actor, organization):
    if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
        from account_security.services import assert_actor_session
        assert_actor_session(actor)
    Membership.objects.select_for_update().filter(user_id=actor.pk, organization=organization).first()
    if not can_manage_memberships(actor, organization):
        raise PermissionDenied("Operation denied")


@sensitive_variables()
def _new_invitation(membership, email):
    raw = secrets.token_urlsafe(32)
    now = timezone.now()
    invitation = Invitation.objects.create(
        membership=membership, scope_digest=scope_digest(membership),
        token_hash=hashlib.sha256(raw.encode()).hexdigest(), created_at=now,
        expires_at=now + timedelta(seconds=settings.ACCOUNT_INVITATION_TTL),
    )
    deliver(email, "invitation", json.dumps({"token": raw}))
    return invitation


@sensitive_variables()
@transaction.atomic
def issue_invitation(actor, organization_id, username, email, role):
    organization = Organization.objects.select_for_update().get(pk=organization_id)
    actor = User.objects.select_for_update().get(pk=actor.pk)
    require_owner(actor, organization)
    # E2-05 does not define granting ownership or adding an existing identity
    # to another tenant. Both require their own explicit membership workflow.
    if role not in {Membership.Role.OBSERVER, Membership.Role.CABINET_USER}:
        raise AccountRejected()
    email = synthetic_address(email)
    if User.objects.filter(username=username).exists() or AccountContact.objects.filter(email=email).exists():
        raise AccountRejected()
    user = User.objects.create_user(username)
    AccountContact.objects.create(user=user, email=email)
    membership = Membership.objects.create(user=user, organization=organization, role=role)
    return _new_invitation(membership, email)


def _locked_scope(invitation_id, actor=None):
    # Lock order: organization -> user -> membership -> invitation. Inviter
    # permission checks read current rows; no role is copied from the session.
    initial = Invitation.objects.select_related("membership").get(pk=invitation_id)
    organization = Organization.objects.select_for_update().get(pk=initial.membership.organization_id)
    user_ids = {initial.membership.user_id}
    if actor is not None:
        user_ids.add(actor.pk)
    locked_users = {u.pk: u for u in User.objects.select_for_update().filter(pk__in=user_ids).order_by("pk")}
    user = locked_users[initial.membership.user_id]
    membership = Membership.objects.select_for_update().get(pk=initial.membership_id)
    invitation = Invitation.objects.select_for_update().get(pk=invitation_id)
    if (membership.user_id != user.pk or membership.organization_id != organization.pk
            or invitation.membership_id != membership.pk
            or not constant_time_compare(invitation.scope_digest, scope_digest(membership))):
        raise AccountRejected()
    return invitation, membership, user, organization


def _pending(invitation, membership, user, organization):
    contact = AccountContact.objects.select_for_update().get(user=user)
    if (not active(user) or organization.archived_at or membership.archived_at
            or membership.state != Membership.State.ACTIVE or contact.activated_at
            or user.has_usable_password() or invitation.used_at or invitation.revoked_at):
        raise AccountRejected()
    # No unnoticed second membership may turn activation into broader access.
    if Membership.objects.filter(user=user).exclude(pk=membership.pk).exists():
        raise AccountRejected()
    return contact


@transaction.atomic
def reinvite(actor, invitation_id):
    invitation, membership, user, organization = _locked_scope(invitation_id, actor)
    require_owner(actor, organization)
    contact = _pending(invitation, membership, user, organization)
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["revoked_at"])
    return _new_invitation(membership, contact.email)


@transaction.atomic
def revoke_invitation(actor, invitation_id):
    invitation, membership, user, organization = _locked_scope(invitation_id, actor)
    require_owner(actor, organization)
    if invitation.used_at:
        raise AccountRejected()
    if invitation.revoked_at is None:
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])


@sensitive_variables()
def _set_password(user, password1, password2):
    form = SetPasswordForm(user, {"new_password1": password1, "new_password2": password2})
    if not form.is_valid():
        raise AccountRejected()
    form.save(commit=False)
    user.save(update_fields=["password"])


@sensitive_variables()
@transaction.atomic
def accept_invitation(raw_token, password1, password2):
    if not isinstance(raw_token, str) or len(raw_token) != 43:
        raise AccountRejected()
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()
    initial = Invitation.objects.get(token_hash=hashed)
    invitation, membership, user, organization = _locked_scope(initial.pk)
    contact = _pending(invitation, membership, user, organization)
    now = timezone.now()
    if invitation.expires_at <= now:
        raise AccountRejected()
    _set_password(user, password1, password2)
    invitation.used_at = now
    invitation.save(update_fields=["used_at"])
    contact.activated_at = now
    contact.save(update_fields=["activated_at"])
    # Acceptance does not log in and never changes Membership.


@sensitive_variables()
@transaction.atomic
def request_recovery(username):
    user = User.objects.select_for_update().filter(username=username).first()
    if user is None or not active(user) or not user.has_usable_password():
        return False
    contact = AccountContact.objects.filter(user=user, activated_at__isnull=False).first()
    if contact is None:
        return False
    deliver(contact.email, "recovery", json.dumps({
        "user_id": str(user.pk), "token": default_token_generator.make_token(user),
    }))
    return True


@sensitive_variables()
@transaction.atomic
def confirm_recovery(user_id, token, password1, password2):
    user = User.objects.select_for_update().get(pk=user_id)
    if (not active(user) or not user.has_usable_password()
            or not AccountContact.objects.filter(user=user, activated_at__isnull=False).exists()
            or not default_token_generator.check_token(user, token)):
        raise AccountRejected()
    _set_password(user, password1, password2)
    if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
        from account_security.services import credentials_changed
        credentials_changed(user, "password_recovered")
    # Django password change invalidates reset tokens and prior session hashes.


@transaction.atomic
def block_account(user_id):
    """Trusted operator only. Not exposed as a tenant-owner HTTP operation.

    A fresh unusable password irreversibly revokes prior session/reset hashes,
    even if someone later toggles is_active. Unblocking is outside E2-05.
    """
    user = User.objects.select_for_update().get(pk=user_id)
    user.is_active = False
    user.set_unusable_password()
    user.save(update_fields=["is_active", "password"])
    if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
        from account_security.services import credentials_changed
        credentials_changed(user, "account_blocked")
    Invitation.objects.filter(
        membership__user=user, used_at__isnull=True, revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
