"""Публикация только изолированного beta-стенда; не production."""
from .settings import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured
from basework.publication import load
from tools.basework_postgresql_rehearsal import marker

try:
    marker()
    if EFFECTIVE['environment'] != 'beta' or EFFECTIVE['mode'] != 'web':  # noqa: F405
        raise ValueError()
    BASEWORK_PUBLIC = load(os.environ)  # noqa: F405
    if BASEWORK_OIDC_ENABLED and BASEWORK_OIDC_CONFIG.redirect_uri != (  # noqa: F405
            BASEWORK_PUBLIC['origin'] + '/auth/basework/oidc/callback'):
        raise ValueError()
except (ValueError, AssertionError, OSError, TypeError, KeyError):
    raise ImproperlyConfigured('Неверный профиль публикации BaseWork') from None

SECURITY_DOWNLOAD_PROBE = False
ALLOWED_HOSTS = [BASEWORK_PUBLIC['host']]
CSRF_TRUSTED_ORIGINS = [BASEWORK_PUBLIC['origin']]
USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
MIDDLEWARE = ['basework.publication.TrustedGateway', *MIDDLEWARE]  # noqa: F405
