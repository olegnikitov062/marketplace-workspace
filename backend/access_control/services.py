"""Live authorization and mutations. Call inside one transaction through HTTP.

Lock order: organization, users in UUID order, then authorization rows.
The organization lock serializes tenant grants, ownership and protected actions.
User locks serialize these with E2-06 block, recovery and session revocation.
"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ownership.models import Organization, Cabinet, Membership, User
from account_security import services as security
from account_security.models import AccountSession, ExportPermit
from .models import Grant, PlatformRoleAssignment, SyntheticRecord, SupportWindow, ExportBinding
from data_isolation.context import record_scope


def platform_for(user):
    return PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).first()


def lock_scope(organization_id, actor_id, target_id=None):
    org = Organization.objects.select_for_update().get(pk=organization_id)
    if org.archived_at:
        raise PermissionDenied()
    ids = {actor_id, target_id} - {None}
    users = {u.pk: u for u in User.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
    actor = users[actor_id]
    return org, actor


def session_for(actor, sensitive=False):
    record = AccountSession.objects.filter(pk=security.current_session.get(), user=actor).first()
    if (record is None or record.level != 'full' or
            not security.record_valid(record, actor, security.state_for(actor))):
        raise PermissionDenied()
    if sensitive and not security.fresh(record, factor=security.authenticator(actor) is not None):
        raise PermissionDenied()
    return record


def live_membership(actor, org):
    return Membership.objects.filter(user=actor, organization=org, state='active', archived_at__isnull=True).first()


def matching(actor, org, resource, action, cabinet=None, platform=False):
    if not security.available(actor) or org.archived_at:
        return Grant.objects.none()
    if cabinet and (cabinet.organization_id != org.pk or cabinet.archived_at):
        return Grant.objects.none()
    query = Grant.objects.filter(organization=org, resource=resource, action=action, revoked_at__isnull=True)
    if platform:
        assignment = platform_for(actor)
        if assignment is None or Membership.objects.filter(user=actor).exists():
            return Grant.objects.none()
        query = query.filter(platform=assignment)
    else:
        member = live_membership(actor, org)
        if member is None:
            return Grant.objects.none()
        query = query.filter(membership=member)
    return query.filter(Q(cabinet__isnull=True) | Q(cabinet=cabinet)) if cabinet else query.filter(cabinet__isnull=True)


def authorize(actor, org, resource, action, cabinet=None, sensitive=False):
    record = session_for(actor, sensitive)
    is_platform = platform_for(actor) is not None
    grants = matching(actor, org, resource, action, cabinet, platform=is_platform)
    if is_platform and resource == 'synthetic_record':
        if action != 'view':
            raise PermissionDenied()
        # Support always requires explicit operator-issued scope and a live window.
        grants = grants.filter(supportwindow__session=record,
            supportwindow__revoked_at__isnull=True, supportwindow__expires_at__gt=timezone.now())
    grant = grants.order_by('created_at', 'pk').first()
    if grant is None:
        raise PermissionDenied()
    return grant


def require_manager(actor, org, resource='memberships', cabinet=None):
    session_for(actor, sensitive=True)
    assignment = platform_for(actor)
    if assignment:
        if resource != 'memberships':
            raise PermissionDenied()
    else:
        member = live_membership(actor, org)
        if member is None or member.role != 'owner':
            raise PermissionDenied()
    return authorize(actor, org, resource, 'manage_access', cabinet, sensitive=True)


def invitation_manager(actor, org):
    require_manager(actor, org)


def target_member(org, membership_id, actor):
    target = Membership.objects.select_related('user').get(pk=membership_id, organization=org)
    if (target.user_id == actor.pk or target.archived_at or target.state != 'active' or
            not security.available(target.user) or platform_for(target.user)):
        raise PermissionDenied()
    if platform_for(actor) and target.role == 'owner':
        raise PermissionDenied()
    return target


def ensure_owner(org):
    # Emergency operator account blocking remains possible; HTTP cannot remove
    # the last usable owner or the last owner's administration grant.
    owners = Membership.objects.filter(organization=org, role='owner', state='active',
        archived_at__isnull=True, user__is_active=True, user__archived_at__isnull=True,
        user__authenticator__confirmed=True, user__authenticator__revoked_at__isnull=True)
    if not Grant.objects.filter(membership__in=owners, resource='memberships', action='manage_access',
            cabinet__isnull=True, revoked_at__isnull=True).exists():
        raise PermissionDenied()


def revoke_grant(grant):
    now = timezone.now()
    Grant.objects.filter(pk=grant.pk, revoked_at__isnull=True).update(revoked_at=now)
    # Also explicit for service readability; DB guards cover raw updates.
    ExportPermit.objects.filter(exportbinding__grant=grant, revoked_at__isnull=True).update(revoked_at=now)
    SupportWindow.objects.filter(grant=grant, revoked_at__isnull=True).update(revoked_at=now)


@transaction.atomic
def issue_grant(actor, organization_id, membership_id, resource, action, cabinet_id=None):
    initial = Membership.objects.get(pk=membership_id, organization_id=organization_id)
    org, actor = lock_scope(organization_id, actor.pk, initial.user_id)
    target = target_member(org, membership_id, actor)
    cabinet = Cabinet.objects.get(pk=cabinet_id, organization=org, archived_at__isnull=True) if cabinet_id else None
    if platform_for(actor):
        require_manager(actor, org)
        # Platform grants bound delegation; they do not authorize direct data
        # mutation/export. Read-only support uses an additional timed window.
        if not matching(actor, org, resource, action, cabinet, platform=True).exists():
            raise PermissionDenied()
    else:
        require_manager(actor, org, resource, cabinet)
        authorize(actor, org, resource, action, cabinet)
    if action == 'manage_access' and target.role != 'owner':
        raise PermissionDenied()
    grant = Grant(organization=org, membership=target, cabinet=cabinet, resource=resource, action=action)
    grant.full_clean()
    grant.save()
    security.event(actor, 'grant_issued')
    return grant


@transaction.atomic
def remove_grant(actor, organization_id, grant_id):
    initial = Grant.objects.select_related('membership').get(pk=grant_id, organization_id=organization_id, membership__isnull=False)
    org, actor = lock_scope(organization_id, actor.pk, initial.membership.user_id)
    target_member(org, initial.membership_id, actor)
    grant = Grant.objects.select_related('cabinet').get(pk=grant_id, revoked_at__isnull=True)
    if platform_for(actor):
        require_manager(actor, org)
        if not matching(actor, org, grant.resource, grant.action, grant.cabinet, platform=True).exists():
            raise PermissionDenied()
    else:
        require_manager(actor, org, grant.resource, grant.cabinet)
        authorize(actor, org, grant.resource, grant.action, grant.cabinet)
    revoke_grant(grant)
    ensure_owner(org)
    security.event(actor, 'grant_revoked')


def template_spec(role, cabinets):
    if role == 'owner':
        if cabinets:
            raise PermissionDenied()
        return [('memberships', a, None) for a in ('view', 'manage_access')] + [
            ('synthetic_record', a, None) for a in ('view', 'export', 'change', 'manage_access')]
    if role not in ('observer', 'cabinet_user') or not cabinets or (role == 'cabinet_user' and len(cabinets) != 1):
        raise PermissionDenied()
    return [('synthetic_record', 'view', c) for c in cabinets]


@transaction.atomic
def apply_template(actor, organization_id, membership_id, role, cabinet_ids):
    initial = Membership.objects.get(pk=membership_id, organization_id=organization_id)
    org, actor = lock_scope(organization_id, actor.pk, initial.user_id)
    target = target_member(org, membership_id, actor)
    require_manager(actor, org)
    if platform_for(actor) and role == 'owner':
        raise PermissionDenied()
    if role == 'owner' and security.authenticator(target.user) is None:
        raise PermissionDenied()
    cabinets = list(Cabinet.objects.filter(pk__in=cabinet_ids, organization=org, archived_at__isnull=True))
    if len(cabinets) != len(set(cabinet_ids)):
        raise PermissionDenied()
    specs = template_spec(role, cabinets)
    for resource, action, cabinet in specs:
        if platform_for(actor):
            if not matching(actor, org, resource, action, cabinet, platform=True).exists():
                raise PermissionDenied()
        else:
            require_manager(actor, org, resource, cabinet)
            authorize(actor, org, resource, action, cabinet)
    for grant in Grant.objects.filter(membership=target, revoked_at__isnull=True):
        if platform_for(actor):
            if not matching(actor, org, grant.resource, grant.action, grant.cabinet, platform=True).exists():
                raise PermissionDenied()
        else:
            require_manager(actor, org, grant.resource, grant.cabinet)
            authorize(actor, org, grant.resource, grant.action, grant.cabinet)
        revoke_grant(grant)
    target.role = role
    target.save(update_fields=['role'])
    for resource, action, cabinet in specs:
        Grant.objects.create(organization=org, membership=target, resource=resource, action=action, cabinet=cabinet)
    ensure_owner(org)
    security.event(actor, 'template_applied')


@transaction.atomic
def suspend_membership(actor, organization_id, membership_id):
    initial = Membership.objects.get(pk=membership_id, organization_id=organization_id)
    org, actor = lock_scope(organization_id, actor.pk, initial.user_id)
    target = target_member(org, membership_id, actor)
    require_manager(actor, org)
    target.state = 'suspended'
    target.save(update_fields=['state'])
    for grant in Grant.objects.filter(membership=target, revoked_at__isnull=True):
        revoke_grant(grant)
    ensure_owner(org)
    security.event(actor, 'membership_suspended')


def resolve_record(org, cabinet_id, record_id):
    return SyntheticRecord.objects.select_related('cabinet').get(pk=record_id, organization=org,
        cabinet_id=cabinet_id, archived_at__isnull=True, cabinet__archived_at__isnull=True,
        cabinet__organization=org)


@transaction.atomic
def record_operation(actor, organization_id, cabinet_id, record_id, action, value=None):
    if not settings.SECURITY_DOWNLOAD_PROBE:
        raise PermissionDenied()
    org, actor = lock_scope(organization_id, actor.pk)
    cabinet = Cabinet.objects.get(pk=cabinet_id, organization=org, archived_at__isnull=True)
    grant = authorize(actor, org, 'synthetic_record', action, cabinet)
    session = session_for(actor)
    with record_scope(actor, session, org, cabinet, action):
        obj = resolve_record(org, cabinet_id, record_id)
        if action == 'view':
            return {'value': obj.value}
        if action == 'change':
            if type(value) is not int or not -1000000 <= value <= 1000000:
                raise PermissionDenied()
            if SyntheticRecord.objects.filter(pk=obj.pk).update(value=value) != 1:
                raise PermissionDenied()
            return {'status': 'ok'}
        if action == 'export':
            permit = ExportPermit.objects.create(user=actor, organization=org, session=session,
                expires_at=timezone.now() + timedelta(minutes=5))
            ExportBinding.objects.create(permit=permit, grant=grant, record=obj)
            return {'permit_id': str(permit.pk)}
    raise PermissionDenied()


@transaction.atomic
def list_records(actor, organization_id, cabinet_id, record_id=None):
    """Narrow synthetic list/search consumer; no cross-cabinet aggregation."""
    if not settings.SECURITY_DOWNLOAD_PROBE:
        raise PermissionDenied()
    org, actor = lock_scope(organization_id, actor.pk)
    cabinet = Cabinet.objects.get(pk=cabinet_id, organization=org, archived_at__isnull=True)
    authorize(actor, org, 'synthetic_record', 'view', cabinet)
    with record_scope(actor, session_for(actor), org, cabinet, 'view'):
        rows = SyntheticRecord.objects.filter(organization=org, cabinet=cabinet, archived_at__isnull=True)
        if record_id is not None:
            rows = rows.filter(pk=record_id)
        return {'records': list(rows.order_by('pk').values('id', 'value')[:100])}


@transaction.atomic
def download(request, permit_id):
    if not settings.SECURITY_DOWNLOAD_PROBE or not request.user.is_authenticated:
        raise PermissionDenied()
    initial = ExportPermit.objects.get(pk=permit_id, user=request.user)
    org, actor = lock_scope(initial.organization_id, request.user.pk)
    record = session_for(actor)
    permit = ExportPermit.objects.get(pk=permit_id, user=actor, session=record,
        revoked_at__isnull=True, expires_at__gt=timezone.now())
    binding = ExportBinding.objects.select_related('grant').get(permit=permit)
    from django.db import connection
    if getattr(settings, 'ISOLATION_ENABLED', False) and connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT mw_isolation.export_cabinet(%s,%s,%s)', [permit.pk, actor.pk, record.pk])
            cabinet_id = cursor.fetchone()[0]
    else:
        cabinet_id = binding.record.cabinet_id
    cabinet = Cabinet.objects.get(pk=cabinet_id, organization=org, archived_at__isnull=True)
    if not matching(actor, org, 'synthetic_record', 'export', cabinet).filter(pk=binding.grant_id).exists():
        raise PermissionDenied()
    with record_scope(actor, record, org, cabinet, 'export'):
        obj = resolve_record(org, cabinet_id, binding.record_id)
        return ('synthetic,value\nexample.invalid,' + str(obj.value) + '\n').encode()


@transaction.atomic
def open_support(actor, organization_id, grant_id, reason):
    org, actor = lock_scope(organization_id, actor.pk)
    record = session_for(actor, sensitive=True)
    assignment = platform_for(actor)
    if assignment is None or reason != 'synthetic_diagnostic' or Membership.objects.filter(user=actor).exists():
        raise PermissionDenied()
    grant = Grant.objects.get(pk=grant_id, organization=org, platform=assignment,
        resource='synthetic_record', action='view', revoked_at__isnull=True)
    if grant.cabinet_id and grant.cabinet.archived_at:
        raise PermissionDenied()
    now = timezone.now()
    window = SupportWindow.objects.create(grant=grant, session=record, reason=reason,
        expires_at=min(now + timedelta(minutes=30), record.created_at + timedelta(hours=4), record.expires_at))
    security.event(actor, 'support_opened')
    return window


@transaction.atomic
def close_support(actor, organization_id, window_id):
    org, actor = lock_scope(organization_id, actor.pk)
    record = session_for(actor, sensitive=True)
    window = SupportWindow.objects.get(pk=window_id, session=record, grant__organization=org,
        grant__platform__user=actor, revoked_at__isnull=True)
    SupportWindow.objects.filter(pk=window.pk).update(revoked_at=timezone.now())
    security.event(actor, 'support_closed')
