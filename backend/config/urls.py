from django.urls import path
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
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'contenttypes'")
            migrated = cursor.fetchone()[0] == 2
        if not migrated:
            return Response({"status": "not-ready"}, status=503)
    except Exception:
        return Response({"status": "not-ready"}, status=503)
    return Response({"status": "ready"})

urlpatterns = [path("api/v1/health/live", live), path("api/v1/health/ready", ready)]
