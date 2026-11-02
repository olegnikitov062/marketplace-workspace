"""Отдельное назначение администратора BaseWork и узкие серверные операции."""
import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

from basework.user_admin_sql import FUNCTIONS, SIGNATURES


def install(apps, editor):
    table = 'basework_administrator'
    if editor.connection.vendor == 'postgresql':
        with editor.connection.cursor() as cursor:
            cursor.execute('SELECT current_user')
            owner = editor.quote_name(cursor.fetchone()[0])
        editor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        editor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        editor.execute(f'REVOKE ALL ON {table} FROM PUBLIC')
        editor.execute(f'CREATE POLICY basework_operator ON {table} TO {owner} USING (true) WITH CHECK (true)')
        editor.execute(f'CREATE POLICY basework_read ON {table} FOR SELECT USING (mw_isolation.claims() IS NOT NULL)')
        editor.execute(f"CREATE TRIGGER basework_immutable BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION security_immutable('revoked_at')")
        editor.execute(f'CREATE TRIGGER basework_no_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION basework_no_delete()')
        editor.execute(f'CREATE TRIGGER basework_revoke AFTER UPDATE ON {table} FOR EACH ROW '
                       'WHEN (OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL) EXECUTE FUNCTION basework_applicationaccess_revoke()')
        editor.execute(FUNCTIONS, params=None)
        for signature in SIGNATURES:
            editor.execute(f'REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC')
    elif editor.connection.vendor == 'sqlite':
        editor.execute(f'''CREATE TRIGGER basework_administrator_immutable BEFORE UPDATE ON {table}
          WHEN OLD.id IS NOT NEW.id OR OLD.user_id IS NOT NEW.user_id OR OLD.created_at IS NOT NEW.created_at
          OR (OLD.revoked_at IS NOT NULL AND OLD.revoked_at IS NOT NEW.revoked_at)
          BEGIN SELECT RAISE(ABORT,'BaseWork: неизменяемое назначение'); END''')
        editor.execute(f"CREATE TRIGGER basework_administrator_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'BaseWork: требуется отзыв'); END")
        editor.execute(f'''CREATE TRIGGER basework_administrator_revoke AFTER UPDATE ON {table}
          WHEN OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL BEGIN
          UPDATE account_security_accountsession SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.user_id AND revoked_at IS NULL;
          UPDATE account_security_trusteddevice SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.user_id AND revoked_at IS NULL;
          UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.user_id AND revoked_at IS NULL;
          END''')
    else:
        raise RuntimeError('Неподдерживаемая база BaseWork')


class Migration(migrations.Migration):
    dependencies = [('basework', '0004_oidc_guards')]
    operations = [
        migrations.CreateModel(name='Administrator', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ('revoked_at', models.DateTimeField(blank=True, null=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ownership.user')),
        ], options={'constraints': [models.UniqueConstraint(condition=models.Q(revoked_at__isnull=True), fields=('user',), name='basework_one_administrator')]}),
        migrations.RunPython(install),
    ]
