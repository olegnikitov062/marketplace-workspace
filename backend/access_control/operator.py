"""Separate migrator-only provisioning; never called by HTTP or recovery."""
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.utils import timezone

from account_security.operator import require_operator_process
from account_security import services as security
from ownership.models import User, Membership, Organization, Cabinet
from .models import PlatformRoleAssignment, Grant
from .services import template_spec, ensure_owner, revoke_grant


def operator_lock():
    require_operator_process()
    # Serialize operator changes across organizations, including the last admin.
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(207, 1)')


@transaction.atomic
def assign_platform(user_id):
    operator_lock()
    user, state = security.locked_user(user_id)
    if Membership.objects.filter(user=user).exists():
        raise PermissionDenied()
    row = PlatformRoleAssignment.objects.create(user=user)
    security.revoke_all_locked(user, state, 'platform_assigned')
    # Existing password-only sessions stop now. Enrollment required at next login.
    return row


@transaction.atomic
def revoke_platform(assignment_id):
    operator_lock()
    assignment = PlatformRoleAssignment.objects.get(pk=assignment_id, revoked_at__isnull=True)
    user = User.objects.select_for_update().get(pk=assignment.user_id)
    if not PlatformRoleAssignment.objects.filter(revoked_at__isnull=True,
            user__is_active=True, user__archived_at__isnull=True,
            user__authenticator__confirmed=True, user__authenticator__revoked_at__isnull=True).exclude(pk=assignment.pk).exists():
        raise PermissionDenied()
    PlatformRoleAssignment.objects.filter(pk=assignment.pk).update(revoked_at=timezone.now())
    for grant in Grant.objects.filter(platform=assignment, revoked_at__isnull=True):
        revoke_grant(grant)
    security.revoke_all_locked(user, security.state_for(user, lock=True), 'platform_revoked')


@transaction.atomic
def grant_platform(assignment_id, organization_id, resource, action, cabinet_id=None):
    operator_lock()
    org = Organization.objects.select_for_update().get(pk=organization_id, archived_at__isnull=True)
    assignment = PlatformRoleAssignment.objects.get(pk=assignment_id, revoked_at__isnull=True)
    user, _ = security.locked_user(assignment.user_id)
    if Membership.objects.filter(user=user).exists():
        raise PermissionDenied()
    cabinet = Cabinet.objects.get(pk=cabinet_id, organization=org, archived_at__isnull=True) if cabinet_id else None
    row = Grant(platform=assignment, organization=org, cabinet=cabinet, resource=resource, action=action)
    row.full_clean()
    row.save()
    security.event(user, 'platform_scope_issued')
    return row


@transaction.atomic
def revoke_platform_grant(grant_id):
    operator_lock()
    initial = Grant.objects.select_related('platform').get(pk=grant_id, platform__isnull=False)
    Organization.objects.select_for_update().get(pk=initial.organization_id)
    user = User.objects.select_for_update().get(pk=initial.platform.user_id)
    row = Grant.objects.get(pk=grant_id, revoked_at__isnull=True)
    revoke_grant(row)
    security.event(user, 'platform_scope_revoked')


@transaction.atomic
def bootstrap_owner(membership_id):
    operator_lock()
    initial = Membership.objects.get(pk=membership_id)
    org = Organization.objects.select_for_update().get(pk=initial.organization_id, archived_at__isnull=True)
    user, _ = security.locked_user(initial.user_id)
    member = Membership.objects.get(pk=membership_id, state='active', archived_at__isnull=True, role='owner')
    if PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).exists() or Grant.objects.filter(membership=member).exists():
        raise PermissionDenied()
    # Owner may still need MFA enrollment. Grant does not bypass the session gate.
    for resource, action, cabinet in template_spec('owner', []):
        Grant.objects.create(organization=org, membership=member, resource=resource, action=action)
    security.event(user, 'owner_grants_bootstrapped')


@transaction.atomic
def change_owner(membership_id, promote):
    operator_lock()
    initial = Membership.objects.get(pk=membership_id)
    org = Organization.objects.select_for_update().get(pk=initial.organization_id, archived_at__isnull=True)
    user, state = security.locked_user(initial.user_id)
    member = Membership.objects.get(pk=membership_id, state='active', archived_at__isnull=True)
    if PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).exists():
        raise PermissionDenied()
    if promote and security.authenticator(user) is None:
        raise PermissionDenied()
    if (member.role == 'owner') == promote:
        raise PermissionDenied()
    for grant in Grant.objects.filter(membership=member, revoked_at__isnull=True):
        revoke_grant(grant)
    member.role = 'owner' if promote else 'observer'
    member.save(update_fields=['role'])
    if promote:
        for resource, action, cabinet in template_spec('owner', []):
            Grant.objects.create(organization=org, membership=member, resource=resource, action=action)
    ensure_owner(org)
    security.revoke_all_locked(user, state, 'operator_owner_changed')
