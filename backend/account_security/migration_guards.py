"""Database invariants; SQLite checks remain explicitly separate from PostgreSQL proof."""
MUTABLE = {
    "accountsecurity": ["version", "recovery_required"],
    "accountsession": ["last_seen", "revoked_at", "password_confirmed_at", "factor_confirmed_at"],
    "authenticator": ["confirmed", "last_t", "drift", "revoked_at", "expires_at", "last_used_at",
                      "throttling_failure_timestamp", "throttling_failure_count"],
    "trusteddevice": ["revoked_at"],
    "recoverycode": ["used_at"],
    "recoverypermit": ["used_at"],
    "exportpermit": ["revoked_at"],
    "loginchallenge": ["used_at"],
    "securityevent": [],
}


def install(apps, schema_editor):
    conn = schema_editor.connection
    pg = conn.vendor == "postgresql"
    if conn.vendor not in {"postgresql", "sqlite"}:
        raise RuntimeError("Unsupported security database")
    if pg:
        schema_editor.execute("""CREATE FUNCTION security_immutable() RETURNS trigger
        LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN
          IF (to_jsonb(NEW)-string_to_array(TG_ARGV[0],',')) IS DISTINCT FROM
             (to_jsonb(OLD)-string_to_array(TG_ARGV[0],','))
             OR (to_jsonb(OLD)->>'revoked_at' IS NOT NULL AND
                 to_jsonb(OLD)->>'revoked_at' IS DISTINCT FROM to_jsonb(NEW)->>'revoked_at')
             OR (to_jsonb(OLD)->>'used_at' IS NOT NULL AND
                 to_jsonb(OLD)->>'used_at' IS DISTINCT FROM to_jsonb(NEW)->>'used_at')
             OR (TG_TABLE_NAME='account_security_accountsecurity' AND
                 (to_jsonb(NEW)->>'version')::bigint < (to_jsonb(OLD)->>'version')::bigint)
             OR (TG_TABLE_NAME='account_security_authenticator' AND
                 (to_jsonb(NEW)->>'last_t')::bigint < (to_jsonb(OLD)->>'last_t')::bigint)
          THEN RAISE EXCEPTION 'Security state is immutable' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $$""")
    for model_name, mutable in MUTABLE.items():
        model = apps.get_model("account_security", model_name)
        table = model._meta.db_table
        if pg:
            columns = ",".join(mutable)
            schema_editor.execute(f"CREATE TRIGGER security_immutable BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION security_immutable('{columns}')")
        else:
            checks = [f'OLD."{f.column}" IS NOT NEW."{f.column}"' for f in model._meta.fields if f.column not in mutable]
            for name in ["used_at", "revoked_at"]:
                if name in mutable:
                    checks.append(f'(OLD.{name} IS NOT NULL AND OLD.{name} IS NOT NEW.{name})')
            if model_name == "accountsecurity":
                checks.append("NEW.version < OLD.version")
            if model_name == "authenticator":
                checks.append("NEW.last_t < OLD.last_t")
            condition = " OR ".join(checks)
            schema_editor.execute(f"CREATE TRIGGER security_immutable_{model_name} BEFORE UPDATE ON {table} WHEN {condition} BEGIN SELECT RAISE(ABORT,'Security state is immutable'); END")
    # Live membership/organization changes permanently revoke issued links, including raw UPDATE.
    for table, fields, scope in [
        ("ownership_membership", ["role", "state", "archived_at"], "user_id=OLD.user_id AND organization_id=OLD.organization_id"),
        ("ownership_organization", ["archived_at"], "organization_id=OLD.id"),
    ]:
        name = "security_links_" + table
        condition = " OR ".join(f"OLD.{field} IS DISTINCT FROM NEW.{field}" if pg else f"OLD.{field} IS NOT NEW.{field}" for field in fields)
        statement = f"UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP WHERE revoked_at IS NULL AND {scope};"
        if pg:
            schema_editor.execute(f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN {statement} RETURN NEW; END $$")
            schema_editor.execute(f"CREATE TRIGGER {name} AFTER UPDATE ON {table} FOR EACH ROW WHEN ({condition}) EXECUTE FUNCTION {name}()")
        else:
            schema_editor.execute(f"CREATE TRIGGER {name} AFTER UPDATE ON {table} WHEN {condition} BEGIN {statement} END")
    statements = """UPDATE account_security_accountsecurity SET version=version+1 WHERE user_id=NEW.id;
      UPDATE account_security_accountsession SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.id AND revoked_at IS NULL;
      UPDATE account_security_trusteddevice SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.id AND revoked_at IS NULL;
      UPDATE account_security_exportpermit SET revoked_at=CURRENT_TIMESTAMP WHERE user_id=NEW.id AND revoked_at IS NULL;"""
    condition = " OR ".join(f"OLD.{f} IS DISTINCT FROM NEW.{f}" if pg else f"OLD.{f} IS NOT NEW.{f}" for f in ["password", "is_active", "archived_at"])
    if pg:
        schema_editor.execute(f"CREATE FUNCTION security_user_revoked() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$ BEGIN {statements} RETURN NEW; END $$")
        schema_editor.execute(f"CREATE TRIGGER security_user_revoked AFTER UPDATE ON ownership_user FOR EACH ROW WHEN ({condition}) EXECUTE FUNCTION security_user_revoked()")
    else:
        schema_editor.execute(f"CREATE TRIGGER security_user_revoked AFTER UPDATE ON ownership_user WHEN {condition} BEGIN {statements} END")


def uninstall(apps, schema_editor):
    pg = schema_editor.connection.vendor == "postgresql"
    for model_name in MUTABLE:
        table = apps.get_model("account_security", model_name)._meta.db_table
        sql = f"DROP TRIGGER security_immutable ON {table}" if pg else f"DROP TRIGGER security_immutable_{model_name}"
        schema_editor.execute(sql)
    if pg:
        schema_editor.execute("DROP FUNCTION security_immutable()")
    for table, name in [("ownership_membership", "security_links_ownership_membership"),
                        ("ownership_organization", "security_links_ownership_organization"),
                        ("ownership_user", "security_user_revoked")]:
        schema_editor.execute(f"DROP TRIGGER {name} ON {table}" if pg else f"DROP TRIGGER {name}")
        if pg:
            schema_editor.execute(f"DROP FUNCTION {name}()")
