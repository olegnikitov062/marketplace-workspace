from django.db import migrations
from account_security.migration_guards import install, uninstall


class Migration(migrations.Migration):
    dependencies = [("account_security", "0001_initial"), ("ownership", "0002_postgresql_ownership_guards"),
                    ("accounts", "0002_immutable_invitation")]
    operations = [migrations.RunPython(install, uninstall)]
