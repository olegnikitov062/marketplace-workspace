from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from two_factor.forms import AuthenticationTokenForm, TOTPDeviceForm

from accounts.limits import allow_attempt, denied
from ownership.models import User
from . import services
from .models import Authenticator, LoginChallenge


class PasswordForm(AuthenticationForm):
    @sensitive_variables()
    def clean(self):
        username = User.normalize_username(self.cleaned_data.get("username", ""))
        if not allow_attempt("mfa_login", self.request.META.get("REMOTE_ADDR", ""), username):
            denied("mfa_login_limited")
            raise forms.ValidationError("Попробуйте позже.")
        with transaction.atomic():
            User.objects.select_for_update().filter(username=username).first()
            result = super().clean()
            user = self.get_user()
            state = services.state_for(user, lock=True)
            self.challenge = LoginChallenge.objects.create(user=user, version=state.version,
                credential_hash=user.get_session_auth_hash(),
                expires_at=timezone.now() + timedelta(seconds=settings.SECURITY_CHALLENGE_SECONDS))
            return result


class TokenForm(AuthenticationTokenForm):
    remember = forms.BooleanField(required=False, initial=False, label="Запомнить устройство на 30 дней")

    def __init__(self, user, initial_device, request=None, **kwargs):
        self.request = request
        super().__init__(user, initial_device, **kwargs)

    def _chosen_device(self, user):
        return Authenticator.objects.select_for_update().filter(pk=self.initial_device.pk,
            user=user, confirmed=True, revoked_at__isnull=True).first() if self.initial_device else None

    @sensitive_variables()
    def clean(self):
        if not allow_attempt("totp", self.request.META.get("REMOTE_ADDR", ""), str(self.user.pk)):
            denied("totp_limited")
            raise forms.ValidationError("Попробуйте позже.")
        # Upstream clean_otp commits throttle counters even when validation fails.
        return super().clean()


class EnrollmentForm(TOTPDeviceForm):
    idempotent = False

    def __init__(self, key, user, request=None, metadata=None, **kwargs):
        self.request = request
        super().__init__(key, user, metadata=metadata, **kwargs)

    @sensitive_variables()
    def clean_token(self):
        if not allow_attempt("enroll", self.request.META.get("REMOTE_ADDR", ""), str(self.user.pk)):
            denied("enrollment_limited")
            raise forms.ValidationError("Попробуйте позже.")
        token = self.cleaned_data["token"]
        device_id = self.request.session.get("security_setup_id")
        device = services.verify_factor(self.user.pk, token, device_id, enrollment=True,
            enrollment_hash=self.request.security_session.session_hash)
        if device is None or device.enrollment_hash != self.request.security_session.session_hash:
            denied("enrollment_code_denied")
            raise forms.ValidationError("Код не принят.")
        self.request.session["security_setup_verified"] = device.pk
        return token


class ConfirmForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, max_length=512, label="Пароль")
    token = forms.CharField(widget=forms.PasswordInput, max_length=64, required=False, label="TOTP")


class RecoveryForm(forms.Form):
    username = forms.CharField(max_length=150, label="Логин")
    password = forms.CharField(widget=forms.PasswordInput, max_length=512, label="Пароль")
    code = forms.CharField(widget=forms.PasswordInput, max_length=128, label="Код восстановления")
