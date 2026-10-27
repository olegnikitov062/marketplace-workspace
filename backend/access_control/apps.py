import os

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class AccessControlConfig(AppConfig):
    name = 'access_control'

    def ready(self):
        # An explicitly named, separately provisioned synthetic cluster only.
        # Normal beta runtime never enables the probe from this branch.
        profile = os.environ.get('E207_REHEARSAL')
        if profile:
            from django.conf import settings
            from django.db import connection
            if profile != 'marketplace-e207-20261005-01a10b2d' or settings.EFFECTIVE['environment'] != 'beta':
                raise ImproperlyConfigured('Unrecognized access rehearsal')
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('cluster_name')")
                if cursor.fetchone() != (profile,):
                    raise ImproperlyConfigured('Access rehearsal requires its isolated cluster')
            settings.SECURITY_DOWNLOAD_PROBE = True
