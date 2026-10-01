from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection

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
        if not migrated:
            return Response({"status": "not-ready"}, status=503)
    except Exception:
        return Response({"status": "not-ready"}, status=503)
    return Response({"status": "ready"})

urlpatterns = [path("api/v1/health/live", live), path("api/v1/health/ready", ready), path("auth/", include("accounts.urls"))]
