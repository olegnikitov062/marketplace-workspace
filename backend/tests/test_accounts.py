"""Synthetic credentials stay in memory; assertions never print their values."""
import hashlib
import json
import secrets
from io import StringIO
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts import services
from accounts.delivery import deliver
from accounts.limits import allow_attempt
from accounts.models import AccountContact, AttemptBucket, AuthDenial, Invitation
from ownership.models import Membership, Organization, User
from ownership.services import membership_role


class AccountFixture:
    def setUp(self):
        super().setUp()
        self.a = Organization.objects.create(name="synthetic-a")
        self.b = Organization.objects.create(name="synthetic-b")
        self.owner = User.objects.create_user("synthetic-owner")
        self.other = User.objects.create_user("synthetic-other")
        Membership.objects.create(user=self.owner, organization=self.a, role="owner")
        Membership.objects.create(user=self.owner, organization=self.b, role="observer")
        Membership.objects.create(user=self.other, organization=self.b, role="owner")
        self.password = secrets.token_urlsafe(24)

    def issue(self):
        invitation = services.issue_invitation(self.owner, self.a.pk, "synthetic-new", "new@example.invalid", "cabinet_user")
        token = json.loads(mail.outbox[-1].body)["token"]
        return invitation, token

    def activate(self):
        invitation, token = self.issue()
        services.accept_invitation(token, self.password, self.password)
        return User.objects.get(pk=invitation.membership.user_id)

    def recovery(self, user):
        self.assertTrue(services.request_recovery(user.username))
        return json.loads(mail.outbox[-1].body)

    def secure_client(self):
        return Client(enforce_csrf_checks=True)

    def post(self, path, data=None, client=None, csrf=True):
        client = client or self.client
        headers = {"HTTP_ORIGIN": "https://testserver"}
        if csrf:
            headers["HTTP_X_CSRFTOKEN"] = client.get("/auth/csrf", secure=True).json()["csrfToken"]
        return client.post(path, urlencode(data or {}), content_type="application/x-www-form-urlencoded", secure=True, **headers)

    def accept_data(self, token):
        return {"token": token, "new_password1": self.password, "new_password2": self.password}


