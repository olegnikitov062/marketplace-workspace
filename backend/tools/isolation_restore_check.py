"""Compare the NEW isolated restore in memory, then quarantine restored access.
Does not create databases, dump files, read real keys or print row data.
"""
from tools.isolation_rehearsal import guard, expect, PROJECT


def main():
    guard()
    from django.db import connection
    from account_security.services import quarantine_restored_access
    import psycopg
    from psycopg import sql
    target = 'mw_e208_01a1105a_restore'
    params = connection.get_connection_params()
    params.pop('cursor_factory', None)
    params.pop('context', None)
    params['dbname'] = target
    with psycopg.connect(**params) as restored:
        expect(restored.execute("SELECT current_database(),current_setting('cluster_name'),session_user").fetchone() ==
               (target, PROJECT, 'mw_beta_migrator'))
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                query = sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier('public', table))
                cursor.execute(query.as_string(connection.connection))
                expect(cursor.fetchall() == restored.execute(query).fetchall())
            # Compare the new private key only in memory; never output values
            # or key fingerprints. Dump/restore must not silently omit it.
            cursor.execute('SELECT singleton,secret FROM mw_isolation.key')
            expect(cursor.fetchall() == restored.execute('SELECT singleton,secret FROM mw_isolation.key').fetchall())
            for metadata in (
                "SELECT tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname",
                "SELECT p.proname,p.prosrc,p.prosecdef,p.proconfig,p.proacl::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='mw_isolation' ORDER BY p.proname",
            ):
                cursor.execute(metadata)
                expect(cursor.fetchall() == restored.execute(metadata).fetchall())
        count = restored.execute("SELECT count(*) FROM access_control_grant WHERE revoked_at IS NOT NULL").fetchone()[0]
        expect(count > 0)
        # Prove irreversible grants after restore; rollback only this probe.
        rejected = False
        try:
            with restored.transaction():
                restored.execute('UPDATE access_control_grant SET revoked_at=NULL WHERE revoked_at IS NOT NULL')
        except psycopg.errors.CheckViolation:
            rejected = True
        expect(rejected)
    connection.close()
    connection.settings_dict['NAME'] = target
    # Never connect the restored database to a web process automatically.
    quarantine_restored_access()
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM account_security_accountsession WHERE revoked_at IS NULL')
        expect(cursor.fetchone() == (0,))
        cursor.execute('SELECT count(*) FROM account_security_exportpermit WHERE revoked_at IS NULL')
        expect(cursor.fetchone() == (0,))
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM pg_class WHERE relrowsecurity AND relforcerowsecurity')
        from data_isolation.sql import TABLES
        expect(cursor.fetchone()[0] == len(TABLES))
    print('E2-08 restore rows, irreversible grant revocation and restored-access quarantine PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('E2-08 restore verification failed; no row or credential data disclosed') from None
