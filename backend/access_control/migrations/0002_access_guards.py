from django.db import migrations
from access_control.migration_guards import install, uninstall


class Migration(migrations.Migration):
    dependencies = [('access_control', '0001_initial')]
    operations = [migrations.RunPython(install, uninstall)]
