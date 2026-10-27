"""Проверки без положительного кэша и без автоматического назначения прав."""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from account_security import services as security
from account_security.models import AccountSession
from access_control.models import Grant
from ownership.models import User
from .models import APPLICATIONS, ApplicationAccess, FederatedSession, IdentityBinding


def resolve_identity(issuer, subject):
    """Вызывать только после проверки токена OIDC библиотекой; не HTTP API."""
    if not isinstance(issuer, str) or not isinstance(subject, str) or not issuer or not subject:
        raise PermissionDenied()
    binding = IdentityBinding.objects.select_related('user').filter(
        issuer=issuer, subject=subject, revoked_at__isnull=True).first()
    if binding is None or not security.available(binding.user):
        raise PermissionDenied()
    return binding


def identity_valid(record):
    link = FederatedSession.objects.select_related('binding').filter(session=record).first()
    # Прежние локальные сессии продолжают собственный проверенный путь MFA.
    return link is None or (link.binding.user_id == record.user_id and link.binding.revoked_at is None)


@transaction.atomic
def attach_identity(record, binding):
    """Связать уже подтверждённую локальную сессию; не выдаёт сессию или MFA."""
    user, state = security.locked_user(record.user_id)
    current = IdentityBinding.objects.select_for_update().get(pk=binding.pk)
    session = AccountSession.objects.select_for_update().get(pk=record.pk, user=user)
    if (current.user_id != user.pk or current.revoked_at or session.level != 'full'
            or not security.record_valid(session, user, state)):
        raise PermissionDenied()
    FederatedSession.objects.create(session=session, binding=current)
    security.event(user, 'basework_identity_attached')


@transaction.atomic
def revoke_identity(binding_id):
    """Операторская операция; HTTP-назначения и реальные сотрудники не включены."""
    initial = IdentityBinding.objects.get(pk=binding_id)
    user = User.objects.select_for_update().get(pk=initial.user_id)
    state = security.state_for(user, lock=True)
    binding = IdentityBinding.objects.select_for_update().get(pk=binding_id)
    if binding.revoked_at is None:
        IdentityBinding.objects.filter(pk=binding.pk).update(revoked_at=timezone.now())
        security.revoke_all_locked(user, state, 'basework_identity_revoked')


@transaction.atomic
def revoke_application(access_id):
    initial = ApplicationAccess.objects.get(pk=access_id)
    user = User.objects.select_for_update().get(pk=initial.user_id)
    state = security.state_for(user, lock=True)
    access = ApplicationAccess.objects.select_for_update().get(pk=access_id)
    if access.revoked_at is None:
        ApplicationAccess.objects.filter(pk=access.pk).update(revoked_at=timezone.now())
        security.revoke_all_locked(user, state, 'basework_access_revoked')


def catalog(user):
    permitted = set(ApplicationAccess.objects.filter(user=user, revoked_at__isnull=True)
                    .values_list('application', flat=True))
    if 'marketplace' in permitted:
        # Навигационный допуск требует живого прикладного права; данные и операции
        # по-прежнему проверяют конкретные organization/cabinet/action в access_control.
        grants = Grant.objects.filter(membership__user=user, membership__state='active',
            membership__archived_at__isnull=True, organization__archived_at__isnull=True,
            membership__organization_id=F('organization_id'), revoked_at__isnull=True,
            action='view', resource__in=['memberships', 'synthetic_record'])
        grants = grants.filter(Q(cabinet__isnull=True) | Q(cabinet__archived_at__isnull=True,
            cabinet__organization_id=F('organization_id')))
        if not grants.exists():
            permitted.discard('marketplace')
    # Прикладные адаптеры ещё не подключены: разрешение меню не обещает работу модуля.
    return [{'id': app, 'access': 'allowed', 'availability': 'unavailable'}
            for app in APPLICATIONS if app in permitted]
