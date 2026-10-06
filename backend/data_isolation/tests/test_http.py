from django.test import override_settings
from access_control.tests import test_http as legacy


class IsolationHTTPTests(legacy.AccessHTTPTests):
    """Re-exercises existing auth/Grant invariants under the new boundary.

    SQLite runs are application regressions, not proof of PostgreSQL policies.
    """
    def list_url(self, obj=None):
        obj = obj or self.ra
        return f'/api/v1/access/organizations/{obj.organization_id}/cabinets/{obj.cabinet_id}/synthetic/'

    def test_list_search_scope_and_unknown_filters(self):
        self.assertEqual(self.member_client.get(self.list_url(), secure=True).status_code, 403)
        self.grant('view', self.ca)
        response = self.member_client.get(self.list_url(), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['records'], [{'id': str(self.ra.pk), 'value': 7}])
        for other in (self.ra2, self.rb):
            self.assertEqual(self.member_client.get(self.list_url() + '?record_id=' + str(other.pk), secure=True).json(), {'records': []})
            self.assertEqual(self.member_client.get(self.list_url(other), secure=True).status_code, 403)
        for query in ('organization_id=' + str(self.b.pk), 'resource=memberships',
                      'record_id=invalid', f'record_id={self.ra.pk}&record_id={self.rb.pk}'):
            self.assertEqual(self.member_client.get(self.list_url() + '?' + query, secure=True).status_code, 403)

    def test_list_revocation_live_session_and_no_cache(self):
        grant = self.grant('view', self.ca)
        before = self.member_client.get(self.list_url(), secure=True)
        self.assertIn('no-store', before.headers['Cache-Control'])
        self.assertEqual(before.status_code, 200)
        self.assertEqual(self.post(self.org_url(f'grants/{grant.pk}/revoke/')).status_code, 200)
        self.assertEqual(self.member_client.get(self.list_url(), secure=True).status_code, 403)

    def test_list_keeps_actions_independent_and_probe_disabled(self):
        self.grant('export', self.ca)
        self.assertEqual(self.member_client.get(self.list_url(), secure=True).status_code, 403)
        self.grant('view', self.ca)
        with override_settings(SECURITY_DOWNLOAD_PROBE=False):
            self.assertEqual(self.member_client.get(self.list_url(), secure=True).status_code, 403)

    def test_scope_reset_after_failure_and_sequential_users(self):
        from data_isolation.context import scope
        self.grant('view', self.ca)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 200)
        self.assertIsNone(scope.get())
        self.assertEqual(self.member_client.get(self.url(self.rb), secure=True).status_code, 403)
        self.assertIsNone(scope.get())
        self.assertEqual(self.client.get(self.url(), secure=True).status_code, 200)
        self.assertIsNone(scope.get())
