"""Runs only as a one-shot administrator of a fresh, isolated own DB."""
import os
from pathlib import Path
import psycopg
from psycopg import sql
name = os.environ["ENVIRONMENT"]
if name not in {"local", "beta"}:
    raise SystemExit("Only local/beta provisioning is authorized")
test = os.environ.get("TARGET_TEST", "false") == "true"
prefix = "mw_" + name
host = "postgres-test" if test else "postgres"
database = prefix + "_test" if test else prefix
bootstrap = prefix + ("_test_bootstrap" if test else "_bootstrap")
admin_secret = "db_test_bootstrap_password" if test else "db_bootstrap_password"
password = Path("/run/secrets/"+admin_secret).read_text().strip()
roles = {prefix+"_test_runner":"db_test_runner_password"} if test else {prefix+"_migrator":"db_migrator_password", prefix+"_web":"db_web_password"}
with psycopg.connect(host=host,dbname=database,user=bootstrap,password=password,autocommit=True,connect_timeout=5) as conn:
    conn.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
    conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    conn.execute("REVOKE CONNECT ON DATABASE postgres FROM PUBLIC")
    conn.execute("REVOKE CONNECT ON DATABASE template1 FROM PUBLIC")
    for role, secret in roles.items():
        if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(role,)).fetchone():
            raise SystemExit("Role already exists; do not overwrite credentials or privileges")
        value=Path("/run/secrets/"+secret).read_text().strip()
        conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEROLE NOREPLICATION NOBYPASSRLS {} PASSWORD {}").format(sql.Identifier(role),sql.SQL("CREATEDB" if test else "NOCREATEDB"),sql.Literal(value)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database),sql.Identifier(role)))
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
    owner=prefix+("_test_runner" if test else "_migrator")
    conn.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(owner)))
    if test:
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE postgres TO {}").format(sql.Identifier(owner)))
    if not test:
        conn.execute(sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT SELECT ON TABLES TO {}").format(sql.Identifier(owner),sql.Identifier(prefix+"_web")))
print("Own database roles provisioned; credentials are not printed")
