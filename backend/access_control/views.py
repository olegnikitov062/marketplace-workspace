from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from accounts.views import mutation
from ownership.models import Membership, Organization, User
from . import services


def protected_read(view):
    @never_cache
    @require_GET
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                raise PermissionDenied()
            return view(request, *args, **kwargs)
        except (PermissionDenied, ObjectDoesNotExist, ValidationError, ValueError):
            return JsonResponse({'status': 'denied'}, status=403)
    return wrapped


def actor(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    return request.user


@protected_read
@transaction.atomic
def memberships(request, organization_id):
    org, user = services.lock_scope(organization_id, request.user.pk)
    services.authorize(user, org, 'memberships', 'view')
    return JsonResponse({'memberships': list(Membership.objects.filter(organization=org).values('id', 'role', 'state'))})


@mutation('access_grant', ['membership_id', 'resource', 'action', 'cabinet_id'])
def grant(request, organization_id):
    row = services.issue_grant(actor(request), organization_id, request.POST['membership_id'],
        request.POST['resource'], request.POST['action'], request.POST['cabinet_id'] or None)
    return JsonResponse({'grant_id': str(row.pk)}, status=201)


@mutation('access_revoke', [])
def revoke(request, organization_id, grant_id):
    services.remove_grant(actor(request), organization_id, grant_id)
    return JsonResponse({'status': 'ok'})


@mutation('access_template', ['role', 'cabinet_ids'])
def template(request, organization_id, membership_id):
    cabinets = request.POST['cabinet_ids'].split(',') if request.POST['cabinet_ids'] else []
    services.apply_template(actor(request), organization_id, membership_id, request.POST['role'], cabinets)
    return JsonResponse({'status': 'ok'})


@mutation('access_suspend', [])
def suspend(request, organization_id, membership_id):
    services.suspend_membership(actor(request), organization_id, membership_id)
    return JsonResponse({'status': 'ok'})


@protected_read
def record(request, organization_id, cabinet_id, record_id):
    return JsonResponse(services.record_operation(request.user, organization_id, cabinet_id, record_id, 'view'))


@mutation('access_change', ['value'])
def change(request, organization_id, cabinet_id, record_id):
    return JsonResponse(services.record_operation(actor(request), organization_id, cabinet_id, record_id,
        'change', int(request.POST['value'])))


@mutation('access_export', [])
def export(request, organization_id, cabinet_id, record_id):
    return JsonResponse(services.record_operation(actor(request), organization_id, cabinet_id, record_id, 'export'), status=201)


@mutation('access_support_open', ['grant_id', 'reason'])
def support_open(request, organization_id):
    window = services.open_support(actor(request), organization_id, request.POST['grant_id'], request.POST['reason'])
    return JsonResponse({'support_id': str(window.pk), 'expires_at': window.expires_at}, status=201)


@mutation('access_support_close', [])
def support_close(request, organization_id, window_id):
    services.close_support(actor(request), organization_id, window_id)
    return JsonResponse({'status': 'ok'})


@protected_read
@transaction.atomic
def platform_status(request):
    user = User.objects.select_for_update().get(pk=request.user.pk)
    services.session_for(user)
    if services.platform_for(user) is None or Membership.objects.filter(user=user).exists():
        raise PermissionDenied()
    return JsonResponse({'organizations': list(Organization.objects.values('id', 'archived_at')),
        'active_accounts': User.objects.filter(is_active=True, archived_at__isnull=True).count()})
