import ast
import json
import subprocess
import sys
from pathlib import Path
from django.test import SimpleTestCase
from data_isolation.sql import TABLES, TRUSTED_TRIGGERS


class IsolationPreparationTests(SimpleTestCase):
    def test_all_rls_tables_exist_before_isolation_migration(self):
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(None)
        target = ('data_isolation', '0001_statement_and_row_policies')
        parents = [node.key for node in loader.graph.node_map[target].parents]
        state = loader.project_state(parents)
        tables = {model._meta.db_table for model in state.apps.get_models()}
        self.assertEqual(set(TABLES) - tables, set())

    def test_table_inventory_and_guard_boundary(self):
        self.assertEqual(len(TABLES),27)
        self.assertEqual(len(set(TABLES)),27)
        self.assertNotIn('accounts_web_lock_only',TRUSTED_TRIGGERS)
        self.assertNotIn('access_web_subject',TRUSTED_TRIGGERS)

    def test_new_rehearsal_is_inert_and_has_only_new_secret_mounts(self):
        root=Path(__file__).resolve().parents[3]
        compose=json.loads((root/'beta/deploy/compose.isolation-rehearsal.json').read_text())
        project='marketplace-e208-20261007-01a1105a-r3'
        self.assertEqual(compose['name'],project)
        for service in compose['services'].values():
            self.assertNotIn('ports',service)
            self.assertEqual(service['pull_policy'],'never')
        self.assertEqual(set(compose['services']['web']['secrets']),
            {'db_web_password','django_secret_key','mfa_encryption_key','isolation_signing_key'})
        for source in compose['secrets'].values():
            self.assertIn('/rehearsals/e2-08-20261007-01a1105a-r3/secrets/',source['file'])
        script=root/'beta/deploy/prepare_isolation_rehearsal.py'
        ast.parse(script.read_text())
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)['project'],project)
