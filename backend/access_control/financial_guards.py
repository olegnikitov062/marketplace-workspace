"""E2-09 schema invariants, frozen with access_control.0003."""
from django.db.migrations.exceptions import IrreversibleError

TABLE = 'access_control_syntheticfinance'
NAMES = ('finance_scope', 'finance_identity', 'finance_nodelete',
         'finance_binding_scope', 'finance_binding_immutable', 'finance_revoke', 'finance_manager')


def install(apps, editor):
    pg = editor.connection.vendor == 'postgresql'
    if editor.connection.vendor not in ('sqlite', 'postgresql'):
        raise RuntimeError('Unsupported finance database')
    differs = 'IS DISTINCT FROM' if pg else 'IS NOT'

    def guard(name, table, when, event, condition, body=None):
        if pg:
            body = body or "RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='23514';"
            editor.execute(f"CREATE FUNCTION public.{name}() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER "
                           f"SET search_path=pg_catalog,public AS $$ BEGIN IF {condition} THEN {body} END IF; "
                           "RETURN NEW; END $$")
            editor.execute(f'REVOKE ALL ON FUNCTION public.{name}() FROM PUBLIC')
            editor.execute(f'CREATE TRIGGER {name} {when} {event} ON public.{table} '
                           f'FOR EACH ROW EXECUTE FUNCTION public.{name}()')
        else:
            body = body or "SELECT RAISE(ABORT, 'Financial operation denied');"
            editor.execute(f'CREATE TRIGGER {name} {when} {event} ON {table} '
                           f'WHEN {condition} BEGIN {body} END')

    guard('finance_scope', TABLE, 'BEFORE', 'INSERT', '''NOT EXISTS(
        SELECT 1 FROM access_control_syntheticrecord r WHERE r.id=NEW.record_id
        AND r.organization_id=NEW.organization_id AND r.cabinet_id=NEW.cabinet_id
        AND r.archived_at IS NULL)''')
    guard('finance_identity', TABLE, 'BEFORE', 'UPDATE', ' OR '.join(
        f'OLD.{f} {differs} NEW.{f}' for f in ('record_id','organization_id','cabinet_id')))
    guard('finance_nodelete', TABLE, 'BEFORE', 'DELETE', 'true')
    guard('finance_binding_immutable', 'access_control_exportbinding', 'BEFORE', 'UPDATE',
          f'OLD.finance_grant_id {differs} NEW.finance_grant_id')
    guard('finance_binding_scope', 'access_control_exportbinding', 'BEFORE', 'INSERT', '''
        NEW.finance_grant_id IS NOT NULL AND NOT EXISTS(
          SELECT 1 FROM access_control_grant g JOIN ownership_membership m ON m.id=g.membership_id
          JOIN account_security_exportpermit p ON p.id=NEW.permit_id
          JOIN access_control_syntheticrecord r ON r.id=NEW.record_id
          WHERE g.id=NEW.finance_grant_id AND g.resource='synthetic_finance' AND g.action='export'
            AND g.platform_id IS NULL AND g.revoked_at IS NULL AND m.state='active'
            AND m.archived_at IS NULL AND m.user_id=p.user_id AND m.organization_id=p.organization_id
            AND g.organization_id=p.organization_id AND r.organization_id=p.organization_id
            AND (g.cabinet_id IS NULL OR g.cabinet_id=r.cabinet_id))''')
    guard('finance_revoke', 'access_control_grant', 'AFTER', 'UPDATE',
          f'OLD.revoked_at {differs} NEW.revoked_at', '''
          UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP
          WHERE revoked_at IS NULL AND id IN (SELECT permit_id FROM access_control_exportbinding
          WHERE finance_grant_id=NEW.id);''')
    guard('finance_manager', 'access_control_grant', 'BEFORE', 'INSERT', '''
        NEW.resource='synthetic_finance' AND NEW.action='manage_access' AND NOT EXISTS(
          SELECT 1 FROM ownership_membership m WHERE m.id=NEW.membership_id AND m.role='owner'
          AND m.state='active' AND m.archived_at IS NULL)''')
    if pg:
        # Close inherited default SELECT in the SAME transaction as table creation.
        editor.execute(f'REVOKE ALL ON public.{TABLE} FROM PUBLIC')
        editor.execute("DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='mw_beta_web') THEN "
                       f'REVOKE ALL ON public.{TABLE} FROM mw_beta_web; END IF; END $$')
        editor.execute(f'ALTER TABLE public.{TABLE} ENABLE ROW LEVEL SECURITY')
        editor.execute(f'ALTER TABLE public.{TABLE} FORCE ROW LEVEL SECURITY')
        with editor.connection.cursor() as cursor:
            cursor.execute('SELECT current_user')
            owner = editor.quote_name(cursor.fetchone()[0])
        # Only the trusted owner/fixed DEFINER functions, never the SQL web role.
        editor.execute(f'CREATE POLICY finance_operator ON public.{TABLE} TO {owner} USING (true) WITH CHECK (true)')
        editor.execute('ALTER TABLE public.access_control_syntheticrecord ADD CONSTRAINT finance_record_scope_key '
                       'UNIQUE(organization_id,cabinet_id,id)')
        editor.execute(f'ALTER TABLE public.{TABLE} ADD CONSTRAINT finance_record_scope_fk '
                       'FOREIGN KEY(organization_id,cabinet_id,record_id) REFERENCES '
                       'public.access_control_syntheticrecord(organization_id,cabinet_id,id)')


def refuse_populated(apps, editor):
    with editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT EXISTS(SELECT 1 FROM {TABLE}) OR EXISTS(SELECT 1 FROM access_control_grant "
                       "WHERE resource='synthetic_finance') OR EXISTS(SELECT 1 FROM access_control_exportbinding "
                       "WHERE finance_grant_id IS NOT NULL)")
        if cursor.fetchone()[0]:
            raise IrreversibleError('Populated finance rollback prohibited')


def uninstall(apps, editor):
    refuse_populated(apps, editor)
    tables = (TABLE, TABLE, TABLE, 'access_control_exportbinding', 'access_control_exportbinding',
              'access_control_grant', 'access_control_grant')
    for name, table in zip(NAMES, tables):
        editor.execute(f'DROP TRIGGER {name}' + (f' ON public.{table}' if editor.connection.vendor == 'postgresql' else ''))
        if editor.connection.vendor == 'postgresql':
            editor.execute(f'DROP FUNCTION public.{name}()')
    if editor.connection.vendor == 'postgresql':
        editor.execute(f'DROP POLICY finance_operator ON public.{TABLE}')
        editor.execute(f'ALTER TABLE public.{TABLE} DROP CONSTRAINT finance_record_scope_fk')
        editor.execute('ALTER TABLE public.access_control_syntheticrecord DROP CONSTRAINT finance_record_scope_key')


def noop(apps, editor):
    pass
