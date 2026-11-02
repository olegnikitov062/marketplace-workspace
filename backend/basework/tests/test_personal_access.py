import json
import secrets
import tempfile
import time
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import CommandError, call_command
from django.test import Client, SimpleTestCase, TestCase

from account_security.models import AccountSession, AccountSecurity, Authenticator
from accounts.models import AccountContact
from ownership.models import Cabinet, Membership, Organization, User
from basework import personal_access as personal
from basework.models import ApplicationAccess


class PersonalGuardTests(SimpleTestCase):
    def test_roster_requires_exact_identity_and_only_available_applications(self):
        entry = {'id': str(uuid.uuid4()), 'username': 'test-personal', 'applications': ['faq', 'rooms']}
        document = {'purpose': 'basework-personal-pilot-v1', 'users': [entry]}
        self.assertEqual(personal.roster(document), {entry['id']: entry})
        for invalid in ({**document, 'purpose': 'other'}, {**document, 'extra': True},
                        {**document, 'users': [entry, entry]},
                        {**document, 'users': [{**entry, 'applications': ['marketplace']}]},
                        {**document, 'users': [{**entry, 'username': 'basework-uat-admin'}]}):
            with self.assertRaises(PermissionDenied):
                personal.roster(invalid)

    def test_operator_guard_cannot_run_with_web_role(self):
        with patch.object(personal, 'require_operator_process', side_effect=PermissionDenied), \
                patch.object(personal, 'roster') as read:
            with self.assertRaises(PermissionDenied):
                personal.guard()
            read.assert_not_called()

    def test_command_does_not_print_codes_or_exception_values(self):
        with patch('basework.management.commands.basework_personal.execute', side_effect=ValueError('secret-code')):
            output = StringIO()
            with self.assertRaises(CommandError) as error:
                call_command('basework_personal', 'create', user=str(uuid.uuid4()), output='/tmp/code.txt', stdout=output)
            self.assertNotIn('secret-code', str(error.exception) + output.getvalue())


class PersonalAccessTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.key = str(uuid.uuid4())
        self.entry = {'id': self.key, 'username': 'test-personal-user', 'applications': ['faq', 'rooms']}
        guard = patch.object(personal, 'guard', return_value={self.key: self.entry})
        guard.start()
        self.addCleanup(guard.stop)
        directory = patch.object(personal, 'OUTPUT', self.root)
        directory.start()
        self.addCleanup(directory.stop)
        self.password = secrets.token_urlsafe(32)
        self.client = Client(enforce_csrf_checks=True)

    def create(self):
        output = self.root / 'initial.txt'
        personal.execute('create', self.key, output=str(output))
        self.code = output.read_text().strip()
        self.user = User.objects.get(pk=self.key)
        return self.code

    def activate(self):
        self.create()
        personal.use_code(self.code, self.password, self.password)
        personal.execute('grant', self.key)
        self.user.refresh_from_db()

    def login(self, password=None):
        self.client.get('/auth/basework/login', secure=True)
        csrf = self.client.get('/auth/csrf', secure=True).json()['csrfToken']
        return self.client.post('/auth/basework/login', urlencode({'base_work_login-current_step': 'auth',
            'auth-username': self.entry['username'], 'auth-password': password or self.password}),
            content_type='application/x-www-form-urlencoded', secure=True,
            HTTP_ORIGIN='https://testserver', HTTP_X_CSRFTOKEN=csrf)

    def submit(self, code=None, password=None, csrf=True):
        token = self.client.get('/auth/csrf', secure=True).json()['csrfToken']
        headers = {'HTTP_ORIGIN': 'https://testserver'}
        if csrf:
            headers['HTTP_X_CSRFTOKEN'] = token
        return self.client.post('/auth/basework/access', urlencode({'code': code or self.code,
            'new_password1': password or self.password, 'new_password2': password or self.password}),
            content_type='application/x-www-form-urlencoded', secure=True, **headers)

    def test_create_does_not_make_tenants_contacts_or_permissions(self):
        self.create()
        self.assertFalse(self.user.has_usable_password())
        for model in (AccountContact, Membership, Organization, Cabinet, ApplicationAccess):
            self.assertFalse(model.objects.exists())
        with self.assertRaises(PermissionDenied):
            personal.execute('create', self.key, output=str(self.root / 'another.txt'))
        self.assertFalse((self.root / 'another.txt').exists())

    def test_activation_and_password_login_without_fake_contact_or_organization(self):
        self.activate()
        self.assertTrue(self.user.check_password(self.password))
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/basework/')
        response = self.client.get('/api/v1/basework/bootstrap', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({x['id'] for x in response.json()['applications']}, {'faq', 'rooms'})
        self.assertEqual(AccountSession.objects.get(user=self.user).level, 'full')

    def test_code_is_single_use_and_not_accepted_as_password(self):
        self.create()
        self.assertContains(self.login(password=self.code), 'Неверный логин или пароль.')
        personal.use_code(self.code, self.password, self.password)
        with self.assertRaises(PermissionDenied):
            personal.use_code(self.code, self.password, self.password)

    def test_bad_password_keeps_code_available(self):
        self.create()
        with self.assertRaises(ValidationError):
            personal.use_code(self.code, '123', '456')
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())
        personal.use_code(self.code, self.password, self.password)

    def test_expired_tampered_and_wrong_signing_context_codes_denied(self):
        self.create()
        with patch('django.core.signing.time.time', return_value=time.time() + personal.LIFETIME + 2):
            with self.assertRaises(PermissionDenied):
                personal.use_code(self.code, self.password, self.password)
        for code in (self.code + 'x', signing.dumps({'user': self.key}, salt='other'), 'invalid'):
            with self.assertRaises(PermissionDenied):
                personal.use_code(code, self.password, self.password)

    def test_recovery_revokes_old_sessions_and_preserves_factor_and_access(self):
        self.activate()
        self.assertEqual(self.login().status_code, 302)
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        device = Authenticator.objects.create(user=self.user, confirmed=True)
        before = list(ApplicationAccess.objects.values_list('id', 'application', 'revoked_at'))
        output = self.root / 'recovery.txt'
        personal.execute('issue-access', self.key, output=str(output))
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap', secure=True).status_code, 401)
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())
        new_password = secrets.token_urlsafe(32)
        personal.use_code(output.read_text().strip(), new_password, new_password)
        self.client.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap', secure=True).status_code, 401)
        self.assertEqual(list(ApplicationAccess.objects.values_list('id', 'application', 'revoked_at')), before)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        self.assertIsNone(device.revoked_at)
        self.assertContains(self.login(password=new_password), 'Подтверждение входа')

    def test_new_issue_invalidates_previous_code(self):
        self.create()
        output = self.root / 'new.txt'
        personal.execute('issue-access', self.key, output=str(output))
        with self.assertRaises(PermissionDenied):
            personal.use_code(self.code, self.password, self.password)
        personal.use_code(output.read_text().strip(), self.password, self.password)

    def test_disabled_or_recovery_required_user_cannot_redeem_code(self):
        self.create()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            personal.use_code(self.code, self.password, self.password)

    def test_existing_account_cannot_be_adopted_by_roster(self):
        User.objects.create_user(self.entry['username'], self.password, id=self.key)
        for action in ('create', 'issue-access', 'grant', 'revoke'):
            with self.assertRaises(PermissionDenied):
                personal.execute(action, self.key, output=str(self.root / 'code.txt') if action in ('create', 'issue-access') else None)

    def test_unknown_uuid_or_unsafe_output_denied_without_records(self):
        for path in ('relative.txt', str(self.root.parent / 'outside.txt')):
            with self.assertRaises(PermissionDenied):
                personal.execute('create', self.key, output=path)
        with self.assertRaises(PermissionDenied):
            personal.execute('create', uuid.uuid4(), output=str(self.root / 'code.txt'))
        self.assertFalse(User.objects.exists())

    def test_module_revocation_does_not_revive_old_session_on_grant(self):
        self.activate()
        self.assertEqual(self.login().status_code, 302)
        personal.execute('revoke', self.key)
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap', secure=True).status_code, 401)
        personal.execute('grant', self.key)
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap', secure=True).status_code, 401)
        self.assertEqual(ApplicationAccess.objects.filter(revoked_at__isnull=True).count(), 2)

    def test_form_secure_csrf_and_no_secret_echo(self):
        self.create()
        page = self.client.get('/auth/basework/access', secure=True)
        self.assertContains(page, 'Код доступа')
        self.assertContains(page, '30 минут')
        self.assertIn('no-store', page['Cache-Control'])
        self.assertEqual(self.client.get('/auth/basework/access').status_code, 403)
        self.assertEqual(self.submit(csrf=False).status_code, 403)
        response = self.submit(password='123')
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, self.code, status_code=400)
        self.assertContains(self.submit(), 'Пароль сохранён')
        self.assertFalse(AccountSession.objects.exists())
        self.assertEqual(self.submit().status_code, 400)

    def test_code_endpoint_rate_limit_and_recovery_state(self):
        self.create()
        with self.settings(ACCOUNT_PEER_LIMIT=1):
            self.assertEqual(self.submit(code='wrong').status_code, 400)
            self.assertEqual(self.submit().status_code, 429)
        state = AccountSecurity.objects.get(user=self.user)
        state.recovery_required = True
        state.save(update_fields=['recovery_required'])
        with self.assertRaises(PermissionDenied):
            personal.use_code(self.code, self.password, self.password)
