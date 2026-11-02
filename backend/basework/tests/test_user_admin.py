"""Пользователи и коды на вымышленных данных; PostgreSQL проверяется отдельно."""
import secrets
import time
import uuid
from datetime import timedelta
from urllib.parse import urlencode
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import Client, TestCase
from django.utils import timezone
from django_otp.oath import TOTP

from ownership.models import User, Membership, Organization
from accounts.models import AccountContact
from account_security import services as security
from account_security.models import Authenticator, AccountSession, AccountSecurity
from access_control.models import PlatformRoleAssignment
from basework.models import Administrator, ApplicationAccess
from basework import personal_access as personal
from basework import user_admin as service

ROOT = '/auth/basework/users/'


def seed(prefix='local-admin'):
    password = secrets.token_urlsafe(32)
    actor = User.objects.create_user(prefix + '-' + uuid.uuid4().hex[:8], password)
    security.event(actor, personal.CREATED)
    PlatformRoleAssignment.objects.create(user=actor)
    Administrator.objects.create(user=actor)
    Authenticator.objects.create(user=actor, name='fixture', confirmed=True)
    return actor, password


def post(client, path, data, *, csrf=True):
    token = client.get('/auth/csrf', secure=True).json()['csrfToken']
    return client.post(path, urlencode(data, doseq=True), content_type='application/x-www-form-urlencoded',
        secure=True, HTTP_ORIGIN='https://testserver', **({'HTTP_X_CSRFTOKEN': token} if csrf else {}))


