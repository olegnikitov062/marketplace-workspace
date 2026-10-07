"""PostgreSQL only: real row-lock ordering, never a SQLite substitute."""
import uuid
from datetime import timedelta
from unittest import skipUnless
from django.db import connection, transaction
from django.test import TransactionTestCase, RequestFactory, override_settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils import timezone

from access_control.tests import test_transactions as legacy
from access_control.models import Grant, SyntheticRecord, SyntheticFinance, ExportBinding
from access_control import services
from account_security import services as security
from account_security.models import ExportPermit
from ownership.models import Cabinet
from data_isolation.context import StatementSigner


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL financial locks and signed SQL')
@override_settings(SECURITY_DOWNLOAD_PROBE=True)
class FinancialConcurrencyTests(TransactionTestCase):
    race = legacy.AccessConcurrencyTests.race

    def setUp(self):
        legacy.AccessConcurrencyTests.setUp(self)
        for user, member, session in self.owners:
            for action in Grant.Action.values:
                Grant.objects.create(membership=member, organization=self.org, resource='synthetic_finance', action=action)
        self.cab = Cabinet.objects.create(organization=self.org, name='synthetic-financial-race', marketplace='synthetic')
        self.obj = SyntheticRecord.objects.create(organization=self.org,cabinet=self.cab)
        SyntheticFinance.objects.create(record=self.obj,organization=self.org,cabinet=self.cab,
                                         revenue=100,cost=30,expenses=20,payout=90)

    def signed(self, fn):
        def run(user):
            with transaction.atomic(), connection.execute_wrapper(StatementSigner(connection,uuid.uuid4().hex)):
                return fn(user)
        return run

    def test_revoke_against_view_and_change(self):
        a,b = self.owners
        for action in ('view','change'):
            grant = Grant.objects.get(membership=a[1],resource='synthetic_finance',action=action)
            if action == 'view':
                consume = lambda u: services.record_operation(u,self.org.pk,self.cab.pk,self.obj.pk,'view')
            else:
                consume = lambda u: services.change_finance(u,self.org.pk,self.cab.pk,self.obj.pk,
                    dict(revenue='123',cost='30',expenses='20',payout='90'))
            result = self.race([(a[0],a[2],self.signed(consume)),
                (b[0],b[2],self.signed(lambda u: services.remove_grant(u,self.org.pk,grant.pk)))])
            self.assertTrue(result[1])
            marker = security.current_session.set(a[2].pk)
            try:
                if action=='view':
                    self.assertEqual(self.signed(consume)(a[0])['finance_visibility'],'restricted')
                else:
                    with self.assertRaises(PermissionDenied):
                        self.signed(consume)(a[0])
            finally:
                security.current_session.reset(marker)

    def test_financial_download_against_revoke_and_regrant(self):
        a,b = self.owners
        ordinary = Grant.objects.get(membership=a[1],resource='synthetic_record',action='export')
        financial = Grant.objects.get(membership=a[1],resource='synthetic_finance',action='export')
        permit = ExportPermit.objects.create(user=a[0],organization=self.org,session=a[2],expires_at=timezone.now()+timedelta(minutes=5))
        ExportBinding.objects.create(permit=permit,grant=ordinary,finance_grant=financial,record=self.obj)
        def read(user):
            request = RequestFactory().get('/synthetic')
            request.user = user
            return services.download(request,permit.pk)
        result = self.race([(a[0],a[2],self.signed(read)),
                           (b[0],b[2],self.signed(lambda u: services.remove_grant(u,self.org.pk,financial.pk)))])
        self.assertTrue(result[1])
        Grant.objects.create(membership=a[1],organization=self.org,resource='synthetic_finance',action='export')
        marker = security.current_session.set(a[2].pk)
        try:
            with self.assertRaises((PermissionDenied,ObjectDoesNotExist)):
                self.signed(read)(a[0])
        finally:
            security.current_session.reset(marker)