class InvitationTests(AccountFixture, TestCase):
    def test_accept_preserves_exact_scope_and_stores_only_hash(self):
        invitation, token = self.issue()
        before = list(Membership.objects.values_list("id", "user_id", "organization_id", "role", "state"))
        self.assertTrue(invitation.token_hash == hashlib.sha256(token.encode()).hexdigest())
        self.assertFalse(token in repr(Invitation.objects.values().get(pk=invitation.pk)))
        services.accept_invitation(token, self.password, self.password)
        self.assertEqual(before, list(Membership.objects.values_list("id", "user_id", "organization_id", "role", "state")))
        user = User.objects.get(pk=invitation.membership.user_id)
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.password == self.password)
        self.assertIsNotNone(AccountContact.objects.get(user=user).activated_at)
        self.assertIsNone(membership_role(user, self.b))
        self.assertEqual(membership_role(user, self.a), "cabinet_user")

    def test_expired_invitation_denied_at_boundary(self):
        invitation, token = self.issue()
        with patch("accounts.services.timezone.now", return_value=invitation.expires_at):
            with self.assertRaises(services.AccountRejected):
                services.accept_invitation(token, self.password, self.password)
        self.assertFalse(User.objects.get(pk=invitation.membership.user_id).has_usable_password())

    def test_used_invitation_denied(self):
        invitation, token = self.issue()
        services.accept_invitation(token, self.password, self.password)
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(token, self.password, self.password)
        with self.assertRaises(services.AccountRejected):
            services.reinvite(self.owner, invitation.pk)

    def test_revoked_invitation_denied(self):
        invitation, token = self.issue()
        services.revoke_invitation(self.owner, invitation.pk)
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(token, self.password, self.password)
        with self.assertRaises(services.AccountRejected):
            services.reinvite(self.owner, invitation.pk)

    def test_reinvite_expires_old_token_and_keeps_scope(self):
        invitation, old = self.issue()
        with patch("accounts.services.timezone.now", return_value=invitation.expires_at):
            replacement = services.reinvite(self.owner, invitation.pk)
        new = json.loads(mail.outbox[-1].body)["token"]
        self.assertEqual(replacement.membership_id, invitation.membership_id)
        self.assertEqual(replacement.scope_digest, invitation.scope_digest)
        self.assertFalse(new == old)
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(old, self.password, self.password)
        services.accept_invitation(new, self.password, self.password)
        self.assertEqual(Membership.objects.filter(user_id=invitation.membership.user_id).count(), 1)

    def test_blocked_pending_account_cannot_accept_or_reinvite(self):
        invitation, token = self.issue()
        services.block_account(invitation.membership.user_id)
        for operation in [lambda: services.accept_invitation(token, self.password, self.password), lambda: services.reinvite(self.owner, invitation.pk)]:
            with self.assertRaises(services.AccountRejected):
                operation()
        self.assertFalse(services.request_recovery("synthetic-new"))
        self.assertEqual(len(mail.outbox), 1)

    def test_foreign_owner_and_observer_cannot_issue_or_reinvite(self):
        invitation, _ = self.issue()
        for actor, organization in [(self.other, self.a), (self.owner, self.b)]:
            with self.assertRaises(PermissionDenied):
                services.issue_invitation(actor, organization.pk, "synthetic-denied", "denied@example.invalid", "observer")
        with self.assertRaises(PermissionDenied):
            services.reinvite(self.other, invitation.pk)
        with self.assertRaises(PermissionDenied):
            services.revoke_invitation(self.other, invitation.pk)

    def test_role_drift_and_added_membership_fail_closed(self):
        invitation, token = self.issue()
        member = invitation.membership
        Membership.objects.filter(pk=member.pk).update(role="owner")
        for operation in [lambda: services.accept_invitation(token, self.password, self.password), lambda: services.reinvite(self.owner, invitation.pk)]:
            with self.assertRaises(services.AccountRejected):
                operation()
        Membership.objects.filter(pk=member.pk).update(role="cabinet_user")
        Membership.objects.create(user_id=member.user_id, organization=self.b, role="observer")
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(token, self.password, self.password)
        with self.assertRaises(services.AccountRejected):
            services.reinvite(self.owner, invitation.pk)

    def test_suspended_and_archived_memberships_organizations_and_users_deny(self):
        invitation, token = self.issue()
        checks = [
            (Membership, invitation.membership_id, {"state": "suspended"}, {"state": "active"}),
            (Membership, invitation.membership_id, {"archived_at": timezone.now()}, {"archived_at": None}),
            (Organization, self.a.pk, {"archived_at": timezone.now()}, {"archived_at": None}),
            (User, invitation.membership.user_id, {"archived_at": timezone.now()}, {"archived_at": None}),
        ]
        for model, pk, values, restore in checks:
            model.objects.filter(pk=pk).update(**values)
            with self.assertRaises(services.AccountRejected):
                services.accept_invitation(token, self.password, self.password)
            model.objects.filter(pk=pk).update(**restore)

    def test_existing_identity_cannot_be_added_to_foreign_org(self):
        self.activate()
        before = Membership.objects.count()
        for username, email in [("synthetic-new", "different@example.invalid"), ("synthetic-different", "NEW@example.invalid")]:
            with self.assertRaises(services.AccountRejected):
                services.issue_invitation(self.other, self.b.pk, username, email, "observer")
        self.assertEqual(Membership.objects.count(), before)

    def test_no_owner_grant_or_real_recipient(self):
        before = User.objects.count()
        with self.assertRaises(services.AccountRejected):
            services.issue_invitation(self.owner, self.a.pk, "synthetic-new", "new@example.invalid", "owner")
        with self.assertRaises(ValidationError):
            services.issue_invitation(self.owner, self.a.pk, "synthetic-new", "synthetic@example.com", "observer")
        self.assertEqual(User.objects.count(), before)

    def test_password_validation_does_not_consume_invitation(self):
        invitation, token = self.issue()
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(token, "1", "1")
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(token, self.password, secrets.token_urlsafe(24))
        self.assertIsNone(Invitation.objects.get(pk=invitation.pk).used_at)
        services.accept_invitation(token, self.password, self.password)

    def test_unique_live_invitation_constraint(self):
        invitation, _ = self.issue()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invitation.objects.create(membership=invitation.membership, scope_digest=invitation.scope_digest, token_hash="f" * 64, expires_at=invitation.expires_at)

    def test_rebound_membership_user_fails_closed(self):
        invitation, token = self.issue()
        Membership.objects.filter(pk=invitation.membership_id).update(user=self.other)
        with self.assertRaises(services.AccountRejected):
            services.accept_invitation(token, self.password, self.password)

    def test_database_rejects_real_contact_and_invalid_invitation_state(self):
        invitation, _ = self.issue()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountContact.objects.create(user=self.owner, email="synthetic@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invitation.objects.filter(pk=invitation.pk).update(used_at=timezone.now(), revoked_at=timezone.now())


class LoginRecoveryTests(AccountFixture, TestCase):
    def test_operator_command_blocks_without_identity_output(self):
        user = self.activate()
        output = StringIO()
        call_command("block_personal_account", str(user.pk), stdout=output)
        user.refresh_from_db()
        self.assertFalse(user.is_active or user.has_usable_password())
        self.assertFalse(user.username in output.getvalue() or str(user.pk) in output.getvalue())

    def test_correct_wrong_password_cookie_and_logout(self):
        user = self.activate()
        client = self.secure_client()
        self.assertEqual(self.post("/auth/login", {"username": user.username, "password": secrets.token_urlsafe(24)}, client).status_code, 401)
        response = self.post("/auth/login", {"username": user.username, "password": self.password}, client)
        self.assertEqual(response.status_code, 200)
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["secure"] and cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertFalse(cookie["domain"])
        self.assertEqual(client.get("/auth/session", secure=True).status_code, 200)
        self.assertEqual(self.post("/auth/logout", client=client).status_code, 200)
        self.assertEqual(client.get("/auth/session", secure=True).status_code, 401)

    def test_block_denies_existing_sessions_login_recovery_and_old_reset(self):
        user = self.activate()
        recovery = self.recovery(user)
        clients = [self.secure_client(), self.secure_client()]
        for client in clients:
            self.assertEqual(self.post("/auth/login", {"username": user.username, "password": self.password}, client).status_code, 200)
        before = list(Membership.objects.filter(user=user).values_list("id", "role", "state"))
        services.block_account(user.pk)
        for client in clients:
            self.assertEqual(client.get("/auth/session", secure=True).status_code, 401)
        self.assertEqual(self.post("/auth/login", {"username": user.username, "password": self.password}).status_code, 401)
        self.assertFalse(services.request_recovery(user.username))
        with self.assertRaises(services.AccountRejected):
            services.confirm_recovery(user.pk, recovery["token"], self.password, self.password)
        self.assertEqual(before, list(Membership.objects.filter(user=user).values_list("id", "role", "state")))
        User.objects.filter(pk=user.pk).update(is_active=True)
        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())
        self.assertFalse(default_token_generator.check_token(user, recovery["token"]))

    def test_recovery_is_one_use_and_invalidates_previous_password_sessions(self):
        user = self.activate()
        self.client.force_login(user)
        recovery = self.recovery(user)
        second = self.recovery(user)
        replacement = secrets.token_urlsafe(24)
        services.confirm_recovery(user.pk, recovery["token"], replacement, replacement)
        user.refresh_from_db()
        self.assertTrue(user.check_password(replacement))
        self.assertFalse(user.check_password(self.password))
        self.assertEqual(self.client.get("/auth/session", secure=True).status_code, 401)
        for payload in [recovery, second]:
            with self.assertRaises(services.AccountRejected):
                services.confirm_recovery(user.pk, payload["token"], self.password, self.password)

    def test_recovery_expiry(self):
        user = self.activate()
        now = datetime(2026, 10, 1, 10, 0, 0)
        with patch.object(default_token_generator, "_now", return_value=now):
            recovery = self.recovery(user)
        with patch.object(default_token_generator, "_now", return_value=now + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 1)):
            with self.assertRaises(services.AccountRejected):
                services.confirm_recovery(user.pk, recovery["token"], self.password, self.password)

    def test_unknown_pending_blocked_recovery_response_is_identical(self):
        invitation, _ = self.issue()
        responses = [self.post("/auth/recovery/request", {"username": "synthetic-absent"})]
        responses.append(self.post("/auth/recovery/request", {"username": "synthetic-new"}))
        services.block_account(invitation.membership.user_id)
        responses.append(self.post("/auth/recovery/request", {"username": "synthetic-new"}))
        self.assertTrue(all(r.status_code == 202 and r.json() == {"status": "accepted"} for r in responses))
        self.assertEqual(len(mail.outbox), 1)

    def test_recovery_cannot_target_other_user_or_weak_password(self):
        user = self.activate()
        recovery = self.recovery(user)
        with self.assertRaises(services.AccountRejected):
            services.confirm_recovery(self.other.pk, recovery["token"], self.password, self.password)
        with self.assertRaises(services.AccountRejected):
            services.confirm_recovery(user.pk, recovery["token"], "1", "1")
        user.refresh_from_db()
        self.assertTrue(default_token_generator.check_token(user, recovery["token"]))

    def test_archive_rejects_authentication_even_with_is_active_true(self):
        user = self.activate()
        User.objects.filter(pk=user.pk).update(archived_at=timezone.now())
        self.assertEqual(self.post("/auth/login", {"username": user.username, "password": self.password}).status_code, 401)
        self.assertFalse(services.request_recovery(user.username))


