"""Explicit local browser regression; SQLite is not PostgreSQL/MFA acceptance.

Run with manage.py test tools.check_security_browser_referrer and the guarded
security_local_checks settings. Existing Playwright/Chromium paths are required;
no dependency installation, remote service, trace or credential file is used.
"""
import json
import os
import secrets
import subprocess
from pathlib import Path

from django.conf import settings
from django.test import LiveServerTestCase, override_settings

from account_security.models import AccountSession, Authenticator
from ownership.models import Membership, Organization, User


@override_settings(STATIC_URL="/__offline_static__/", MEDIA_URL="/__offline_media__/")
class BrowserReferrerCheck(LiveServerTestCase):
    def test_owner_form_and_csrf_in_real_chromium(self):
        self.assertEqual(os.environ.get("DJANGO_SETTINGS_MODULE"), "config.security_local_checks")
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertFalse(os.environ.get("DEBUG") or os.environ.get("PWDEBUG"))
        self.assertTrue(all(os.environ.get(name) for name in ("E206_PLAYWRIGHT_MODULE", "E206_CHROMIUM")))
        password = secrets.token_urlsafe(32)
        owner = User.objects.create_user("synthetic-browser-owner", password)
        organization = Organization.objects.create(name="synthetic-browser-referrer")
        Membership.objects.create(user=owner, organization=organization, role="owner")
        script = Path(__file__).resolve().parents[2] / "scripts/e2_06_referrer_browser.cjs"
        try:
            result = subprocess.run(["node", str(script)], input=json.dumps({
                "base": self.live_server_url, "username": owner.username, "password": password,
            }).encode(), capture_output=True, timeout=150)
        except (OSError, subprocess.TimeoutExpired):
            self.fail("Browser unavailable or timed out; private output suppressed")
        # Never attach stderr, submitted credentials or browser exception details.
        self.assertEqual(result.returncode, 0, "Browser form/CSRF regression failed; output suppressed")
        self.assertEqual(result.stdout.strip(), b"PASS real-browser-form-csrf-and-referrer")
        self.assertEqual(Authenticator.objects.count(), 0)
        self.assertEqual(AccountSession.objects.filter(level="full").count(), 0)
        self.assertEqual(AccountSession.objects.filter(level="enroll", revoked_at__isnull=False).count(), 1)
