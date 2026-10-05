import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from unittest import skipUnless

from django.db import connection, connections, transaction, IntegrityError
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.test import TransactionTestCase
from django.utils import timezone

from ownership.models import User, Organization, Membership, Cabinet
from account_security.models import Authenticator, AccountSession
from account_security import services as security
from access_control.models import Grant, SyntheticRecord
from access_control import services


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL independent connections and row locks')
class AccessConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='synthetic-concurrent')
        self.owners = []
        for n in range(2):
            u = User.objects.create_user('synthetic-owner-' + str(n), secrets.token_urlsafe(24))
            m = Membership.objects.create(user=u, organization=self.org, role='owner')
            a = Authenticator.objects.create(user=u, name='synthetic', confirmed=True)
            state = security.state_for(u)
            now = timezone.now()
            s = AccountSession.objects.create(user=u, session_hash=security.digest(secrets.token_urlsafe(32)),
                credential_hash=u.get_session_auth_hash(), version=state.version, level='full', authenticator=a,
                expires_at=now+timedelta(hours=1), password_confirmed_at=now, factor_confirmed_at=now)
            for r, action, _ in services.template_spec('owner', []):
                Grant.objects.create(membership=m, organization=self.org, resource=r, action=action)
            self.owners.append((u, m, s))
        u = User.objects.create_user('synthetic-member', secrets.token_urlsafe(24))
        self.member = Membership.objects.create(user=u, organization=self.org, role='observer')

    def race(self, actions):
        barrier = Barrier(2)
        def execute(spec):
            user, session, action = spec
            connections.close_all()
            marker = security.current_session.set(session.pk)
            try:
                barrier.wait(timeout=10)
                action(user)
                return True
            except (PermissionDenied, ObjectDoesNotExist, IntegrityError):
                return False
            finally:
                security.current_session.reset(marker)
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(execute, actions))

    def test_two_owners_cannot_suspend_each_other_and_lose_last_owner(self):
        a, b = self.owners
        result = self.race([(a[0], a[2], lambda u: services.suspend_membership(u, self.org.pk, b[1].pk)),
                            (b[0], b[2], lambda u: services.suspend_membership(u, self.org.pk, a[1].pk))])
        self.assertEqual(sorted(result), [False, True])
        self.assertEqual(Membership.objects.filter(organization=self.org, role='owner', state='active').count(), 1)

    def test_issuance_racing_issuer_suspension_has_no_post_revoke_authority(self):
        a, b = self.owners
        self.race([(a[0], a[2], lambda u: services.issue_grant(u, self.org.pk, self.member.pk, 'synthetic_record', 'view')),
                   (b[0], b[2], lambda u: services.suspend_membership(u, self.org.pk, a[1].pk))])
        marker = security.current_session.set(a[2].pk)
        try:
            with self.assertRaises(PermissionDenied):
                services.issue_grant(a[0], self.org.pk, self.member.pk, 'synthetic_record', 'export')
        finally:
            security.current_session.reset(marker)

    def test_raw_concurrent_revocation_cannot_remove_both_owners(self):
        a, b = self.owners
        def revoke(member):
            with transaction.atomic():
                Grant.objects.filter(membership=member, resource='memberships', action='manage_access').update(revoked_at=timezone.now())
        results = self.race([(a[0], a[2], lambda u: revoke(a[1])), (b[0], b[2], lambda u: revoke(b[1]))])
        self.assertEqual(sorted(results), [False, True])

    def test_download_racing_revocation_has_linearized_result(self):
        from django.test import RequestFactory
        from access_control.models import ExportBinding
        from account_security.models import ExportPermit
        a, b = self.owners
        cabinet = Cabinet.objects.create(organization=self.org, name='synthetic', marketplace='synthetic')
        obj = SyntheticRecord.objects.create(organization=self.org, cabinet=cabinet)
        grant = Grant.objects.get(membership=a[1], action='export')
        permit = ExportPermit.objects.create(user=a[0], organization=self.org, session=a[2], expires_at=timezone.now()+timedelta(minutes=5))
        ExportBinding.objects.create(permit=permit, grant=grant, record=obj)
        def read(user):
            req = RequestFactory().get('/synthetic')
            req.user = user
            services.download(req, permit.pk)
        self.race([(a[0], a[2], read), (b[0], b[2], lambda u: services.remove_grant(u, self.org.pk, grant.pk))])
        marker = security.current_session.set(a[2].pk)
        try:
            with self.assertRaises((PermissionDenied, ObjectDoesNotExist)):
                read(a[0])
        finally:
            security.current_session.reset(marker)

    def test_two_operator_revocations_preserve_last_administrator(self):
        from unittest.mock import patch
        from access_control import operator
        from access_control.models import PlatformRoleAssignment
        assignments = []
        for n in range(2):
            user = User.objects.create_user('synthetic-platform-' + str(n), secrets.token_urlsafe(24))
            Authenticator.objects.create(user=user, name='synthetic', confirmed=True)
            assignments.append(PlatformRoleAssignment.objects.create(user=user))
        a, b = self.owners
        # Actual PostgreSQL advisory lock; operator identity is covered by the
        # isolated operator scenario, not by this algorithmic concurrency test.
        with patch.object(operator, 'require_operator_process'):
            results = self.race([(a[0], a[2], lambda u: operator.revoke_platform(assignments[0].pk)),
                                 (b[0], b[2], lambda u: operator.revoke_platform(assignments[1].pk))])
        self.assertEqual(sorted(results), [False, True])
