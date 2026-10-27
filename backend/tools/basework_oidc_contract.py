"""Точный контракт PostgreSQL для локального OIDC, без выдачи прав при импорте."""
from tools.access_web_grants import ContractError
from basework.oidc_sql import GUARD, TRANSITION


def require(value):
    if not value:
        raise ContractError('oidc_contract_failed')


def verify(cursor):
    cursor.execute("SELECT c.relrowsecurity,c.relforcerowsecurity,r.rolname FROM pg_class c "
                   "JOIN pg_roles r ON r.oid=c.relowner WHERE c.oid='public.basework_oidcattempt'::regclass")
    require(cursor.fetchone() == (True, True, 'mw_beta_migrator'))
    cursor.execute("SELECT policyname,cmd,roles,qual,with_check FROM pg_policies "
                   "WHERE schemaname='public' AND tablename='basework_oidcattempt' ORDER BY policyname")
    require(cursor.fetchall() == [('oidc_operator', 'ALL', ['mw_beta_migrator'], 'true', 'true'),
                                  ('oidc_read', 'SELECT', ['public'], '(mw_isolation.claims() IS NOT NULL)', None)])
    cursor.execute("SELECT has_table_privilege('mw_beta_web','basework_oidcattempt','SELECT'), "
                   "has_table_privilege('mw_beta_web','basework_oidcattempt','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'), "
                   "EXISTS(SELECT 1 FROM pg_attribute a WHERE a.attrelid='basework_oidcattempt'::regclass AND a.attnum>0 "
                   "AND NOT a.attisdropped AND has_column_privilege('mw_beta_web',a.attrelid,a.attnum,'INSERT,UPDATE,REFERENCES'))")
    require(cursor.fetchone() == (True, False, False))
    for name, source, definer, executable in [('basework_oidc_immutable', GUARD, False, False),
                                            ('basework_oidc_transition', TRANSITION, True, True)]:
        cursor.execute("SELECT p.prosecdef,p.proconfig,r.rolname,p.prosrc,has_function_privilege('mw_beta_web',p.oid,'EXECUTE'), "
                       "EXISTS(SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0) "
                       "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner "
                       "WHERE n.nspname='public' AND p.proname=%s", [name])
        rows = cursor.fetchall()
        require(len(rows) == 1)
        actual_definer, config, owner, body, execute, public = rows[0]
        require(actual_definer == definer and config == ['search_path=pg_catalog, public']
                and owner == 'mw_beta_migrator' and body.strip() == source.split('$$')[1].strip()
                and execute == executable and not public)
    cursor.execute("SELECT tgname,tgenabled,p.proname FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid "
                   "WHERE tgrelid='basework_oidcattempt'::regclass AND NOT tgisinternal ORDER BY tgname")
    require(cursor.fetchall() == [('basework_no_delete', 'O', 'basework_no_delete'),
                                  ('basework_oidc_immutable', 'O', 'basework_oidc_immutable')])
