"""Только изолированные тесты. Запуск рабочего сервера запрещён родительским guard."""
from .isolation_local_checks import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'basework']  # noqa: F405
BASEWORK_ENABLED = True
