"""Изолированные проверки FAQ; реальные данные и назначения не используются."""
import copy
import json
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from django.conf import settings
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from account_security.models import AccountSession
from basework import faq, services
from basework.models import ApplicationAccess
from basework.tests import test_password_login as password_tests


DOCUMENT = {
    'version': 7, 'updatedAt': '2026-10-29T12:00:00+03:00',
    'people': [{'name': 'Тестовый сотрудник', 'role': 'Учёт поставок'}, {'name': 'Второй', 'role': 'Склад'}],
    'items': [
        {'id': 'q-1', 'cat': 'Поставки', 'q': 'Как передать отчёт?', 'contacts': [['Тестовый сотрудник', 'После сверки'], ['Второй', 'Резерв']]},
        {'id': 'q-2', 'cat': 'Другое', 'q': ('Длинный вопрос ' * 150).strip(), 'contacts': []},
    ],
}


class FaqContractTests(SimpleTestCase):
    def test_exact_document_categories_contacts_and_version(self):
        result = faq.parse_document(json.dumps(DOCUMENT).encode())
        self.assertEqual(result, DOCUMENT)
        self.assertEqual(faq.search(result), {**DOCUMENT, 'categories': ['Поставки', 'Другое'], 'total': 2})

    def test_search_question_category_person_role_note_and_combination(self):
        for query in ('ОТЧЕТ', 'Поставки', 'сотрудник', 'учет', 'сверки', 'отчёт резерв'):
            self.assertEqual([i['id'] for i in faq.search(DOCUMENT, query)['items']], ['q-1'])
        self.assertEqual(faq.search(DOCUMENT, 'нет такого')['items'], [])
        self.assertEqual(faq.search(DOCUMENT, 'отчет', 'Другое')['items'], [])
        self.assertEqual([i['id'] for i in faq.search(DOCUMENT, category='Другое')['items']], ['q-2'])
        self.assertEqual(faq.search(DOCUMENT, 'нет такого')['version'], 7)

    def test_empty_source_is_not_an_error(self):
        doc = {'version': 0, 'updatedAt': '', 'people': [], 'items': []}
        self.assertEqual(faq.search(faq.parse_document(json.dumps(doc).encode())), {**doc, 'categories': [], 'total': 0})

    def test_editor_fields_are_not_forwarded(self):
        doc = copy.deepcopy(DOCUMENT)
        doc.update(adminKey='synthetic-key', adminPath='synthetic-editor', warning='synthetic-private')
        doc['people'][0]['password'] = 'synthetic-secret'
        doc['items'][0]['internal'] = 'synthetic-secret'
        self.assertEqual(faq.parse_document(json.dumps(doc).encode()), DOCUMENT)

    def test_malformed_source_fails_closed(self):
        for mutate in (
            lambda d: d.update(version=True),
            lambda d: d.update(updatedAt=None),
            lambda d: d['items'][0].update(id=''),
            lambda d: d['items'].append(d['items'][0]),
            lambda d: d['people'].append(d['people'][0]),
            lambda d: d['items'][0].update(contacts=[['Неизвестный', '']]),
            lambda d: d.update(items={}),
        ):
            doc = copy.deepcopy(DOCUMENT)
            mutate(doc)
            with self.assertRaises(ValueError):
                faq.parse_document(json.dumps(doc).encode())
        with self.assertRaises(ValueError):
            faq.parse_document(b' ' * (faq.MAX_BYTES + 1))

    def test_only_fixed_server_url_without_credentials_or_query(self):
        for url in ('', 'file:///data.json', 'https://reader:key@example.invalid/api/items',
                    'https://example.invalid/api/items?key=x', 'https://example.invalid/api/items#x',
                    'https://example.invalid/editor', 'https://example.invalid:bad/api/items'):
            with override_settings(BASEWORK_FAQ_URL=url):
                self.assertFalse(faq.configured())
                with self.assertRaises(faq.SourceUnavailable):
                    faq.read_source()


class FaqTransportTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.status, cls.body, cls.content_type, cls.requests = 200, json.dumps(DOCUMENT).encode(), 'application/json', []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                cls.requests.append((self.command, self.path, dict(self.headers)))
                self.send_response(cls.status)
                self.send_header('Content-Type', cls.content_type)
                self.send_header('Location', '/editor')
                self.end_headers()
                self.wfile.write(cls.body)
            def log_message(self, *args):
                pass
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        super().tearDownClass()

    def test_http_get_only_no_credentials_and_no_redirect(self):
        cls = type(self)
        with override_settings(BASEWORK_FAQ_URL=f'http://127.0.0.1:{self.server.server_port}/api/items'):
            self.assertEqual(faq.read_source(), DOCUMENT)
            method, path, headers = cls.requests[-1]
            self.assertEqual((method, path), ('GET', '/api/items'))
            self.assertTrue({'Cookie', 'Authorization', 'X-Admin-Key'}.isdisjoint(headers))
            for status, body, content_type in ((302, b'', 'application/json'), (500, b'{}', 'application/json'),
                    (200, b'<html>', 'text/html'), (200, b'{', 'application/json'),
                    (200, b' ' * (faq.MAX_BYTES + 1), 'application/json')):
                cls.status, cls.body, cls.content_type = status, body, content_type
                before = len(cls.requests)
                with self.assertRaises(faq.SourceUnavailable):
                    faq.read_source()
                self.assertEqual(len(cls.requests), before + 1)


