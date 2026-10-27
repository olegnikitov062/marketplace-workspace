from django.test import TestCase, override_settings
from tools.security_role_scenario import seed, run, operator_action


class SecurityRoleScenarioTests(TestCase):
    @override_settings(SECURITY_RECOVERY_CODE_COUNT=2)
    def test_http_scenario_prepared_for_restricted_login(self):
        run(seed(), operator_action)
