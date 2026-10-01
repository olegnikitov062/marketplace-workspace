from functools import wraps
from django.conf import settings

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_POST

from ownership.models import User
from . import services
from .limits import allow_attempt, denied


def reject(kind, status=400):
    denied(kind)
    return JsonResponse({"status": "denied"}, status=status)


def mutation(action, fields, principal=None):
    def decorate(view):
        @never_cache
        @sensitive_post_parameters()
        @require_POST
        @csrf_protect
        @wraps(view)
        @sensitive_variables()
        def wrapped(request, *args, **kwargs):
            identity = User.normalize_username(request.POST.get(principal, "")[:150]) if principal else None
            if not allow_attempt(action, request.META.get("REMOTE_ADDR", ""), identity):
                return reject("rate_limited", 429)
            if request.content_type != "application/x-www-form-urlencoded" and (fields or request.body):
                return reject("invalid_request")
            if (set(request.POST) - {"csrfmiddlewaretoken"} != set(fields)
                    or any(len(request.POST.getlist(key)) != 1 for key in fields)
                    or any(len(request.POST[key]) > 512 for key in fields)):
                return reject("invalid_request")
            try:
                return view(request, *args, **kwargs)
            except PermissionDenied:
                return reject("permission_denied", 403)
            except (services.AccountRejected, ObjectDoesNotExist, ValidationError, IntegrityError, ValueError):
                return reject(action)
        return wrapped
    return decorate


@never_cache
@require_GET
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@mutation("login", ["username", "password"], principal="username")
@sensitive_variables()
def login(request):
    if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
        # Runtime E2-06 has a single library wizard; the old password-only URL
        # cannot create a session, including for users without an enrolled factor.
        return JsonResponse({"status": "use_mfa_login", "login": "/auth/mfa/login/"}, status=409)
    # Serialize successful authentication/password checks with block/reset.
    with transaction.atomic():
        User.objects.select_for_update().filter(username=User.normalize_username(request.POST["username"])).first()
        form = AuthenticationForm(request, data=request.POST)
        if not form.is_valid():
            return reject("login", 401)
        django_login(request, form.get_user())
    return JsonResponse({"status": "ok"})


@mutation("logout", [])
def logout(request):
    if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
        from account_security.services import logout as security_logout
        security_logout(request)
    else:
        django_logout(request)
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def session(request):
    # Technical probe only: no identity, role, membership or session inventory.
    return JsonResponse({"authenticated": request.user.is_authenticated}, status=200 if request.user.is_authenticated else 401)


@mutation("invite", ["organization_id", "username", "email", "role"])
def invite(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    invitation = services.issue_invitation(request.user, **{key: request.POST[key] for key in ["organization_id", "username", "email", "role"]})
    return JsonResponse({"invitation_id": str(invitation.pk)}, status=201)


@mutation("reinvite", [])
def reinvite(request, invitation_id):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    invitation = services.reinvite(request.user, invitation_id)
    return JsonResponse({"invitation_id": str(invitation.pk)}, status=201)


@mutation("revoke", [])
def revoke(request, invitation_id):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    services.revoke_invitation(request.user, invitation_id)
    return JsonResponse({"status": "ok"})


@mutation("accept", ["token", "new_password1", "new_password2"])
def accept(request):
    services.accept_invitation(request.POST["token"], request.POST["new_password1"], request.POST["new_password2"])
    return JsonResponse({"status": "ok"})


@mutation("recovery_request", ["username"], principal="username")
def recovery_request(request):
    if not services.request_recovery(User.normalize_username(request.POST["username"])):
        denied("recovery_unavailable")
    # Identical response for absent, pending, blocked and active accounts.
    return JsonResponse({"status": "accepted"}, status=202)


@mutation("recovery_confirm", ["user_id", "token", "new_password1", "new_password2"])
def recovery_confirm(request):
    services.confirm_recovery(request.POST["user_id"], request.POST["token"], request.POST["new_password1"], request.POST["new_password2"])
    return JsonResponse({"status": "ok"})
