from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from account_security import services as security
from account_security.models import AccountSession
from access_control import operator
from access_control.models import Grant, PlatformRoleAssignment
from access_control.tests import test_http


class PlatformHTTPTests(test_http.AccessHTTPTests):
    # unittest includes the base HTTP tests too. Keep a separate focused class
    # through load_tests below, without hiding any inherited assertions.
    def test_support_close_and_grant_revocation(self):
        user, assignment, client = self.platform()
        grant = Grant.objects.create(platform=assignment, organization=self.a, resource='synthetic_record', action='view')
        result = self.post(self.org_url('support/'), {'grant_id': str(grant.pk), 'reason': 'synthetic_diagnostic'}, client)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(client.get(self.url(), secure=True).status_code, 200)
        self.assertEqual(self.post(self.org_url('support/' + result.json()['support_id'] + '/close/'), client=client).status_code, 200)
        self.assertEqual(client.get(self.url(), secure=True).status_code, 403)
        self.post(self.org_url('support/'), {'grant_id': str(grant.pk), 'reason': 'synthetic_diagnostic'}, client)
        Grant.objects.filter(pk=grant.pk).update(revoked_at=timezone.now())
        self.assertEqual(client.get(self.url(), secure=True).status_code, 403)

    def test_admin_delegates_only_operator_granted_scope_not_self_or_owner(self):
        user, assignment, client = self.platform()
        Grant.objects.create(platform=assignment, organization=self.a, resource='memberships', action='manage_access')
        Grant.objects.create(platform=assignment, organization=self.a, cabinet=self.ca, resource='synthetic_record', action='export')
        data = {'membership_id': str(self.mm.pk), 'resource': 'synthetic_record', 'action': 'export', 'cabinet_id': str(self.ca.pk)}
        self.assertEqual(self.post(self.org_url('grants/'), data, client).status_code, 201)
        self.assertEqual(self.post(self.url(suffix='export/'), client=client).status_code, 403)
        data['cabinet_id'] = str(self.ca2.pk)
        self.assertEqual(self.post(self.org_url('grants/'), data, client).status_code, 403)
        data.update(cabinet_id=str(self.ca.pk), membership_id=str(self.om.pk))
        self.assertEqual(self.post(self.org_url('grants/'), data, client).status_code, 403)
        self.assertEqual(self.post(self.org_url(f'memberships/{self.mm.pk}/template/'),
            {'role': 'owner', 'cabinet_ids': ''}, client).status_code, 403)

    def test_admin_four_hour_limit(self):
        user, assignment, client = self.platform()
        record = self.session_record(client)
        # Updating last_seen is allowed; immutable creation timestamp is retained.
        future = record.created_at + timedelta(hours=4, seconds=1)
        AccountSession.objects.filter(pk=record.pk).update(last_seen=future)
        with patch('django.utils.timezone.now', return_value=future):
            self.assertEqual(client.get('/api/v1/access/platform/status/', secure=True).status_code, 403)

    def test_last_administrator_revocation_denied_by_operator_service(self):
        user, assignment, client = self.platform()
        # Only process/SQL-identity guard is mocked locally; never a PostgreSQL claim.
        with patch.object(operator, 'operator_lock'):
            with self.assertRaises(PermissionDenied):
                operator.revoke_platform(assignment.pk)
        self.assertTrue(PlatformRoleAssignment.objects.filter(pk=assignment.pk, revoked_at__isnull=True).exists())

    def test_owner_without_factor_has_no_grant_access(self):
        from account_security.models import Authenticator
        Authenticator.objects.filter(user=self.owner).update(confirmed=False, revoked_at=timezone.now())
        self.assertEqual(self.client.get(self.url(), secure=True).status_code, 403)


def load_tests(loader, tests, pattern):
    import unittest
    names = [name for name in PlatformHTTPTests.__dict__ if name.startswith('test_')]
    return unittest.TestSuite(PlatformHTTPTests(name) for name in names)
