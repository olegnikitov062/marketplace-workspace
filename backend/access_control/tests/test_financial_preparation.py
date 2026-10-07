import json
import subprocess
import sys
from pathlib import Path
from django.test import SimpleTestCase


class FinancialPreparationTests(SimpleTestCase):
    def test_restore_evidence_redacts_exception_and_retains_failed_stage(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from tools.financial_restore_evidence import RestoreEvidence
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()) as output:
            path = Path(directory) / 'restore-events.jsonl'
            with self.assertRaisesRegex(RuntimeError, 'synthetic-secret'):
                with RestoreEvidence(path) as evidence:
                    evidence.checkpoint('metadata', 2)
                    raise RuntimeError('synthetic-secret SELECT cost; Cookie: hidden')
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(events[-1], {'event':'restore_failed','stage':'metadata','index':2})
            self.assertEqual(len(events), 2)
            self.assertNotIn('synthetic-secret', path.read_text() + output.getvalue())
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                with RestoreEvidence(path):
                    self.fail('Existing evidence was overwritten')
            self.assertEqual(path.read_bytes(), before)

    def test_restore_evidence_rejects_untrusted_stage_or_index(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from tools.financial_restore_evidence import RestoreEvidence
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            path = Path(directory) / 'restore-events.jsonl'
            with RestoreEvidence(path) as evidence:
                for stage, index in (('Cookie: hidden', 0), ('rows', 'hidden'),
                                     ('rows', -1), ('rows', 1001), ('rows', True)):
                    with self.assertRaises(ValueError):
                        evidence.checkpoint(stage, index)
                evidence.checkpoint('quarantine_verify')
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(events[-1]['event'], 'restore_passed')
            self.assertNotIn('hidden', path.read_text())

    def test_limits_accept_stricter_django_session_options(self):
        from tools.financial_runtime_limits import validate
        for values in ((20,5000,2000,20000,1),(20,15000,5000,20000,8)):
            self.assertEqual(validate(values)['statement_timeout_ms'],values[1])

    def test_limits_reject_unlimited_and_excessive_settings(self):
        from tools.financial_runtime_limits import validate
        for values in ((20,0,2000,20000,1),(20,15001,2000,20000,1),
                       (20,5000,0,20000,1),(20,5000,5001,20000,1),
                       (20,5000,2000,0,1),(20,5000,2000,20001,1),
                       (21,5000,2000,20000,1),(20,5000,2000,20000,9)):
            with self.assertRaises(ValueError):
                validate(values)

    def test_limits_require_complete_numeric_context(self):
        from tools.financial_runtime_limits import validate
        for values in ((),(20,5000,2000,20000),(20,'5000',2000,20000,1),(20,None,2000,20000,1)):
            with self.assertRaises(ValueError):
                validate(values)

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
