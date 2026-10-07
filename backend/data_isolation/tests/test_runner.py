from django.test import SimpleTestCase
from tools.isolation_test_runner import safe_line


class EvidenceTests(SimpleTestCase):
    def test_only_complete_summary_records_are_admitted(self):
        self.assertEqual(safe_line('Ran 8 tests in 1.25s'), {'event': 'count', 'tests': 8, 'seconds': 1.25})
        self.assertEqual(safe_line('OK (skipped=2)'), {'event': 'unittest_ok', 'skipped': 2})
        self.assertEqual(safe_line('FAILED (failures=1, errors=2)'), {'event': 'unittest_failed'})

    def test_raw_errors_parameters_and_test_values_are_dropped(self):
        for line in ('ValueError: synthetic-secret', 'SELECT synthetic-secret',
                     'Ran 8 tests in 1.2s synthetic-secret', 'OK synthetic-secret',
                     'FAIL: test_x (suite.C.test_x) synthetic-secret',
                     "FAIL: test_x (suite.C.test_x) (token='synthetic-secret')",
                     '  File "/workspace/auth.py", line 1, in login'):
            self.assertIsNone(safe_line(line))

    def test_failure_preserves_only_static_test_identity(self):
        self.assertEqual(safe_line('ERROR: test_x (suite.C.test_x)'),
                         {'event': 'test_failure', 'kind': 'ERROR', 'test': 'suite.C.test_x'})

    def test_only_static_test_locations_are_recorded(self):
        self.assertEqual(safe_line('  File "/workspace/access_control/tests/test_http.py", line 77, in test_export'),
                         {'event': 'test_location', 'file': 'access_control/tests/test_http.py', 'line': 77, 'function': 'test_export'})
        self.assertIsNone(safe_line('  File "/workspace/private/synthetic-secret.py", line 77, in test_export'))
        self.assertIsNone(safe_line('  File "/workspace/access_control/tests/test_http.py", line 77, in test_export synthetic-secret'))

    def test_test_key_provisioning_refuses_main_database_before_key_access(self):
        from unittest.mock import Mock, patch
        from tools.isolation_django_runner import prepare_test_signing_key
        cursor = Mock()
        cursor.fetchone.return_value = ('mw_beta', 'mw_beta_migrator', 'mw_beta_migrator', 'synthetic')
        fake = Mock(vendor='postgresql')
        fake.cursor.return_value.__enter__ = Mock(return_value=cursor)
        fake.cursor.return_value.__exit__ = Mock(return_value=False)
        with patch('tools.isolation_django_runner.marker'), patch('tools.isolation_django_runner.connection', fake), patch('tools.isolation_django_runner.transaction.atomic') as atomic, patch('tools.isolation_django_runner.signing_key') as key:
            atomic.return_value.__enter__.return_value = None
            atomic.return_value.__exit__.return_value = False
            with self.assertRaises(RuntimeError):
                prepare_test_signing_key()
            key.assert_not_called()
            self.assertEqual(cursor.execute.call_count, 1)

    def test_durable_evidence_excludes_raw_child_output(self):
        import contextlib
        import io
        import tempfile
        from unittest.mock import Mock, patch
        from tools.isolation_test_runner import run
        child = Mock(stdout=io.StringIO('ValueError: synthetic-secret\nRan 2 tests in 1.2s\nOK\n'))
        child.wait.return_value = 0
        child.poll.return_value = 0
        with tempfile.TemporaryFile(mode='w+') as evidence, contextlib.redirect_stdout(io.StringIO()) as output:
            with patch('tools.isolation_test_runner.subprocess.Popen', return_value=child):
                self.assertEqual(run(evidence), 0)
            evidence.seek(0)
            saved = evidence.read()
        self.assertNotIn('synthetic-secret', saved + output.getvalue())
        self.assertIn('suite_finished', saved)
        self.assertIn('"passed_without_skips": true', saved)

    def test_zero_exit_without_complete_summary_is_not_pass(self):
        import contextlib
        import io
        import tempfile
        from unittest.mock import Mock, patch
        from tools.isolation_test_runner import run
        for text in ('', 'Ran 0 tests in 0.0s\nOK\n', 'Ran 2 tests in 1.2s\nOK (skipped=1)\n'):
            child = Mock(stdout=io.StringIO(text))
            child.wait.return_value = 0
            child.poll.return_value = 0
            with tempfile.TemporaryFile(mode='w+') as evidence, contextlib.redirect_stdout(io.StringIO()):
                with patch('tools.isolation_test_runner.subprocess.Popen', return_value=child):
                    self.assertEqual(run(evidence), 1)
