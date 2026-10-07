from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from django.conf import settings

@api_view(["GET"])
def live(request):
    return Response({"status": "ok"})

@api_view(["GET"])
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.execute("SELECT app, name FROM django_migrations")
            migrated = {
                ("contenttypes", "0002_remove_content_type_name"),
                ("ownership", "0002_postgresql_ownership_guards"),
                ("accounts", "0002_immutable_invitation"),
                ("sessions", "0001_initial"),
            }.issubset(set(cursor.fetchall()))
        if getattr(settings, "ACCESS_CONTROL_ENABLED", False):
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM django_migrations WHERE app='access_control' AND name='0002_access_guards'")
                migrated = migrated and cursor.fetchone()[0] == 1
        if not migrated:
            return Response({"status": "not-ready"}, status=503)
        if getattr(settings, 'ISOLATION_ENABLED', False) and connection.vendor == 'postgresql':
            from data_isolation.sql import TABLES
            with connection.cursor() as cursor:
                cursor.execute('SELECT mw_isolation.claims() IS NOT NULL')
                if cursor.fetchone() != (True,):
                    return Response({'status': 'not-ready'}, status=503)
                cursor.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                               "WHERE n.nspname='public' AND c.relname=ANY(%s) AND c.relrowsecurity AND c.relforcerowsecurity", [list(TABLES)])
                if cursor.fetchone()[0] != len(TABLES):
                    return Response({'status': 'not-ready'}, status=503)
                cursor.execute("SELECT count(*) FROM django_migrations WHERE app='data_isolation' AND name='0002_financial_operations'")
                if cursor.fetchone() != (1,):
                    return Response({'status': 'not-ready'}, status=503)
                from tools.financial_web_contract import verify as verify_finance
                verify_finance(cursor)
        if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
            from account_security.crypto import cipher
            from account_security.models import Authenticator
            cipher()
            # Detect a valid-format but wrong key against existing encrypted data.
            Authenticator.objects.only("key").first()
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM django_migrations WHERE app='account_security' AND name='0002_revocation_guards'")
                if cursor.fetchone()[0] != 1:
                    return Response({"status": "not-ready"}, status=503)
    except Exception:
        return Response({"status": "not-ready"}, status=503)
    return Response({"status": "ready"})

urlpatterns = [path("api/v1/health/live", live), path("api/v1/health/ready", ready), path("auth/", include("accounts.urls"))]
if getattr(settings, "ACCOUNT_SECURITY_ENABLED", False):
    urlpatterns.append(path("auth/", include("account_security.urls")))

if getattr(settings, "ACCESS_CONTROL_ENABLED", False):
    urlpatterns.append(path("api/v1/access/", include("access_control.urls")))
