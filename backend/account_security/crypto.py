"""Authenticated encryption; the key is never derived from Django SECRET_KEY."""
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.views.decorators.debug import sensitive_variables


@sensitive_variables()
def cipher():
    try:
        key = getattr(settings, "MFA_TEST_KEY", None)
        if key is None:
            key = Path(settings.MFA_ENCRYPTION_KEY_FILE).read_bytes().strip()
        return Fernet(key)
    except (OSError, ValueError, TypeError, AttributeError):
        raise ImproperlyConfigured("MFA encryption key unavailable") from None


@sensitive_variables()
def seal(value):
    return cipher().encrypt(value.encode()).decode()


@sensitive_variables()
def unseal(value):
    try:
        return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, UnicodeError, ValueError):
        raise ImproperlyConfigured("MFA encrypted state unavailable") from None


class EncryptedTextField(models.TextField):
    def value_to_string(self, obj):
        raise ImproperlyConfigured("Encrypted credentials require PostgreSQL pg_dump backup, not Django fixtures")

    def get_prep_value(self, value):
        return seal(str(value)) if value is not None else None

    def from_db_value(self, value, expression, connection):
        return unseal(value) if value is not None else None
