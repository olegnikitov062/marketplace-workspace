from collections import OrderedDict

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_POST
from two_factor.plugins.registry import GeneratorMethod
from two_factor.views.core import LoginView, SetupView, QRGeneratorView
from two_factor.views.utils import IdempotentSessionWizardView

from accounts.views import mutation
from ownership.models import User
from . import services
from .forms import PasswordForm, TokenForm, EnrollmentForm, ConfirmForm, RecoveryForm
from .models import AccountSession, Authenticator, ExportPermit, LoginChallenge, TrustedDevice


class StrictWizard:
    """Reject untrusted step names before upstream diagnostic logging."""
    allowed_steps = frozenset()

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            for name in (self.get_prefix(request) + "-current_step", "wizard_goto_step"):
                value = request.POST.get(name)
                if value is not None and value not in self.allowed_steps:
                    return JsonResponse({"status": "denied"}, status=400)
            if "challenge_device" in request.POST:
                return JsonResponse({"status": "denied"}, status=400)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(sensitive_post_parameters(), name="dispatch")
class PersonalLogin(StrictWizard, LoginView):
    allowed_steps = frozenset({"auth", "token"})
    template_name = "account_security/wizard.html"
    form_list = (("auth", PasswordForm), ("token", TokenForm))
    condition_dict = {"token": lambda view: bool(view.get_device()) and not view.remember_agent}

    def get_user(self):
        user = super().get_user()
        challenge_id = self.storage.data.get("security_challenge")
        if user and challenge_id:
            challenge = LoginChallenge.objects.filter(pk=challenge_id, user=user, used_at__isnull=True,
                                                       expires_at__gt=timezone.now()).first()
            if (challenge is None or not services.available(user)
                    or challenge.version != services.state_for(user).version
                    or not constant_time_compare(challenge.credential_hash, user.get_session_auth_hash())):
                raise PermissionDenied()
        return user

    def get_device(self, step=None):
        user = self.get_user()
        return services.authenticator(user) if user else None

    @property
    def remember_agent(self):
        user = self.get_user()
        return bool(user and services.remembered(self.request, user, services.state_for(user)))

    def get_form(self, step=None, **kwargs):
        return IdempotentSessionWizardView.get_form(self, step=step, **kwargs)

    def get_context_data(self, form, **kwargs):
        return IdempotentSessionWizardView.get_context_data(self, form=form, **kwargs)

    @sensitive_variables()
    def process_step(self, form):
        result = super().process_step(form)
        if self.steps.current == "auth":
            self.storage.data["security_challenge"] = str(form.challenge.pk)
        elif self.steps.current == "token":
            self.storage.data["security_device"] = form.user.otp_device.pk
            self.storage.data["security_remember"] = bool(form.cleaned_data.get("remember"))
        return result

    @sensitive_variables()
    def done(self, form_list, **kwargs):
        user = self.get_user()
        level, raw = services.complete_login(self.request, user.pk,
            self.storage.data.get("security_challenge"),
            self.storage.data.get("security_device"), self.storage.data.get("security_remember", False))
        response = redirect("/auth/mfa/setup/" if level == "enroll" else "/auth/security/")
        if raw:
            response.set_cookie(settings.SECURITY_TRUST_COOKIE, raw,
                max_age=settings.SECURITY_TRUST_SECONDS, secure=settings.SESSION_COOKIE_SECURE,
                httponly=True, samesite="Lax", path="/auth/")
        return response


class EncryptedGenerator(GeneratorMethod):
    def get_setup_forms(self, wizard):
        return {"generator": EnrollmentForm}

    def get_devices(self, user):
        return Authenticator.objects.filter(user=user, confirmed=True, revoked_at__isnull=True)


@method_decorator([sensitive_post_parameters(), csrf_protect], name="dispatch")
class PersonalSetup(StrictWizard, SetupView):
    allowed_steps = frozenset({"welcome", "generator"})
    template_name = "account_security/wizard.html"
    qrcode_url = "account_security:qr"
    form_list = (("welcome", forms.Form), ("generator", EnrollmentForm))

    def get(self, request, *args, **kwargs):
        return IdempotentSessionWizardView.get(self, request, *args, **kwargs)

    def get_form_list(self):
        return IdempotentSessionWizardView.get_form_list(self)

    def get_available_methods(self):
        return [EncryptedGenerator()]

    def get_method(self):
        return EncryptedGenerator()

    def get_key(self, step):
        device = Authenticator.objects.filter(pk=self.request.session.get("security_setup_id"),
            user=self.request.user, confirmed=False, revoked_at__isnull=True,
            enrollment_hash=self.request.security_session.session_hash,
            expires_at__gt=timezone.now()).first()
        if device is None:
            raise PermissionDenied()
        return device.key

    def process_step(self, form):
        if self.steps.current == "welcome":
            services.begin_enrollment(self.request)
        return super().process_step(form)

    @sensitive_variables()
    def done(self, form_list, **kwargs):
        codes = services.finish_enrollment(self.request, self.request.session.get("security_setup_id"))
        return render(self.request, "account_security/codes.html", {"codes": codes})


