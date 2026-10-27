from django.test import SimpleTestCase
from tools import access_web_grants as acl


class AccessRoleContractTests(SimpleTestCase):
    def test_platform_assignment_and_synthetic_seed_are_not_web_writable(self):
        self.assertNotIn('access_control_platformroleassignment', acl.INSERT)
        self.assertNotIn('access_control_platformroleassignment', acl.UPDATE)
        self.assertNotIn('access_control_syntheticrecord', acl.INSERT)
        self.assertEqual(acl.UPDATE['access_control_syntheticrecord'], ('value',))
        self.assertEqual(acl.UPDATE['access_control_grant'], ('revoked_at',))
        self.assertNotIn('is_active', acl.UPDATE['ownership_user'])
        self.assertNotIn('organization_id', acl.UPDATE['ownership_membership'])

    def test_sql_plan_does_not_grant_schema_or_migrator_authority(self):
        sql = '\n'.join(acl.grant_statements(acl.MAIN_ROLE))
        for token in ('GRANT ALL', 'WITH GRANT OPTION', 'BYPASSRLS', 'CREATEROLE', 'GRANT CREATE', 'GRANT mw_beta_migrator'):
            self.assertNotIn(token, sql)
        with self.assertRaises(acl.ContractError):
            acl.grant_statements('production_web')
