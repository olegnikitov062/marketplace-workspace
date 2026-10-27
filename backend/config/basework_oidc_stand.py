"""Только локальная HTTPS-приёмка синтетического API, не рабочие настройки."""
from .settings import *  # noqa: F403
from tools.basework_postgresql_rehearsal import marker
from django.core.exceptions import ImproperlyConfigured

marker()
if not BASEWORK_OIDC_ENABLED:  # noqa: F405
    raise ImproperlyConfigured('Требуется изолированный OIDC-стенд')
SECURITY_DOWNLOAD_PROBE = True
