"""Offline HTTP-scenario/guard checks; never called SQL privilege evidence."""
from unittest import mock

from django.test import TestCase, SimpleTestCase

from tools.account_role_scenario import seed, run
from tools.verify_account_web_role import require_test_environment
from tools.account_web_grants import ContractError, grant_statements, revoke_statements


class AccountRoleScenarioTests(TestCase):
    def test_full_http_scenario_without_sql_role_claim(self):
        fixture = seed()
        run(fixture)


class AccountRoleGuardTests(SimpleTestCase):
    def test_guard_refuses_main_database_wrong_role_or_host(self):
        allowed = {"environment": "beta", "mode": "test", "DB_HOST": "postgres-test", "DB_PORT": "5432", "DB_NAME": "mw_beta_test", "DB_USER": "mw_beta_test_runner"}
        require_test_environment(allowed)
        for field, value in [("environment", "production"), ("mode", "web"), ("DB_HOST", "postgres"), ("DB_NAME", "mw_beta"), ("DB_USER", "mw_beta_web")]:
            with self.assertRaises(RuntimeError):
                require_test_environment({**allowed, field: value})

    def test_sql_role_cannot_be_arbitrary_or_injected(self):
        for role in ["mw_production_web", "postgres", "mw_beta_web; DROP TABLE test"]:
            with self.assertRaises(ContractError):
                grant_statements(role)
            with self.assertRaises(ContractError):
                revoke_statements(role)

    def test_default_plan_does_not_initialize_django_or_connect(self):
        from tools.manage_account_web_grants import main
        with mock.patch("sys.argv", ["manage_account_web_grants"]), mock.patch("django.setup") as setup, mock.patch("builtins.print"):
            main()
        setup.assert_not_called()
