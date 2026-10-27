from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Cabinet, CabinetLegalEntity, LegalEntity, Membership


def membership_role(user, organization):
    """Live organization-local template; does not authorize cabinet reads/exports."""
    if not user.is_active or user.archived_at or organization.archived_at:
        return None
    return Membership.objects.filter(
        user_id=user.pk, user__is_active=True, user__archived_at__isnull=True,
        organization_id=organization.pk, organization__archived_at__isnull=True,
        state=Membership.State.ACTIVE, archived_at__isnull=True,
    ).values_list("role", flat=True).first()


def can_manage_memberships(user, organization):
    # The only role-derived distinction specified by D1 in this task.
    return membership_role(user, organization) == Membership.Role.OWNER


@transaction.atomic
def observe_legal_entity(cabinet, legal_entity):
    """Record a newly observed attribution, never invent historical validity."""
    cabinet = Cabinet.objects.select_for_update().get(pk=cabinet.pk)
    legal_entity = LegalEntity.objects.get(pk=legal_entity.pk)
    if cabinet.organization_id != legal_entity.organization_id:
        raise ValidationError("Legal entity belongs to another organization.")
    if cabinet.archived_at or cabinet.organization.archived_at or legal_entity.archived_at:
        raise ValidationError("Cannot change attribution of archived objects.")
    current = CabinetLegalEntity.objects.filter(cabinet=cabinet, observed_until__isnull=True).first()
    if current is not None and current.legal_entity_id == legal_entity.pk:
        return current
    observed = timezone.now()
    if current is not None:
        if observed <= current.observed_from:
            raise ValidationError("Observation must follow the current attribution.")
        current.observed_until = observed
        current.save(update_fields=["observed_until"])
    return CabinetLegalEntity.objects.create(
        organization_id=cabinet.organization_id, cabinet=cabinet,
        legal_entity=legal_entity, observed_from=observed,
    )
