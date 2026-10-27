"""Контракт согласованной библиотеки. Это не проверка действующего SSO."""
import hashlib
import time
from base64 import urlsafe_b64encode
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from authlib.integrations.django_client import OAuth
from django.test import RequestFactory, SimpleTestCase
from joserfc import jwt
from joserfc.jwk import RSAKey


class OIDCLibraryTests(SimpleTestCase):
    def setUp(self):
        self.key = RSAKey.generate_key(2048, parameters={'kid': 'isolated-key'})
        self.client = OAuth().register('basework_contract', client_id='isolated-client',
            client_secret='isolated-secret',
            issuer='https://provider.example.invalid',
            authorization_endpoint='https://provider.example.invalid/authorize',
            token_endpoint='https://provider.example.invalid/token',
            jwks={'keys': [self.key.as_dict(private=False)]},
            id_token_signing_alg_values_supported=['RS256'],
            client_kwargs={'scope': 'openid', 'code_challenge_method': 'S256', 'default_timeout': 5})
        self.request = RequestFactory().get('/callback')
        self.request.session = {}
        self.redirect = 'https://basework.example.invalid/callback'

    def begin(self):
        response = self.client.authorize_redirect(self.request, self.redirect)
        return parse_qs(urlsplit(response.url).query)

    def token(self, expected_nonce, **changes):
        now = int(time.time())
        claims = {'iss': 'https://provider.example.invalid', 'sub': 'explicit-subject',
                  'aud': 'isolated-client', 'iat': now, 'exp': now+60, 'nonce': expected_nonce}
        claims.update(changes)
        return {'id_token': jwt.encode({'alg': 'RS256', 'kid': 'isolated-key'}, claims, self.key)}

    def callback(self, state):
        request = RequestFactory().get('/callback', {'state': state, 'code': 'isolated-code'})
        request.session = self.request.session
        return request

    def test_code_pkce_nonce_fixed_redirect(self):
        params = self.begin()
        self.assertEqual(params['response_type'], ['code'])
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertEqual(params['redirect_uri'], [self.redirect])
        saved = self.client.framework.get_state_data(self.request.session, params['state'][0])
        expected = urlsafe_b64encode(hashlib.sha256(saved['code_verifier'].encode()).digest()).decode().rstrip('=')
        self.assertEqual(params['code_challenge'], [expected])
        self.assertEqual(params['nonce'], [saved['nonce']])

    def test_unknown_state_rejected_before_token_exchange(self):
        self.begin()
        with patch.object(self.client, 'fetch_access_token') as fetch:
            with self.assertRaises(Exception):
                self.client.authorize_access_token(self.callback('unknown'))
            fetch.assert_not_called()

    def test_library_consumes_state_and_validates_signed_token(self):
        params = self.begin()
        token = self.token(params['nonce'][0])
        with patch.object(self.client, 'fetch_access_token', return_value=token) as fetch:
            result = self.client.authorize_access_token(self.callback(params['state'][0]), leeway=0)
            self.assertEqual(result['userinfo']['sub'], 'explicit-subject')
            self.assertEqual(fetch.call_args.kwargs['redirect_uri'], self.redirect)
            self.assertIn('code_verifier', fetch.call_args.kwargs)
            with self.assertRaises(Exception):
                self.client.authorize_access_token(self.callback(params['state'][0]))
            self.assertEqual(fetch.call_count, 1)

    def test_wrong_issuer_audience_nonce_expiration_or_signature_rejected(self):
        for changes in ({'iss': 'https://other.example.invalid'}, {'aud': 'other-client'},
                        {'nonce': 'other'}, {'exp': int(time.time())-10}):
            with self.subTest(changes=changes):
                token = self.token('expected', **changes)
                with self.assertRaises(Exception):
                    self.client.parse_id_token(token, nonce='expected', leeway=0)
        other = RSAKey.generate_key(2048, parameters={'kid': 'isolated-key'})
        self.client.server_metadata['jwks'] = {'keys': [other.as_dict(private=False)]}
        with self.assertRaises(Exception):
            self.client.parse_id_token(self.token('expected'), nonce='expected', leeway=0)

    def test_provider_failure_does_not_produce_identity(self):
        params = self.begin()
        with patch.object(self.client, 'fetch_access_token', side_effect=ConnectionError()):
            with self.assertRaises(ConnectionError):
                self.client.authorize_access_token(self.callback(params['state'][0]))
        self.assertIsNone(self.client.framework.get_state_data(self.request.session, params['state'][0]))
