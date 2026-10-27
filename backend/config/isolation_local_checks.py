"""Offline behavior only. SQLite cannot establish PostgreSQL RLS correctness."""
import secrets
from .access_local_checks import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'data_isolation']  # noqa: F405
MIDDLEWARE = ['data_isolation.middleware.IsolationBoundary', *MIDDLEWARE]  # noqa: F405
MIDDLEWARE.append('data_isolation.middleware.ActorContext')
ISOLATION_ENABLED = True
ISOLATION_OFFLINE = True
ISOLATION_TEST_KEY = secrets.token_bytes(32)
