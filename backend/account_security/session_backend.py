from django.contrib.sessions.backends.db import SessionStore as DjangoSessionStore
from django.core.exceptions import ImproperlyConfigured

from .crypto import seal, unseal


class SessionStore(DjangoSessionStore):
    """Django DB sessions with encrypted payload, including library wizard data."""

    def encode(self, session_dict):
        return "mfa1:" + seal(super().encode(session_dict))

    def decode(self, session_data):
        if not session_data.startswith("mfa1:"):
            return {}  # Pre-E2-06 sessions cannot bypass enrollment/registry.
        try:
            return super().decode(unseal(session_data[5:]))
        except ImproperlyConfigured:
            return {}  # Fail closed; never fall back to plaintext sessions.
