"""Password-encrypted offline key envelope; no transfer or external storage client."""
import base64
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from django.views.decorators.debug import sensitive_variables


@sensitive_variables()
def wrapping_key(password, salt):
    if len(password) < 16:
        raise ValueError("Backup passphrase is too short")
    raw = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(password.encode())
    return base64.urlsafe_b64encode(raw)


@sensitive_variables()
def wrap(key, password):
    Fernet(key)  # Reject malformed TOTP keys before writing an envelope.
    salt = os.urandom(16)
    token = Fernet(wrapping_key(password, salt)).encrypt(key)
    return json.dumps({"format": "mw-mfa-key-v1", "salt": base64.b64encode(salt).decode(),
                       "ciphertext": token.decode()}).encode()


@sensitive_variables()
def unwrap(envelope, password):
    try:
        if len(envelope) > 4096:
            raise ValueError()
        data = json.loads(envelope)
        if data["format"] != "mw-mfa-key-v1":
            raise ValueError()
        salt = base64.b64decode(data["salt"], validate=True)
        if len(salt) != 16:
            raise ValueError()
        key = Fernet(wrapping_key(password, salt)).decrypt(data["ciphertext"].encode())
        Fernet(key)
        return key
    except (KeyError, ValueError, TypeError, InvalidToken, UnicodeError):
        raise ValueError("Key backup could not be restored") from None
