"""E2-06 combined column privileges; PostgreSQL execution pending. No network/DDL occurs on import.

Only two fixed beta roles. Existing SELECT grants are preserved. Grant/revoke
callers must supply a transaction and an already guarded PostgreSQL connection.
"""
MAIN_ROLE = "mw_beta_web"
TEST_ROLE = "mw_beta_test_e2_06_web"
from tools.account_web_grants import READ_TABLES as ACCOUNT_READ, INSERT as ACCOUNT_INSERT, UPDATE as ACCOUNT_UPDATE

SECURITY_INSERT = {
    "account_security_accountsecurity": ("user_id", "version", "recovery_required"),
    "account_security_loginchallenge": ("id", "user_id", "version", "credential_hash", "expires_at", "used_at"),
    "account_security_authenticator": ("name", "user_id", "confirmed", "created_at", "last_used_at", "throttling_failure_timestamp", "throttling_failure_count", "key", "step", "t0", "digits", "tolerance", "drift", "last_t", "revoked_at", "enrollment_hash", "enrollment_version", "expires_at"),
    "account_security_accountsession": ("id", "user_id", "session_hash", "credential_hash", "version", "level", "authenticator_id", "trusted_device_id", "created_at", "expires_at", "last_seen", "revoked_at", "password_confirmed_at", "factor_confirmed_at"),
    "account_security_trusteddevice": ("id", "user_id", "authenticator_id", "token_hash", "credential_hash", "version", "created_at", "expires_at", "revoked_at"),
    "account_security_recoverycode": ("id", "user_id", "verifier", "created_at", "used_at"),
    "account_security_exportpermit": ("id", "user_id", "organization_id", "session_id", "created_at", "expires_at", "revoked_at"),
    "account_security_securityevent": ("occurred_at", "user_id", "kind"),
}
SECURITY_UPDATE = {
    "account_security_accountsecurity": ("version", "recovery_required"),
    "account_security_loginchallenge": ("used_at",),
    "account_security_authenticator": ("confirmed", "last_t", "drift", "revoked_at", "expires_at", "last_used_at", "throttling_failure_timestamp", "throttling_failure_count"),
    "account_security_accountsession": ("last_seen", "revoked_at", "password_confirmed_at", "factor_confirmed_at"),
    "account_security_trusteddevice": ("revoked_at",),
    "account_security_recoverycode": ("used_at",),
    "account_security_recoverypermit": ("used_at",),
    "account_security_exportpermit": ("revoked_at",),
}
SECURITY_READ = tuple(sorted(set(SECURITY_INSERT) | set(SECURITY_UPDATE)))
READ_TABLES = (*ACCOUNT_READ, *SECURITY_READ)
INSERT = {**ACCOUNT_INSERT, **SECURITY_INSERT}
UPDATE = {**ACCOUNT_UPDATE, **SECURITY_UPDATE}
LOCK_TABLES = ("ownership_organization", "ownership_membership")
FUNCTION = "accounts_web_lock_only"
BODY = """BEGIN
    IF current_user = TG_ARGV[0] THEN
        RAISE EXCEPTION 'Web may lock but not update ownership identity' USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;"""


class ContractError(Exception):
    """Only fixed diagnostic codes, never SQL values/identities/credentials."""


def checked_role(role):
    if role not in {MAIN_ROLE, TEST_ROLE}:
        raise ContractError("unexpected_role")
    return role


def grant_statements(role):
    role = checked_role(role)
    statements = [f"CREATE FUNCTION public.{FUNCTION}() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$\n{BODY}\n$$"]
    for table in LOCK_TABLES:
        statements.append(f"CREATE TRIGGER {FUNCTION} BEFORE UPDATE OF id ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.{FUNCTION}('{role}')")
    for privilege, tables in [("INSERT", INSERT), ("UPDATE", UPDATE)]:
        for table, columns in tables.items():
            statements.append(f"GRANT {privilege} ({', '.join(columns)}) ON TABLE public.{table} TO {role}")
    statements.append(f"GRANT DELETE ON TABLE public.django_session TO {role}")
    return statements


