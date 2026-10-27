from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from access_control.tests import test_http as access_tests
from account_security.models import AccountSession, ExportPermit
from ownership.models import Membership, User
from basework.models import ApplicationAccess, FederatedSession, IdentityBinding
from basework import services


@override_settings(SECURITY_DOWNLOAD_PROBE=True)
class BaseWorkHTTPTests(TestCase):
    setUp = access_tests.AccessHTTPTests.setUp
    post = access_tests.AccessHTTPTests.post
    start_login = access_tests.AccessHTTPTests.start_login
    otp = access_tests.AccessHTTPTests.otp
    login = access_tests.AccessHTTPTests.login
    session_record = access_tests.AccessHTTPTests.session_record
    grant = access_tests.AccessHTTPTests.grant
    url = access_tests.AccessHTTPTests.url

    def bootstrap(self, client=None):
        return (client or self.member_client).get('/api/v1/basework/bootstrap', secure=True)

    def binding(self):
        return IdentityBinding.objects.create(user=self.member, issuer='https://issuer.example.invalid', subject='subject-a')

    def allow(self, app='faq'):
        return ApplicationAccess.objects.create(user=self.member, application=app)

    def test_native_uuid_profile_and_empty_catalog(self):
        result = self.bootstrap()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['session']['user']['id'], str(self.member.pk))
        self.assertEqual(result.json()['applications'], [])
        self.assertIn('no-store', result['Cache-Control'])
        self.assertNotIn('token', result.content.decode().lower().replace('csrftoken', ''))

    def test_polling_does_not_extend_idle_timeout(self):
        record = self.session_record(self.member_client)
        original = record.last_seen
        self.bootstrap()
        record.refresh_from_db()
        self.assertEqual(record.last_seen, original)
        with patch('account_security.services.timezone.now', return_value=original+timedelta(seconds=settings.SECURITY_IDLE_SECONDS+1)):
            self.assertEqual(self.bootstrap().status_code, 401)

    def test_explicit_shell_access_does_not_connect_adapter_or_grant_data(self):
        self.allow()
        self.allow('marketplace')
        self.assertEqual([x['id'] for x in self.bootstrap().json()['applications']], ['faq'])
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.member_client.get('/api/v1/basework/applications/faq', secure=True).status_code, 503)
        self.assertEqual(self.member_client.get('/api/v1/basework/applications/rooms', secure=True).status_code, 403)
        for name in ('fbs', 'finkos', 'fanbox', 'admin'):
            self.assertEqual(self.member_client.get('/api/v1/basework/applications/'+name, secure=True).status_code, 403)

    def test_marketplace_catalog_requires_live_grant_and_membership(self):
        self.allow('marketplace')
        grant = self.grant('view', self.ca)
        self.assertEqual(len(self.bootstrap().json()['applications']), 1)
        grant.revoked_at = timezone.now()
        grant.save(update_fields=['revoked_at'])
        self.assertEqual(self.bootstrap().json()['applications'], [])
        self.grant('view', self.ca2)
        Membership.objects.filter(pk=self.mm.pk).update(state='suspended')
        result = self.bootstrap()
        self.assertTrue(result.status_code in (401, 403) or result.json()['applications'] == [])

    def test_unknown_identity_and_email_username_never_link(self):
        before = User.objects.count()
        for issuer, subject in [('https://issuer.example.invalid', self.member.username), ('', ''), (None, None)]:
            with self.assertRaises(PermissionDenied):
                services.resolve_identity(issuer, subject)
        self.assertEqual(User.objects.count(), before)
        binding = self.binding()
        self.assertEqual(services.resolve_identity(binding.issuer, binding.subject).user_id, self.member.pk)
        with self.assertRaises(PermissionDenied):
            services.resolve_identity(binding.issuer+'/', binding.subject)

    def test_identity_revoke_denies_old_cookie_old_api_and_file(self):
        binding = self.binding()
        record = self.session_record(self.member_client)
        services.attach_identity(record, binding)
        old_cookie = self.member_client.cookies[settings.SESSION_COOKIE_NAME].value
        permit = ExportPermit.objects.create(user=self.member, organization=self.a, session=record,
                                            expires_at=timezone.now()+timedelta(minutes=5))
        services.revoke_identity(binding.pk)
        record.refresh_from_db()
        permit.refresh_from_db()
        self.assertIsNotNone(record.revoked_at)
        self.assertIsNotNone(permit.revoked_at)
        self.member_client.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assertEqual(self.bootstrap().status_code, 401)
        self.member_client.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assertEqual(self.member_client.get('/auth/session', secure=True).status_code, 401)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        with self.assertRaises(PermissionDenied):
            services.resolve_identity(binding.issuer, binding.subject)

    def test_raw_revoke_and_tombstone_immutability(self):
        binding = self.binding()
        services.attach_identity(self.session_record(self.member_client), binding)
        IdentityBinding.objects.filter(pk=binding.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.bootstrap().status_code, 401)
        for fields in ({'revoked_at': None}, {'subject': 'other'}, {'user': self.owner}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                IdentityBinding.objects.filter(pk=binding.pk).update(**fields)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FederatedSession.objects.all().delete()

    def test_foreign_session_binding_is_rejected_by_service_and_database(self):
        binding = self.binding()
        owner_record = self.session_record(self.client)
        with self.assertRaises(PermissionDenied):
            services.attach_identity(owner_record, binding)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FederatedSession.objects.create(session=owner_record, binding=binding)

    def test_missing_unknown_expired_revoked_and_blocked_session(self):
        client = Client()
        self.assertEqual(self.bootstrap(client).json()['status'], 'anonymous')
        client.cookies[settings.SESSION_COOKIE_NAME] = 'unknown-session-cookie'
        self.assertEqual(self.bootstrap(client).json()['status'], 'session_expired')
        record = self.session_record(self.member_client)
        with patch('account_security.services.timezone.now', return_value=record.expires_at+timedelta(seconds=1)):
            self.assertEqual(self.bootstrap().status_code, 401)
        self.login(self.member, self.member_client)
        User.objects.filter(pk=self.member.pk).update(is_active=False)
        self.assertEqual(self.bootstrap().status_code, 401)

    def test_unregistered_session_is_denied(self):
        client = Client()
        client.force_login(self.member, backend='accounts.backends.PersonalAccountBackend')
        self.assertEqual(self.bootstrap(client).status_code, 401)

    def test_partial_mfa_never_receives_profile_or_catalog(self):
        from account_security import services as security
        from account_security.models import Authenticator
        Authenticator.objects.filter(user=self.owner).update(revoked_at=timezone.now())
        client = Client(enforce_csrf_checks=True)
        self.start_login(self.owner, client)
        self.assertEqual(self.bootstrap(client).json()['status'], 'mfa_required')
        record = self.session_record(client)
        self.assertFalse(security.fresh(record, factor=True))
        self.assertEqual(client.get('/auth/mfa/setup/', secure=True).status_code, 200)
        self.assertEqual(self.post('/api/v1/basework/logout', client=client).status_code, 200)
        self.assertEqual(self.bootstrap(client).status_code, 401)

    def test_registry_or_catalog_failure_is_closed(self):
        with patch('account_security.middleware.AccountSession.objects.filter', side_effect=DatabaseError()):
            self.assertEqual(self.bootstrap().status_code, 503)
        with patch('basework.services.ApplicationAccess.objects.filter', side_effect=DatabaseError()):
            self.assertEqual(self.bootstrap().status_code, 503)

    def test_logout_requires_csrf_and_revokes_before_cookie_clear(self):
        record = self.session_record(self.member_client)
        cookie = self.member_client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(self.member_client.post('/api/v1/basework/logout', secure=True).status_code, 403)
        self.assertEqual(self.post('/api/v1/basework/logout', client=self.member_client).status_code, 200)
        record.refresh_from_db()
        self.assertIsNotNone(record.revoked_at)
        self.assertEqual(self.member_client.cookies[settings.SESSION_COOKIE_NAME]['max-age'], 0)
        self.member_client.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(self.bootstrap().status_code, 401)
        self.assertEqual(self.bootstrap(self.client).status_code, 200)

    def test_logout_failure_never_reports_success_or_clears_cookie(self):
        cookie = self.member_client.cookies[settings.SESSION_COOKIE_NAME].value
        with patch('basework.views.security.logout', side_effect=DatabaseError()):
            self.assertEqual(self.post('/api/v1/basework/logout', client=self.member_client).status_code, 503)
        self.assertEqual(self.member_client.cookies[settings.SESSION_COOKIE_NAME].value, cookie)

    def test_failure_after_logout_rolls_back_revocation_and_cookie(self):
        from account_security import services as security
        original = security.logout
        record = self.session_record(self.member_client)
        cookie = self.member_client.cookies[settings.SESSION_COOKIE_NAME].value
        def fail_after_logout(request, **kwargs):
            original(request, **kwargs)
            raise DatabaseError()
        with patch('basework.views.security.logout', side_effect=fail_after_logout):
            response = self.post('/api/v1/basework/logout', client=self.member_client)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        record.refresh_from_db()
        self.assertIsNone(record.revoked_at)
        self.assertEqual(self.member_client.cookies[settings.SESSION_COOKIE_NAME].value, cookie)
        self.assertEqual(self.bootstrap().status_code, 200)

    def test_logout_all_is_separate_and_other_user_is_unchanged(self):
        second = Client(enforce_csrf_checks=True)
        self.login(self.member, second)
        self.assertEqual(self.post('/api/v1/basework/logout-all', client=self.member_client).status_code, 200)
        self.assertEqual(self.bootstrap(second).status_code, 401)
        self.assertEqual(self.bootstrap(self.client).status_code, 200)

    def test_shell_access_revocation_revokes_existing_sessions(self):
        access = self.allow()
        services.revoke_application(access.pk)
        self.assertEqual(self.bootstrap().status_code, 401)
        self.login(self.member, self.member_client)
        self.assertEqual(self.bootstrap().json()['applications'], [])

    def test_other_organization_cabinet_and_object_remain_forbidden(self):
        self.allow('marketplace')
        self.grant('view', self.ca)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 200)
        for record in (self.ra2, self.rb):
            self.assertEqual(self.member_client.get(self.url(record), secure=True).status_code, 403)
        self.assertEqual(self.bootstrap(self.client).json()['applications'], [])
