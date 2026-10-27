"""Full suite on a fresh guarded beta test DB; skips are a failure.

No keepdb: refuses an existing Django test DB instead of deleting/reusing it.
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if os.environ["DJANGO_SETTINGS_MODULE"] != "config.settings":
    raise SystemExit("PostgreSQL acceptance requires guarded runtime settings")
django.setup()

from django.conf import settings
from django.db import connection
from django.test.runner import DiscoverRunner


class StrictRunner(DiscoverRunner):
    def run_suite(self, suite, **kwargs):
        result = super().run_suite(suite, **kwargs)
        if result.skipped:
            result.failures.append(("PostgreSQL acceptance", "Skipped tests are not accepted"))
        return result


def main():
    if settings.EFFECTIVE != {
        "environment": "beta", "mode": "test", "DB_HOST": "postgres-test",
        "DB_PORT": "5432", "DB_NAME": "mw_beta_test", "DB_USER": "mw_beta_test_runner",
    } or connection.vendor != "postgresql":
        raise SystemExit("Only isolated beta test PostgreSQL is allowed")
    name = "mw_beta_test_e2_06_suite"
    connection.settings_dict["TEST"]["NAME"] = name
    with connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = %s)", [name])
        if cursor.fetchone()[0]:
            raise SystemExit("Test DB exists; preserve it and investigate, do not auto-delete")
    raise SystemExit(StrictRunner(verbosity=1, interactive=False).run_tests(["account_security.tests", "tests.test_ownership", "tests.test_ownership_migrations", "tests.test_guard"]))


if __name__ == "__main__":
    main()
