"""Local SQLite checks only; PostgreSQL evidence is recorded separately."""
from .security_local_checks import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'access_control']  # noqa: F405
ACCESS_CONTROL_ENABLED = True
