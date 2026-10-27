from django.test import TestCase
from unittest import skipUnless
from django.db import connection
from django.core import mail
from django.core.mail import send_mail

class RuntimeTests(TestCase):
    @skipUnless(connection.vendor == "postgresql", "Requires guarded beta PostgreSQL runtime")
    def test_health_and_migrations(self):
        self.assertEqual(self.client.get("/api/v1/health/live").json(), {"status":"ok"})
        self.assertEqual(self.client.get("/api/v1/health/ready").json(), {"status":"ready"})
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database, role = cursor.fetchone()
        self.assertTrue(database.startswith("test_mw_"))
        self.assertTrue(role.endswith("_test_runner"))
    def test_messages_never_leave_memory(self):
        send_mail("synthetic", "synthetic", "sender@example.invalid", ["recipient@example.invalid"])
        self.assertEqual(len(mail.outbox), 1)
    def test_no_business_or_registration_routes(self):
        for path in ["/auth/register", "/api/v1/orders", "/admin/"]:
            self.assertEqual(self.client.get(path).status_code,404)
