"""Real Django middleware/CSRF/session consumers; synthetic identities only."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.db import transaction, IntegrityError
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from account_security.tests import test_http as security_tests
from account_security.models import AccountSession, Authenticator, ExportPermit
from account_security import services as security
from accounts.models import AccountContact
from accounts.services import block_account
from ownership.models import User, Organization, Membership, Cabinet
from access_control.models import Grant, SyntheticRecord, PlatformRoleAssignment, SupportWindow
from access_control import services, operator


@override_settings(SECURITY_DOWNLOAD_PROBE=True)
class AccessHTTPTests(TestCase):
    post = security_tests.SecurityHTTPTests.post
    start_login = security_tests.SecurityHTTPTests.start_login
    otp = security_tests.SecurityHTTPTests.otp
    enroll = security_tests.SecurityHTTPTests.enroll
    login = security_tests.SecurityHTTPTests.login
    session_record = security_tests.SecurityHTTPTests.record

    def setUp(self):
        with override_settings(ACCESS_CONTROL_ENABLED=False):
            security_tests.SecurityHTTPTests.setUp(self)
        self.ca = Cabinet.objects.create(organization=self.a, name='synthetic-a1', marketplace='synthetic')
        self.ca2 = Cabinet.objects.create(organization=self.a, name='synthetic-a2', marketplace='synthetic')
        self.cb = Cabinet.objects.create(organization=self.b, name='synthetic-b1', marketplace='synthetic')
        self.ra = SyntheticRecord.objects.create(organization=self.a, cabinet=self.ca, value=7)
        self.ra2 = SyntheticRecord.objects.create(organization=self.a, cabinet=self.ca2, value=9)
        self.rb = SyntheticRecord.objects.create(organization=self.b, cabinet=self.cb, value=11)
        self.om = Membership.objects.get(user=self.owner, organization=self.a)
        self.mm = Membership.objects.get(user=self.member, organization=self.a)
        self.mb = Membership.objects.create(user=self.member, organization=self.b, role='observer')
        for resource, action, _ in services.template_spec('owner', []):
            Grant.objects.create(organization=self.a, membership=self.om, resource=resource, action=action)
        # Synthetic confirmed factor; actual login still verifies a real TOTP.
        Authenticator.objects.create(user=self.owner, name='synthetic', confirmed=True)
        self.member_client = Client(enforce_csrf_checks=True)
        self.login(self.owner)
        self.login(self.member, self.member_client)

    def url(self, obj=None, suffix=''):
        obj = obj or self.ra
        return f'/api/v1/access/organizations/{obj.organization_id}/cabinets/{obj.cabinet_id}/synthetic/{obj.pk}/' + suffix

    def org_url(self, suffix, org=None):
        return f'/api/v1/access/organizations/{(org or self.a).pk}/' + suffix

    def grant(self, action='view', cabinet=None, member=None, resource='synthetic_record'):
        member = member or self.mm
        return Grant.objects.create(organization_id=member.organization_id, membership=member,
            cabinet=cabinet, resource=resource, action=action)

    def download(self, permit_id, client=None):
        return (client or self.member_client).get(f'/auth/security/probe/{permit_id}/', secure=True)

    def export(self):
        response = self.post(self.url(suffix='export/'), client=self.member_client)
        self.assertEqual(response.status_code, 201)
        return response.json()['permit_id']

    def test_default_deny_and_four_independent_actions(self):
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.grant('export', self.ca)
        permit = self.export()
        self.assertEqual(self.download(permit).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.post(self.url(suffix='change/'), {'value': '4'}, client=self.member_client).status_code, 403)
        self.grant('change', self.ca)
        self.assertEqual(self.post(self.url(suffix='change/'), {'value': '4'}, client=self.member_client).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.grant('view', self.ca)
        self.assertEqual(self.member_client.get(self.url(), secure=True).json(), {'value': 4, 'finance_visibility': 'restricted'})
        self.assertEqual(self.post(self.org_url('grants/'), {'membership_id': str(self.om.pk),
            'resource': 'synthetic_record', 'action': 'view', 'cabinet_id': str(self.ca.pk)}, client=self.member_client).status_code, 403)

    def test_two_organizations_and_identifier_substitution(self):
        self.grant('view', self.ca)
        self.grant('view', self.cb, self.mb)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(self.rb), secure=True).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(self.ra2), secure=True).status_code, 403)
        for url in [self.url().replace(str(self.a.pk), str(self.b.pk)),
                    self.url().replace(str(self.ca.pk), str(self.ca2.pk)),
                    self.url().replace(str(self.ra.pk), str(self.rb.pk))]:
            self.assertEqual(self.member_client.get(url, secure=True).status_code, 403)

    def test_organization_scope_includes_future_cabinets(self):
        self.grant()
        c = Cabinet.objects.create(organization=self.a, name='synthetic-future', marketplace='synthetic')
        r = SyntheticRecord.objects.create(organization=self.a, cabinet=c)
        self.assertEqual(self.member_client.get(self.url(r), secure=True).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(self.rb), secure=True).status_code, 403)

    def test_revoke_regrant_never_restores_old_link(self):
        g = self.grant('export', self.ca)
        permit = self.export()
        self.assertEqual(self.download(permit).status_code, 200)
        response = self.post(self.org_url(f'grants/{g.pk}/revoke/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.download(permit).status_code, 403)
        self.grant('export', self.ca)
        self.assertEqual(self.download(permit).status_code, 403)
        self.assertEqual(self.download(self.export()).status_code, 200)
        self.assertEqual(self.download(permit, self.client).status_code, 403)

    def test_raw_revocation_is_permanent(self):
        g = self.grant('export')
        permit = self.export()
        Grant.objects.filter(pk=g.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.download(permit).status_code, 403)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Grant.objects.filter(pk=g.pk).update(revoked_at=None)

    def test_member_suspension_and_reactivation_do_not_restore_grants(self):
        self.grant('view')
        g = self.grant('export')
        permit = self.export()
        self.assertEqual(self.post(self.org_url(f'memberships/{self.mm.pk}/suspend/')).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        Membership.objects.filter(pk=self.mm.pk).update(state='active')
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.download(permit).status_code, 403)

    def test_archived_cabinet_and_record_revoke_organization_grant_link(self):
        self.grant('view')
        self.grant('export')
        permit = self.export()
        Cabinet.objects.filter(pk=self.ca.pk).update(archived_at=timezone.now())
        self.assertEqual(self.download(permit).status_code, 403)
        Cabinet.objects.filter(pk=self.ca.pk).update(archived_at=None)
        self.assertEqual(self.download(permit).status_code, 403)
        newer = self.export()
        SyntheticRecord.objects.filter(pk=self.ra.pk).update(archived_at=timezone.now())
        self.assertEqual(self.download(newer).status_code, 403)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)

    def test_archive_organization_denies_live_session(self):
        self.grant('view')
        Organization.objects.filter(pk=self.a.pk).update(archived_at=timezone.now())
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)

    def test_no_self_elevation_or_foreign_scope(self):
        data = {'membership_id': str(self.om.pk), 'resource': 'synthetic_record', 'action': 'export', 'cabinet_id': ''}
        self.assertEqual(self.post(self.org_url('grants/'), data).status_code, 403)
        data.update(membership_id=str(self.mm.pk), cabinet_id=str(self.cb.pk))
        self.assertNotEqual(self.post(self.org_url('grants/'), data).status_code, 201)
        data.update(membership_id=str(self.mb.pk), cabinet_id='')
        self.assertNotEqual(self.post(self.org_url('grants/'), data).status_code, 201)

    def test_missing_issuer_permission_denies_delegation(self):
        Grant.objects.filter(membership=self.om, action='export').update(revoked_at=timezone.now())
        data = {'membership_id': str(self.mm.pk), 'resource': 'synthetic_record', 'action': 'export', 'cabinet_id': ''}
        self.assertEqual(self.post(self.org_url('grants/'), data).status_code, 403)

    def test_owner_http_issue_organization_grant(self):
        data = {'membership_id': str(self.mm.pk), 'resource': 'synthetic_record', 'action': 'view', 'cabinet_id': ''}
        result = self.post(self.org_url('grants/'), data)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(self.member_client.get(self.url(self.ra2), secure=True).status_code, 200)

    def test_password_recovery_preserves_exact_grants_and_revoked_links(self):
        import secrets
        from django.contrib.auth.tokens import default_token_generator
        from accounts.services import confirm_recovery
        g = self.grant('export', self.ca)
        permit = self.export()
        Grant.objects.filter(pk=g.pk).update(revoked_at=timezone.now())
        before = list(Grant.objects.filter(membership__user=self.member).values_list('id', 'organization_id', 'cabinet_id', 'action', 'revoked_at'))
        password = secrets.token_urlsafe(24)
        self.member.refresh_from_db()
        confirm_recovery(self.member.pk, default_token_generator.make_token(self.member), password, password)
        after = list(Grant.objects.filter(membership__user=self.member).values_list('id', 'organization_id', 'cabinet_id', 'action', 'revoked_at'))
        self.assertTrue(before == after)
        self.assertEqual(self.download(permit).status_code, 302)  # Old session is no longer authenticated.

    def test_templates_and_promotion_require_mfa(self):
        path = self.org_url(f'memberships/{self.mm.pk}/template/')
        self.assertEqual(self.post(path, {'role': 'observer', 'cabinet_ids': f'{self.ca.pk},{self.ca2.pk}'}).status_code, 200)
        self.assertEqual(Grant.objects.filter(membership=self.mm, revoked_at__isnull=True).count(), 2)
        self.assertEqual(self.post(path, {'role': 'cabinet_user', 'cabinet_ids': str(self.ca.pk)}).status_code, 200)
        self.assertEqual(Grant.objects.filter(membership=self.mm, revoked_at__isnull=True).count(), 1)
        self.assertEqual(self.post(path, {'role': 'owner', 'cabinet_ids': ''}).status_code, 403)
        Authenticator.objects.create(user=self.member, name='synthetic', confirmed=True)
        self.assertEqual(self.post(path, {'role': 'owner', 'cabinet_ids': ''}).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)

    def test_last_owner_self_change_is_denied(self):
        self.assertEqual(self.post(self.org_url(f'memberships/{self.om.pk}/suspend/')).status_code, 403)
        g = Grant.objects.get(membership=self.om, resource='memberships', action='manage_access')
        self.assertEqual(self.post(self.org_url(f'grants/{g.pk}/revoke/')).status_code, 403)

    def test_csrf_on_all_new_mutations(self):
        paths = [self.url(suffix='change/'), self.url(suffix='export/'), self.org_url('grants/'),
            self.org_url(f'grants/{self.ra.pk}/revoke/'), self.org_url(f'memberships/{self.mm.pk}/template/'),
            self.org_url(f'memberships/{self.mm.pk}/suspend/'), self.org_url('support/'),
            self.org_url(f'support/{self.ra.pk}/close/')]
        for path in paths:
            self.assertEqual(self.post(path, csrf=False).status_code, 403)

    def test_stale_confirmation_cannot_change_access_or_invite(self):
        AccountSession.objects.filter(pk=self.session_record().pk).update(password_confirmed_at=timezone.now()-timedelta(minutes=6))
        self.assertEqual(self.post(self.org_url(f'memberships/{self.mm.pk}/suspend/')).status_code, 403)
        self.assertEqual(self.post('/auth/invitations', {'organization_id': str(self.a.pk),
            'username': 'synthetic-new', 'email': 'new@example.invalid', 'role': 'observer'}).status_code, 403)

    def test_invitation_is_real_grant_consumer(self):
        self.assertEqual(self.post('/auth/invitations', {'organization_id': str(self.a.pk),
            'username': 'synthetic-new', 'email': 'new@example.invalid', 'role': 'observer'}).status_code, 201)
        Membership.objects.filter(pk=self.mm.pk).update(role='owner')
        Authenticator.objects.create(user=self.member, name='synthetic-standby', confirmed=True)
        self.grant('manage_access', member=self.mm, resource='memberships')
        Grant.objects.filter(membership=self.om, resource='memberships', action='manage_access').update(revoked_at=timezone.now())
        self.assertEqual(self.post('/auth/invitations', {'organization_id': str(self.a.pk),
            'username': 'synthetic-new2', 'email': 'new2@example.invalid', 'role': 'observer'}).status_code, 403)

    def test_blocked_user_cannot_use_grants_or_be_promoted(self):
        self.grant('view')
        block_account(self.member.pk)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.post(self.org_url(f'memberships/{self.mm.pk}/template/'),
            {'role': 'owner', 'cabinet_ids': ''}).status_code, 403)

    def test_raw_cross_tenant_and_immutable_grants(self):
        for fields in [dict(organization=self.b, membership=self.mm), dict(organization=self.a, membership=self.mm, cabinet=self.cb)]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Grant.objects.create(**fields, resource='synthetic_record', action='view')
        g = self.grant()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Grant.objects.filter(pk=g.pk).update(action='export')

    def platform(self):
        user = User.objects.create_user('synthetic-platform', self.password)
        AccountContact.objects.create(user=user, email='platform@example.invalid', activated_at=timezone.now())
        assignment = PlatformRoleAssignment.objects.create(user=user)
        Authenticator.objects.create(user=user, name='synthetic', confirmed=True)
        client = Client(enforce_csrf_checks=True)
        self.login(user, client)
        return user, assignment, client

    def test_platform_support_expiry_and_no_automatic_data_access(self):
        user, assignment, client = self.platform()
        self.assertEqual(client.get('/api/v1/access/platform/status/', secure=True).status_code, 200)
        self.assertEqual(client.get(self.url(), secure=True).status_code, 403)
        g = Grant.objects.create(platform=assignment, organization=self.a, cabinet=self.ca, resource='synthetic_record', action='view')
        self.assertEqual(client.get(self.url(), secure=True).status_code, 403)
        result = self.post(self.org_url('support/'), {'grant_id': str(g.pk), 'reason': 'synthetic_diagnostic'}, client)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(client.get(self.url(), secure=True).status_code, 200)
        self.assertEqual(client.get(self.url(self.ra2), secure=True).status_code, 403)
        self.assertEqual(self.post(self.url(suffix='export/'), client=client).status_code, 403)
        self.assertEqual(self.post(self.url(suffix='change/'), {'value': '2'}, client).status_code, 403)
        window = SupportWindow.objects.get(pk=result.json()['support_id'])
        with patch('django.utils.timezone.now', return_value=window.expires_at+timedelta(seconds=1)):
            self.assertEqual(client.get(self.url(), secure=True).status_code, 403)

    def test_platform_revocation_invalidates_existing_session(self):
        user, assignment, client = self.platform()
        PlatformRoleAssignment.objects.filter(pk=assignment.pk).update(revoked_at=timezone.now())
        self.assertEqual(client.get('/api/v1/access/platform/status/', secure=True).status_code, 403)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PlatformRoleAssignment.objects.filter(pk=assignment.pk).update(revoked_at=None)

    def test_platform_no_membership_or_owner_recovery(self):
        user, assignment, client = self.platform()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Membership.objects.create(user=user, organization=self.a, role='owner')
        with self.assertRaises(PermissionDenied):
            security.issue_operator_recovery(user.pk)

    def test_platform_limits_and_mfa_enforced(self):
        user, assignment, client = self.platform()
        record = self.session_record(client)
        AccountSession.objects.filter(pk=record.pk).update(last_seen=timezone.now()-timedelta(minutes=16))
        self.assertEqual(client.get('/api/v1/access/platform/status/', secure=True).status_code, 403)
        self.assertTrue(security.required(user))
        with self.assertRaises(PermissionDenied):
            operator.assign_platform(self.member.pk)  # Offline settings are not an operator.
