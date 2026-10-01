"""E2-06 S1: new isolated DB + non-owner LOGIN role; no main-beta access.

Separately authorized operation, never run by the ordinary test suite.
Passwords live only in memory; existing test databases/roles are never reused.
On error preserve created resources, disable the new role, and print a code only.
"""
import os
from pathlib import Path
import secrets

import psycopg
from psycopg import sql

from tools.security_web_grants import READ_TABLES, TEST_ROLE, apply_fresh as apply, revoke_fresh as revoke, verify_privileges, verify_guards

DATABASE = "mw_beta_test_e2_06_web"


def require_test_environment(effective):
    if effective != {
        "environment": "beta", "mode": "test", "DB_HOST": "postgres-test",
        "DB_PORT": "5432", "DB_NAME": "mw_beta_test", "DB_USER": "mw_beta_test_runner",
    }:
        raise RuntimeError("probe_requires_isolated_beta_test")


def assert_denied(cursor, query, parameters=None):
    cursor.execute("SAVEPOINT denied_probe")
    try:
        cursor.execute(query, parameters)
    except psycopg.errors.InsufficientPrivilege:
        cursor.execute("ROLLBACK TO SAVEPOINT denied_probe")
    else:
        cursor.execute("ROLLBACK TO SAVEPOINT denied_probe")
        raise RuntimeError("unexpected_sql_permission")
    finally:
        cursor.execute("RELEASE SAVEPOINT denied_probe")