@override_settings(BASEWORK_FAQ_URL='http://127.0.0.1:9/api/items', PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FaqHTTPTests(TestCase):
    setUp = password_tests.PasswordLoginTests.setUp
    post = password_tests.PasswordLoginTests.post
    login = password_tests.PasswordLoginTests.login
    path = password_tests.PasswordLoginTests.path
    endpoint = '/api/v1/basework/faq/items'

    def allow(self):
        return ApplicationAccess.objects.create(user=self.user, application='faq')

    def get(self, suffix=''):
        return self.client.get(self.endpoint + suffix, secure=True)

    def test_password_login_permission_before_source_and_exact_response(self):
        with patch('basework.faq.read_source', return_value=DOCUMENT) as source:
            self.assertEqual(self.get().status_code, 401)
            self.login()
            self.assertEqual(self.get().status_code, 403)
            source.assert_not_called()
            self.allow()
            response = self.get()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), faq.search(DOCUMENT))
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(source.call_count, 1)
            catalog = self.client.get('/api/v1/basework/bootstrap', secure=True).json()['applications']
            self.assertEqual(catalog, [{'id': 'faq', 'access': 'allowed', 'availability': 'available'}])

    def test_source_runs_outside_transaction_and_sql_signer(self):
        self.login()
        self.allow()
        outer_blocks = len(connection.atomic_blocks)
        def read():
            # В TestCase остаются только внешние транзакции самого тестового раннера.
            self.assertEqual(len(connection.atomic_blocks), outer_blocks)
            self.assertEqual(connection.execute_wrappers, [])
            return DOCUMENT
        with patch('basework.faq.read_source', side_effect=read):
            self.assertEqual(self.get().status_code, 200)

    def test_revocation_within_60_seconds_and_old_cookie_replay(self):
        self.login()
        access = self.allow()
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with patch('basework.faq.read_source', return_value=DOCUMENT) as source:
            self.assertEqual(self.get().status_code, 200)
            started = time.monotonic()
            services.revoke_application(access.pk)
            for _ in range(2):
                self.client.cookies[settings.SESSION_COOKIE_NAME] = cookie
                self.assertEqual(self.get().status_code, 401)
            self.assertLess(time.monotonic() - started, 60)
            self.assertEqual(source.call_count, 1)
            self.login()
            self.assertEqual(self.get().status_code, 403)

    def test_revocation_during_source_read_prevents_response(self):
        self.login()
        access = self.allow()
        def read():
            services.revoke_application(access.pk)
            return DOCUMENT
        with patch('basework.faq.read_source', side_effect=read):
            response = self.get()
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('items', response.json())

    def test_permission_removed_during_read_is_rechecked(self):
        self.login()
        access = self.allow()
        def read():
            ApplicationAccess.objects.filter(pk=access.pk).update(revoked_at=timezone.now())
            return DOCUMENT
        with patch('basework.faq.read_source', side_effect=read):
            self.assertIn(self.get().status_code, (401, 403))

    def test_user_blocked_during_read_is_rechecked(self):
        self.login()
        self.allow()
        def read():
            type(self.user).objects.filter(pk=self.user.pk).update(is_active=False)
            return DOCUMENT
        with patch('basework.faq.read_source', side_effect=read):
            self.assertEqual(self.get().status_code, 401)

    def test_all_write_methods_denied_even_with_csrf_and_right(self):
        self.login()
        self.allow()
        token = self.client.get('/auth/csrf', secure=True).json()['csrfToken']
        with patch('basework.faq.read_source') as source:
            for method in ('post', 'put', 'patch', 'delete'):
                response = getattr(self.client, method)(self.endpoint, data='{}', content_type='application/json',
                    secure=True, HTTP_ORIGIN='https://testserver', HTTP_X_CSRFTOKEN=token)
                self.assertEqual(response.status_code, 405)
            source.assert_not_called()

    def test_source_error_does_not_disclose_details_or_break_catalog(self):
        self.login()
        self.allow()
        with patch('basework.faq.read_source', side_effect=faq.SourceUnavailable('synthetic-secret')):
            response = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'source_unavailable'})
        self.assertEqual(self.client.get('/api/v1/basework/bootstrap', secure=True).status_code, 200)

    def test_search_and_reject_client_supplied_url_or_role(self):
        self.login()
        self.allow()
        with patch('basework.faq.read_source', return_value=DOCUMENT) as source:
            self.assertEqual(self.get('?q=резерв').json()['items'], [DOCUMENT['items'][0]])
            for suffix in ('?url=http://example.invalid', '?role=admin', '?q=a&q=b', '?q=' + 'x' * 301):
                self.assertEqual(self.get(suffix).status_code, 400)
            self.assertEqual(source.call_count, 1)

    def test_unconfigured_and_partial_mfa_fail_closed(self):
        self.membership.role = 'owner'
        self.membership.save(update_fields=['role'])
        self.login()
        self.allow()
        with patch('basework.faq.read_source') as source:
            self.assertEqual(self.get().status_code, 403)
            source.assert_not_called()

    def test_missing_registry_and_expired_session_fail_before_read(self):
        self.login()
        self.allow()
        record = AccountSession.objects.get(user=self.user)
        with patch('basework.faq.read_source') as source:
            with patch('account_security.services.timezone.now', return_value=record.expires_at + timedelta(seconds=1)):
                self.assertEqual(self.get().status_code, 401)
            forged = Client()
            forged.force_login(self.user, backend='accounts.backends.PersonalAccountBackend')
            self.assertEqual(forged.get(self.endpoint, secure=True).status_code, 401)
            source.assert_not_called()
