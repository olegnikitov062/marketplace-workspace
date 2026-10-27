"""Additional E2-08 contract; ordinary web table/column ACL remains E2-07."""
from data_isolation.sql import TABLES, DENIED_TABLES, TRUSTED_TRIGGERS
from tools import access_web_grants as previous

ROLE = 'mw_beta_web'
PUBLIC_FUNCTIONS = ('allowed(text,jsonb,text)', 'claims()', 'export_cabinet(uuid,uuid,uuid)')


def apply(cursor, key):
    previous.verify_privileges(cursor, ROLE, True)
    previous.verify_guards(cursor, ROLE, True)
    if len(key) != 32:
        raise previous.ContractError('invalid_isolation_key')
    cursor.execute('INSERT INTO mw_isolation.key(singleton,secret) VALUES(true,%s)', [key])
    cursor.execute('GRANT USAGE ON SCHEMA mw_isolation TO mw_beta_web')
    for name in PUBLIC_FUNCTIONS:
        cursor.execute(f'GRANT EXECUTE ON FUNCTION mw_isolation.{name} TO mw_beta_web')
    verify(cursor)


def verify(cursor, financial=False):
    extra = {'access_control_exportbinding': (*previous.INSERT['access_control_exportbinding'], 'finance_grant_id')} if financial else None
    previous.verify_privileges(cursor, ROLE, True, extra_insert=extra)
    previous.verify_guards(cursor, ROLE, True)
    cursor.execute("SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,r.rolname "
                   "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                   "JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='public' AND c.relname=ANY(%s)", [list(TABLES)])
    rows = cursor.fetchall()
    if len(rows) != len(TABLES) or any(not enabled or not forced or owner != 'mw_beta_migrator'
                                    for _, enabled, forced, owner in rows):
        raise previous.ContractError('isolation_table_contract')
    cursor.execute("SELECT tablename,policyname FROM pg_policies WHERE schemaname='public' AND tablename=ANY(%s)", [list(TABLES)])
    expected = {(t, 'isolation_' + op) for t in TABLES for op in
                (('operator',) if t in DENIED_TABLES else ('operator','select','insert','update','delete'))}
    if set(cursor.fetchall()) != expected:
        raise previous.ContractError('isolation_policy_contract')
    cursor.execute("SELECT has_table_privilege(%s,'mw_isolation.key','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'), "
                   "has_schema_privilege(%s,'mw_isolation','CREATE')", [ROLE, ROLE])
    if any(cursor.fetchone()):
        raise previous.ContractError('web_can_access_signing_key')
    cursor.execute("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                   "WHERE n.nspname='mw_isolation' AND has_function_privilege(%s,p.oid,'EXECUTE')", [ROLE])
    if cursor.fetchone()[0] != len(PUBLIC_FUNCTIONS) + (2 if financial else 0):
        raise previous.ContractError('unexpected_isolation_function_acl')
    cursor.execute("SELECT p.proname,p.prosecdef,r.rolname,p.proconfig,has_function_privilege(%s,p.oid,'EXECUTE') "
                   "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner "
                   "WHERE n.nspname='public' AND p.proname=ANY(%s)", [ROLE,list(TRUSTED_TRIGGERS)])
    trigger_rows = cursor.fetchall()
    if len(trigger_rows) != len(TRUSTED_TRIGGERS) or any(
            not definer or owner != 'mw_beta_migrator' or config != ['search_path=pg_catalog, public'] or executable
            for _,definer,owner,config,executable in trigger_rows):
        raise previous.ContractError('isolation_trigger_contract')
