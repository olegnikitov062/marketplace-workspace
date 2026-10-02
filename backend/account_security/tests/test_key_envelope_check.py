import contextlib
import io
import secrets
import tempfile
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import SimpleTestCase

from account_security.key_backup import wrap
from tools.check_mfa_key_envelope import main, verify


class OwnerEnvelopeCheckTests(SimpleTestCase):
    def test_correct_wrong_and_tampered_copy_without_plaintext_output(self):
        password = secrets.token_urlsafe(32)
        key = Fernet.generate_key()
        envelope = wrap(key, password)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic-envelope.json"
            source.write_bytes(envelope)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                self.assertIsNone(verify(source, password))
                with self.assertRaises(ValueError):
                    verify(source, secrets.token_urlsafe(32))
                self.assertEqual(source.read_bytes(), envelope)
                source.write_bytes(envelope[:-1] + b"!")
                with self.assertRaises(ValueError):
                    verify(source, password)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(list(Path(folder).iterdir()), [source])
            self.assertNotIn(key, source.read_bytes())

    def test_noninteractive_terminal_refused_before_password_prompt(self):
        with patch("sys.argv", ["check", "--input", "unused-synthetic-envelope.json"]), \
                patch("sys.stdin.isatty", return_value=False), \
                patch("tools.check_mfa_key_envelope.getpass.getpass") as prompt:
            with self.assertRaises(SystemExit):
                main()
        prompt.assert_not_called()

    def test_getpass_echo_fallback_refused(self):
        import getpass
        import warnings

        def unsafe_prompt(_):
            warnings.warn("synthetic echo fallback", getpass.GetPassWarning)
            return "must-not-be-used"

        with patch("sys.argv", ["check", "--input", "unused-synthetic-envelope.json"]), \
                patch("sys.stdin.isatty", return_value=True), \
                patch("sys.stdout.isatty", return_value=True), \
                patch("tools.check_mfa_key_envelope.getpass.getpass", side_effect=unsafe_prompt), \
                patch("tools.check_mfa_key_envelope.verify") as check:
            with self.assertRaises(SystemExit):
                main()
        check.assert_not_called()
