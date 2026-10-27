"""Защита привязок и отзыва; рабочие роли здесь не назначаются."""
from django.db import migrations

TABLES = ('basework_identitybinding', 'basework_federatedsession', 'basework_applicationaccess')


def install(apps, editor):
    pg = editor.connection.vendor == 'postgresql'
    if editor.connection.vendor not in {'sqlite', 'postgresql'}:
        raise RuntimeError('Неподдерживаемая база BaseWork')
    if pg:
        with editor.connection.cursor() as cursor:
            cursor.execute('SELECT current_user')
            owner = editor.quote_name(cursor.fetchone()[0])
        editor.execute("""CREATE FUNCTION basework_no_delete() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          RAISE EXCEPTION 'BaseWork: требуется отзыв вместо удаления' USING ERRCODE='23514';
        END $$""")
        editor.execute('REVOKE ALL ON FUNCTION basework_no_delete() FROM PUBLIC')
    for table in TABLES:
        model = apps.get_model('basework', table.removeprefix('basework_'))
        mutable = [] if table.endswith('federatedsession') else ['revoked_at']
        if pg:
            editor.execute(f"CREATE TRIGGER basework_immutable BEFORE UPDATE ON {table} "
                           f"FOR EACH ROW EXECUTE FUNCTION security_immutable('{','.join(mutable)}')")
            editor.execute(f'CREATE TRIGGER basework_no_delete BEFORE DELETE ON {table} '
                           'FOR EACH ROW EXECUTE FUNCTION basework_no_delete()')
            editor.execute(f'REVOKE ALL ON {table} FROM PUBLIC')
            editor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
            editor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
            editor.execute(f'CREATE POLICY basework_operator ON {table} TO {owner} USING (true) WITH CHECK (true)')
            editor.execute(f"CREATE POLICY basework_read ON {table} FOR SELECT "
                           "USING (mw_isolation.claims() IS NOT NULL)")
        else:
            checks = [f'OLD."{f.column}" IS NOT NEW."{f.column}"' for f in model._meta.fields
                      if f.column not in mutable]
            if mutable:
                checks.append('(OLD.revoked_at IS NOT NULL AND OLD.revoked_at IS NOT NEW.revoked_at)')
            editor.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE ON {table} WHEN {' OR '.join(checks)} "
                           "BEGIN SELECT RAISE(ABORT,'BaseWork: неизменяемая привязка'); END")
            editor.execute(f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
                           "BEGIN SELECT RAISE(ABORT,'BaseWork: требуется отзыв'); END")
    # Сырой отзыв также закрывает старые API; удалить историю отзыва нельзя.
    for table in ('basework_identitybinding', 'basework_applicationaccess'):
        sql = """
          UPDATE account_security_accountsession SET revoked_at=CURRENT_TIMESTAMP
            WHERE user_id=NEW.user_id AND revoked_at IS NULL;
          UPDATE account_security_trusteddevice SET revoked_at=CURRENT_TIMESTAMP
            WHERE user_id=NEW.user_id AND revoked_at IS NULL;
          UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP
            WHERE user_id=NEW.user_id AND revoked_at IS NULL;
        """
        if pg:
            editor.execute(f"CREATE FUNCTION {table}_revoke() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER "
                           f"SET search_path=pg_catalog,public AS $$ BEGIN {sql} RETURN NEW; END $$")
            editor.execute(f'REVOKE ALL ON FUNCTION {table}_revoke() FROM PUBLIC')
            editor.execute(f'CREATE TRIGGER basework_revoke AFTER UPDATE ON {table} FOR EACH ROW '
                           f'WHEN (OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL) EXECUTE FUNCTION {table}_revoke()')
        else:
            editor.execute(f'CREATE TRIGGER {table}_revoke AFTER UPDATE ON {table} '
                           f'WHEN OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL BEGIN {sql} END')
    condition = """NOT EXISTS (SELECT 1 FROM basework_identitybinding b
      JOIN account_security_accountsession s ON s.user_id=b.user_id
      WHERE b.id=NEW.binding_id AND s.id=NEW.session_id
      AND b.revoked_at IS NULL AND s.revoked_at IS NULL AND s.level='full')"""
    if pg:
        editor.execute(f"""CREATE FUNCTION basework_session_binding() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$ BEGIN
          IF {condition} THEN RAISE EXCEPTION 'BaseWork: несовместимая сессия' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $$""")
        editor.execute('REVOKE ALL ON FUNCTION basework_session_binding() FROM PUBLIC')
        editor.execute('CREATE TRIGGER basework_session_binding BEFORE INSERT ON basework_federatedsession '
                       'FOR EACH ROW EXECUTE FUNCTION basework_session_binding()')
    else:
        editor.execute(f'CREATE TRIGGER basework_session_binding BEFORE INSERT ON basework_federatedsession '
                       f"WHEN {condition} BEGIN SELECT RAISE(ABORT,'BaseWork: несовместимая сессия'); END")


class Migration(migrations.Migration):
    dependencies = [('basework', '0001_initial'), ('data_isolation', '0002_financial_operations')]
    # Откат схемы уничтожил бы историю отзыва. Нужна отдельная новая миграция.
    operations = [migrations.RunPython(install)]
