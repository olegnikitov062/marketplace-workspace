from django.db import migrations
from data_isolation.sql import install, uninstall


class Migration(migrations.Migration):
    dependencies = [
        ('access_control', '0002_access_guards'),
        ('sessions', '0001_initial'),
    ]
    operations = [migrations.RunPython(install, uninstall)]
