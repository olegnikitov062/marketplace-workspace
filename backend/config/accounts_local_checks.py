"""Offline tests only; SQLite is not a beta/PostgreSQL substitute."""
from .ownership_local_checks import *  # noqa: F403
from accounts.policy import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.sessions", "rest_framework", "accounts"]  # noqa: F405
ROOT_URLCONF = "config.urls"
ALLOWED_HOSTS = ["testserver", "localhost"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SESSION_COOKIE_NAME = "mw_offline_session"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [], "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
