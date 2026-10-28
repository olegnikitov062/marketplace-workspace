"""Вход через штатные формы, CSRF и реестр сессий на изолированной тестовой БД."""
import secrets
import time
from urllib.parse import urlencode
from unittest.mock import patch

from django.conf import settings
from django.test import Client, TestCase
from django.utils import timezone
from django_otp.oath import TOTP

from accounts.models import AccountContact
from account_security.models import AccountSession, Authenticator
from ownership.models import Membership, Organization, User


class PasswordLoginTests(TestCase):
    path = '/auth/basework/login'

    def setUp(self):
        self.password = secrets.token_urlsafe(32)
        self.user = User.objects.create_user('synthetic-basework-login', self.password)
        AccountContact.objects.create(user=self.user, email='login@example.invalid', activated_at=timezone.now())
        self.organization = Organization.objects.create(name='synthetic-login')
        self.membership = Membership.objects.create(user=self.user, organization=self.organization, role='observer')
        self.client = Client(enforce_csrf_checks=True)

    def post(self, data, *, csrf=True, path=None):
        headers = {'HTTP_ORIGIN': 'https://testserver'}
        if csrf:
            headers['HTTP_X_CSRFTOKEN'] = self.client.get('/auth/csrf', secure=True).json()['csrfToken']
        return self.client.post(path or self.path, urlencode(data), content_type='application/x-www-form-urlencoded', secure=True, **headers)

    def login(self, password=None, path=None):
        self.client.get(path or self.path, secure=True)
        return self.post({'base_work_login-current_step':'auth', 'auth-username':self.user.username,
                          'auth-password':self.password if password is None else password}, path=path)

    def test_form_has_labels_autocomplete_and_no_cache(self):
        r=self.client.get(self.path, secure=True)
        for text in ['Вход в аккаунт', 'Логин', 'Пароль', 'autocomplete="username"', 'autocomplete="current-password"']:
            self.assertContains(r, text)
        self.assertIn('no-store', r['Cache-Control'])

    def test_password_opens_basework_without_oidc_and_logout_revokes_session(self):
        r=self.login()
        self.assertEqual(r.status_code,302)
        self.assertEqual(r['Location'],'/basework/')
        r=self.client.get('/api/v1/basework/bootstrap',secure=True)
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['session']['user']['id'],str(self.user.pk))
        self.assertEqual(r.json()['applications'],[])
        old_cookie=self.client.cookies[settings.SESSION_COOKIE_NAME].value
        csrf=r.json()['csrfToken']
        r=self.client.post('/api/v1/basework/logout',data='',content_type='application/json',secure=True,
                           HTTP_ORIGIN='https://testserver',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap',secure=True).status_code,401)
        self.client.cookies[settings.SESSION_COOKIE_NAME]=old_cookie
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap',secure=True).status_code,401)
        self.assertIsNotNone(AccountSession.objects.get(user=self.user).revoked_at)

    def test_wrong_password_is_readable_and_does_not_create_session(self):
        r=self.login(secrets.token_urlsafe(32))
        self.assertContains(r,'Неверный логин или пароль.')
        self.assertFalse(AccountSession.objects.exists())
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap',secure=True).status_code,401)

    def test_post_requires_csrf(self):
        self.client.get(self.path,secure=True)
        self.assertEqual(self.post({'base_work_login-current_step':'auth','auth-username':self.user.username,
                                    'auth-password':self.password},csrf=False).status_code,403)
        self.assertFalse(AccountSession.objects.exists())

    def test_disabled_user_cannot_login(self):
        self.user.is_active=False
        self.user.save(update_fields=['is_active'])
        self.assertContains(self.login(),'Неверный логин или пароль.')
        self.assertFalse(AccountSession.objects.exists())

    def test_external_next_cannot_change_redirect(self):
        r=self.login(path=self.path+'?next=https://example.invalid/')
        self.assertEqual(r['Location'],'/basework/')

    def test_owner_still_requires_enrollment(self):
        self.membership.role='owner'
        self.membership.save(update_fields=['role'])
        r=self.login()
        self.assertEqual(r['Location'],'/auth/mfa/setup/')
        self.assertEqual(AccountSession.objects.get(user=self.user).level,'enroll')
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap',secure=True).status_code,403)

    def test_existing_factor_is_required_then_returns_to_basework(self):
        device=Authenticator.objects.create(user=self.user,confirmed=True)
        r=self.login()
        self.assertContains(r,'Подтверждение входа')
        self.assertFalse(AccountSession.objects.exists())
        tick=int(time.time()//30)
        totp=TOTP(device.bin_key,device.step,device.t0,device.digits,device.drift)
        totp.time=tick*30+1
        code=str(totp.token()).zfill(6)
        with patch('django_otp.plugins.otp_totp.models.time.time',return_value=totp.time):
            r=self.post({'base_work_login-current_step':'token','token-otp_token':code})
        self.assertEqual(r.status_code,302)
        self.assertEqual(r['Location'],'/basework/')
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap',secure=True).status_code,200)