class HttpAndDeliveryTests(AccountFixture, TestCase):
    def test_readiness_requires_account_migrations(self):
        self.assertEqual(self.client.get("/api/v1/health/ready").status_code, 200)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app = 'accounts' AND name = '0002_immutable_invitation'")
        self.assertEqual(self.client.get("/api/v1/health/ready").status_code, 503)

    def test_foreign_origin_is_rejected_with_valid_csrf_token(self):
        client = self.secure_client()
        token = client.get("/auth/csrf", secure=True).json()["csrfToken"]
        response = client.post("/auth/logout", "", content_type="application/x-www-form-urlencoded", secure=True,
                               HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="https://foreign.example.invalid")
        self.assertEqual(response.status_code, 403)

    def test_csrf_required_for_every_mutation_including_anonymous(self):
        invitation, _ = self.issue()
        paths = ["/auth/login", "/auth/logout", "/auth/invitations", "/auth/invitations/accept", "/auth/recovery/request", "/auth/recovery/confirm", f"/auth/invitations/{invitation.pk}/reinvite", f"/auth/invitations/{invitation.pk}/revoke"]
        for logged_in in [False, True]:
            client = self.secure_client()
            if logged_in:
                client.force_login(self.owner)
            for path in paths:
                self.assertEqual(self.post(path, client=client, csrf=False).status_code, 403)
                self.assertEqual(client.get(path, secure=True).status_code, 405)

    def test_http_accept_and_recovery_with_csrf(self):
        invitation, token = self.issue()
        client = self.secure_client()
        self.assertEqual(self.post("/auth/invitations/accept", self.accept_data(token), client).status_code, 200)
        self.assertEqual(client.get("/auth/session", secure=True).status_code, 401)
        self.assertEqual(self.post("/auth/recovery/request", {"username": "synthetic-new"}, client).status_code, 202)
        payload = json.loads(mail.outbox[-1].body)
        payload.update(new_password1=self.password, new_password2=self.password)
        self.assertEqual(self.post("/auth/recovery/confirm", payload, client).status_code, 200)
        self.assertEqual(self.post("/auth/recovery/confirm", payload, client).status_code, 400)

    def test_issue_http_permission_and_no_scope_overrides(self):
        client = self.secure_client()
        data = {"organization_id": str(self.a.pk), "username": "synthetic-new", "email": "new@example.invalid", "role": "observer"}
        self.assertEqual(self.post("/auth/invitations", data, client).status_code, 403)
        client.force_login(self.owner)
        response = self.post("/auth/invitations", data, client)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), {"invitation_id"})
        url = f"/auth/invitations/{response.json()['invitation_id']}/reinvite"
        self.assertEqual(self.post(url, {"role": "owner", "organization_id": str(self.b.pk)}, client).status_code, 400)
        self.assertEqual(self.post(url, client=client).status_code, 201)

    def test_accept_ignores_no_extra_privilege_fields(self):
        _, token = self.issue()
        data = {**self.accept_data(token), "role": "owner"}
        self.assertEqual(self.post("/auth/invitations/accept", data).status_code, 400)
        self.assertFalse(User.objects.get(username="synthetic-new").has_usable_password())

    def test_owner_permission_is_live_after_login(self):
        client = self.secure_client()
        client.force_login(self.owner)
        Membership.objects.filter(user=self.owner, organization=self.a).update(state="suspended")
        data = {"organization_id": str(self.a.pk), "username": "synthetic-new", "email": "new@example.invalid", "role": "observer"}
        self.assertEqual(self.post("/auth/invitations", data, client).status_code, 403)

    def test_no_public_registration_block_or_mfa(self):
        for path in ["/auth/register", "/auth/block", "/auth/unblock", "/auth/totp", "/admin/"]:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_no_real_delivery_even_if_backend_overridden(self):
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"), patch("django.core.mail.backends.smtp.EmailBackend.open") as smtp:
            with self.assertRaises(ImproperlyConfigured):
                self.issue()
            smtp.assert_not_called()
        self.assertFalse(User.objects.filter(username="synthetic-new").exists())
        with self.assertRaises(ValidationError):
            deliver("synthetic@example.com", "synthetic", "synthetic")
        self.issue()
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(all(address.endswith("@example.invalid") for address in mail.outbox[0].to))

    def test_mail_payloads_never_appear_in_http_or_audit(self):
        _, token = self.issue()
        response = self.post("/auth/invitations/accept", self.accept_data(token))
        self.assertFalse(token.encode() in response.content or self.password.encode() in response.content)
        self.post("/auth/login", {"username": "synthetic-new", "password": secrets.token_urlsafe(24)})
        audit = repr(list(AuthDenial.objects.values()))
        for value in [token, self.password, "synthetic-new", "example.invalid"]:
            self.assertFalse(value in audit)

    @override_settings(ACCOUNT_PRINCIPAL_LIMIT=2, ACCOUNT_PEER_LIMIT=20)
    def test_login_rate_limit_is_shared_by_principal_and_has_window(self):
        data = {"username": "synthetic-missing", "password": secrets.token_urlsafe(24)}
        for _ in range(2):
            self.assertEqual(self.post("/auth/login", data).status_code, 401)
        self.assertEqual(self.post("/auth/login", data).status_code, 429)
        self.assertTrue(all(len(key) == 64 for key in AttemptBucket.objects.values_list("key", flat=True)))
        with patch("accounts.limits.timezone.now", return_value=timezone.now() + timedelta(seconds=settings.ACCOUNT_ATTEMPT_WINDOW + 1)):
            self.assertEqual(self.post("/auth/login", data).status_code, 401)

    @override_settings(ACCOUNT_PEER_LIMIT=2, ACCOUNT_PRINCIPAL_LIMIT=20)
    def test_peer_limit_cannot_be_bypassed_by_changing_login(self):
        self.assertTrue(allow_attempt("login", "synthetic-peer", "one"))
        self.assertTrue(allow_attempt("login", "synthetic-peer", "two"))
        self.assertFalse(allow_attempt("login", "synthetic-peer", "three"))

    @override_settings(ACCOUNT_PRINCIPAL_LIMIT=1)
    def test_recovery_rate_limit(self):
        self.assertEqual(self.post("/auth/recovery/request", {"username": "synthetic-absent"}).status_code, 202)
        self.assertEqual(self.post("/auth/recovery/request", {"username": "synthetic-absent"}).status_code, 429)
