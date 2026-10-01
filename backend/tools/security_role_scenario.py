"""Synthetic E2-06 HTTP scenario reusable with a real limited PostgreSQL LOGIN.

No assertions render submitted values, response bodies, links or cookies.
"""
import re
import secrets
import time
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import Client, override_settings
from django.utils import timezone
from django_otp.oath import TOTP

from accounts.models import AccountContact
from ownership.models import User, Organization, Membership
from tools.account_role_scenario import expect, post


def seed():
    a = Organization.objects.create(name="synthetic-security-a")
    b = Organization.objects.create(name="synthetic-security-b")
    password = secrets.token_urlsafe(24)
    user = User.objects.create_user("synthetic-security-owner", password)
    Membership.objects.create(user=user, organization=a, role="owner")
    Membership.objects.create(user=user, organization=b, role="observer")
    AccountContact.objects.create(user=user, email="security@example.invalid", activated_at=timezone.now())
    return {"user_id": user.pk, "username": user.username, "password": password, "a": a.pk, "b": b.pk}


def password_step(client, fixture):
    client.get("/auth/mfa/login/", secure=True)
    return post(client, "/auth/mfa/login/", {"personal_login-current_step": "auth",
        "auth-username": fixture["username"], "auth-password": fixture["password"]})


def code_for(device):
    tick = max(int(time.time() // 30), device.last_t + 1)
    otp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    otp.time = tick * 30 + 1
    return str(otp.token()).zfill(6), otp.time


def finish_setup(client, fixture):
    from account_security.models import Authenticator
    expect(client.get("/auth/mfa/setup/", secure=True).status_code == 200, "setup_page")
    expect(post(client, "/auth/mfa/setup/", {"personal_setup-current_step": "welcome"}).status_code == 200, "setup_started")
    device = Authenticator.objects.get(user_id=fixture["user_id"], confirmed=False, revoked_at__isnull=True)
    code, now = code_for(device)
    with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
        result = post(client, "/auth/mfa/setup/", {"personal_setup-current_step": "generator", "generator-token": code})
    expect(result.status_code == 200, "setup_confirmed")
    codes = [value.decode() for value in re.findall(rb"<code>([^<]+)</code>", result.content)]
    expect(len(codes) == settings.SECURITY_RECOVERY_CODE_COUNT, "recovery_codes_once")
    expect(client.get("/auth/session", secure=True).status_code == 401, "setup_revokes_session")
    device.refresh_from_db()
    return device, codes


def login(client, fixture, remember=False):
    from account_security.services import authenticator
    result = password_step(client, fixture)
    if result.status_code == 200:
        device = authenticator(User.objects.get(pk=fixture["user_id"]))
        code, now = code_for(device)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            result = post(client, "/auth/mfa/login/", {"personal_login-current_step": "token",
                "token-otp_token": code, "token-remember": "on" if remember else ""})
    expect(result.status_code == 302, "login_complete")
    expect(client.get("/auth/session", secure=True).status_code == 200, "full_session")


def operator_action(action, fixture):
    from accounts.services import block_account
    from account_security.services import issue_operator_recovery
    if action == "demote":
        Membership.objects.filter(user_id=fixture["user_id"], organization_id=fixture["a"]).update(role="observer")
    elif action == "restore_role":
        Membership.objects.filter(user_id=fixture["user_id"], organization_id=fixture["a"]).update(role="owner")
    elif action == "recover":
        return issue_operator_recovery(fixture["user_id"])
    elif action == "block":
        block_account(fixture["user_id"])
    else:
        raise RuntimeError("unknown_operator_action")


def run(fixture, operator):
    from account_security import services
    from account_security.models import AccountSession, TrustedDevice, RecoveryCode
    from django.db import connection
    client = Client(enforce_csrf_checks=True)
    expect(post(client, "/auth/mfa/login/", {}, csrf=False).status_code == 403, "csrf_required")
    expect(password_step(client, fixture).status_code == 302, "owner_password_stage")
    expect(client.get("/auth/session", secure=True).status_code == 403, "no_full_session_before_mfa")
    device, codes = finish_setup(client, fixture)
    with connection.cursor() as cursor:
        cursor.execute("SELECT key FROM account_security_authenticator WHERE id=%s", [device.pk])
        expect(device.key not in cursor.fetchone()[0], "totp_encrypted")
    expect(all(row.startswith("pbkdf2_sha256$") for row in RecoveryCode.objects.values_list("verifier", flat=True)), "codes_hashed")
    login(client, fixture, remember=True)
    expect(TrustedDevice.objects.filter(user_id=fixture["user_id"], revoked_at__isnull=True).count() == 1, "trusted_registry")
    expect(post(client, "/auth/security/disable/").status_code == 403, "owner_cannot_disable")
    user = User.objects.get(pk=fixture["user_id"])
    record = AccountSession.objects.get(session_hash=services.digest(client.cookies[settings.SESSION_COOKIE_NAME].value))
    with override_settings(SECURITY_DOWNLOAD_PROBE=True):
        permit = services.issue_export_probe(user, Organization.objects.get(pk=fixture["a"]), record)
        path = f"/auth/security/probe/{permit.pk}/"
        expect(client.get(path, secure=True).status_code == 200, "probe_download")
        expect(Client().get(path, secure=True).status_code != 200, "probe_not_public")
        operator("demote", fixture)
        invitation = {"organization_id": str(fixture["a"]), "username": "synthetic-probe-new", "email": "probe@example.invalid", "role": "observer"}
        expect(post(client, "/auth/invitations", invitation).status_code == 403, "live_role_change")
        expect(client.get(path, secure=True).status_code == 403, "old_link_revoked")
        operator("restore_role", fixture)
        expect(client.get(path, secure=True).status_code == 403, "old_link_does_not_revive")
        invitation["organization_id"] = str(fixture["b"])
        expect(post(client, "/auth/invitations", invitation).status_code == 403, "foreign_org")
    # Recovery consumes only an operator-issued permit; no web issuance privilege.
    permit = operator("recover", fixture)
    expect(client.get("/auth/session", secure=True).status_code == 401, "operator_revoked_session")
    recovery = Client(enforce_csrf_checks=True)
    values = {"username": fixture["username"], "password": fixture["password"], "code": permit}
    expect(post(recovery, "/auth/mfa/operator-recovery/", values).status_code == 302, "operator_permit_consumed")
    expect(recovery.get("/auth/session", secure=True).status_code == 403, "recovery_is_restricted")
    expect(post(Client(enforce_csrf_checks=True), "/auth/mfa/operator-recovery/", values).status_code != 302, "operator_permit_single_use")
    finish_setup(recovery, fixture)
    login(recovery, fixture)
    operator("block", fixture)
    expect(recovery.get("/auth/session", secure=True).status_code == 401, "block_revokes_session")
    expect(password_step(Client(enforce_csrf_checks=True), fixture).status_code != 302, "blocked_login")
    expect(settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend", "locmem_only")
    expect(not getattr(mail, "outbox", []), "no_external_or_unexpected_delivery")
