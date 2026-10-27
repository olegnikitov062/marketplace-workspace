"""Minimal E2-09 ACL delta; no provisioning or secret reads on import."""
from access_control.financial_guards import TABLE, NAMES
from data_isolation.financial_sql import PUBLIC_FUNCTIONS
from tools import isolation_web_contract as isolation
from tools.access_web_grants import ContractError


def apply(cursor):
    isolation.verify(cursor)
    cursor.execute("SELECT count(*) FROM django_migrations WHERE app='data_isolation' AND name='0002_financial_operations'")
    if cursor.fetchone() != (1,):
        raise ContractError('finance_migration_required')
    cursor.execute('GRANT INSERT(finance_grant_id) ON public.access_control_exportbinding TO mw_beta_web')
    for signature in PUBLIC_FUNCTIONS:
        cursor.execute(f'GRANT EXECUTE ON FUNCTION mw_isolation.{signature} TO mw_beta_web')
    verify(cursor)


def verify(cursor):
    isolation.verify(cursor, financial=True)
    cursor.execute("SELECT has_table_privilege('mw_beta_web',%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'), "
                   "EXISTS(SELECT 1 FROM pg_attribute a WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped "
                   "AND has_column_privilege('mw_beta_web',a.attrelid,a.attnum,'SELECT,INSERT,UPDATE,REFERENCES'))",
                   ['public.' + TABLE] * 2)
    if any(cursor.fetchone()):
        raise ContractError('financial_table_exposed')
    cursor.execute("SELECT c.relrowsecurity,c.relforcerowsecurity,r.rolname FROM pg_class c "
                   "JOIN pg_roles r ON r.oid=c.relowner WHERE c.oid=%s::regclass", ['public.' + TABLE])
    if cursor.fetchone() != (True, True, 'mw_beta_migrator'):
        raise ContractError('financial_rls_contract')
    cursor.execute("SELECT policyname,roles,qual,with_check FROM pg_policies WHERE schemaname='public' AND tablename=%s", [TABLE])
    if cursor.fetchall() != [('finance_operator', ['mw_beta_migrator'], 'true', 'true')]:
        raise ContractError('financial_operator_policy')
    cursor.execute("SELECT p.proname,p.prosecdef,p.proconfig,r.rolname, "
                   "has_function_privilege('mw_beta_web',p.oid,'EXECUTE'), "
                   "EXISTS(SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0) "
                   "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner "
                   "WHERE (n.nspname='mw_isolation' AND p.proname IN ('finance_allowed','finance_read','finance_write')) "
                   "OR (n.nspname='public' AND p.proname=ANY(%s))", [list(NAMES)])
    rows = cursor.fetchall()
    if len(rows) != len(NAMES) + 3:
        raise ContractError('financial_functions_missing')
    for name, definer, config, owner, executable, public in rows:
        if (not definer or config != ['search_path=pg_catalog, public'] or owner != 'mw_beta_migrator'
                or public or executable != (name in ('finance_read', 'finance_write'))):
            raise ContractError('financial_function_contract')
