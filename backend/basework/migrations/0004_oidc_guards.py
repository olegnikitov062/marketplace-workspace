"""Защита одноразовой попытки; выдача прав web выполняется отдельно."""
from django.db import migrations
from basework.oidc_sql import GUARD, TRANSITION


def install(apps, editor):
    if editor.connection.vendor == 'sqlite':
        return  # OIDC runtime требует PostgreSQL; SQLite не подтверждает эту защиту.
    if editor.connection.vendor != 'postgresql':
        raise RuntimeError('OIDC требует PostgreSQL')
    with editor.connection.cursor() as cursor:
        cursor.execute('SELECT current_user')
        owner = editor.quote_name(cursor.fetchone()[0])
    editor.execute(GUARD, params=None)
    editor.execute(TRANSITION, params=None)
    editor.execute('REVOKE ALL ON basework_oidcattempt FROM PUBLIC')
    editor.execute('ALTER TABLE basework_oidcattempt ENABLE ROW LEVEL SECURITY')
    editor.execute('ALTER TABLE basework_oidcattempt FORCE ROW LEVEL SECURITY')
    editor.execute(f'CREATE POLICY oidc_operator ON basework_oidcattempt TO {owner} USING (true) WITH CHECK (true)')
    editor.execute("CREATE POLICY oidc_read ON basework_oidcattempt FOR SELECT USING (mw_isolation.claims() IS NOT NULL)")


class Migration(migrations.Migration):
    dependencies = [('basework', '0003_oidc_attempt')]
    operations = [migrations.RunPython(install)]
