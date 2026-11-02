"""Адресные права нового администратора; запуск только после проверки миграции."""
from basework.user_admin_sql import SIGNATURES


def apply(cursor):
    from account_security.operator import require_operator_process
    require_operator_process()
    cursor.execute('GRANT SELECT ON public.basework_administrator TO mw_beta_web')
    for signature in SIGNATURES:
        cursor.execute(f'GRANT EXECUTE ON FUNCTION public.{signature} TO mw_beta_web')
    verify(cursor)


def verify(cursor):
    cursor.execute("SELECT c.relrowsecurity,c.relforcerowsecurity,r.rolname FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE c.oid='public.basework_administrator'::regclass")
    if cursor.fetchone() != (True, True, 'mw_beta_migrator'):
        raise RuntimeError('BaseWork: отсутствует FORCE RLS администратора')
    cursor.execute("SELECT has_table_privilege('mw_beta_web','public.basework_administrator','SELECT'), "
                   "has_table_privilege('mw_beta_web','public.basework_administrator','INSERT,UPDATE,DELETE,TRUNCATE')")
    if cursor.fetchone() != (True, False):
        raise RuntimeError('BaseWork: недопустимые права таблицы администратора')
    cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_attribute a WHERE a.attrelid='public.basework_administrator'::regclass "
                   "AND a.attnum>0 AND NOT a.attisdropped AND has_column_privilege('mw_beta_web',a.attrelid,a.attnum,'INSERT,UPDATE,REFERENCES'))")
    if cursor.fetchone() != (False,):
        raise RuntimeError('BaseWork: недопустимые права столбцов администратора')
    cursor.execute("SELECT policyname,cmd,roles,qual,with_check FROM pg_policies WHERE schemaname='public' "
                   "AND tablename='basework_administrator' ORDER BY policyname")
    if cursor.fetchall() != [('basework_operator', 'ALL', ['mw_beta_migrator'], 'true', 'true'),
                             ('basework_read', 'SELECT', ['public'], '(mw_isolation.claims() IS NOT NULL)', None)]:
        raise RuntimeError('BaseWork: недопустимые политики администратора')
    cursor.execute("SELECT t.tgname,t.tgenabled,p.proname FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid "
                   "WHERE t.tgrelid='public.basework_administrator'::regclass AND NOT t.tgisinternal ORDER BY t.tgname")
    if cursor.fetchall() != [('basework_immutable', 'O', 'security_immutable'), ('basework_no_delete', 'O', 'basework_no_delete'),
                             ('basework_revoke', 'O', 'basework_applicationaccess_revoke')]:
        raise RuntimeError('BaseWork: недопустимые триггеры администратора')
    for signature in SIGNATURES:
        cursor.execute("SELECT p.prosecdef,p.proconfig,r.rolname,has_function_privilege('mw_beta_web',p.oid,'EXECUTE'), "
                       "EXISTS(SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0) "
                       "FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE p.oid=%s::regprocedure", ['public.' + signature])
        if cursor.fetchone() != (True, ['search_path=pg_catalog, public'], 'mw_beta_migrator', True, False):
            raise RuntimeError('BaseWork: недопустимые права функций администратора')
