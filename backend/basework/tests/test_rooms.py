"""Контракты переговорок и серверные права на изолированных данных."""
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.db import connection
from django.test import TestCase, SimpleTestCase, override_settings

from basework import rooms, services
from basework.models import ApplicationAccess
from basework.tests import test_password_login as password_tests

DOCUMENT = {'events': [], 'rooms': [{'id': 'big', 'name': 'Большая'}], 'user': {'name': 'Тест', 'role': 'employee'},
            'policy': {'timeZone': 'Europe/Moscow', 'weekdays': [1,2,3,4,5], 'start': '08:00', 'end': '19:00'}}


@override_settings(BASEWORK_ROOMS_WRITES=True)
class RoomsHTTPTests(TestCase):
    setUp = password_tests.PasswordLoginTests.setUp
    post = password_tests.PasswordLoginTests.post
    login = password_tests.PasswordLoginTests.login
    path = '/auth/basework/login'
    endpoint = '/api/v1/basework/rooms/events'
    query = '?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z'

    def allow(self):
        return ApplicationAccess.objects.create(user=self.user, application='rooms')

    def read(self):
        return self.client.get(self.endpoint+self.query, secure=True)

    def write(self, csrf=True, **changes):
        headers = {'HTTP_ORIGIN': 'https://testserver', 'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
        if csrf:
            headers['HTTP_X_CSRFTOKEN'] = self.client.get('/auth/csrf', secure=True).json()['csrfToken']
        headers.update(changes)
        return self.client.post(self.endpoint, data='{}', content_type='application/json', secure=True, **headers)

    def test_session_and_right_checked_before_source(self):
        with patch('basework.rooms.exchange', return_value=(200, DOCUMENT)) as source:
            self.assertEqual(self.read().status_code, 401)
            self.login()
            self.assertEqual(self.read().status_code, 403)
            self.assertEqual(self.write().status_code, 403)
            source.assert_not_called()
            self.allow()
            response = self.read()
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(source.call_args.args[0], str(self.user.pk))

    def test_read_outside_transaction_and_recheck(self):
        self.login(); access=self.allow()
        outer=len(connection.atomic_blocks)
        def read(*args):
            self.assertEqual(len(connection.atomic_blocks),outer)
            self.assertEqual(connection.execute_wrappers,[])
            services.revoke_application(access.pk)
            return 200,DOCUMENT
        with patch('basework.rooms.exchange',side_effect=read):
            self.assertEqual(self.read().status_code,401)

    def test_csrf_idempotency_and_readonly(self):
        self.login(); self.allow()
        with patch('basework.rooms.exchange') as source:
            self.assertEqual(self.write(csrf=False).status_code,403)
            self.assertEqual(self.write(HTTP_IDEMPOTENCY_KEY='bad').status_code,400)
            with override_settings(BASEWORK_ROOMS_WRITES=False):
                self.assertEqual(self.write().status_code,403)
            source.assert_not_called()

    def test_write_is_locked_and_does_not_accept_actor_from_browser(self):
        self.login(); self.allow()
        def write(actor,method,path,body,operation):
            self.assertTrue(connection.in_atomic_block)
            self.assertEqual(str(actor),str(self.user.pk))
            self.assertEqual((method,path),('POST','/api/events'))
            self.assertTrue(rooms.operation_id(operation))
            return 201, {'created': [], 'skipped':0}
        with patch('basework.rooms.exchange',side_effect=write):
            self.assertEqual(self.write().status_code,201)

    def test_uncertain_write_never_claims_success(self):
        self.login(); self.allow()
        with patch('basework.rooms.exchange',side_effect=rooms.SourceUnavailable('secret')):
            response=self.write()
            self.assertEqual((response.status_code,response.json()),(503,{'status':'operation_unknown'}))

    def test_revoke_and_cookie_replay_no_write(self):
        self.login(); access=self.allow()
        cookie=self.client.cookies[settings.SESSION_COOKIE_NAME].value
        token=self.client.get('/auth/csrf',secure=True).json()['csrfToken']
        services.revoke_application(access.pk)
        with patch('basework.rooms.exchange') as source:
            for _ in range(2):
                self.client.cookies[settings.SESSION_COOKIE_NAME]=cookie
                self.assertEqual(self.read().status_code,401)
                self.assertEqual(self.client.post(self.endpoint,data='{}',content_type='application/json',secure=True,
                    HTTP_X_CSRFTOKEN=token,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_ORIGIN='https://testserver').status_code,401)
            source.assert_not_called()

    def test_route_and_range_validation(self):
        self.login(); self.allow()
        with patch('basework.rooms.exchange') as source:
            for suffix in ('','?from=2026-01-01&to=2026-01-02','?from=2026-01-01T00:00:00Z&to=2027-01-01T00:00:00Z',self.query+'&url=http://evil.invalid'):
                self.assertEqual(self.client.get(self.endpoint+suffix,secure=True).status_code,400)
            self.assertEqual(self.client.get(self.endpoint+'/bad'+self.query,secure=True).status_code,400)
            source.assert_not_called()

    def test_unknown_retry_readonly_and_revoked_session_for_all_methods(self):
        self.login(); access = self.allow()
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        token = self.client.get('/auth/csrf', secure=True).json()['csrfToken']
        operations = [(method, str(uuid.uuid4())) for method in ('POST', 'PUT', 'DELETE')]
        def send(method, operation):
            self.client.cookies[settings.SESSION_COOKIE_NAME] = cookie
            path = self.endpoint + ('/' + 'a'*32 if method != 'POST' else '')
            return getattr(self.client, method.lower())(path, data='{}', content_type='application/json', secure=True,
                HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=operation, HTTP_ORIGIN='https://testserver')
        with patch('basework.rooms.exchange', side_effect=rooms.SourceUnavailable()) as source:
            for method, operation in operations:
                self.assertEqual(send(method, operation).status_code, 503)
                self.assertEqual(source.call_args.args[-1], operation)
        with patch('basework.rooms.exchange') as source:
            with override_settings(BASEWORK_ROOMS_WRITES=False):
                for method, operation in operations:
                    self.assertEqual(send(method, operation).status_code, 403)
            services.revoke_application(access.pk)
            for method, operation in operations:
                self.assertEqual(send(method, operation).status_code, 401)
            source.assert_not_called()


class RoomsContractTests(SimpleTestCase):
    def test_source_config_is_explicit_and_local_http_only(self):
        with tempfile.TemporaryDirectory() as directory:
            key=Path(directory)/'synthetic.key'; key.write_bytes(b'x'*32)
            with override_settings(BASEWORK_ROOMS_KEY_FILE=str(key)):
                for url in ('','http://example.invalid/api/basework','https://reader:key@example.invalid/api/basework',
                            'https://example.invalid/api/basework?x=1','https://example.invalid/other'):
                    with override_settings(BASEWORK_ROOMS_URL=url): self.assertFalse(rooms.configured())
                with override_settings(BASEWORK_ROOMS_URL='https://example.invalid/api/basework'): self.assertTrue(rooms.configured())

    def test_document_projects_only_allowed_fields(self):
        value={**DOCUMENT,'secret':'not-public','user':{**DOCUMENT['user'],'password':'not-public'}}
        result=rooms.document(value)
        self.assertNotIn('not-public',json.dumps(result))
        self.assertEqual(result['policy'],DOCUMENT['policy'])
        with self.assertRaises(ValueError): rooms.document({**value,'policy':{}})

    def test_room_color_is_preserved_without_arbitrary_css(self):
        value={**DOCUMENT,'rooms':[{'id':'big','name':'Большая','color':'#7b5cf0','secret':'not-public'}]}
        self.assertEqual(rooms.document(value)['rooms'],[{'id':'big','name':'Большая','color':'#7b5cf0'}])
        value['rooms'][0]['color']='url(https://example.invalid)'
        self.assertNotIn('color',rooms.document(value)['rooms'][0])

    def test_conflict_details_strip_private_fields_and_validate_times(self):
        item={'roomId':'big','title':'Планёрка','start':'2026-11-02T10:00:00+03:00','end':'2026-11-02T11:00:00+03:00','owner':'private','password':'secret'}
        result=rooms.conflict_details({'conflicts':[{'with':item}]*5,'error':'secret'})
        self.assertEqual(len(result['conflicts']),3)
        self.assertEqual(set(result['conflicts'][0]),{'roomId','title','start','end'})
        self.assertNotIn('secret',json.dumps(result))
        with self.assertRaises(ValueError): rooms.conflict_details({'conflict':{**item,'end':'invalid'}})
        with self.assertRaises(ValueError): rooms.conflict_details({'conflict':{**item,'start':'2026-11-02T10:00:00'}})

    def test_optional_updated_timestamp(self):
        item={'id':'a'*32,'roomId':'big','title':'Тест','start':'2026-11-02T10:00:00+03:00','end':'2026-11-02T11:00:00+03:00',
              'createdBy':'Тест','updatedBy':'Тест','revision':'b'*64,'mine':True,'canEdit':True,'updatedAt':'2026-11-01T10:00:00Z'}
        self.assertEqual(rooms.event(item)['updatedAt'],item['updatedAt'])
        with self.assertRaises(ValueError): rooms.event({**item,'updatedAt':'bad'})
