"""Authlib проверяет OIDC; транспорт ограничен тремя точными HTTPS endpoint."""
import time
from pathlib import Path
from authlib.integrations.django_client import OAuth
from authlib.integrations.django_client.apps import DjangoOAuth2App
from authlib.integrations.requests_client import OAuth2Session
from django.core.exceptions import PermissionDenied
from django.db import connection
from authlib.integrations.base_client import OAuthError
from joserfc.errors import JoseError
from .oidc_configuration import current


class RestrictedSession(OAuth2Session):
    def request(self, method, url, **kwargs):
        provider = current()
        if connection.in_atomic_block or (method.upper(), url) not in {
                ('GET', provider.discovery), ('GET', provider.jwks_uri), ('POST', provider.token_endpoint)}:
            raise PermissionDenied()
        self.trust_env = False
        kwargs.update(allow_redirects=False, timeout=(2, 3), verify=provider.ca_file or True, stream=True)
        response = super().request(method, url, **kwargs)
        try:
            if response.status_code != 200:
                raise PermissionDenied()
            chunks, size, started = [], 0, time.monotonic()
            for chunk in response.iter_content(1):
                size += len(chunk)
                if size > 131072 or time.monotonic() - started > 5:
                    raise PermissionDenied()
                chunks.append(chunk)
            response._content = b''.join(chunks)
            response._content_consumed = True
            return response
        finally:
            response.close()


class OIDCApp(DjangoOAuth2App):
    client_cls = RestrictedSession

    def load_server_metadata(self):
        if self._server_metadata_url and not getattr(self, '_verified_discovery', False):
            provider = current()
            with self._get_session() as session:
                response = session.request('GET', provider.discovery, withhold_token=True)
                metadata = response.json()
            expected = {'issuer': provider.issuer, 'authorization_endpoint': provider.authorization_endpoint,
                        'token_endpoint': provider.token_endpoint, 'jwks_uri': provider.jwks_uri}
            if not isinstance(metadata, dict) or any(metadata.get(k) != v for k, v in expected.items()):
                raise PermissionDenied()
            for name, value in [('code_challenge_methods_supported', 'S256'),
                                ('id_token_signing_alg_values_supported', 'RS256'),
                                ('response_types_supported', 'code'),
                                ('token_endpoint_auth_methods_supported', 'client_secret_basic')]:
                if not isinstance(metadata.get(name), list) or value not in metadata[name]:
                    raise PermissionDenied()
            # Входящие jwks, параметры транспорта и auth_method не становятся настройками Authlib.
            self.server_metadata = {**expected, 'id_token_signing_alg_values_supported': ['RS256'],
                                    'code_challenge_methods_supported': ['S256']}
            self._verified_discovery = True
        return self.server_metadata


def client(discovery=False):
    provider = current()
    return OAuth().register('basework', client_cls=OIDCApp, client_id=provider.client_id,
        client_secret=Path(provider.secret_file).read_text().strip(),
        server_metadata_url=provider.discovery if discovery else None,
        issuer=provider.issuer, authorization_endpoint=provider.authorization_endpoint,
        token_endpoint=provider.token_endpoint, jwks_uri=provider.jwks_uri,
        code_challenge_methods_supported=['S256'], id_token_signing_alg_values_supported=['RS256'],
        client_kwargs={'scope': 'openid', 'code_challenge_method': 'S256',
                       'token_endpoint_auth_method': 'client_secret_basic'})


def exchange(attempt, code):
    provider = current()
    app = client(discovery=True)
    try:
        token = app.fetch_access_token(redirect_uri=provider.redirect_uri, code=code, code_verifier=attempt.verifier)
        claims = app.parse_id_token(token, nonce=attempt.nonce, leeway=0)
    except (OAuthError, JoseError, ValueError, KeyError, TypeError):
        raise PermissionDenied() from None
    if (claims is None or claims.get('iss') != provider.issuer or not isinstance(claims.get('sub'), str)
            or not claims['sub'] or len(claims['sub']) > 255):
        raise PermissionDenied()
    return claims['iss'], claims['sub']