def revoke_statements(role):
    role = checked_role(role)
    statements = [f"REVOKE DELETE ON TABLE public.django_session FROM {role}"]
    for privilege, tables in [("INSERT", INSERT), ("UPDATE", UPDATE)]:
        for table, columns in tables.items():
            statements.append(f"REVOKE {privilege} ({', '.join(columns)}) ON TABLE public.{table} FROM {role}")
    statements.extend(f"DROP TRIGGER {FUNCTION} ON public.{table}" for table in LOCK_TABLES)
    statements.append(f"DROP FUNCTION public.{FUNCTION}()")
    return statements


def verify_privileges(cursor, role, applied):
    role = checked_role(role)
    cursor.execute("SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=%s", [role])
    flags = cursor.fetchone()
    if flags is None or any(flags):
        raise ContractError("unsafe_role_flags")
    cursor.execute("SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)", [role])
    if cursor.fetchone()[0]:
        raise ContractError("role_inherits_other_roles")
    cursor.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=%s)", [role])
    if cursor.fetchone()[0]:
        raise ContractError("web_owns_objects")
    cursor.execute("SELECT has_schema_privilege(%s,'public','CREATE'), has_database_privilege(%s,current_database(),'CREATE')", [role, role])
    if any(cursor.fetchone()):
        raise ContractError("web_can_create_schema")
    cursor.execute("SELECT count(*) FROM pg_database WHERE datallowconn AND datname<>current_database() AND has_database_privilege(%s,oid,'CONNECT')", [role])
    if cursor.fetchone()[0]:
        raise ContractError("web_can_connect_other_database")
    for table in READ_TABLES:
        cursor.execute("SELECT has_table_privilege(%s,%s,'SELECT')", [role, "public." + table])
        if not cursor.fetchone()[0]:
            raise ContractError("missing_required_select")
    cursor.execute("""SELECT c.relname, a.attname,
        has_column_privilege(%s,c.oid,a.attnum,'INSERT'),
        has_column_privilege(%s,c.oid,a.attnum,'UPDATE'),
        has_column_privilege(%s,c.oid,a.attnum,'REFERENCES')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid
        WHERE n.nspname='public' AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped""", [role] * 3)
    for table, column, insert, update, references in cursor.fetchall():
        if (insert != (applied and column in INSERT.get(table, ()))
                or update != (applied and column in UPDATE.get(table, ())) or references):
            raise ContractError("unexpected_column_privileges")
    cursor.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid WHERE n.nspname='public' AND c.relkind IN ('r','p')
        AND a.attnum>0 AND NOT a.attisdropped AND has_column_privilege(%s,c.oid,a.attnum,
        'INSERT WITH GRANT OPTION,UPDATE WITH GRANT OPTION,REFERENCES WITH GRANT OPTION')""", [role])
    if cursor.fetchone()[0]:
        raise ContractError("web_can_delegate_column_privileges")
    cursor.execute("""SELECT c.relname,
        has_table_privilege(%s,c.oid,'DELETE'),
        has_table_privilege(%s,c.oid,'TRUNCATE,TRIGGER,MAINTAIN')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p')""", [role] * 2)
    for table, delete, other in cursor.fetchall():
        if delete != (applied and table == "django_session") or other:
            raise ContractError("unexpected_table_privileges")
    cursor.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p') AND has_table_privilege(%s,c.oid,
        'DELETE WITH GRANT OPTION,TRUNCATE WITH GRANT OPTION,TRIGGER WITH GRANT OPTION,MAINTAIN WITH GRANT OPTION')""", [role])
    if cursor.fetchone()[0]:
        raise ContractError("web_can_delegate_table_privileges")
    if sequence_access_count(cursor, role):
        raise ContractError("unexpected_sequence_privileges")


def sequence_access_count(cursor, role):
    # WHERE conjuncts can be reordered; CASE prevents evaluation on TOAST/tables.
    cursor.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND CASE WHEN c.relkind='S'
        THEN has_sequence_privilege(%s,c.oid,'USAGE,SELECT,UPDATE') ELSE false END""", [role])
    return cursor.fetchone()[0]


