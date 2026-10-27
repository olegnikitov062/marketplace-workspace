"""Render by default; applying/revoking requires separately authorized beta C2."""
import argparse
import os

from tools.account_web_grants import MAIN_ROLE, apply, revoke, grant_statements, revoke_statements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["plan", "apply", "revoke"], default="plan", nargs="?")
    action = parser.parse_args().action
    if action == "plan":
        print("-- APPLY (inside one guarded transaction):")
        print(";\n".join(grant_statements(MAIN_ROLE)) + ";")
        print("-- REVOKE (after old web restored; preserves original SELECT):")
        print(";\n".join(revoke_statements(MAIN_ROLE)) + ";")
        return
    if os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings") != "config.settings":
        raise SystemExit("Only guarded runtime settings are permitted")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection, transaction
    if settings.EFFECTIVE != {
        "environment": "beta", "mode": "migrate", "DB_HOST": "postgres",
        "DB_PORT": "5432", "DB_NAME": "mw_beta", "DB_USER": "mw_beta_migrator",
    }:
        raise SystemExit("Only own beta migrator is permitted")
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), session_user, current_user")
            if cursor.fetchone() != ("mw_beta", "mw_beta_migrator", "mw_beta_migrator"):
                raise RuntimeError("Unexpected database identity")
            cursor.execute("SELECT app,name FROM django_migrations")
            if not {("accounts", "0002_immutable_invitation"), ("ownership", "0002_postgresql_ownership_guards"), ("sessions", "0001_initial")}.issubset(set(cursor.fetchall())):
                raise RuntimeError("Missing required migrations")
            {"apply": apply, "revoke": revoke}[action](cursor, MAIN_ROLE)
    except Exception:
        raise SystemExit("Account web privilege operation refused/rolled back; inspect reviewed preconditions") from None
    print("Account web privilege operation verified and committed")


if __name__ == "__main__":
    main()
