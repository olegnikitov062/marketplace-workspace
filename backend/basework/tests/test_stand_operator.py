import uuid
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, TestCase

from basework import stand_operator as operator
from basework.models import IdentityBinding, ApplicationAccess
from access_control.models import Grant
from ownership.models import User, Membership


class OperatorGuardsTests(SimpleTestCase):
    def test_roster_is_explicit_and_synthetic(self):
        key = str(uuid.uuid4())
        good = {'project': operator.PROJECT, 'users': [{'id': key, 'username': 'basework-uat-a'}]}
        self.assertEqual(operator.roster(good), {key: 'basework-uat-a'})
        for change in ({'project': 'production'}, {'users': []}, {'users': good['users'] * 2},
                       {'users': [{'id': key, 'username': 'admin'}]},
                       {'users': [{'id': 1, 'username': 'basework-uat-a'}]}, {'extra': True}):
            with self.assertRaises((PermissionDenied, ValueError)):
                operator.roster({**good, **change})

    def test_cluster_role_and_mode_checks_cannot_be_skipped(self):
        with patch.object(operator, 'marker'), patch.object(operator, 'connection') as db, \
             patch.object(operator, 'require_operator_process') as role, \
             patch.dict(operator.os.environ, BASEWORK_OPERATOR_CONFIG_FILE=operator.CONFIG):
            db.vendor = 'sqlite'
            with self.assertRaises(PermissionDenied):
                operator.guard()
            role.assert_not_called()
            db.vendor = 'postgresql'
            role.side_effect = PermissionDenied
            with self.assertRaises(PermissionDenied):
                operator.guard()
            role.side_effect = None
            cursor = db.cursor.return_value.__enter__.return_value
            for row in (('production', 170001, False, False), (operator.PROJECT, 160001, False, False),
                        (operator.PROJECT, 170001, True, False), (operator.PROJECT, 170001, False, True)):
                cursor.fetchone.return_value = row
                with self.assertRaises(PermissionDenied):
                    operator.guard()

    def test_command_suppresses_sensitive_exception_details(self):
        with patch('basework.management.commands.basework_stand.execute', side_effect=ValueError('sensitive')):
            with self.assertRaises(CommandError) as raised:
                call_command('basework_stand', 'grant-view', user=str(uuid.uuid4()), stdout=StringIO())
            self.assertNotIn('sensitive', str(raised.exception))


class OperatorActionsTests(TestCase):
    def setUp(self):
        self.key = str(uuid.uuid4())
        self.name = 'basework-uat-test'
        self.guard = patch.object(operator, 'guard', return_value={self.key: self.name})
        self.guard.start()
        self.addCleanup(self.guard.stop)
        self.password = patch.object(operator, 'password_file', return_value='x' * 40)
        self.password.start()
        self.addCleanup(self.password.stop)
        self.provider = patch.object(operator, 'current', return_value=SimpleNamespace(issuer='https://issuer.example.invalid'))
        self.provider.start()
        self.addCleanup(self.provider.stop)
        self.data = {'user_id': self.key, 'issuer': 'https://issuer.example.invalid', 'subject': 'synthetic-subject'}

    def create(self):
        operator.execute('create-user', self.key, password_path='/run/secrets/basework_uat_a')

    def test_unknown_uuid_and_repeated_creation_denied(self):
        with self.assertRaises(PermissionDenied):
            operator.execute('create-user', str(uuid.uuid4()))
        self.assertEqual(User.objects.count(), 0)
        self.create()
        with self.assertRaises(PermissionDenied):
            operator.execute('create-user', self.key)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Membership.objects.get(user_id=self.key).role, 'observer')
        self.assertEqual(Grant.objects.count(), 0)

    def test_explicit_binding_and_revoked_history_never_reassigned(self):
        self.create()
        with patch.object(operator, 'document', return_value={**self.data, 'issuer': 'https://wrong.invalid'}):
            with self.assertRaises(PermissionDenied):
                operator.execute('bind-identity', self.key)
        with patch.object(operator, 'document', return_value=self.data):
            operator.execute('bind-identity', self.key)
            with self.assertRaises(PermissionDenied):
                operator.execute('bind-identity', self.key)
            with patch.object(operator, 'current', side_effect=PermissionDenied):
                operator.execute('revoke-identity', self.key)
            with self.assertRaises(PermissionDenied):
                operator.execute('bind-identity', self.key)
        self.assertIsNotNone(IdentityBinding.objects.get().revoked_at)

    def test_grant_only_own_synthetic_view_and_preserve_revoked_history(self):
        self.create()
        operator.execute('grant-view', self.key)
        grant = Grant.objects.get()
        self.assertEqual((grant.resource, grant.action), ('synthetic_record', 'view'))
        self.assertEqual(grant.cabinet_id, operator.ids(self.key)['cabinet'])
        self.assertEqual(ApplicationAccess.objects.get().application, 'marketplace')
        with self.assertRaises(PermissionDenied):
            operator.execute('grant-view', self.key)
        operator.execute('revoke-view', self.key)
        grant.refresh_from_db()
        self.assertIsNotNone(grant.revoked_at)
        self.assertIsNotNone(ApplicationAccess.objects.get().revoked_at)
        with self.assertRaises(PermissionDenied):
            operator.execute('grant-view', self.key)
