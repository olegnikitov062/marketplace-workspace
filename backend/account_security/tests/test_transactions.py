import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from unittest import skipUnless

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.hashers import make_password
from django.db import connection, connections
from django.test import TransactionTestCase, RequestFactory
from django.utils import timezone
from django_otp.oath import TOTP

from accounts.services import block_account
from ownership.models import User, Membership, Organization
from account_security import services
from account_security.models import Authenticator, RecoveryCode, AccountSession, LoginChallenge
from account_security.session_backend import SessionStore


@skipUnless(connection.vendor == "postgresql", "PostgreSQL row locks and independent connections required")
class SecurityConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(24)
        self.user = User.objects.create_user("synthetic-concurrent", self.password)
        self.org = Organization.objects.create(name="synthetic-concurrent")
        Membership.objects.create(user=self.user, organization=self.org, role="owner")
        self.state = services.state_for(self.user)
        self.device = Authenticator.objects.create(user=self.user, name="default", confirmed=True)

    def race(self, actions):
        barrier = Barrier(len(actions))
        def execute(action):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as executor:
            return list(executor.map(execute, actions))

    def request(self):
        request = RequestFactory().post("/auth/mfa/recovery/", secure=True)
        request.session = SessionStore()
        request.user = AnonymousUser()
        return request

    def test_same_totp_has_one_successful_consumer(self):
        totp = TOTP(self.device.bin_key)
        code = str(totp.token()).zfill(6)
        def action():
            return services.verify_factor(self.user.pk, code, self.device.pk) is not None
        self.assertEqual(sorted(self.race([action, action])), [False, True])

    def test_same_recovery_code_has_one_successful_consumer(self):
        code = secrets.token_urlsafe(24)
        RecoveryCode.objects.create(user=self.user, verifier=make_password(code))
        def action():
            return services.recover_with_code(self.request(), self.user.username, self.password, code)
        self.assertEqual(sorted(self.race([action, action])), [False, True])
        self.assertEqual(AccountSession.objects.filter(level="recover", revoked_at__isnull=True).count(), 1)

    def test_same_operator_permit_has_one_successful_consumer(self):
        token = services.issue_operator_recovery(self.user.pk)
        def action():
            return services.consume_operator_recovery(self.request(), self.user.username, self.password, token)
        self.assertEqual(sorted(self.race([action, action])), [False, True])
        self.assertEqual(AccountSession.objects.filter(level="recover", revoked_at__isnull=True).count(), 1)

    def test_concurrent_attempt_limit_cannot_lose_increments(self):
        from accounts.limits import allow_attempt
        from accounts.models import AttemptBucket
        from django.conf import settings
        def action():
            return allow_attempt("totp", "127.0.0.1", str(self.user.pk))
        count = settings.ACCOUNT_PRINCIPAL_LIMIT + 2
        results = self.race([action] * count)
        self.assertLessEqual(sum(results), settings.ACCOUNT_PRINCIPAL_LIMIT)
        self.assertTrue(AttemptBucket.objects.filter(attempts=count).exists())

    def test_same_login_challenge_cannot_create_two_sessions(self):
        from django.core.exceptions import PermissionDenied
        challenge = LoginChallenge.objects.create(user=self.user, version=self.state.version,
            credential_hash=self.user.get_session_auth_hash(), expires_at=timezone.now()+timedelta(minutes=5))
        def action():
            try:
                services.complete_login(self.request(), self.user.pk, challenge.pk, self.device.pk)
                return True
            except PermissionDenied:
                return False
        self.assertEqual(sorted(self.race([action, action])), [False, True])

    def test_block_racing_login_leaves_no_valid_session(self):
        from django.core.exceptions import PermissionDenied
        challenge = LoginChallenge.objects.create(user=self.user, version=self.state.version,
            credential_hash=self.user.get_session_auth_hash(), expires_at=timezone.now()+timedelta(minutes=5))
        def login():
            try:
                services.complete_login(self.request(), self.user.pk, challenge.pk, self.device.pk)
            except PermissionDenied:
                pass
        self.race([login, lambda: block_account(self.user.pk)])
        self.assertFalse(User.objects.get(pk=self.user.pk).is_active)
        self.assertFalse(AccountSession.objects.filter(user=self.user, revoked_at__isnull=True).exists())
