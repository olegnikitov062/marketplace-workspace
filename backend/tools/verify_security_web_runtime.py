"""Read-only E2-06 S2 smoke inside the updated beta web; no synthetic user writes."""
import json
import os
from urllib.error import HTTPError
from urllib.request import urlopen

from tools.security_web_grants import MAIN_ROLE, verify_privileges, verify_guards


def main():
    if os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings") != "config.settings":
        raise SystemExit("Only guarded runtime settings are permitted")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    if settings.EFFECTIVE != {
        "environment": "beta", "mode": "web", "DB_HOST": "postgres",
        "DB_PORT": "5432", "DB_NAME": "mw_beta", "DB_USER": MAIN_ROLE,
    }:
        raise SystemExit("Only own beta web is permitted")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(),session_user,current_user")
            if cursor.fetchone() != ("mw_beta", MAIN_ROLE, MAIN_ROLE):
                raise RuntimeError("Unexpected runtime role")
            verify_privileges(cursor, MAIN_ROLE, applied=True)
            verify_guards(cursor, MAIN_ROLE, applied=True)
        for path, status, body in [
            ("/api/v1/health/live", 200, {"status": "ok"}),
            ("/api/v1/health/ready", 200, {"status": "ready"}),
            ("/auth/session", 401, {"authenticated": False}),
            ("/auth/login", 405, None),
            ("/auth/mfa/login/", 200, None),
        ]:
            try:
                response = urlopen("http://127.0.0.1:8000" + path, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                if response.status != status:
                    raise RuntimeError("Unexpected HTTP status")
                if body is not None and json.load(response) != body:
                    raise RuntimeError("Unexpected health/auth result")
    except Exception:
        raise SystemExit("E2-06 S2 runtime smoke failed; no request/credential details emitted") from None
    print("E2-06 S2 PASS: restricted beta web SQL contract, live/ready and anonymous auth denials")


if __name__ == "__main__":
    main()