def login(client, user, password, device=None):
    client.get('/auth/basework/login', secure=True)
    response = post(client, '/auth/basework/login', {'base_work_login-current_step': 'auth',
                    'auth-username': user.username, 'auth-password': password})
    if device is not None:
        tick = max(int(time.time() // 30), device.last_t + 1)
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = tick * 30 + 1
        with patch('django_otp.plugins.otp_totp.models.time.time', return_value=totp.time):
            response = post(client, '/auth/basework/login', {'base_work_login-current_step': 'token',
                            'token-otp_token': str(totp.token()).zfill(6)})
    return response


class UserAdminTests(TestCase):
    def setUp(self):
        self.actor, self.password = seed()
        self.client = Client(enforce_csrf_checks=True)
        self.assertEqual(login(self.client, self.actor, self.password,
                         Authenticator.objects.get(user=self.actor)).status_code, 302)

    def form_data(self, username='new-member', apps=None):
        result = self.client.get(ROOT + 'new/', secure=True)
        return {'ticket': result.context['form']['ticket'].value(), 'username': username,
                'applications': ['faq', 'rooms'] if apps is None else apps}

    def create(self, username='new-member', apps=None):
        self.data = self.form_data(username, apps)
        response = post(self.client, ROOT + 'new/', self.data)
        self.assertEqual(response.status_code, 200)
        self.user = User.objects.get(username=username)
        self.code = response.context['invitation'].split('Код доступа: ')[1].split('\n')[0]
        return response

    def detail(self):
        return ROOT + str(self.user.pk) + '/'

    def version(self):
        return AccountSecurity.objects.get(user=self.user).version

    def test_create_invitation_and_user_sees_login_after_password(self):
        response = self.create()
        self.assertContains(response, 'Логин: new-member')
        self.assertContains(response, 'https://testserver/auth/basework/access')
        self.assertContains(response, '30 минут')
        self.assertContains(response, 'до ' + timezone.localtime(timezone.now() + timedelta(minutes=30), ZoneInfo('Europe/Moscow')).strftime('%H:%M') + ' МСК')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertFalse(AccountContact.objects.exists())
        self.assertFalse(Organization.objects.exists())
        self.assertFalse(Membership.objects.exists())
        self.assertEqual(set(ApplicationAccess.objects.filter(user=self.user).values_list('application', flat=True)), {'faq', 'rooms'})
        client = Client(enforce_csrf_checks=True)
        password = secrets.token_urlsafe(32)
        result = post(client, '/auth/basework/access', {'code': self.code, 'new_password1': password, 'new_password2': password})
        self.assertContains(result, '<strong>new-member</strong>', html=True)
        self.assertEqual(login(client, self.user, password).status_code, 302)
        self.assertFalse(client.get('/api/v1/basework/bootstrap', secure=True).json()['canManageUsers'])

    def test_only_specific_basework_admin_can_manage(self):
        self.assertTrue(self.client.get('/api/v1/basework/bootstrap', secure=True).json()['canManageUsers'])
        Administrator.objects.filter(user=self.actor).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(ROOT, secure=True).status_code, 401)
        self.assertEqual(login(self.client, self.actor, self.password,
                         Authenticator.objects.get(user=self.actor)).status_code, 302)
        self.assertEqual(self.client.get(ROOT, secure=True).status_code, 403)
        self.assertFalse(self.client.get('/api/v1/basework/bootstrap', secure=True).json()['canManageUsers'])

    def test_plain_user_with_rooms_permission_is_not_admin(self):
        user = User.objects.create_user('rooms-admin-fixture', self.password)
        ApplicationAccess.objects.create(user=user, application='rooms')
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(login(client, user, self.password).status_code, 302)
        self.assertEqual(client.get(ROOT, secure=True).status_code, 403)
        self.assertEqual(post(client, ROOT + 'new/', self.form_data()).status_code, 403)
        self.assertFalse(User.objects.filter(username='new-member').exists())

    def test_anonymous_and_csrf_and_https_required(self):
        self.assertEqual(Client().get(ROOT, secure=True).status_code, 401)
        self.assertEqual(self.client.get(ROOT).status_code, 403)
        self.assertEqual(post(self.client, ROOT + 'new/', self.form_data(), csrf=False).status_code, 403)
        self.assertFalse(User.objects.filter(username='new-member').exists())

    def test_create_replay_and_duplicate_username_are_not_second_accounts(self):
        self.create()
        self.assertEqual(post(self.client, ROOT + 'new/', self.data).status_code, 409)
        self.assertEqual(post(self.client, ROOT + 'new/', self.form_data()).status_code, 409)
        self.assertEqual(User.objects.filter(username='new-member').count(), 1)
        self.assertEqual(self.version(), 2)

    def test_unknown_permissions_and_fields_are_rejected(self):
        for data in ({**self.form_data(), 'applications': ['marketplace']},
                     {**self.form_data(), 'admin': 'true'},
                     {**self.form_data(), 'applications': ['faq', 'faq']}):
            self.assertEqual(post(self.client, ROOT + 'new/', data).status_code, 400)
        self.assertFalse(User.objects.filter(username='new-member').exists())

    def test_expired_or_foreign_ticket_fails(self):
        data = self.form_data()
        with patch('django.core.signing.time.time', return_value=time.time() + 901):
            self.assertEqual(post(self.client, ROOT + 'new/', data).status_code, 409)
        other = User.objects.create_user('another-person', self.password)
        data['ticket'] = service.creation_ticket(other)
        self.assertEqual(post(self.client, ROOT + 'new/', data).status_code, 403)

    def test_stale_confirmation_blocks_all_mutations(self):
        self.create()
        AccountSession.objects.filter(user=self.actor).update(password_confirmed_at=timezone.now() - timedelta(minutes=6))
        for path, data in ((ROOT + 'new/', self.form_data('second-member')),
                           (self.detail(), {'version': self.version(), 'action': 'code'}),
                           (self.detail(), {'version': self.version(), 'action': 'access', 'applications': []})):
            response = post(self.client, path, data)
            self.assertContains(response, 'Подтвердить вход', status_code=403)

    def test_access_change_revokes_session_and_replay_is_stale(self):
        self.create()
        password = secrets.token_urlsafe(32)
        personal.use_code(self.code, password, password)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(login(client, self.user, password).status_code, 302)
        cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
        data = {'version': self.version(), 'action': 'access', 'applications': ['faq']}
        self.assertEqual(post(self.client, self.detail(), data).status_code, 302)
        self.assertEqual(client.get('/api/v1/basework/bootstrap', secure=True).status_code, 401)
        self.assertEqual(post(self.client, self.detail(), data).status_code, 409)
        self.assertEqual(post(self.client, self.detail(), {**data, 'version': self.version(), 'applications': ['faq', 'rooms']}).status_code, 302)
        client.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(client.get('/api/v1/basework/bootstrap', secure=True).status_code, 401)

    def test_code_reissue_preserves_mfa_and_permissions(self):
        self.create()
        before = list(ApplicationAccess.objects.filter(user=self.user).values_list('pk', flat=True))
        device = Authenticator.objects.create(user=self.user, confirmed=True)
        data = {'version': self.version(), 'action': 'code'}
        response = post(self.client, self.detail(), data)
        self.assertEqual(response.status_code, 200)
        code = response.context['invitation'].split('Код доступа: ')[1].split('\n')[0]
        self.assertNotEqual(code, self.code)
        self.assertEqual(post(self.client, self.detail(), data).status_code, 409)
        self.assertEqual(list(ApplicationAccess.objects.filter(user=self.user).values_list('pk', flat=True)), before)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        self.assertIsNone(device.revoked_at)
        password = secrets.token_urlsafe(32)
        self.assertEqual(personal.use_code(code, password, password), self.user.username)

    def test_cannot_change_self_or_other_admin_or_legacy_user(self):
        self.create()
        legacy = User.objects.create_user('legacy-member', self.password)
        for user in (self.actor, legacy):
            response = post(self.client, ROOT + str(user.pk) + '/', {'version': 1, 'action': 'code'})
            self.assertIn(response.status_code, [403, 404])
        PlatformRoleAssignment.objects.create(user=self.user)
        self.assertEqual(post(self.client, self.detail(), {'version': self.version(), 'action': 'code'}).status_code, 403)

    def test_listing_search_and_no_code_in_get(self):
        self.create()
        self.assertContains(self.client.get(ROOT + '?q=new-member', secure=True), 'new-member')
        self.assertContains(self.client.get(ROOT + '?q=absent-user', secure=True), 'никого не найдено')
        self.assertNotContains(self.client.get(self.detail(), secure=True), self.code)
        self.assertNotContains(self.client.get(ROOT, secure=True), self.code)

    def test_admin_revocation_prevents_old_and_new_sessions_after_restore(self):
        self.create()
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        Administrator.objects.filter(user=self.actor).update(revoked_at=timezone.now())
        self.assertEqual(post(self.client, self.detail(), {'version': self.version(), 'action': 'code'}).status_code, 401)
        Administrator.objects.create(user=self.actor)
        self.client.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(self.client.get(ROOT, secure=True).status_code, 401)
