import os
from django.db import connection
import psycopg
from config.guard import secret
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
import django
django.setup()
with connection.cursor() as cursor:
    cursor.execute("SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=current_user")
    if any(cursor.fetchone()): raise SystemExit("Web role is overprivileged")
    cursor.execute("SELECT pg_has_role(current_user,'mw_beta_migrator','MEMBER')")
    if cursor.fetchone()[0]:raise SystemExit("Web inherits migration privileges")
try:
    with connection.cursor() as cursor:cursor.execute("CREATE TABLE forbidden_probe(id integer)")
except Exception:
    connection.close()
else:raise SystemExit("Web can create schema objects")
try:
    psycopg.connect(host="postgres",dbname="postgres",user="mw_beta_web",password=secret(os.environ["DB_PASSWORD_FILE"]),connect_timeout=3)
except psycopg.OperationalError:
    pass
else:raise SystemExit("Web can connect to system database")
print("Web role flags, migration membership, DDL denial, system DB CONNECT denial passed")
