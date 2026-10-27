import json
from unittest.mock import Mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from basework.publication import TrustedGateway, parse, load


CONFIG = {'origin': 'https://basework.example.invalid', 'trusted_proxy_ips': ['172.20.0.2']}


class PublicationTests(SimpleTestCase):
    def test_exact_origin_and_peers(self):
        value = parse(json.dumps(CONFIG))
        self.assertEqual(value['authority'], 'basework.example.invalid')
        self.assertEqual(value['trusted_proxy_ips'], ('172.20.0.2',))
        for origin in ('http://basework.example.invalid', 'https://basework.example.invalid/',
                       'https://basework.example.invalid:443', 'https://basework.example.invalid/a',
                       'https://basework.example.invalid?x=1', 'https://user@basework.example.invalid'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                parse(json.dumps({**CONFIG, 'origin': origin}))

    def test_no_ranges_duplicates_or_extra_fields(self):
        for peers in ([], ['172.20.0.0/16'], ['*'], ['0.0.0.0'], ['172.20.0.2'] * 2, ['fe80::1%eth0'], [None]):
            with self.subTest(peers=peers), self.assertRaises(ValueError):
                parse(json.dumps({**CONFIG, 'trusted_proxy_ips': peers}))
        for raw in ('{}', '[]', '{"origin":"a","origin":"b"}', ' ' * 8193,
                    json.dumps({**CONFIG, 'extra': True})):
            with self.assertRaises(ValueError):
                parse(raw)
        with self.assertRaises(ValueError):
            load({'BASEWORK_PUBLIC_CONFIG_FILE': '/tmp/config.json'})

    @override_settings(BASEWORK_PUBLIC=parse(json.dumps(CONFIG)), ALLOWED_HOSTS=['basework.example.invalid'],
                       SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'), USE_X_FORWARDED_HOST=False)
    def test_gateway_denies_before_downstream_and_replaces_client_address(self):
        headers = {'REMOTE_ADDR': '172.20.0.2', 'HTTP_HOST': 'basework.example.invalid',
                   'HTTP_X_FORWARDED_PROTO': 'https', 'HTTP_X_BASEWORK_CLIENT_IP': '192.0.2.17'}
        factory = RequestFactory()
        downstream = Mock(return_value=HttpResponse('ok'))
        middleware = TrustedGateway(downstream)
        for change in ({'REMOTE_ADDR': '172.20.0.3'}, {'HTTP_HOST': 'other.invalid'},
                       {'HTTP_HOST': 'basework.example.invalid:443'}, {'HTTP_X_FORWARDED_PROTO': 'http'},
                       {'HTTP_X_FORWARDED_PROTO': 'https,http'}, {'HTTP_X_FORWARDED_HOST': 'other.invalid'},
                       {'HTTP_X_BASEWORK_CLIENT_IP': ''}, {'HTTP_X_BASEWORK_CLIENT_IP': '192.0.2.17,192.0.2.18'}):
            with self.subTest(change=change):
                response = middleware(factory.get('/auth/csrf', **{**headers, **change}))
                self.assertEqual(response.status_code, 403)
                self.assertIn('no-store', response['Cache-Control'])
                downstream.assert_not_called()
        for path in ('/auth/security/probe', '/auth/security/probe/00000000-0000-0000-0000-000000000001/'):
            self.assertEqual(middleware(factory.get(path, **headers)).status_code, 404)
            downstream.assert_not_called()
        request = factory.get('/auth/csrf', **headers, HTTP_X_FORWARDED_FOR='198.51.100.1', HTTP_FORWARDED='for=198.51.100.2')
        self.assertEqual(middleware(request).status_code, 200)
        self.assertTrue(request.is_secure())
        self.assertEqual(request.META['REMOTE_ADDR'], '192.0.2.17')
        self.assertNotIn('HTTP_X_FORWARDED_FOR', request.META)
        self.assertNotIn('HTTP_FORWARDED', request.META)
        downstream.assert_called_once_with(request)


class AuthOptionsTests(TestCase):
    def test_anonymous_minimal_flag_and_no_cache(self):
        for enabled in (False, True):
            with override_settings(BASEWORK_OIDC_ENABLED=enabled):
                result = self.client.get('/api/v1/basework/auth-options', secure=True)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json(), {'oidcEnabled': enabled})
                self.assertIn('no-store', result['Cache-Control'])
        self.assertEqual(self.client.post('/api/v1/basework/auth-options', secure=True).status_code, 405)