def verify_guards(cursor, role, applied):
    cursor.execute("SELECT prosrc, prosecdef FROM pg_proc WHERE oid=to_regprocedure('public.accounts_web_lock_only()')")
    function = cursor.fetchone()
    cursor.execute("""SELECT c.relname, t.tgargs, t.tgtype, t.tgenabled, p.proname,
        ARRAY(SELECT a.attname FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum=ANY(t.tgattr::smallint[]))
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND t.tgname='accounts_web_lock_only' ORDER BY c.relname""")
    triggers = cursor.fetchall()
    if not applied:
        if function is not None or triggers:
            raise ContractError("guard_objects_already_exist")
        return
    if function is None or function[0].strip() != BODY or function[1]:
        raise ContractError("guard_definition_changed")
    if {row[0] for row in triggers} != set(LOCK_TABLES):
        raise ContractError("guard_triggers_changed")
    for _, arguments, flags, enabled, function_name, columns in triggers:
        if (bytes(arguments) != (role + "\0").encode() or flags != 19 or enabled != "O"
                or function_name != FUNCTION or columns != ["id"]):
            raise ContractError("guard_trigger_definition_changed")


def apply_fresh(cursor, role):
    verify_privileges(cursor, role, applied=False)
    verify_guards(cursor, role, applied=False)
    cursor.execute("SELECT attidentity FROM pg_attribute WHERE attrelid='public.accounts_authdenial'::regclass AND attname='id'")
    if cursor.fetchone() != ("d",):
        raise ContractError("audit_requires_django_identity_column")
    for statement in grant_statements(role):
        cursor.execute(statement)
    verify_privileges(cursor, role, applied=True)
    verify_guards(cursor, role, applied=True)


def revoke_fresh(cursor, role):
    # Refuse to erase later or broader grants/changed trigger definitions.
    verify_privileges(cursor, role, applied=True)
    verify_guards(cursor, role, applied=True)
    for statement in revoke_statements(role):
        cursor.execute(statement)
    verify_privileges(cursor, role, applied=False)
    verify_guards(cursor, role, applied=False)


def delta_statements(role, revoke=False):
    role = checked_role(role)
    verb, preposition = ("REVOKE", "FROM") if revoke else ("GRANT", "TO")
    for privilege, mapping in [("INSERT", SECURITY_INSERT), ("UPDATE", SECURITY_UPDATE)]:
        for table, columns in mapping.items():
            yield f"{verb} {privilege} ({', '.join(columns)}) ON TABLE public.{table} {preposition} {role}"


def upgrade_main(cursor):
    from tools import account_web_grants as previous
    previous.verify_privileges(cursor, MAIN_ROLE, applied=True)
    previous.verify_guards(cursor, MAIN_ROLE, applied=True)
    # Main E2-05 default SELECT grants must already cover added tables. Refuse
    # instead of silently broadening them or overwriting a later policy.
    for table in SECURITY_READ:
        cursor.execute("SELECT has_table_privilege(%s,%s,'SELECT')", [MAIN_ROLE, "public." + table])
        if not cursor.fetchone()[0]:
            raise ContractError("missing_security_select_review_acl")
    for sql in delta_statements(MAIN_ROLE):
        cursor.execute(sql)
    verify_privileges(cursor, MAIN_ROLE, applied=True)
    verify_guards(cursor, MAIN_ROLE, applied=True)


def rollback_main_delta(cursor):
    from tools import account_web_grants as previous
    verify_privileges(cursor, MAIN_ROLE, applied=True)
    verify_guards(cursor, MAIN_ROLE, applied=True)
    for sql in delta_statements(MAIN_ROLE, revoke=True):
        cursor.execute(sql)
    previous.verify_privileges(cursor, MAIN_ROLE, applied=True)
    previous.verify_guards(cursor, MAIN_ROLE, applied=True)
