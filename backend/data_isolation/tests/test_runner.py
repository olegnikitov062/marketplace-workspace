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
