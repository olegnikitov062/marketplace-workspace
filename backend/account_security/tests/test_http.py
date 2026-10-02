"""Synthetic HTTP/library integration. Credential assertions never render values."""
import json
import secrets
import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from cryptography.fernet import Fernet
from django.conf import settings
from django.core import mail
from django.db import connection, transaction, IntegrityError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django_otp.oath import TOTP

from accounts.models import AccountContact, AttemptBucket
from accounts import services as accounts
from ownership.models import User, Organization, Membership
from account_security import services
from account_security.models import (AccountSecurity, AccountSession, Authenticator, ExportPermit,
                                    RecoveryCode, TrustedDevice, LoginChallenge)


@override_settings(SECURITY_RECOVERY_CODE_COUNT=2, SECURITY_DOWNLOAD_PROBE=True)
class SecurityHTTPTests(TestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(24)
        self.owner = User.objects.create_user("synthetic-owner", self.password)
        self.member = User.objects.create_user("synthetic-member", self.password)
        self.a = Organization.objects.create(name="synthetic-a")
        self.b = Organization.objects.create(name="synthetic-b")
        Membership.objects.create(user=self.owner, organization=self.a, role="owner")
        Membership.objects.create(user=self.owner, organization=self.b, role="observer")
        Membership.objects.create(user=self.member, organization=self.a, role="observer")
        AccountContact.objects.create(user=self.owner, email="owner@example.invalid", activated_at=timezone.now())
        AccountContact.objects.create(user=self.member, email="member@example.invalid", activated_at=timezone.now())
        self.client = Client(enforce_csrf_checks=True)

    def post(self, path, data=None, client=None, csrf=True):
        client = client or self.client
        headers = {"HTTP_ORIGIN": "https://testserver"}
        if csrf:
            headers["HTTP_X_CSRFTOKEN"] = client.get("/auth/csrf", secure=True).json()["csrfToken"]
        return client.post(path, urlencode(data or {}), content_type="application/x-www-form-urlencoded",
                           secure=True, **headers)

    def start_login(self, user=None, client=None, password=None):
        user = user or self.owner
        client = client or self.client
        client.get("/auth/mfa/login/", secure=True)
        return self.post("/auth/mfa/login/", {"personal_login-current_step": "auth",
            "auth-username": user.username, "auth-password": password or self.password}, client)

    def otp(self, device, step=None):
        tick = step if step is not None else max(int(time.time() // 30), device.last_t + 1)
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = tick * 30 + 1
        return str(totp.token()).zfill(6), tick * 30 + 1

    def enroll(self, user=None, client=None):
        user = user or self.owner
        client = client or self.client
        self.start_login(user, client)
        self.assertEqual(client.get("/auth/mfa/setup/", secure=True).status_code, 200)
        result = self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"}, client)
        self.assertEqual(result.status_code, 200)
        device = Authenticator.objects.get(user=user, confirmed=False, revoked_at__isnull=True)
        code, now = self.otp(device)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            response = self.post("/auth/mfa/setup/", {"personal_setup-current_step": "generator", "generator-token": code}, client)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context is not None and "codes" in response.context)
        codes = response.context["codes"]
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        self.assertEqual(client.get("/auth/session", secure=True).status_code, 401)
        return device, codes

    def login(self, user=None, client=None, remember=False):
        user = user or self.owner
        client = client or self.client
        result = self.start_login(user, client)
        device = services.authenticator(user)
        if device and result.status_code == 200:
            code, now = self.otp(device)
            with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
                result = self.post("/auth/mfa/login/", {"personal_login-current_step": "token",
                    "token-otp_token": code, "token-remember": "on" if remember else ""}, client)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(client.get("/auth/session", secure=True).status_code, 200)
        return client

    def record(self, client=None):
        client = client or self.client
        return AccountSession.objects.get(session_hash=services.digest(client.cookies[settings.SESSION_COOKIE_NAME].value))

    def test_owner_requires_confirmed_factor_and_get_does_not_enroll(self):
        result = self.start_login()
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 403)
        self.assertEqual(self.post("/auth/invitations", {"organization_id": str(self.a.pk), "username": "synthetic-new",
            "email": "new@example.invalid", "role": "observer"}).status_code, 403)
        self.client.get("/auth/mfa/setup/", secure=True)
        self.assertEqual(Authenticator.objects.count(), 0)
        self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"})
        self.assertFalse(Authenticator.objects.get(user=self.owner).confirmed)

    def test_pending_wizard_secret_is_encrypted_before_confirmation(self):
        from django.contrib.sessions.models import Session
        self.start_login()
        self.client.get("/auth/mfa/setup/", secure=True)
        self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"})
        device = Authenticator.objects.get(user=self.owner, confirmed=False, revoked_at__isnull=True)
        from base64 import b32encode
        rawkey = b32encode(device.bin_key).decode()
        qr = self.client.get("/auth/mfa/qr/", secure=True)
        self.assertEqual(qr.status_code, 200)
        self.assertTrue(qr["Content-Type"].startswith("image/svg+xml"))
        self.assertIn("no-store", qr["Cache-Control"])
        rows = list(Session.objects.values_list("session_data", flat=True))
        self.assertTrue(bool(rows) and all(row.startswith("mfa1:") for row in rows))
        self.assertTrue(all(device.key not in row and rawkey not in row and self.password not in row for row in rows))
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            from django.core import serializers
            serializers.serialize("json", [device])
        result = self.post("/auth/mfa/setup/", {"personal_setup-current_step": "generator", "generator-token": "not-a-code"})
        self.assertEqual(result.status_code, 200)
        self.assertFalse(Authenticator.objects.get(user=self.owner).confirmed)

    def test_enrollment_encryption_hashes_and_no_plaintext_session(self):
        device, codes = self.enroll()
        from django.contrib.sessions.models import Session
        with connection.cursor() as cursor:
            cursor.execute("SELECT key FROM account_security_authenticator WHERE id=%s", [device.pk])
            encrypted = cursor.fetchone()[0]
        self.assertFalse(device.key in encrypted)
        from account_security.crypto import cipher
        self.assertTrue(cipher().decrypt(encrypted.encode()).decode() == device.key)
        self.assertTrue(all(c.verifier.startswith("pbkdf2_sha256$") for c in RecoveryCode.objects.all()))
        for session in Session.objects.all():
            self.assertFalse(device.key in session.session_data)
            self.assertTrue(all(code not in session.session_data for code in codes))
        self.assertFalse(any(code in " ".join(RecoveryCode.objects.values_list("verifier", flat=True)) for code in codes))

    def test_login_good_bad_expired_replayed_totp_and_no_full_session(self):
        device, _ = self.enroll()
        self.start_login()
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        old, now = self.otp(device, device.last_t - 4)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now + 120):
            self.post("/auth/mfa/login/", {"personal_login-current_step": "token", "token-otp_token": old})
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        device.refresh_from_db()
        valid, current = self.otp(device)
        # Advance beyond the library throttle delay without relying on sleep.
        Authenticator.objects.filter(pk=device.pk).update(throttling_failure_timestamp=timezone.now()-timedelta(minutes=1))
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=current):
            response = self.post("/auth/mfa/login/", {"personal_login-current_step": "token", "token-otp_token": valid})
        self.assertEqual(response.status_code, 302)
        other = Client(enforce_csrf_checks=True)
        self.start_login(client=other)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=current):
            self.post("/auth/mfa/login/", {"personal_login-current_step": "token", "token-otp_token": valid}, other)
        self.assertEqual(other.get("/auth/session", secure=True).status_code, 401)

    def test_optional_member_password_login_and_promotion_applies_immediately(self):
        self.login(self.member)
        Membership.objects.filter(user=self.member, organization=self.a).update(role="owner")
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.start_login(self.member)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 403)

    def test_legacy_password_endpoint_cannot_bypass_mfa(self):
        self.assertEqual(self.post("/auth/login", {"username": self.owner.username, "password": self.password}).status_code, 409)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)

    def test_logout_current_preserves_other_session_and_all_revokes(self):
        self.login(self.member)
        other = self.login(self.member, Client(enforce_csrf_checks=True))
        self.assertEqual(self.post("/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.assertEqual(other.get("/auth/session", secure=True).status_code, 200)
        self.assertEqual(self.post("/auth/security/logout-all/", client=other).status_code, 200)
        self.assertEqual(other.get("/auth/session", secure=True).status_code, 401)

    def test_remembered_device_requires_password_and_is_revoked_globally(self):
        self.enroll()
        self.login(remember=True)
        self.assertEqual(TrustedDevice.objects.count(), 1)
        self.assertTrue(self.client.cookies[settings.SECURITY_TRUST_COOKIE]["httponly"])
        self.assertTrue(self.client.cookies[settings.SECURITY_TRUST_COOKIE]["secure"])
        self.post("/auth/logout")
        self.start_login(password=secrets.token_urlsafe(24))
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.assertEqual(self.start_login().status_code, 302)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 200)
        self.assertIsNone(self.record().factor_confirmed_at)
        stolen_cookie = self.client.cookies[settings.SECURITY_TRUST_COOKIE].value
        self.post("/auth/security/logout-all/")
        self.assertTrue(TrustedDevice.objects.get().revoked_at is not None)
        self.client.cookies[settings.SECURITY_TRUST_COOKIE] = stolen_cookie
        self.assertEqual(self.start_login().status_code, 200)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)

    def test_idle_and_absolute_expiry(self):
        self.login(self.member)
        record = self.record()
        with patch("account_security.services.timezone.now", return_value=record.last_seen+timedelta(hours=1)):
            self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.login(self.member)
        record = self.record()
        with patch("account_security.services.timezone.now", return_value=record.expires_at):
            self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)

    def test_recovery_code_is_one_time_restricts_scope_and_keeps_old_factor_until_confirmed(self):
        device, codes = self.enroll()
        self.login()
        old_client = self.client
        recovery = Client(enforce_csrf_checks=True)
        before = list(Membership.objects.order_by("pk").values_list("id", "organization_id", "user_id", "role", "state"))
        response = self.post("/auth/mfa/recovery/", {"username": self.owner.username,
            "password": self.password, "code": codes[0]}, recovery)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(old_client.get("/auth/session", secure=True).status_code, 401)
        self.assertEqual(recovery.get("/auth/session", secure=True).status_code, 403)
        self.assertTrue(Authenticator.objects.get(pk=device.pk).confirmed)
        repeated = Client(enforce_csrf_checks=True)
        self.post("/auth/mfa/recovery/", {"username": self.owner.username, "password": self.password, "code": codes[0]}, repeated)
        self.assertEqual(repeated.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(before == list(Membership.objects.order_by("pk").values_list("id", "organization_id", "user_id", "role", "state")))

    def test_password_reset_preserves_mfa_and_revokes_all(self):
        device, _ = self.enroll()
        self.login(remember=True)
        accounts.request_recovery(self.owner.username)
        data = json.loads(mail.outbox[-1].body)
        new_password = secrets.token_urlsafe(24)
        accounts.confirm_recovery(data["user_id"], data["token"], new_password, new_password)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(Authenticator.objects.get(pk=device.pk).confirmed)
        self.assertTrue(TrustedDevice.objects.get().revoked_at is not None)
        self.assertEqual(self.start_login(password=new_password).status_code, 200)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)

    def test_block_denies_sessions_login_recovery_operator_and_invite(self):
        _, codes = self.enroll()
        self.login(remember=True)
        accounts.block_account(self.owner.pk)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.start_login()
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.post("/auth/mfa/recovery/", {"username": self.owner.username, "password": self.password, "code": codes[0]})
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.assertFalse(accounts.request_recovery(self.owner.username))
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.issue_operator_recovery(self.owner.pk)

    def test_membership_change_denies_real_invitation_and_permanently_revokes_probe(self):
        self.enroll()
        self.login()
        permit = services.issue_export_probe(self.owner, self.a, self.record())
        url = f"/auth/security/probe/{permit.pk}/"
        self.assertEqual(self.client.get(url, secure=True).status_code, 200)
        Membership.objects.filter(user=self.owner, organization=self.a).update(role="observer")
        self.assertEqual(self.post("/auth/invitations", {"organization_id": str(self.a.pk), "username": "synthetic-new",
            "email": "new@example.invalid", "role": "observer"}).status_code, 403)
        self.assertEqual(self.client.get(url, secure=True).status_code, 403)
        Membership.objects.filter(user=self.owner, organization=self.a).update(role="owner")
        self.assertEqual(self.client.get(url, secure=True).status_code, 403)

    def test_probe_not_bearer_and_cross_organization_denied(self):
        self.login(self.member)
        permit = services.issue_export_probe(self.member, self.a, self.record())
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.issue_export_probe(self.member, self.b, self.record())
        self.assertEqual(Client().get(f"/auth/security/probe/{permit.pk}/", secure=True).status_code, 302)
        second = self.login(self.member, Client(enforce_csrf_checks=True))
        self.assertEqual(second.get(f"/auth/security/probe/{permit.pk}/", secure=True).status_code, 403)

    def test_csrf_mutations_and_headers(self):
        self.assertEqual(self.post("/auth/mfa/login/", {}, csrf=False).status_code, 403)
        self.login(self.member)
        for path in ["/auth/mfa/setup/", "/auth/security/confirm/", "/auth/security/password/",
                     "/auth/security/logout-all/", "/auth/security/disable/", "/auth/mfa/recovery/",
                     "/auth/mfa/operator-recovery/", "/auth/logout"]:
            self.assertEqual(self.post(path, {}, csrf=False).status_code, 403)
        response = self.client.get("/auth/security/", secure=True)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Referrer-Policy"], "same-origin")

    def test_native_form_origin_is_required_even_with_valid_csrf_token(self):
        path = "/auth/mfa/login/"
        self.client.get(path, secure=True)
        token = self.client.get("/auth/csrf", secure=True).json()["csrfToken"]
        form = urlencode({"personal_login-current_step": "auth",
            "auth-username": self.owner.username, "auth-password": self.password,
            "csrfmiddlewaretoken": token})
        for origin in ("null", "https://example.invalid"):
            response = self.client.post(path, form, content_type="application/x-www-form-urlencoded",
                secure=True, HTTP_ORIGIN=origin)
            self.assertEqual(response.status_code, 403)
        self.assertEqual(LoginChallenge.objects.count(), 0)
        self.assertEqual(AttemptBucket.objects.count(), 0)
        response = self.client.post(path, form, content_type="application/x-www-form-urlencoded",
            secure=True, HTTP_ORIGIN="https://testserver")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/auth/mfa/setup/")
        partial = self.client.get("/auth/session", secure=True)
        self.assertEqual(partial.status_code, 403)
        self.assertEqual(partial["Referrer-Policy"], "same-origin")
        self.assertEqual(AccountSession.objects.filter(level="full").count(), 0)

    def test_wrong_encryption_key_fails_closed(self):
        self.login(self.member)
        with override_settings(MFA_TEST_KEY=Fernet.generate_key()):
            self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)

    def test_revoked_record_cannot_be_reactivated_by_sql(self):
        self.login(self.member)
        record = self.record()
        self.post("/auth/logout")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountSession.objects.filter(pk=record.pk).update(revoked_at=None)

    def test_operator_recovery_is_single_use_scope_preserved_and_mfa_not_disabled(self):
        device, _ = self.enroll()
        self.login(remember=True)
        before = list(Membership.objects.order_by("pk").values_list("user_id", "organization_id", "role", "state"))
        permit = services.issue_operator_recovery(self.owner.pk)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        guest = Client(enforce_csrf_checks=True)
        response = self.post("/auth/mfa/operator-recovery/", {"username": self.owner.username,
            "password": self.password, "code": permit}, guest)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(guest.get("/auth/session", secure=True).status_code, 403)
        other = Client(enforce_csrf_checks=True)
        self.post("/auth/mfa/operator-recovery/", {"username": self.owner.username,
            "password": self.password, "code": permit}, other)
        self.assertEqual(other.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(Authenticator.objects.get(pk=device.pk).confirmed)
        self.assertTrue(before == list(Membership.objects.order_by("pk").values_list("user_id", "organization_id", "role", "state")))

    def test_recovery_finishes_replacement_then_requires_new_login(self):
        old_device, codes = self.enroll()
        self.post("/auth/mfa/recovery/", {"username": self.owner.username, "password": self.password, "code": codes[0]})
        self.client.get("/auth/mfa/setup/", secure=True)
        self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"})
        pending = Authenticator.objects.get(user=self.owner, confirmed=False, revoked_at__isnull=True)
        code, now = self.otp(pending)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            result = self.post("/auth/mfa/setup/", {"personal_setup-current_step": "generator", "generator-token": code})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(Authenticator.objects.get(pk=old_device.pk).revoked_at is not None)
        self.assertTrue(Authenticator.objects.get(pk=pending.pk).confirmed)
        self.assertFalse(AccountSecurity.objects.get(user=self.owner).recovery_required)
        self.login()

    def test_owner_cannot_disable_optional_member_can_after_confirmation(self):
        self.enroll()
        self.login()
        self.assertEqual(self.post("/auth/security/disable/").status_code, 403)
        self.post("/auth/logout")
        self.enroll(self.member)
        self.login(self.member)
        self.assertEqual(self.post("/auth/security/disable/").status_code, 200)
        self.assertIsNone(services.authenticator(self.member))
        self.login(self.member)

    def test_password_change_revokes_other_session_and_trust(self):
        self.enroll()
        self.login(remember=True)
        other = self.login(client=Client(enforce_csrf_checks=True))
        new_password = secrets.token_urlsafe(24)
        response = self.post("/auth/security/password/", {"old_password": self.password,
            "new_password1": new_password, "new_password2": new_password})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(other.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(TrustedDevice.objects.get().revoked_at is not None)
        self.assertIsNotNone(services.authenticator(self.owner))

    def test_sensitive_change_requires_recent_totp_even_for_trusted_login(self):
        self.enroll()
        self.login(remember=True)
        self.post("/auth/logout")
        self.login()
        self.client.get("/auth/mfa/setup/", secure=True)
        self.assertEqual(self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"}).status_code, 403)
        device = services.authenticator(self.owner)
        code, now = self.otp(device)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            self.assertEqual(self.post("/auth/security/confirm/", {"password": self.password, "token": code}).status_code, 302)
        self.client.get("/auth/mfa/setup/", secure=True)
        self.assertEqual(self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"}).status_code, 200)

    def test_selected_session_and_device_revocation_reject_foreign_ids(self):
        self.login(self.member)
        first = self.record()
        other = self.login(self.member, Client(enforce_csrf_checks=True))
        second = self.record(other)
        self.assertEqual(self.post(f"/auth/security/sessions/{second.pk}/revoke/").status_code, 200)
        self.assertEqual(other.get("/auth/session", secure=True).status_code, 401)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 200)
        stranger = User.objects.create_user("synthetic-stranger", self.password)
        stranger_client = self.login(stranger, Client(enforce_csrf_checks=True))
        self.assertEqual(self.post(f"/auth/security/sessions/{first.pk}/revoke/", client=stranger_client).status_code, 400)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 200)

    def test_challenge_expiry_and_password_change_cannot_finish_mfa(self):
        self.enroll()
        self.start_login()
        LoginChallenge.objects.filter(user=self.owner, used_at__isnull=True).exists()
        self.owner.refresh_from_db()
        self.owner.set_password(secrets.token_urlsafe(24))
        self.owner.save(update_fields=["password"])
        device = services.authenticator(self.owner)
        code, now = self.otp(device)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            response = self.post("/auth/mfa/login/", {"personal_login-current_step": "token", "token-otp_token": code})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)

    def test_attempt_limits_survive_new_cookie_and_wrong_factor(self):
        self.enroll()
        device = services.authenticator(self.owner)
        for _ in range(settings.ACCOUNT_PRINCIPAL_LIMIT + 1):
            guest = Client(enforce_csrf_checks=True)
            self.start_login(client=guest, password=secrets.token_urlsafe(24))
        guest = Client(enforce_csrf_checks=True)
        self.start_login(client=guest)
        self.assertEqual(guest.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(AttemptBucket.objects.filter(attempts__gt=settings.ACCOUNT_PRINCIPAL_LIMIT).exists())

    def test_totp_throttle_counter_and_enrollment_replay(self):
        device, _ = self.enroll()
        code, now = self.otp(device, device.last_t)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            self.assertIsNone(services.verify_factor(self.owner.pk, code, device.pk))
        device.refresh_from_db()
        self.assertGreater(device.throttling_failure_count, 0)

    def test_untrusted_wizard_step_is_not_logged(self):
        secret = secrets.token_urlsafe(24)
        with self.assertNoLogs("two_factor", level="WARNING"):
            result = self.post("/auth/mfa/login/", {"personal_login-current_step": secret})
        self.assertEqual(result.status_code, 400)

    def test_login_challenge_expires_after_five_minutes(self):
        self.enroll()
        self.start_login()
        challenge = LoginChallenge.objects.filter(user=self.owner, used_at__isnull=True).latest("expires_at")
        with patch("account_security.views.timezone.now", return_value=challenge.expires_at):
            result = self.post("/auth/mfa/login/", {"personal_login-current_step": "token", "token-otp_token": "000000"})
        self.assertEqual(result.status_code, 403)

    def test_selected_trusted_device_revokes_its_sessions_and_link(self):
        self.enroll()
        self.login(remember=True)
        device = TrustedDevice.objects.get()
        remembered = Client(enforce_csrf_checks=True)
        remembered.cookies[settings.SECURITY_TRUST_COOKIE] = self.client.cookies[settings.SECURITY_TRUST_COOKIE].value
        self.login(client=remembered)
        permit = services.issue_export_probe(self.owner, self.a, self.record(remembered))
        self.assertEqual(self.post(f"/auth/security/devices/{device.pk}/revoke/").status_code, 200)
        self.assertEqual(remembered.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(ExportPermit.objects.get(pk=permit.pk).revoked_at is not None)
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 200)

    def test_fresh_confirmation_expires_at_five_minutes(self):
        self.enroll()
        self.login()
        record = self.record()
        with patch("account_security.services.timezone.now", return_value=record.password_confirmed_at + timedelta(minutes=5)):
            self.assertFalse(services.fresh(record))

    def test_pending_factor_cannot_be_consumed_from_another_session(self):
        self.start_login()
        self.client.get("/auth/mfa/setup/", secure=True)
        self.post("/auth/mfa/setup/", {"personal_setup-current_step": "welcome"})
        device = Authenticator.objects.get(user=self.owner, confirmed=False, revoked_at__isnull=True)
        code, now = self.otp(device)
        with patch("django_otp.plugins.otp_totp.models.time.time", return_value=now):
            self.assertIsNone(services.verify_factor(self.owner.pk, code, device.pk, enrollment=True,
                enrollment_hash=services.digest("synthetic-other-session")))
        device.refresh_from_db()
        self.assertEqual(device.last_t, -1)

    def test_restore_quarantine_cannot_revive_sessions_trust_codes_or_owner_privileges(self):
        device, codes = self.enroll()
        self.login(remember=True)
        before = list(Membership.objects.order_by("pk").values_list("id", "role", "state"))
        services.quarantine_restored_access()
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.post("/auth/mfa/recovery/", {"username": self.owner.username, "password": self.password, "code": codes[0]})
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        self.assertTrue(TrustedDevice.objects.get().revoked_at is not None)
        self.assertTrue(Authenticator.objects.get(pk=device.pk).revoked_at is not None)
        self.assertTrue(before == list(Membership.objects.order_by("pk").values_list("id", "role", "state")))
