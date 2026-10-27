"""E2-09 consumers and negative disclosure checks, synthetic data only."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.db import transaction, IntegrityError
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from access_control import services, financial, operator
from access_control.models import Grant, SyntheticRecord, SyntheticFinance, ExportBinding
from access_control.tests import test_http as legacy
from account_security.models import AccountSession, Authenticator, ExportPermit
from access_control.models import SupportWindow
from ownership.models import Membership, Cabinet, Organization
from accounts.services import block_account


@override_settings(SECURITY_DOWNLOAD_PROBE=True)
class FinancialHTTPTests(TestCase):
    # Reuse only the synthetic fixture and helpers, not duplicate inherited tests.
    post = legacy.AccessHTTPTests.post
    start_login = legacy.AccessHTTPTests.start_login
    otp = legacy.AccessHTTPTests.otp
    enroll = legacy.AccessHTTPTests.enroll
    login = legacy.AccessHTTPTests.login
    session_record = legacy.AccessHTTPTests.session_record
    url = legacy.AccessHTTPTests.url
    org_url = legacy.AccessHTTPTests.org_url
    grant = legacy.AccessHTTPTests.grant
    export = legacy.AccessHTTPTests.export
    download = legacy.AccessHTTPTests.download
    platform = legacy.AccessHTTPTests.platform

    def setUp(self):
        legacy.AccessHTTPTests.setUp(self)
        for record in (self.ra, self.ra2, self.rb):
            self.make_finance(record)

    def make_finance(self, record, **values):
        return SyntheticFinance.objects.create(record=record, organization=record.organization,
            cabinet=record.cabinet, **{**dict(revenue='100.00', cost='40.00', expenses='10.00', payout='80.00'), **values})

    def fg(self, action='view', cabinet=None, member=None):
        return self.grant(action, cabinet, member, 'synthetic_finance')

    def owner_finance(self):
        for action in Grant.Action.values:
            self.fg(action, member=self.om)

    def list_url(self, obj=None):
        return self.url(obj).rsplit('/', 2)[0] + '/'

    def change_values(self, **values):
        return {**dict(revenue='130.00', cost='50.00', expenses='20.00', payout='99.00'), **values}

    def assert_restricted(self, response):
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['finance_visibility'], 'restricted')
        self.assertNotIn('finance', data)
        self.assertNotIn('finance_totals', data)
        for row in data.get('records', []):
            self.assertNotIn('finance', row)

    def test_ordinary_actions_templates_and_owner_do_not_grant_finance(self):
        for action in Grant.Action.values:
            if action != 'manage_access':
                self.grant(action, self.ca)
        self.assert_restricted(self.member_client.get(self.url(), secure=True))
        self.assert_restricted(self.client.get(self.url(), secure=True))
        self.assert_restricted(self.member_client.get(self.list_url(), secure=True))
        self.assertEqual(self.download(self.export()).content, b'synthetic,value\nexample.invalid,7\n')
        for role, cabinets in [('owner', []), ('observer', [self.ca]), ('cabinet_user', [self.ca])]:
            self.assertFalse(any(resource == 'synthetic_finance' for resource, _, _ in services.template_spec(role, cabinets)))

    def test_scope_intersection_and_same_actor_two_organizations(self):
        self.fg('view', self.ca)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.grant('view')
        self.grant('view', self.cb, self.mb)
        self.assertEqual(self.member_client.get(self.url(), secure=True).json()['finance']['profit'], '50.00')
        self.assert_restricted(self.member_client.get(self.url(self.ra2), secure=True))
        self.assert_restricted(self.member_client.get(self.url(self.rb), secure=True))
        self.fg('view', self.cb, self.mb)
        self.assertEqual(self.member_client.get(self.url(self.rb), secure=True).json()['finance']['profit'], '50.00')
        for url in (self.url().replace(str(self.a.pk), str(self.b.pk)),
                    self.url().replace(str(self.ra.pk), str(self.rb.pk))):
            self.assertEqual(self.member_client.get(url, secure=True).status_code, 403)

    def test_direct_derived_and_aggregate_projection(self):
        self.grant('view', self.ca)
        self.fg('view')
        second = SyntheticRecord.objects.create(organization=self.a, cabinet=self.ca, value=3)
        self.make_finance(second, revenue='200.00', cost='70.00', expenses='30.00', payout='120.00')
        data = self.member_client.get(self.list_url(), secure=True).json()
        self.assertEqual(len(data['records']), 2)
        self.assertEqual(data['finance_totals'], dict(revenue='300.00', cost='110.00', expenses='40.00',
            payout='200.00', profit='150.00', margin_percent='50.00', currency='RUB',
            scope='returned_records', financial_records=2))
        searched = self.member_client.get(self.list_url() + '?record_id=' + str(self.ra.pk), secure=True).json()
        self.assertEqual(searched['finance_totals']['profit'], '50.00')
        self.assertEqual(len(searched['records']), 1)
        self.assertEqual(self.member_client.get(self.url(self.ra2), secure=True).status_code, 403)

    def test_hidden_finance_changes_do_not_change_bodies_headers_or_row_count(self):
        self.grant('view')
        paths = (self.url(), self.list_url(), self.list_url() + '?record_id=' + str(self.ra.pk))
        before = [self.member_client.get(path, secure=True) for path in paths]
        SyntheticFinance.objects.filter(record=self.ra).update(revenue='98765.43', cost='0', expenses='99', payout='1')
        after = [self.member_client.get(path, secure=True) for path in paths]
        for a, b in zip(before, after):
            self.assert_restricted(b)
            self.assertEqual(a.content, b.content)
            self.assertEqual(a.status_code, b.status_code)
            for header in ('Content-Length', 'Content-Type', 'Cache-Control', 'ETag', 'Last-Modified'):
                self.assertEqual(a.get(header), b.get(header))
        empty = SyntheticRecord.objects.create(organization=self.a, cabinet=self.ca, value=3)
        response = self.member_client.get(self.list_url(), secure=True)
        self.make_finance(empty)
        self.assertEqual(response.content, self.member_client.get(self.list_url(), secure=True).content)

    def test_filters_sort_group_fields_and_duplicate_parameters_are_denied(self):
        self.grant('view')
        for query in ('cost__gt=1','sort=profit','order_by=revenue','group_by=payout',
                      'fields=value,cost','aggregate=profit','finance=true','resource=synthetic_finance',
                      'organization_id=' + str(self.b.pk), 'record_id=x',
                      f'record_id={self.ra.pk}&record_id={self.ra.pk}'):
            for path in (self.url(), self.list_url()):
                self.assertEqual(self.member_client.get(path + '?' + query, secure=True).status_code, 403)

    def test_change_requires_both_actions_and_never_returns_money(self):
        path = self.url(suffix='finance/change/')
        self.grant('change', self.ca)
        self.fg('view', self.ca)
        before = SyntheticFinance.objects.get(record=self.ra).revenue
        self.assertEqual(self.post(path, self.change_values(), self.member_client).status_code, 403)
        self.assertEqual(SyntheticFinance.objects.get(record=self.ra).revenue, before)
        self.fg('change', self.ca)
        self.assertEqual(self.post(path, self.change_values(), self.member_client).json(), {'status': 'ok'})
        self.assertEqual(SyntheticFinance.objects.get(record=self.ra).revenue, Decimal('130.00'))
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.post(path, self.change_values(), self.member_client, csrf=False).status_code, 403)
        for bad in ('NaN', 'Infinity', '-1', '1.001', '1e2', '1000000000000', ''):
            self.assertEqual(self.post(path, self.change_values(cost=bad), self.member_client).status_code, 403)
        self.assertEqual(SyntheticFinance.objects.get(record=self.ra).cost, Decimal('50.00'))

    def test_hidden_input_and_nonexistent_finance_same_denial(self):
        self.grant('change')
        empty = SyntheticRecord.objects.create(organization=self.a, cabinet=self.ca)
        for obj in (self.ra, empty):
            for values in (self.change_values(), self.change_values(cost='NaN')):
                response = self.post(self.url(obj, 'finance/change/'), values, self.member_client)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {'status': 'denied'})
        response = self.post(self.url(suffix='change/'), {'value': '1','cost': '2'}, self.member_client)
        self.assertEqual(response.status_code, 400)
        self.ra.refresh_from_db()
        self.assertEqual(self.ra.value, 7)

    def test_export_independent_of_view_and_projection_never_expands(self):
        self.grant('export', self.ca)
        ordinary = self.export()
        self.fg('view', self.ca)
        self.assertEqual(self.download(self.export()).content, b'synthetic,value\nexample.invalid,7\n')
        self.fg('export', self.ca)
        financial_permit = self.export()
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        body = self.download(financial_permit).content
        self.assertIn(b'profit,margin_percent', body)
        self.assertIn(b'100.00,40.00,10.00,80.00,RUB,50.00,50.00', body)
        self.assertEqual(self.download(ordinary).content, b'synthetic,value\nexample.invalid,7\n')
        self.assertEqual(self.download(financial_permit, self.client).status_code, 403)
        self.assertEqual(self.member_client.get('/auth/security/probe/' + financial_permit + '/?fields=cost', secure=True).status_code, 403)

    def test_finance_revoke_with_overlapping_grant_and_regrant_old_link_stays_dead(self):
        self.owner_finance()
        self.grant('export')
        fg = self.fg('export', self.ca)
        permit = self.export()
        self.fg('export')
        self.assertEqual(self.post(self.org_url(f'grants/{fg.pk}/revoke/')).status_code, 200)
        self.assertEqual(self.download(permit).status_code, 403)
        self.fg('export', self.ca)
        self.assertEqual(self.download(permit).status_code, 403)
        self.assertEqual(self.download(self.export()).status_code, 200)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExportPermit.objects.filter(pk=permit).update(revoked_at=None)

    def test_live_view_revoke_keeps_ordinary_list_but_removes_fields_and_totals(self):
        self.owner_finance()
        self.grant('view')
        fg = self.fg('view')
        self.assertIn('finance_totals', self.member_client.get(self.list_url(), secure=True).json())
        self.assertEqual(self.post(self.org_url(f'grants/{fg.pk}/revoke/')).status_code, 200)
        self.assert_restricted(self.member_client.get(self.url(), secure=True))
        self.assert_restricted(self.member_client.get(self.list_url(), secure=True))

    def test_delegation_needs_financial_manager_and_own_action_scope(self):
        data = dict(membership_id=str(self.mm.pk), resource='synthetic_finance', action='view', cabinet_id=str(self.ca.pk))
        self.assertEqual(self.post(self.org_url('grants/'), data).status_code, 403)
        self.fg('manage_access', self.ca, self.om)
        self.assertEqual(self.post(self.org_url('grants/'), data).status_code, 403)
        self.fg('view', self.ca, self.om)
        response = self.post(self.org_url('grants/'), data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.post(self.org_url('grants/'), {**data, 'cabinet_id': ''}).status_code, 403)
        self.assertEqual(self.post(self.org_url('grants/'), {**data, 'membership_id': str(self.om.pk)}).status_code, 403)
        self.assertEqual(self.post(self.org_url('grants/'), {**data, 'action': 'manage_access'}).status_code, 403)
        AccountSession.objects.filter(pk=self.session_record().pk).update(password_confirmed_at=timezone.now()-timedelta(minutes=6))
        self.assertEqual(self.post(self.org_url('grants/'), data).status_code, 403)

    def test_template_cannot_silently_remove_financial_grant_without_authority(self):
        grant = self.fg('view', self.ca)
        path = self.org_url(f'memberships/{self.mm.pk}/template/')
        self.assertEqual(self.post(path, {'role':'cabinet_user','cabinet_ids':str(self.ca.pk)}).status_code, 403)
        grant.refresh_from_db()
        self.assertIsNone(grant.revoked_at)
        self.owner_finance()
        self.assertEqual(self.post(path, {'role':'cabinet_user','cabinet_ids':str(self.ca.pk)}).status_code, 200)
        self.assertFalse(Grant.objects.filter(membership=self.mm, resource='synthetic_finance', revoked_at__isnull=True).exists())

    def test_platform_support_never_reads_writes_exports_or_delegates_finance(self):
        user, assignment, client = self.platform()
        grant = Grant.objects.create(platform=assignment, organization=self.a, cabinet=self.ca, resource='synthetic_record', action='view')
        opened = self.post(self.org_url('support/'), {'grant_id':str(grant.pk),'reason':'synthetic_diagnostic'}, client)
        self.assertEqual(opened.status_code, 201)
        self.assert_restricted(client.get(self.url(), secure=True))
        self.assert_restricted(client.get(self.list_url(), secure=True))
        for action in Grant.Action.values:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Grant.objects.create(platform=assignment, organization=self.a, resource='synthetic_finance', action=action)
        self.assertEqual(self.post(self.url(suffix='finance/change/'), self.change_values(), client).status_code, 403)
        self.assertEqual(self.post(self.url(suffix='export/'), client=client).status_code, 403)
        self.assertEqual(self.post(self.org_url('grants/'), dict(membership_id=str(self.mm.pk), resource='synthetic_finance', action='view', cabinet_id=''), client).status_code, 403)
        self.assertEqual(self.post(self.org_url('support/' + opened.json()['support_id'] + '/close/'), client=client).status_code, 200)
        self.assertEqual(client.get(self.url(), secure=True).status_code, 403)

    def test_block_mfa_and_archive_reject_existing_sessions_and_links(self):
        self.grant('view')
        self.grant('export')
        self.fg('view')
        self.fg('export')
        permit = self.export()
        Cabinet.objects.filter(pk=self.ca.pk).update(archived_at=timezone.now())
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.download(permit).status_code, 403)
        Cabinet.objects.filter(pk=self.ca.pk).update(archived_at=None)
        self.assertEqual(self.download(permit).status_code, 403)
        Membership.objects.filter(pk=self.mm.pk).update(role='owner')
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        block_account(self.member.pk)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)

    def test_binding_and_financial_identity_immutable_and_cross_scope_denied(self):
        self.grant('export')
        fg = self.fg('export')
        permit = self.export()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExportBinding.objects.filter(permit_id=permit).update(finance_grant=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SyntheticFinance.objects.filter(record=self.ra).update(cabinet=self.cb)
        empty = SyntheticRecord.objects.create(organization=self.a, cabinet=self.ca)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SyntheticFinance.objects.create(record=empty, organization=self.b, cabinet=self.cb, **self.change_values())
        with self.assertRaises(IntegrityError), transaction.atomic():
            SyntheticFinance.objects.filter(record=self.ra).delete()

    def test_zero_revenue_and_negative_profit_only_visible_with_access(self):
        self.grant('view')
        self.fg('view')
        SyntheticFinance.objects.filter(record=self.ra).update(revenue=0)
        data = self.member_client.get(self.url(), secure=True).json()['finance']
        self.assertEqual(data['profit'], '-50.00')
        self.assertIsNone(data['margin_percent'])

    def test_bootstrap_is_explicit_operator_only_and_requires_mfa(self):
        with self.assertRaises(PermissionDenied):
            operator.bootstrap_finance(self.om.pk)
        with patch.object(operator, 'operator_lock'):
            operator.bootstrap_finance(self.om.pk)
            with self.assertRaises(PermissionDenied):
                operator.bootstrap_finance(self.om.pk)
        self.assertEqual(Grant.objects.filter(membership=self.om, resource='synthetic_finance').count(), 4)

    def test_financial_bootstrap_refuses_owner_without_confirmed_factor(self):
        Authenticator.objects.filter(user=self.owner).update(confirmed=False)
        with patch.object(operator, 'operator_lock'), self.assertRaises(PermissionDenied):
            operator.bootstrap_finance(self.om.pk)
        self.assertFalse(Grant.objects.filter(resource='synthetic_finance').exists())

    def test_password_recovery_preserves_financial_scope_and_does_not_revive_links(self):
        import secrets
        from django.contrib.auth.tokens import default_token_generator
        from accounts.services import confirm_recovery
        self.grant('export', self.ca)
        revoked = self.fg('export', self.ca)
        self.fg('view', self.cb, self.mb)
        permit = self.export()
        Grant.objects.filter(pk=revoked.pk).update(revoked_at=timezone.now())
        before = list(Grant.objects.filter(membership__user=self.member).order_by('pk').values())
        password = secrets.token_urlsafe(24)
        self.member.refresh_from_db()
        confirm_recovery(self.member.pk, default_token_generator.make_token(self.member), password, password)
        self.assertTrue(before == list(Grant.objects.filter(membership__user=self.member).order_by('pk').values()))
        self.assertIsNotNone(ExportPermit.objects.get(pk=permit).revoked_at)
        self.assertEqual(self.download(permit).status_code, 302)

    def test_membership_suspension_revokes_finance_without_expanding_other_organization(self):
        self.grant('view')
        self.grant('export')
        self.fg('view')
        self.fg('export')
        self.grant('view', self.cb, self.mb)
        self.fg('view', self.cb, self.mb)
        permit = self.export()
        self.assertEqual(self.post(self.org_url(f'memberships/{self.mm.pk}/suspend/')).status_code, 200)
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.download(permit).status_code, 403)
        self.assertEqual(self.member_client.get(self.url(self.rb), secure=True).json()['finance']['profit'], '50.00')
        self.assertFalse(Grant.objects.filter(membership=self.mm, revoked_at__isnull=True).exists())

    def test_archived_record_and_organization_never_revive_export(self):
        self.grant('view')
        self.grant('export')
        self.fg('view')
        self.fg('export')
        permit = self.export()
        SyntheticRecord.objects.filter(pk=self.ra.pk).update(archived_at=timezone.now())
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 403)
        self.assertEqual(self.download(permit).status_code, 403)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SyntheticRecord.objects.filter(pk=self.ra.pk).update(archived_at=None)
        self.assertEqual(self.download(permit).status_code, 403)
        other = SyntheticRecord.objects.create(organization=self.a,cabinet=self.ca)
        self.make_finance(other)
        response = self.post(self.url(other,'export/'),client=self.member_client)
        self.assertEqual(response.status_code,201)
        second = response.json()['permit_id']
        Organization.objects.filter(pk=self.a.pk).update(archived_at=timezone.now())
        self.assertEqual(self.member_client.get(self.list_url(), secure=True).status_code, 403)
        self.assertEqual(self.download(second).status_code, 403)

    def test_support_expiry_does_not_leave_financial_or_ordinary_visibility(self):
        user, assignment, client = self.platform()
        grant = Grant.objects.create(platform=assignment,organization=self.a,cabinet=self.ca,resource='synthetic_record',action='view')
        result = self.post(self.org_url('support/'), {'grant_id':str(grant.pk),'reason':'synthetic_diagnostic'}, client)
        self.assertEqual(result.status_code, 201)
        self.assert_restricted(client.get(self.url(), secure=True))
        with patch('django.utils.timezone.now',return_value=timezone.now()+timedelta(minutes=31)):
            self.assertEqual(client.get(self.url(), secure=True).status_code, 403)

    def test_total_is_exactly_returned_hundred_not_unseen_records(self):
        self.grant('view', self.ca)
        self.fg('view', self.ca)
        for n in range(100):
            obj = SyntheticRecord.objects.create(organization=self.a,cabinet=self.ca,value=n)
            self.make_finance(obj,revenue=str(n+1))
        data = self.member_client.get(self.list_url(),secure=True).json()
        self.assertEqual(len(data['records']),100)
        self.assertEqual(data['finance_totals']['financial_records'],100)
        self.assertEqual(Decimal(data['finance_totals']['revenue']),sum(Decimal(r['finance']['revenue']) for r in data['records']))
        self.assertEqual(data['finance_totals']['scope'],'returned_records')
        self.assertNotIn('count',data)

    def test_context_reset_and_default_deny(self):
        from data_isolation.context import scope, record_scope
        from account_security import services as security
        self.grant('view')
        self.fg('view')
        self.assertEqual(self.member_client.get(self.url(), secure=True).status_code, 200)
        self.assertIsNone(scope.get())
        marker = security.current_session.set(self.session_record(self.member_client).pk)
        try:
            with self.assertRaises(PermissionDenied):
                financial.read(self.member, self.a, self.ca, [self.ra.pk])
        finally:
            security.current_session.reset(marker)
        self.assertIsNone(scope.get())
