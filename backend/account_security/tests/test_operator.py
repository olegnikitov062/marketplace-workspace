import json
import secrets
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase
from django.core.exceptions import PermissionDenied

from account_security.key_backup import wrap, unwrap
from account_security.operator import verify_owner_proof, write_private_new, require_operator_process


class OperatorProofTests(SimpleTestCase):
    def test_proof_bound_to_exact_owner_and_no_embedded_fallback(self):
        proof = secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"synthetic-verifier.json"
            path.write_text(json.dumps({"user_id": "synthetic-owner", "verifier": make_password(proof)}), encoding="utf-8")
            self.assertTrue(verify_owner_proof("synthetic-owner", proof, path))
            self.assertFalse(verify_owner_proof("synthetic-other", proof, path))
            self.assertFalse(verify_owner_proof("synthetic-owner", secrets.token_urlsafe(32), path))
            self.assertFalse(verify_owner_proof("synthetic-owner", proof, Path(folder)/"missing"))

    def test_web_offline_process_cannot_issue_operator_command(self):
        with self.assertRaises(PermissionDenied):
            require_operator_process()

    def test_runtime_configuration_rejects_missing_dedicated_key(self):
        from account_security.configuration import configure
        from django.core.exceptions import ImproperlyConfigured
        from unittest.mock import patch
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                configure({"INSTALLED_APPS": [], "MIDDLEWARE": [], "SESSION_COOKIE_NAME": "synthetic"})

    def test_encrypted_key_backup_restore_and_wrong_passphrase(self):
        key = Fernet.generate_key()
        password = secrets.token_urlsafe(32)
        envelope = wrap(key, password)
        self.assertFalse(key in envelope)
        self.assertTrue(unwrap(envelope, password) == key)
        with self.assertRaises(ValueError):
            unwrap(envelope, secrets.token_urlsafe(32))

    def test_secret_output_never_overwrites_existing_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"synthetic-output"
            value = secrets.token_bytes(32)
            write_private_new(path, value)
            with self.assertRaises(FileExistsError):
                write_private_new(path, b"replacement")
            self.assertTrue(path.read_bytes() == value)

    def test_maintenance_refuses_auth_and_business_paths_without_database(self):
        from account_security.maintenance import application
        for path in ["/auth/login", "/auth/mfa/login/", "/auth/session", "/api/v1/health/ready", "/"]:
            observed = []
            body = application({"PATH_INFO": path}, lambda status, headers: observed.append(status))
            self.assertEqual(observed, ["503 Service Unavailable"])
            self.assertEqual(body, [b'{"status":"maintenance"}'])
