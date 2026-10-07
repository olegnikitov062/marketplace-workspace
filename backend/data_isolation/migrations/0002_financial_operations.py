from django.db import migrations
from data_isolation.financial_sql import install, uninstall


class Migration(migrations.Migration):
    dependencies = [('data_isolation', '0001_statement_and_row_policies'),
                    ('access_control', '0003_financial_schema')]
    operations = [migrations.RunPython(install, uninstall)]