class PersonalQR(QRGeneratorView):
    def get(self, request, *args, **kwargs):
        if not Authenticator.objects.filter(pk=request.session.get("security_setup_id"), user=request.user,
            confirmed=False, revoked_at__isnull=True, expires_at__gt=timezone.now(),
            enrollment_hash=request.security_session.session_hash).exists():
            raise PermissionDenied()
        return super().get(request, *args, **kwargs)


@never_cache
@login_required
@require_GET
def panel(request):
    return render(request, "account_security/panel.html", {
        "current_session_id": request.security_session.pk,
        "sessions": AccountSession.objects.filter(user=request.user, revoked_at__isnull=True,
                                                   expires_at__gt=timezone.now()).order_by("created_at"),
        "devices": TrustedDevice.objects.filter(user=request.user, revoked_at__isnull=True,
                                                 expires_at__gt=timezone.now()),
        "mfa_required": services.required(request.user),
        "mfa_enabled": services.authenticator(request.user) is not None,
    })


@never_cache
@sensitive_post_parameters()
@csrf_protect
@login_required
def confirm(request):
    form = ConfirmForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if services.reauthenticate(request, **form.cleaned_data):
            return redirect("/auth/security/")
        form.add_error(None, "Подтверждение не принято.")
    return render(request, "account_security/form.html", {"form": form, "title": "Повторное подтверждение"})


@never_cache
@sensitive_post_parameters()
@csrf_protect
def recovery(request, operator=False):
    form = RecoveryForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        values = form.cleaned_data
        action = services.consume_operator_recovery if operator else services.recover_with_code
        if action(request, values["username"], values["password"], values["code"]):
            return redirect("/auth/mfa/setup/")
        form.add_error(None, "Восстановление не разрешено.")
    return render(request, "account_security/form.html", {"form": form, "title": "Восстановление второго фактора"})


@mutation("session_revoke", [])
def revoke_session(request, session_id):
    if not request.user.is_authenticated or not services.fresh(request.security_session,
            factor=services.authenticator(request.user) is not None):
        raise PermissionDenied()
    services.logout(request, selected=session_id)
    return JsonResponse({"status": "ok"})


@mutation("logout_all", [])
def logout_all(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    services.logout(request, all_sessions=True)
    response = JsonResponse({"status": "ok"})
    response.delete_cookie(settings.SECURITY_TRUST_COOKIE, path="/auth/")
    return response


@mutation("device_revoke", [])
def revoke_device(request, device_id):
    if not request.user.is_authenticated or not services.fresh(request.security_session):
        raise PermissionDenied()
    with transaction.atomic():
        user, state = services.locked_user(request.user.pk)
        services.assert_actor_session(user)
        device = TrustedDevice.objects.select_for_update().get(pk=device_id, user=user)
        now = timezone.now()
        device.revoked_at = now
        device.save(update_fields=["revoked_at"])
        sessions = AccountSession.objects.filter(user=user, trusted_device=device)
        sessions.filter(revoked_at__isnull=True).update(revoked_at=now)
        ExportPermit.objects.filter(session__in=sessions, revoked_at__isnull=True).update(revoked_at=now)
        services.event(user, "device_revoked")
    return JsonResponse({"status": "ok"})


@mutation("mfa_disable", [])
def disable(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    services.disable(request)
    return JsonResponse({"status": "ok"})


@never_cache
@sensitive_post_parameters()
@csrf_protect
@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user, state = services.locked_user(request.user.pk)
            services.assert_actor_session(user)
            record = AccountSession.objects.get(pk=request.security_session.pk)
            if not services.fresh(record, factor=services.authenticator(user) is not None):
                raise PermissionDenied()
            # Validate again under the User lock against concurrent password changes.
            form = PasswordChangeForm(user, request.POST)
            if not form.is_valid():
                raise PermissionDenied()
            form.save(commit=False)
            user.save(update_fields=["password"])
            services.credentials_changed(user, "password_changed")
        services.django_logout(request)
        return redirect("/auth/mfa/login/")
    return render(request, "account_security/form.html", {"form": form, "title": "Смена пароля"})


@never_cache
@login_required
@require_GET
def download(request, permit_id):
    return HttpResponse(services.read_export_probe(request, permit_id), content_type="text/csv")
