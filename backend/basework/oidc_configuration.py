"""Закрытая конфигурация OIDC: фиксированный стенд или явно заданный провайдер."""
import hashlib
import json
import os
import re
import ssl
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied

PROJECT = 'basework-stage3-pg-20261027'
ISSUER = 'https://idp:8443'
CALLBACK = 'https://web:8443/auth/basework/oidc/callback'
CA = '/run/secrets/oidc_ca'
SECRET = '/run/secrets/oidc_client_secret'
CONFIG_FILE = '/run/config/basework_oidc.json'
CALLBACK_PATH = '/auth/basework/oidc/callback'


@dataclass(frozen=True)
class Provider:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    client_id: str
    redirect_uri: str
    secret_file: str
    ca_file: str | None

    @property
    def discovery(self):
        return self.issuer + '/.well-known/openid-configuration'


ISOLATED = Provider(ISSUER, ISSUER+'/authorize', ISSUER+'/token', ISSUER+'/jwks',
                    'basework-isolated', CALLBACK, SECRET, CA)


def https_url(value):
    if not isinstance(value, str) or not re.fullmatch(r'https://[a-z0-9.:-]+(?:/[A-Za-z0-9._~/-]*)?', value):
        raise ValueError()
    url = urlsplit(value)
    if (not url.hostname or url.port == 0 or url.username or url.password
            or url.netloc != url.hostname + (':' + str(url.port) if url.port is not None else '')
            or not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*', url.hostname)
            or any(part in {'.', '..'} for part in url.path.split('/')) or '//' in url.path):
        raise ValueError()
    return url


def secret_path(value):
    if not isinstance(value, str) or not re.fullmatch(r'/run/secrets/[A-Za-z0-9_-]+', value):
        raise ValueError()
    if PurePosixPath(value).parent != PurePosixPath('/run/secrets'):
        raise ValueError()
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def load(env):
    mode = env.get('BASEWORK_OIDC_MODE', 'disabled')
    if mode == 'disabled':
        return None
    if mode == 'isolated':
        if (env.get('BASEWORK_PG_REHEARSAL') != PROJECT
                or json.loads(Path('/run/basework-pg/manifest.json').read_text())
                != {'project': PROJECT, 'synthetic_only': True}):
            raise ValueError()
        provider = ISOLATED
    elif mode == 'provider':
        if env.get('BASEWORK_OIDC_CONFIG_FILE') != CONFIG_FILE:
            raise ValueError()
        raw = Path(CONFIG_FILE).read_bytes()
        if len(raw) > 8192:
            raise ValueError()
        data = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(data, dict) or set(data) != set(Provider.__dataclass_fields__):
            raise ValueError()
        provider = Provider(**data)
        issuer = https_url(provider.issuer)
        if provider.issuer.endswith('/'):
            raise ValueError()
        endpoints = [provider.authorization_endpoint, provider.token_endpoint, provider.jwks_uri, provider.discovery]
        for address in endpoints:
            endpoint = https_url(address)
            if endpoint.netloc != issuer.netloc or not endpoint.path.startswith(issuer.path + '/'):
                raise ValueError()
        if len(set(endpoints)) != 4 or https_url(provider.redirect_uri).path != CALLBACK_PATH:
            raise ValueError()
        if not isinstance(provider.client_id, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{1,100}', provider.client_id):
            raise ValueError()
    else:
        raise ValueError()
    secret = Path(secret_path(provider.secret_file)).read_text().strip()
    if not 32 <= len(secret) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in secret):
        raise ValueError()
    if provider.ca_file is not None:
        ssl.create_default_context(cafile=secret_path(provider.ca_file))
    return provider


def configure(namespace):
    namespace['BASEWORK_OIDC_ENABLED'] = False
    namespace['BASEWORK_OIDC_CONFIG'] = None
    try:
        provider = load(os.environ)
    except (OSError, ValueError, TypeError):
        raise ImproperlyConfigured('Недопустимая конфигурация OIDC или недоступны файлы доверия') from None
    if provider is None:
        return
    namespace['BASEWORK_OIDC_CONFIG'] = provider
    namespace['BASEWORK_OIDC_ENABLED'] = True
    # OIDC никогда не включает небезопасные cookie даже в ENVIRONMENT=local.
    namespace['SESSION_COOKIE_SECURE'] = True
    namespace['CSRF_COOKIE_SECURE'] = True


def current():
    provider = getattr(settings, 'BASEWORK_OIDC_CONFIG', None)
    if not getattr(settings, 'BASEWORK_OIDC_ENABLED', False) or not isinstance(provider, Provider):
        raise PermissionDenied()
    return provider


def fingerprint():
    # Все закреплённые параметры участвуют в привязке незавершённой попытки.
    provider = current()
    parts = [json.dumps(asdict(provider), sort_keys=True).encode(), Path(provider.secret_file).read_bytes(),
             Path(provider.ca_file).read_bytes() if provider.ca_file else b'system-ca']
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, 'big'))
        digest.update(part)
    return digest.hexdigest()
