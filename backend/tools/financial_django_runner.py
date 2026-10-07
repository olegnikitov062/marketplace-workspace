"""Provision only the fresh isolated test database before HTTP regressions.

Production key provisioning remains configure/apply. Never accepts mw_beta,
SQLite, another cluster or an existing key; does not grant any SQL privilege.
"""
import uuid

from django.db import connection, transaction
from django.test.runner import DiscoverRunner
from data_isolation.context import StatementSigner, signing_key
from tools.financial_rehearsal import PROJECT, expect, marker


def prepare_test_signing_key():
    marker()
    expect(connection.vendor == 'postgresql')
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),session_user,current_user,current_setting(\'cluster_name\')')
        expect(cursor.fetchone() == ('test_mw_beta', 'mw_beta_migrator', 'mw_beta_migrator', PROJECT))
        cursor.execute('SELECT count(*) FROM mw_isolation.key')
        expect(cursor.fetchone() == (0,))
        cursor.execute('INSERT INTO mw_isolation.key(singleton,secret) VALUES(true,%s)', [signing_key()])
        # Prove the real statement/signature adapter before any HTTP fixture.
        with connection.execute_wrapper(StatementSigner(connection, uuid.uuid4().hex)):
            cursor.execute('SELECT mw_isolation.claims() IS NOT NULL')
            expect(cursor.fetchone() == (True,))


class IsolationDiscoverRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        old_config = super().setup_databases(**kwargs)
        prepare_test_signing_key()
        return old_config
