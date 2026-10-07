from django.apps import AppConfig


class DataIsolationConfig(AppConfig):
    name = 'data_isolation'

    def ready(self):
        import os
        financial = os.environ.get('E209_REHEARSAL')
        if financial and os.environ.get('E208_REHEARSAL'):
            raise RuntimeError('Conflicting rehearsal profiles')
        profile = financial or os.environ.get('E208_REHEARSAL')
        if profile:
            from django.conf import settings
            from django.db import connection
            from django.core.exceptions import ImproperlyConfigured
            expected = 'marketplace-e209-20261007-01a115d9-r3' if financial else 'marketplace-e208-20261007-01a1105a-r4'
            if profile != expected or settings.EFFECTIVE['environment'] != 'beta':
                raise ImproperlyConfigured('Unrecognized isolation rehearsal')
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('cluster_name')")
                if cursor.fetchone() != (profile,):
                    raise ImproperlyConfigured('Isolation rehearsal requires its isolated cluster')
            settings.SECURITY_DOWNLOAD_PROBE = True
