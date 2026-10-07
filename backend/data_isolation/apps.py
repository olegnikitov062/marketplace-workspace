from django.apps import AppConfig


class DataIsolationConfig(AppConfig):
    name = 'data_isolation'

    def ready(self):
        import os
        profile = os.environ.get('E208_REHEARSAL')
        if profile:
            from django.conf import settings
            from django.db import connection
            from django.core.exceptions import ImproperlyConfigured
            if profile != 'marketplace-e208-20261007-01a1105a-r3' or settings.EFFECTIVE['environment'] != 'beta':
                raise ImproperlyConfigured('Unrecognized isolation rehearsal')
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('cluster_name')")
                if cursor.fetchone() != (profile,):
                    raise ImproperlyConfigured('Isolation rehearsal requires its isolated cluster')
            settings.SECURITY_DOWNLOAD_PROBE = True
