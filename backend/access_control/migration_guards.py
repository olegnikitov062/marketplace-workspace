"""DB invariants. SQLite exercises logic, not PostgreSQL locking/ACL evidence."""
TABLES = ('grant', 'platformroleassignment', 'supportwindow', 'syntheticrecord', 'exportbinding')


def install(apps, editor):
    pg = editor.connection.vendor == 'postgresql'
    if editor.connection.vendor not in ('sqlite', 'postgresql'):
        raise RuntimeError('Unsupported access database')

    def trigger(table, name, when, event, condition, statements, fail=False):
        if pg:
            body = "RAISE EXCEPTION 'Access invariant rejected' USING ERRCODE='23514';" if fail else statements
            editor.execute(f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN {body} RETURN NEW; END $$")
            editor.execute(f'CREATE TRIGGER {name} {when} {event} ON {table} FOR EACH ROW WHEN ({condition}) EXECUTE FUNCTION {name}()')
        else:
            body = "SELECT RAISE(ABORT, 'Access invariant rejected');" if fail else statements
            editor.execute(f'CREATE TRIGGER {name} {when} {event} ON {table} WHEN {condition} BEGIN {body} END')

    different = 'IS DISTINCT FROM' if pg else 'IS NOT'
    for name in TABLES:
        model = apps.get_model('access_control', name)
        table = model._meta.db_table
        mutable = {'revoked_at'} if name != 'syntheticrecord' else {'value', 'archived_at'}
        checks = [f'OLD.{f.column} {different} NEW.{f.column}' for f in model._meta.fields if f.column not in mutable]
        terminal = 'archived_at' if name == 'syntheticrecord' else 'revoked_at'
        if name != 'exportbinding':
            checks.append(f'(OLD.{terminal} IS NOT NULL AND OLD.{terminal} {different} NEW.{terminal})')
        trigger(table, f'access_immutable_{name}', 'BEFORE', 'UPDATE', ' OR '.join(checks), '', True)
        if pg:
            editor.execute(f"CREATE FUNCTION access_nodelete_{name}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Access history retained' USING ERRCODE='23514'; END $$")
            editor.execute(f'CREATE TRIGGER access_nodelete_{name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION access_nodelete_{name}()')
        else:
            editor.execute(f"CREATE TRIGGER access_nodelete_{name} BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'Access history retained'); END")

    # BEFORE INSERT queries cannot be placed in PostgreSQL trigger WHEN clauses.
    def insert_guard(table, name, condition):
        if pg:
            editor.execute(f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN IF {condition} THEN RAISE EXCEPTION 'Access scope rejected' USING ERRCODE='23514'; END IF; RETURN NEW; END $$")
            editor.execute(f'CREATE TRIGGER {name} BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION {name}()')
        else:
            editor.execute(f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN {condition} BEGIN SELECT RAISE(ABORT, 'Access scope rejected'); END")

    insert_guard('access_control_grant', 'access_scope_grant', '''
      NOT EXISTS(SELECT 1 FROM ownership_organization WHERE id=NEW.organization_id AND archived_at IS NULL)
      OR (NEW.membership_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ownership_membership m
          JOIN ownership_user u ON u.id=m.user_id WHERE m.id=NEW.membership_id AND m.organization_id=NEW.organization_id
          AND m.state='active' AND m.archived_at IS NULL AND u.is_active AND u.archived_at IS NULL))
      OR (NEW.cabinet_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ownership_cabinet WHERE id=NEW.cabinet_id
          AND organization_id=NEW.organization_id AND archived_at IS NULL))
      OR (NEW.platform_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM access_control_platformroleassignment p
          JOIN ownership_user u ON u.id=p.user_id WHERE p.id=NEW.platform_id AND p.revoked_at IS NULL
          AND u.is_active AND u.archived_at IS NULL))''')
    insert_guard('access_control_syntheticrecord', 'access_scope_record', '''NOT EXISTS(
      SELECT 1 FROM ownership_cabinet c JOIN ownership_organization o ON o.id=c.organization_id
      WHERE c.id=NEW.cabinet_id AND c.organization_id=NEW.organization_id AND c.archived_at IS NULL AND o.archived_at IS NULL)''')
    insert_guard('access_control_platformroleassignment', 'access_separate_platform', '''
      EXISTS(SELECT 1 FROM ownership_membership WHERE user_id=NEW.user_id)
      OR NOT EXISTS(SELECT 1 FROM ownership_user WHERE id=NEW.user_id AND is_active AND archived_at IS NULL)''')
    insert_guard('ownership_membership', 'access_separate_member', '''EXISTS(
      SELECT 1 FROM access_control_platformroleassignment WHERE user_id=NEW.user_id AND revoked_at IS NULL)''')
    insert_guard('access_control_exportbinding', 'access_scope_export', '''NOT EXISTS(
      SELECT 1 FROM account_security_exportpermit p JOIN access_control_grant g ON g.id=NEW.grant_id
      JOIN ownership_membership m ON m.id=g.membership_id
      JOIN access_control_syntheticrecord r ON r.id=NEW.record_id
      WHERE p.id=NEW.permit_id AND g.revoked_at IS NULL AND g.resource='synthetic_record' AND g.action='export'
      AND m.user_id=p.user_id AND m.organization_id=p.organization_id AND g.organization_id=p.organization_id
      AND r.organization_id=p.organization_id AND (g.cabinet_id IS NULL OR g.cabinet_id=r.cabinet_id))''')
    support_limit = "NEW.expires_at > NEW.created_at + interval '30 minutes'" if pg else "julianday(NEW.expires_at) > julianday(NEW.created_at) + 30.0/1440"
    insert_guard('access_control_supportwindow', 'access_scope_support', '''NOT EXISTS(
      SELECT 1 FROM access_control_grant g JOIN access_control_platformroleassignment a ON a.id=g.platform_id
      JOIN account_security_accountsession s ON s.id=NEW.session_id
      WHERE g.id=NEW.grant_id AND g.revoked_at IS NULL AND a.revoked_at IS NULL AND a.user_id=s.user_id
      AND g.resource='synthetic_record' AND g.action='view' AND s.revoked_at IS NULL)
      OR NEW.reason <> 'synthetic_diagnostic' OR NEW.expires_at <= NEW.created_at OR ''' + support_limit)

    trigger('access_control_grant', 'access_revoke_grant', 'AFTER', 'UPDATE',
        f'OLD.revoked_at {different} NEW.revoked_at', '''
        UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP WHERE revoked_at IS NULL
          AND id IN(SELECT permit_id FROM access_control_exportbinding WHERE grant_id=NEW.id);
        UPDATE access_control_supportwindow SET revoked_at=CURRENT_TIMESTAMP WHERE revoked_at IS NULL AND grant_id=NEW.id;''')
    for table, name, condition, predicate in [
        ('ownership_membership', 'member', f'OLD.role {different} NEW.role OR OLD.state {different} NEW.state OR OLD.archived_at {different} NEW.archived_at', 'membership_id=NEW.id'),
        ('ownership_organization', 'org', f'OLD.archived_at {different} NEW.archived_at', 'organization_id=NEW.id'),
        ('ownership_cabinet', 'cabinet', f'OLD.archived_at {different} NEW.archived_at', 'cabinet_id=NEW.id'),
        ('access_control_platformroleassignment', 'platform', f'OLD.revoked_at {different} NEW.revoked_at', 'platform_id=NEW.id'),
    ]:
        statements = f'UPDATE access_control_grant SET revoked_at=CURRENT_TIMESTAMP WHERE revoked_at IS NULL AND {predicate};'
        if name == 'cabinet':
            # Organization-wide grants remain valid for other cabinets.
            statements += '''UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP WHERE revoked_at IS NULL
              AND id IN(SELECT b.permit_id FROM access_control_exportbinding b JOIN access_control_syntheticrecord r
              ON r.id=b.record_id WHERE r.cabinet_id=NEW.id);'''
        if name == 'platform':
            statements += '''UPDATE account_security_accountsession SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.user_id AND revoked_at IS NULL;
              UPDATE account_security_trusteddevice SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.user_id AND revoked_at IS NULL;'''
        trigger(table, f'access_revoke_{name}', 'AFTER', 'UPDATE', condition, statements)
    trigger('access_control_syntheticrecord', 'access_revoke_record', 'AFTER', 'UPDATE',
        f'OLD.archived_at {different} NEW.archived_at', '''UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP
          WHERE revoked_at IS NULL AND id IN(SELECT permit_id FROM access_control_exportbinding WHERE record_id=NEW.id);''')

    if pg:
        editor.execute("""CREATE FUNCTION access_web_subject() RETURNS trigger LANGUAGE plpgsql
          SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN
          IF current_user IN ('mw_beta_web','mw_beta_test_e2_07_01a10b2d_web') AND NEW.platform_id IS NOT NULL
          THEN RAISE EXCEPTION 'Operator scope required' USING ERRCODE='42501'; END IF;
          RETURN NEW; END $$""")
        editor.execute('CREATE TRIGGER access_web_subject BEFORE INSERT OR UPDATE ON access_control_grant FOR EACH ROW EXECUTE FUNCTION access_web_subject()')
        editor.execute("""CREATE FUNCTION access_owner_lock() RETURNS trigger LANGUAGE plpgsql
          SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN
          PERFORM id FROM ownership_organization WHERE id=NEW.organization_id FOR UPDATE;
          RETURN NEW; END $$""")
        for table in ('ownership_membership', 'access_control_grant'):
            editor.execute(f'CREATE TRIGGER access_owner_lock BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION access_owner_lock()')
        editor.execute("""CREATE FUNCTION access_last_owner() RETURNS trigger LANGUAGE plpgsql
          SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN
          IF TG_TABLE_NAME='ownership_membership' THEN
            IF OLD.role<>'owner' OR (NEW.role=OLD.role AND NEW.state=OLD.state AND NEW.archived_at IS NOT DISTINCT FROM OLD.archived_at)
            THEN RETURN NEW; END IF;
          ELSE
            IF OLD.resource<>'memberships' OR OLD.action<>'manage_access' OR OLD.membership_id IS NULL
              OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL THEN RETURN NEW; END IF;
          END IF;
          IF EXISTS(SELECT 1 FROM ownership_organization WHERE id=NEW.organization_id AND archived_at IS NULL)
            AND NOT EXISTS(SELECT 1 FROM ownership_membership m JOIN ownership_user u ON u.id=m.user_id
              JOIN access_control_grant g ON g.membership_id=m.id
              JOIN account_security_authenticator a ON a.user_id=u.id
              WHERE m.organization_id=NEW.organization_id AND m.role='owner' AND m.state='active' AND m.archived_at IS NULL
              AND u.is_active AND u.archived_at IS NULL AND a.confirmed AND a.revoked_at IS NULL
              AND g.resource='memberships' AND g.action='manage_access' AND g.revoked_at IS NULL AND g.cabinet_id IS NULL)
          THEN RAISE EXCEPTION 'Last owner protected' USING ERRCODE='23514'; END IF;
          RETURN NEW; END $$""")
        for table in ('ownership_membership', 'access_control_grant'):
            editor.execute(f'CREATE CONSTRAINT TRIGGER access_last_owner AFTER UPDATE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION access_last_owner()')
        # Composite FKs independently prevent cross-tenant relationships.
        editor.execute('ALTER TABLE ownership_membership ADD CONSTRAINT access_member_org_unique UNIQUE(organization_id,id)')
        editor.execute('ALTER TABLE access_control_grant ADD CONSTRAINT access_grant_member_fk FOREIGN KEY(organization_id,membership_id) REFERENCES ownership_membership(organization_id,id)')
        editor.execute('ALTER TABLE access_control_grant ADD CONSTRAINT access_grant_cabinet_fk FOREIGN KEY(organization_id,cabinet_id) REFERENCES ownership_cabinet(organization_id,id)')
        editor.execute('ALTER TABLE access_control_syntheticrecord ADD CONSTRAINT access_record_cabinet_fk FOREIGN KEY(organization_id,cabinet_id) REFERENCES ownership_cabinet(organization_id,id)')


def uninstall(apps, editor):
    pg = editor.connection.vendor == 'postgresql'
    entries = [(f'access_control_{n}', f'access_{kind}_{n}') for n in TABLES for kind in ('immutable', 'nodelete')]
    entries += [('access_control_grant','access_scope_grant'), ('access_control_syntheticrecord','access_scope_record'),
        ('access_control_platformroleassignment','access_separate_platform'), ('ownership_membership','access_separate_member'),
        ('access_control_exportbinding','access_scope_export'), ('access_control_supportwindow','access_scope_support'),
        ('access_control_grant','access_revoke_grant'), ('ownership_membership','access_revoke_member'),
        ('ownership_organization','access_revoke_org'), ('ownership_cabinet','access_revoke_cabinet'),
        ('access_control_platformroleassignment','access_revoke_platform'), ('access_control_syntheticrecord','access_revoke_record')]
    for table, name in reversed(entries):
        editor.execute(f'DROP TRIGGER {name}' + (f' ON {table}' if pg else ''))
        if pg:
            editor.execute(f'DROP FUNCTION {name}()')
    if pg:
        for table in ('ownership_membership', 'access_control_grant'):
            editor.execute(f'DROP TRIGGER access_last_owner ON {table}')
            editor.execute(f'DROP TRIGGER access_owner_lock ON {table}')
        editor.execute('DROP TRIGGER access_web_subject ON access_control_grant')
        for name in ('access_last_owner', 'access_owner_lock', 'access_web_subject'):
            editor.execute(f'DROP FUNCTION {name}()')
        for table, constraint in [('access_control_grant','access_grant_member_fk'), ('access_control_grant','access_grant_cabinet_fk'),
            ('access_control_syntheticrecord','access_record_cabinet_fk'), ('ownership_membership','access_member_org_unique')]:
            editor.execute(f'ALTER TABLE {table} DROP CONSTRAINT {constraint}')
