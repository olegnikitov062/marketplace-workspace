import json
import subprocess
import sys
from pathlib import Path
from django.test import SimpleTestCase


class FinancialPreparationTests(SimpleTestCase):
    def test_default_plan_is_inert_and_secret_mounts_are_new(self):
        root = Path(__file__).resolve().parents[3]
        script = root/'beta/deploy/prepare_financial_rehearsal.py'
        result = subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0)
        plan = json.loads(result.stdout)
        compose = json.loads((root/'beta/deploy/compose.financial-rehearsal.json').read_text())
        self.assertEqual(plan['project'],compose['name'])
        self.assertEqual(plan['default_action'],'print plan')
        self.assertIn('e209-',plan['project'])
        self.assertTrue(compose['networks']['private']['internal'])
        for service in compose['services'].values():
            self.assertNotIn('ports',service)
            self.assertEqual(service['pull_policy'],'never')
            self.assertEqual(service['restart'],'no')
            self.assertEqual(service['logging']['driver'],'none')
        for source in compose['secrets'].values():
            self.assertTrue(source['file'].startswith(plan['root']+'/secrets/'))
        self.assertEqual(set(compose['services']['web']['secrets']),
                         {'db_web_password','django_secret_key','mfa_encryption_key','isolation_signing_key'})
        self.assertIn('max_connections=20',compose['services']['postgres']['command'])
        self.assertIn('statement_timeout=15000',compose['services']['postgres']['command'])

    def test_financial_function_migration_requires_both_schema_and_rls(self):
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(None)
        parents = {node.key for node in loader.graph.node_map[('data_isolation','0002_financial_operations')].parents}
        self.assertEqual(parents,{('access_control','0003_financial_schema'),('data_isolation','0001_statement_and_row_policies')})

    def test_server_evidence_redacts_unknown_lines_and_requires_current_financial_tests(self):
        from tools.financial_test_runner import safe_line, LABELS
        for line in ('Cookie: synthetic-secret', 'SELECT cost FROM synthetic;',
                     'FAIL: test_x (invalid message with payload)', 'Traceback: synthetic-secret'):
            self.assertIsNone(safe_line(line))
        self.assertEqual(safe_line('OK (skipped=1)'),{'event':'unittest_ok','skipped':1})
        self.assertIn('access_control.tests.test_financial',LABELS)
        self.assertIn('access_control.tests.test_financial_migrations',LABELS)
        self.assertIn('access_control.tests.test_financial_transactions',LABELS)
