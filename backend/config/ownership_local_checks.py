"""Explicit SQLite-only model checks. Never imports runtime config or credentials.

This module cannot run a web server and does not prove PostgreSQL isolation.
"""
import sys

if len(sys.argv) < 2 or sys.argv[1] not in {"test", "check", "makemigrations", "sqlmigrate"}:
    raise RuntimeError("Only offline ownership checks are allowed with these settings")

SECRET_KEY = "synthetic-offline-checks-no-runtime-credentials"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "ownership"]
AUTH_USER_MODEL = "ownership.User"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
