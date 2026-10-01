import os
from django.core.exceptions import ImproperlyConfigured
from .guard import validate, secret, ConfigurationError
try:
    EFFECTIVE = validate(os.environ)
    SECRET_KEY = secret(os.environ["DJANGO_SECRET_KEY_FILE"])
    DB_PASSWORD = secret(os.environ["DB_PASSWORD_FILE"])
except (ConfigurationError, OSError) as exc:
    raise ImproperlyConfigured(str(exc)) from None
DEBUG = False
ENVIRONMENT = EFFECTIVE["environment"]
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "web", "testserver"] if EFFECTIVE["mode"] == "test" else ["127.0.0.1", "localhost", "web"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "rest_framework", "ownership", "accounts"]
AUTH_USER_MODEL = "ownership.User"
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware"]
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "HOST": EFFECTIVE["DB_HOST"], "PORT": EFFECTIVE["DB_PORT"], "NAME": EFFECTIVE["DB_NAME"], "USER": EFFECTIVE["DB_USER"], "PASSWORD": DB_PASSWORD, "OPTIONS": {"connect_timeout": 5, "options": "-c statement_timeout=5000 -c lock_timeout=2000"}, "TEST": {"NAME": "test_" + EFFECTIVE["DB_NAME"]}}}
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": [], "DEFAULT_PERMISSION_CLASSES": [], "UNAUTHENTICATED_USER": None, "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SESSION_COOKIE_NAME = "mw_" + ENVIRONMENT + "_session"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_SECURE = ENVIRONMENT != "local"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = ENVIRONMENT != "local"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = []
SECURE_CONTENT_TYPE_NOSNIFF = True
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
from accounts.policy import *  # noqa: F403 -- explicit shared synthetic E2-05 policy
from account_security.configuration import configure
configure(globals())
# MFA is mandatory for owners; no public registration, RBAC or source adapters.
