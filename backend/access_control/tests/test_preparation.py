import ast
import json
from pathlib import Path

from django.test import SimpleTestCase


class PreparationTests(SimpleTestCase):
    def test_isolated_compose_has_no_old_mounts_or_ports(self):
        root = Path(__file__).resolve().parents[3]
        data = json.loads((root/'beta/deploy/compose.access-rehearsal.json').read_text())
        self.assertEqual(data['name'], 'marketplace-e207-20261005-01a10b2d')
        self.assertEqual(set(data['services']), {'postgres', 'bootstrap', 'controller', 'web'})
        self.assertTrue(data['networks']['private']['internal'])
        for name, service in data['services'].items():
            self.assertFalse(service.get('ports'))
            self.assertEqual(service['pull_policy'], 'never')
            self.assertEqual(service['logging']['driver'], 'none')
            for volume in service.get('volumes', []):
                if volume['type'] == 'bind' and volume['target'] != '/workspace':
                    self.assertIn('/e2-07-20261005-01a10b2d/', volume['source'])
        self.assertEqual(set(data['services']['web']['secrets']), {'db_web_password', 'django_secret_key', 'mfa_encryption_key'})

    def test_rehearsal_python_parses_without_execution(self):
        root = Path(__file__).resolve().parents[3]
        for name in ['beta/deploy/prepare_access_rehearsal.py', 'backend/tools/access_rehearsal.py',
                     'backend/tools/access_restore_check.py', 'backend/tools/verify_access_web_runtime.py']:
            ast.parse((root/name).read_text())
