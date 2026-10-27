import unittest
from config.guard import validate, ConfigurationError

class GuardTests(unittest.TestCase):
    def base(self):
        return {"ENVIRONMENT": "beta", "PROCESS_MODE": "web", "DB_HOST": "postgres", "DB_PORT": "5432", "DB_NAME": "mw_beta", "DB_USER": "mw_beta_web", "DB_PASSWORD_FILE": "/run/secrets/db_web_password", "DJANGO_SECRET_KEY_FILE": "/run/secrets/django_secret_key"}
    def test_valid_process_roles(self):
        for mode, host, name, user, password in [("web", "postgres", "mw_beta", "mw_beta_web", "db_web_password"), ("migrate", "postgres", "mw_beta", "mw_beta_migrator", "db_migrator_password"), ("test", "postgres-test", "mw_beta_test", "mw_beta_test_runner", "db_test_runner_password")]:
            values = self.base() | {"PROCESS_MODE": mode, "DB_HOST": host, "DB_NAME": name, "DB_USER": user, "DB_PASSWORD_FILE": "/run/secrets/"+password}
            self.assertEqual(validate(values)["mode"], mode)
    def test_rejects_unsafe_effective_configuration(self):
        cases = {"ENVIRONMENT": ["", "production", "unknown"], "DB_HOST": ["wb_postgres", "127.0.0.1", "example.invalid"], "DB_NAME": ["mw_production", "postgres"], "DB_USER": ["mw_beta_bootstrap", "mw_production_web"], "PROCESS_MODE": ["worker", ""], "DB_PORT": ["5434"], "DB_PASSWORD_FILE": ["/run/secrets/db_bootstrap_password", "../../secret", "/run/secrets/../secret"]}
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key,value=value), self.assertRaises(ConfigurationError):
                    validate(self.base() | {key:value})
        for key in ["EXTERNAL_READS_ENABLED", "EXTERNAL_WRITES_ENABLED", "REAL_MESSAGES_ENABLED", "SCHEDULES_ENABLED", "DATABASE_URL", "SOURCE_DATABASE_URL", "WB_TOKEN", "SMTP_HOST", "EMAIL_HOST", "SOURCE_URL"]:
            with self.subTest(key=key), self.assertRaises(ConfigurationError):
                validate(self.base() | {key:"enabled"})