def run(settings, connection):
    from django.db.migrations.executor import MigrationExecutor
    from tools.security_role_scenario import seed, run as run_http, operator_action
    from accounts.services import block_account
    require_test_environment(settings.EFFECTIVE)
    if connection.vendor != "postgresql":
        raise RuntimeError("postgresql_required")
    bootstrap_password = Path("/run/secrets/db_test_bootstrap_password").read_text().strip()
    password = secrets.token_urlsafe(48)
    runner_password = connection.settings_dict["PASSWORD"]
    created_role = False
    with psycopg.connect(host="postgres-test", port=5432, dbname="postgres", user="mw_beta_test_bootstrap", password=bootstrap_password, autocommit=True, connect_timeout=5) as admin:
        try:
            # Avoid SQL/error logs containing even the credential verifier.
            admin.execute("SET log_statement = 'none'")
            admin.execute("SET log_min_error_statement = 'panic'")
            if admin.execute("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=%s), EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)", [DATABASE, TEST_ROLE]).fetchone() != (False, False):
                raise RuntimeError("probe_resource_already_exists")
            verifier = admin.pgconn.encrypt_password(password.encode(), TEST_ROLE.encode(), b"scram-sha-256").decode()
            admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(sql.Identifier(TEST_ROLE), sql.Literal(verifier)))
            created_role = True
            admin.execute(sql.SQL("COMMENT ON ROLE {} IS 'marketplace-workspace E2-06 S1 synthetic probe'").format(sql.Identifier(TEST_ROLE)))
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER mw_beta_test_runner").format(sql.Identifier(DATABASE)))
            admin.execute(sql.SQL("COMMENT ON DATABASE {} IS 'marketplace-workspace E2-06 S1 synthetic probe'").format(sql.Identifier(DATABASE)))
            admin.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(DATABASE)))
            admin.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(DATABASE), sql.Identifier(TEST_ROLE)))
            connection.close()
            connection.settings_dict["NAME"] = DATABASE
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            fixture = seed()
            with psycopg.connect(host="postgres-test", port=5432, dbname=DATABASE, user="mw_beta_test_bootstrap", password=bootstrap_password, connect_timeout=5) as setup:
                setup.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
                setup.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(TEST_ROLE)))
                for table in READ_TABLES:
                    setup.execute(sql.SQL("GRANT SELECT ON TABLE public.{} TO {}").format(sql.Identifier(table), sql.Identifier(TEST_ROLE)))
                with setup.cursor() as cursor:
                    apply(cursor, TEST_ROLE)
                    # Exercise rollback on fresh untouched ACL, then reapply.
                    revoke(cursor, TEST_ROLE)
                    apply(cursor, TEST_ROLE)
            # Establish a real restricted LOGIN session, never SET ROLE from an
            # owner session: RESET ROLE cannot recover bootstrap/runner rights.
            def use_role(user, credential):
                connection.close()
                connection.settings_dict.update(USER=user, PASSWORD=credential)

            def operator(action, fixture):
                use_role("mw_beta_test_runner", runner_password)
                try:
                    return operator_action(action, fixture)
                finally:
                    use_role(TEST_ROLE, password)

            use_role(TEST_ROLE, password)
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), session_user, current_user")
                if cursor.fetchone() != (DATABASE, TEST_ROLE, TEST_ROLE):
                    raise RuntimeError("unexpected_application_role")
                verify_privileges(cursor, TEST_ROLE, applied=True)
                verify_guards(cursor, TEST_ROLE, applied=True)
            run_http(fixture, operator=operator)
            # Independent SQL-negative checks on a connection whose session_user
            # is the same non-owner LOGIN role. No statement may escape this DB.
            with psycopg.connect(host="postgres-test", port=5432, dbname=DATABASE, user=TEST_ROLE, password=password, connect_timeout=5) as limited:
                with limited.cursor() as cursor:
                    for query in [
                        "CREATE TABLE public.account_forbidden_probe(id integer)",
                        "CREATE TEMP TABLE account_forbidden_probe(id integer)",
                        "UPDATE ownership_organization SET id=id",
                        "UPDATE ownership_membership SET id=id",
                        "UPDATE ownership_membership SET role=role",
                        "UPDATE ownership_membership SET organization_id=organization_id",
                        "UPDATE ownership_user SET is_active=true",
                        "DELETE FROM ownership_user",
                        "UPDATE ownership_brand SET name=name",
                        "UPDATE django_migrations SET name=name",
                        "TRUNCATE accounts_invitation",
                        "INSERT INTO account_security_recoverypermit(user_id) SELECT id FROM ownership_user",
                        "UPDATE account_security_securityevent SET kind=kind",
                        "UPDATE account_security_authenticator SET key=key",
                        "UPDATE account_security_accountsession SET level=level",
                        "SET ROLE mw_beta_test_runner",
                        "SET ROLE mw_beta_test_bootstrap",
                    ]:
                        assert_denied(cursor, query)
                    cursor.execute("SELECT count(*) FROM pg_database WHERE datallowconn AND datname<>%s AND has_database_privilege(current_user,oid,'CONNECT')", [DATABASE])
                    if cursor.fetchone()[0]:
                        raise RuntimeError("foreign_database_connect")
                    cursor.execute("RESET ROLE")
                    cursor.execute("SELECT session_user,current_user")
                    if cursor.fetchone() != (TEST_ROLE, TEST_ROLE):
                        raise RuntimeError("reset_role_escalation")
        finally:
            connection.close()
            if created_role:
                # Preserve role/DB evidence; remove even its disposable verifier.
                admin.execute(sql.SQL("ALTER ROLE {} NOLOGIN PASSWORD NULL").format(sql.Identifier(TEST_ROLE)))
                if admin.execute("SELECT rolcanlogin, rolpassword IS NULL FROM pg_authid WHERE rolname=%s", [TEST_ROLE]).fetchone() != (False, True):
                    raise RuntimeError("probe_role_not_disabled")
    print("E2-06 S1 PASS: restricted LOGIN role, exact DML, rollback/reapply, HTTP lifecycle/CSRF, SQL denials; probe role disabled")


def main():
    if os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings") != "config.settings":
        raise SystemExit("Only guarded runtime settings are permitted")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    try:
        run(settings, connection)
    except Exception as error:
        # Only technical categories, never exception text/SQL/traceback locals.
        state = getattr(error, "sqlstate", None)
        if not isinstance(state, str) or len(state) != 5 or not state.isalnum():
            state = "none"
        raise SystemExit(f"E2-06 S1 FAIL: {type(error).__name__}; SQLSTATE={state}; preserve resources; no credential/SQL output") from None


if __name__ == "__main__":
    main()
