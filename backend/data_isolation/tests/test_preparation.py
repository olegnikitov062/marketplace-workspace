import ast
import json
import subprocess
import sys
from pathlib import Path
from django.test import SimpleTestCase
from data_isolation.sql import TABLES, TRUSTED_TRIGGERS


class IsolationPreparationTests(SimpleTestCase):
    def test_table_inventory_and_guard_boundary(self):
        self.assertEqual(len(TABLES),27)
        self.assertEqual(len(set(TABLES)),27)
        self.assertNotIn('accounts_web_lock_only',TRUSTED_TRIGGERS)
        self.assertNotIn('access_web_subject',TRUSTED_TRIGGERS)

    def test_new_rehearsal_is_inert_and_has_only_new_secret_mounts(self):
        root=Path(__file__).resolve().parents[3]
        compose=json.loads((root/'beta/deploy/compose.isolation-rehearsal.json').read_text())
        project='marketplace-e208-20261006-01a1105a'
        self.assertEqual(compose['name'],project)
        for service in compose['services'].values():
            self.assertNotIn('ports',service)
            self.assertEqual(service['pull_policy'],'never')
        self.assertEqual(set(compose['services']['web']['secrets']),
            {'db_web_password','django_secret_key','mfa_encryption_key','isolation_signing_key'})
        for source in compose['secrets'].values():
            self.assertIn('/rehearsals/e2-08-20261006-01a1105a/secrets/',source['file'])
        script=root/'beta/deploy/prepare_isolation_rehearsal.py'
        ast.parse(script.read_text())
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)['project'],project)
