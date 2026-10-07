"""NEW isolated restore only; comparisons stay in memory, output is pass/fail."""
from tools.financial_rehearsal import guard, expect, PROJECT

TARGET = 'mw_e209_01a115d9_r2_restore'
METADATA = (
    "SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('public','mw_isolation') ORDER BY 1,2",
    "SELECT n.nspname,c.relname,c.relkind,r.rolname,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text "
    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner "
    "WHERE n.nspname IN ('public','mw_isolation') ORDER BY 1,2",
    "SELECT table_schema,table_name,column_name,ordinal_position,data_type,udt_name,is_nullable,column_default,"
    "numeric_precision,numeric_scale FROM information_schema.columns "
    "WHERE table_schema IN ('public','mw_isolation') ORDER BY 1,2,4",
    "SELECT n.nspname,c.relname,a.attname,a.attacl::text FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
    "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('public','mw_isolation') "
    "AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1,2,3",
    "SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies "
    "WHERE schemaname IN ('public','mw_isolation') ORDER BY 1,2,3",
    "SELECT n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),p.prosrc,p.prosecdef,p.proconfig,"
    "p.proacl::text,r.rolname,p.provolatile FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
    "JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname IN ('public','mw_isolation') ORDER BY 1,2,3",
    "SELECT n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid),t.tgenabled FROM pg_trigger t "
    "JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname IN ('public','mw_isolation') AND NOT t.tgisinternal ORDER BY 1,2,3",
    "SELECT n.nspname,c.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated FROM pg_constraint k "
    "JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname IN ('public','mw_isolation') ORDER BY 1,2,3",
    "SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes "
    "WHERE schemaname IN ('public','mw_isolation') ORDER BY 1,2,3",
    "SELECT n.nspname,r.rolname,n.nspacl::text FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner "
    "WHERE n.nspname IN ('public','mw_isolation') ORDER BY 1",
    "SELECT r.rolname,n.nspname,d.defaclobjtype,d.defaclacl::text FROM pg_default_acl d "
    "JOIN pg_roles r ON r.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace ORDER BY 1,2,3",
)


def main():
    guard()
    import psycopg
    from psycopg import sql
    from django.db import connection
    from account_security.services import quarantine_restored_access
    from tools.financial_web_contract import verify
    params = connection.get_connection_params()
    params.pop('cursor_factory', None)
    params.pop('context', None)
    params['dbname'] = TARGET
    with connection.cursor() as cursor:
        verify(cursor)  # Source ACL; restore deliberately denies web CONNECT.
    with psycopg.connect(**params) as restored, connection.cursor() as cursor:
        expect(restored.execute("SELECT current_database(),current_setting('cluster_name'),session_user").fetchone()
               == (TARGET, PROJECT, 'mw_beta_migrator'))
        expect(restored.execute("SELECT has_database_privilege('mw_beta_web',current_database(),'CONNECT')").fetchone() == (False,))
        for statement in METADATA:
            cursor.execute(statement)
            expect(cursor.fetchall() == restored.execute(statement).fetchall())
        cursor.execute(METADATA[0])
        for schema, table in cursor.fetchall():
            # Includes the new synthetic signing key. No values/hashes are emitted.
            query = sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(schema,table))
            cursor.execute(query.as_string(connection.connection))
            expect(cursor.fetchall() == restored.execute(query).fetchall())
        cursor.execute("SELECT schemaname,sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY 1,2")
        for schema, name in cursor.fetchall():
            query = sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(schema,name))
            cursor.execute(query.as_string(connection.connection))
            expect(cursor.fetchall() == restored.execute(query).fetchall())
        expect(restored.execute("SELECT count(*) FROM access_control_grant WHERE resource='synthetic_finance' AND revoked_at IS NOT NULL").fetchone()[0] > 0)
        for statement in (
            "UPDATE access_control_grant SET revoked_at=NULL WHERE resource='synthetic_finance' AND revoked_at IS NOT NULL",
            "UPDATE account_security_exportpermit SET revoked_at=NULL WHERE revoked_at IS NOT NULL",
            "UPDATE access_control_exportbinding SET finance_grant_id=NULL WHERE finance_grant_id IS NOT NULL",
        ):
            refused = False
            try:
                with restored.transaction():
                    restored.execute(statement)
                    raise RuntimeError('restore_guard_missing')
            except psycopg.errors.CheckViolation:
                refused = True
            expect(refused)
    connection.close()
    connection.settings_dict['NAME'] = TARGET
    quarantine_restored_access()
    with connection.cursor() as cursor:
        for table in ('account_security_accountsession','account_security_exportpermit'):
            cursor.execute(f'SELECT count(*) FROM {table} WHERE revoked_at IS NULL')
            expect(cursor.fetchone() == (0,))
        cursor.execute('SELECT count(*) FROM account_security_accountsecurity WHERE NOT recovery_required')
        expect(cursor.fetchone() == (0,))
        cursor.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                       "WHERE n.nspname='public' AND c.relrowsecurity AND c.relforcerowsecurity")
        expect(cursor.fetchone() == (28,))
        cursor.execute("SELECT has_table_privilege('mw_beta_web','public.access_control_syntheticfinance','SELECT,INSERT,UPDATE,DELETE')")
        expect(cursor.fetchone() == (False,))
    print('E2-09 restore rows/schema/ACL/functions/guards/sequences and restored-access quarantine PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('E2-09 restore verification failed; preserve resources; no details disclosed') from None
