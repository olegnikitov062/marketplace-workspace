"""Личные пользователи BaseWork. Источники приложений и назначения администраторов не изменяются."""
import uuid

from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from account_security import services as security
from account_security.models import AccountSession, SecurityEvent
from access_control.models import PlatformRoleAssignment
from accounts.models import AccountContact
from ownership.models import User, Membership
from .models import Administrator, ApplicationAccess
from . import personal_access as personal

CHOICES = (('faq', 'FAQ — чтение и поиск'), ('rooms', 'Переговорки — доступ к расписанию'))


class StaleOperation(Exception):
    pass


class ConfirmationRequired(Exception):
    pass


def is_administrator(user):
    return bool(user.is_authenticated and Administrator.objects.filter(user=user, revoked_at__isnull=True).exists()
                and PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).exists()
                and not Membership.objects.filter(user=user).exists())


def authorize(actor, *, target=None, change=False):
    if not is_administrator(actor):
        raise PermissionDenied()
    record = AccountSession.objects.filter(pk=security.current_session.get(), user=actor).first()
    if (record is None or record.level != 'full' or record.authenticator_id is None
            or not security.record_valid(record, actor, security.state_for(actor))):
        raise PermissionDenied()
    if change:
        if not security.fresh(record, factor=True):
            raise ConfirmationRequired()
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SELECT public.basework_authorize_admin(%s)', [target])
        elif not getattr(settings, 'ISOLATION_OFFLINE', False):
            raise PermissionDenied()
        else:
            list(User.objects.select_for_update().filter(pk__in=[actor.pk, target] if target else [actor.pk]).order_by('pk'))
    return record


def managed_users():
    return User.objects.filter(securityevent__kind=personal.CREATED, archived_at__isnull=True,
                               is_active=True).exclude(accountcontact__isnull=False).exclude(membership__isnull=False).distinct()


def target_user(actor, target, version):
    user = personal.personal_user(User.objects.select_for_update().get(pk=target))
    if (user.pk == actor.pk or Membership.objects.filter(user=user).exists()
            or PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).exists()
            or Administrator.objects.filter(user=user, revoked_at__isnull=True).exists()):
        raise PermissionDenied()
    state = security.state_for(user, lock=True)
    if state.recovery_required:
        raise PermissionDenied()
    if state.version != version:
        raise StaleOperation()
    return user, state


def creation_ticket(actor):
    return signing.dumps({'actor': str(actor.pk), 'target': str(uuid.uuid4())}, salt='basework.user-create.v1')


def ticket_target(actor, token):
    try:
        value = signing.loads(token, salt='basework.user-create.v1', max_age=900)
        if value['actor'] != str(actor.pk):
            raise PermissionDenied()
        return uuid.UUID(value['target'])
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        raise StaleOperation() from None


def validate_applications(applications):
    if not isinstance(applications, list) or len(applications) != len(set(applications)) or not set(applications) <= personal.APPLICATIONS:
        raise PermissionDenied()


def set_applications(user, applications):
    validate_applications(applications)
    old = set(ApplicationAccess.objects.filter(user=user, revoked_at__isnull=True,
              application__in=personal.APPLICATIONS).values_list('application', flat=True))
    for app in sorted(old ^ set(applications)):
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SELECT public.basework_set_application(%s,%s,%s)', [user.pk, app, app in applications])
        elif getattr(settings, 'ISOLATION_OFFLINE', False):
            if app in applications:
                ApplicationAccess.objects.create(user=user, application=app)
            else:
                ApplicationAccess.objects.filter(user=user, application=app, revoked_at__isnull=True).update(revoked_at=timezone.now())
        else:
            raise PermissionDenied()
    return bool(old ^ set(applications))


def audit(actor, target, action):
    # Связь инициатора с проверенным UUID, без логина, кода и введённых полей.
    security.event(actor, action + ':' + target.pk.hex)


@transaction.atomic
@sensitive_variables()
def create(actor, ticket, username, applications):
    target = ticket_target(actor, ticket)
    authorize(actor, target=target, change=True)
    validate_applications(applications)
    if User.objects.filter(pk=target).exists():
        raise StaleOperation()
    personal.roster({'purpose': 'basework-personal-pilot-v1', 'users': [
        {'id': str(target), 'username': username, 'applications': applications or ['faq']} ]})
    if User.objects.filter(username__iexact=username).exists():
        raise ValidationError('Этот логин уже занят.')
    user = User.objects.create_user(username, id=target)
    security.event(user, personal.CREATED)
    state = security.state_for(user, lock=True)
    set_applications(user, applications)
    code = personal.issue_code(user, state)
    audit(actor, user, 'create')
    return user, code


@transaction.atomic
def update_access(actor, target, version, applications):
    authorize(actor, target=target, change=True)
    user, state = target_user(actor, target, version)
    if set_applications(user, applications):
        security.revoke_all_locked(user, state, 'basework_access_updated')
        audit(actor, user, 'access')
    return user


@transaction.atomic
@sensitive_variables()
def issue(actor, target, version):
    authorize(actor, target=target, change=True)
    user, state = target_user(actor, target, version)
    code = personal.issue_code(user, state)
    audit(actor, user, 'code')
    return user, code
