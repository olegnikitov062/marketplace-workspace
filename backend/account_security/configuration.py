"""Installed by runtime settings unconditionally; legacy offline checks stay separate."""
import os
from pathlib import Path

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from . import policy


def configure(namespace, offline=False):
    namespace.update({key: getattr(policy, key) for key in dir(policy) if key.isupper()})
    namespace["ACCOUNT_SECURITY_ENABLED"] = True
    namespace["INSTALLED_APPS"] += ["django_otp", "django_otp.plugins.otp_totp",
        "django_otp.plugins.otp_static", "formtools", "two_factor", "account_security"]
    namespace["MIDDLEWARE"] += ["account_security.middleware.SessionGate"]
    namespace["TEMPLATES"] = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True, "OPTIONS": {"context_processors": [
            "django.template.context_processors.request", "django.template.context_processors.csrf"]}}]
    namespace["SECURITY_TRUST_COOKIE"] = namespace["SESSION_COOKIE_NAME"] + "_trusted"
    if offline:
        namespace["MFA_TEST_KEY"] = Fernet.generate_key()
    else:
        key_path = os.environ.get("MFA_ENCRYPTION_KEY_FILE")
        if key_path != "/run/secrets/mfa_encryption_key":
            raise ImproperlyConfigured("MFA encryption key must use its dedicated secret mount")
        try:
            Fernet(Path(key_path).read_bytes().strip())
        except (ValueError, OSError, TypeError):
            raise ImproperlyConfigured("MFA encryption key unavailable") from None
        namespace["MFA_ENCRYPTION_KEY_FILE"] = key_path
