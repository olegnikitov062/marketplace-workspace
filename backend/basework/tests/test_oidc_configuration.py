"""Закрытая конфигурация и границы транспорта без сетевых обращений."""
from pathlib import Path
import json
import ssl
from dataclasses import asdict, replace
from unittest.mock import patch
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.test import SimpleTestCase
from basework.oidc_configuration import configure, ISOLATED, CONFIG_FILE, fingerprint
from basework.oidc_client import RestrictedSession, client


class OIDCConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.provider = replace(ISOLATED, issuer='https://auth.example.invalid/login',
            authorization_endpoint='https://auth.example.invalid/login/api/oidc/authorization',
            token_endpoint='https://auth.example.invalid/login/api/oidc/token',
            jwks_uri='https://auth.example.invalid/login/jwks.json', client_id='basework-test',
            redirect_uri='https://app.example.invalid/auth/basework/oidc/callback')
        self.env = {'BASEWORK_OIDC_MODE': 'provider', 'BASEWORK_OIDC_CONFIG_FILE': CONFIG_FILE}

    def config(self, data=None, raw=None):
        if raw is None:
            raw = json.dumps(asdict(self.provider) if data is None else data).encode()
        with patch.dict('os.environ', self.env, clear=True), patch.object(Path, 'read_bytes', return_value=raw), \
                patch.object(Path, 'read_text', return_value='s'*40), patch('ssl.create_default_context'):
            namespace = {}
            configure(namespace)
            return namespace

    def test_disabled_by_default_without_secret_reads(self):
        namespace = {}
        with patch.dict('os.environ', {}, clear=True), patch.object(Path, 'read_text', side_effect=AssertionError()):
            configure(namespace)
        self.assertFalse(namespace['BASEWORK_OIDC_ENABLED'])

    def test_arbitrary_runtime_mode_is_rejected(self):
        with patch.dict('os.environ', {'BASEWORK_OIDC_MODE': 'production'}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                configure({})

    def test_isolated_mode_requires_exact_marker(self):
        with patch.dict('os.environ', {'BASEWORK_OIDC_MODE': 'isolated', 'BASEWORK_PG_REHEARSAL': 'wrong'}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                configure({})

    def test_network_transport_rejects_other_urls_and_methods_before_io(self):
        with self.settings(BASEWORK_OIDC_ENABLED=True, BASEWORK_OIDC_CONFIG=self.provider), \
                RestrictedSession() as session, patch('requests.sessions.Session.request', side_effect=AssertionError()):
            for method, url in [('GET', 'http://idp:8443/jwks'), ('GET', 'https://other.invalid'),
                                ('GET', self.provider.discovery+'?next=other'), ('POST', self.provider.discovery),
                                ('GET', self.provider.token_endpoint), ('POST', self.provider.jwks_uri)]:
                with self.subTest(method=method, url=url), self.assertRaises(PermissionDenied):
                    session.request(method, url)

    def test_network_transport_rejects_open_transaction(self):
        with self.settings(BASEWORK_OIDC_ENABLED=True, BASEWORK_OIDC_CONFIG=self.provider), \
                RestrictedSession() as session, patch('basework.oidc_client.connection') as connection:
            connection.in_atomic_block = True
            with patch('requests.sessions.Session.request', side_effect=AssertionError()), self.assertRaises(PermissionDenied):
                session.request('GET', self.provider.discovery)

    def test_provider_does_not_require_rehearsal_marker_and_forces_secure_cookies(self):
        namespace = self.config()
        self.assertEqual(namespace['BASEWORK_OIDC_CONFIG'], self.provider)
        self.assertTrue(namespace['SESSION_COOKIE_SECURE'])
        self.assertTrue(namespace['CSRF_COOKIE_SECURE'])
        self.assertTrue(namespace['BASEWORK_OIDC_ENABLED'])

    def test_only_exact_config_path(self):
        for path in ('', '/tmp/provider.json', '/run/config/../secrets/key'):
            with patch.dict('os.environ', {**self.env, 'BASEWORK_OIDC_CONFIG_FILE': path}, clear=True), \
                    patch.object(Path, 'read_bytes', side_effect=AssertionError()), self.assertRaises(ImproperlyConfigured):
                configure({})

    def test_strict_schema_and_duplicate_keys(self):
        data = asdict(self.provider)
        for invalid in ({}, [], {**data, 'client_secret': 'forbidden'}, {k:v for k,v in data.items() if k != 'ca_file'}):
            with self.subTest(invalid_type=type(invalid).__name__), self.assertRaises(ImproperlyConfigured):
                self.config(invalid)
        for raw in (b'{"issuer":"one","issuer":"two"}', b' ' * 8193, b'null', b'not-json'):
            with self.assertRaises(ImproperlyConfigured):
                self.config(raw=raw)

    def test_noncanonical_and_insecure_urls_rejected(self):
        for field, value in [('issuer', v) for v in (
                'http://auth.example.invalid', 'https://auth.example.invalid/login/',
                'https://user:secret@auth.example.invalid/login', 'https://auth.example.invalid/login?x=1',
                'https://auth.example.invalid/login#fragment', 'https://auth.example.invalid/a/../login',
                'https://auth.example.invalid/%2f', 'https://auth.example.invalid:99999',
                'https://auth.example.invalid:/login', 'https://auth.example.invalid:0443/login',
                'https://auth.example.invalid/\nlogin', 'https://auth.example.invalid/login//nested')]:
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                self.config({**asdict(self.provider), field:value})

    def test_endpoints_confined_to_configured_origin_and_prefix(self):
        for field in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
            for value in ('https://other.invalid/login/api', 'https://auth.example.invalid/other',
                          self.provider.discovery, self.provider.issuer+'/../other'):
                with self.subTest(field=field, value=value), self.assertRaises(ImproperlyConfigured):
                    self.config({**asdict(self.provider), field:value})

    def test_callback_and_client_id_are_not_arbitrary(self):
        for field, value in [('redirect_uri', 'https://app.example.invalid/other'),
                             ('redirect_uri', self.provider.redirect_uri+'?next=external'),
                             ('client_id', ''), ('client_id', 'has spaces'), ('client_id', 'x'*101)]:
            with self.subTest(field=field), self.assertRaises(ImproperlyConfigured):
                self.config({**asdict(self.provider), field:value})

    def test_secret_and_ca_paths_confined(self):
        for field in ('secret_file', 'ca_file'):
            for value in ('/tmp/key', '/run/secrets/../key', '/run/secrets/key/other', False):
                with self.subTest(field=field), self.assertRaises(ImproperlyConfigured):
                    self.config({**asdict(self.provider), field:value})

    def test_ca_may_use_system_trust_but_never_disable_tls(self):
        self.assertIsNone(self.config({**asdict(self.provider), 'ca_file':None})['BASEWORK_OIDC_CONFIG'].ca_file)
        with patch.dict('os.environ', self.env, clear=True), \
                patch.object(Path, 'read_bytes', return_value=json.dumps(asdict(self.provider)).encode()), \
                patch.object(Path, 'read_text', return_value='s'*40), \
                patch('ssl.create_default_context', side_effect=ssl.SSLError('synthetic')), \
                self.assertRaises(ImproperlyConfigured):
            configure({})

    def test_short_or_invalid_secret_rejected_without_echo(self):
        for value in ('', 'short', 'a'*32+'\ninternal', 'a'*4097):
            with patch.dict('os.environ', self.env, clear=True), \
                    patch.object(Path, 'read_bytes', return_value=json.dumps(asdict(self.provider)).encode()), \
                    patch.object(Path, 'read_text', return_value=value), self.assertRaises(ImproperlyConfigured) as raised:
                configure({})
            self.assertNotIn('short', str(raised.exception))

    def test_disabled_transport_denies_even_configured_address(self):
        with self.settings(BASEWORK_OIDC_ENABLED=False, BASEWORK_OIDC_CONFIG=self.provider), \
                patch('requests.sessions.Session.request', side_effect=AssertionError()), \
                RestrictedSession() as session, self.assertRaises(PermissionDenied):
            session.request('GET', self.provider.discovery)

    def test_fingerprint_covers_each_parameter_and_rotated_files(self):
        with self.settings(BASEWORK_OIDC_ENABLED=True, BASEWORK_OIDC_CONFIG=self.provider), \
                patch.object(Path, 'read_bytes', return_value=b'synthetic'):
            initial = fingerprint()
            for field in asdict(self.provider):
                changed = replace(self.provider, **{field: getattr(self.provider, field)+'changed'})
                with self.settings(BASEWORK_OIDC_CONFIG=changed):
                    self.assertNotEqual(initial, fingerprint(), field)
            with patch.object(Path, 'read_bytes', return_value=b'rotated'):
                self.assertNotEqual(initial, fingerprint())

    def test_authorization_has_fixed_client_callback_and_pkce(self):
        from urllib.parse import parse_qs, urlsplit
        with self.settings(BASEWORK_OIDC_ENABLED=True, BASEWORK_OIDC_CONFIG=self.provider), \
                patch.object(Path, 'read_text', return_value='s'*40):
            response = client().create_authorization_url(self.provider.redirect_uri,
                state='state', nonce='nonce', code_verifier='v'*43)
        url = urlsplit(response['url'])
        self.assertEqual(url.scheme+'://'+url.netloc+url.path, self.provider.authorization_endpoint)
        query = parse_qs(url.query)
        self.assertEqual(query['client_id'], [self.provider.client_id])
        self.assertEqual(query['redirect_uri'], [self.provider.redirect_uri])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertEqual(query['scope'], ['openid'])

    def test_general_guard_remains_closed(self):
        from config.guard import validate, ConfigurationError, DISABLED
        for key in DISABLED:
            with self.assertRaises(ConfigurationError):
                validate({'ENVIRONMENT':'beta', 'PROCESS_MODE':'web', **self.env, key:'true'})
