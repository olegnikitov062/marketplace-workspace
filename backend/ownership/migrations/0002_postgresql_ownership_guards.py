from django.db import migrations

from ownership.migration_operations import PostgreSQLRunSQL


TENANT_TABLES = [
    "ownership_membership", "ownership_legalentity", "ownership_brand",
    "ownership_cabinet", "ownership_sourceconnection", "ownership_cabinetlegalentity",
]
ALL_TABLES = ["ownership_user", "ownership_organization", *TENANT_TABLES]
RELATIONS = [
    ("ownership_sourceconnection", "cabinet_id", "ownership_cabinet", "source_cabinet_org_fk"),
    ("ownership_cabinetlegalentity", "cabinet_id", "ownership_cabinet", "history_cabinet_org_fk"),
    ("ownership_cabinetlegalentity", "legal_entity_id", "ownership_legalentity", "history_legal_org_fk"),
]

FORWARD = [
    f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY (organization_id, {field}) "
    f"REFERENCES {target} (organization_id, id) ON DELETE RESTRICT ON UPDATE RESTRICT"
    for table, field, target, name in RELATIONS
]
FORWARD += ["""
CREATE FUNCTION ownership_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Ownership history must be archived, not deleted' USING ERRCODE = '23514';
END;
$$;
""", """
CREATE FUNCTION ownership_fixed_organization() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN
        RAISE EXCEPTION 'Organization ownership is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
""", """
CREATE FUNCTION ownership_fixed_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.cabinet_id IS DISTINCT FROM OLD.cabinet_id
       OR NEW.legal_entity_id IS DISTINCT FROM OLD.legal_entity_id
       OR NEW.observed_from IS DISTINCT FROM OLD.observed_from
       OR (OLD.observed_until IS NOT NULL AND NEW.observed_until IS DISTINCT FROM OLD.observed_until) THEN
        RAISE EXCEPTION 'Historical attribution is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
"""]
FORWARD += [f"CREATE TRIGGER ownership_no_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION ownership_no_delete()" for table in ALL_TABLES]
FORWARD += [f"CREATE TRIGGER ownership_fixed_org BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION ownership_fixed_organization()" for table in TENANT_TABLES]
FORWARD += ["CREATE TRIGGER ownership_fixed_history BEFORE UPDATE ON ownership_cabinetlegalentity FOR EACH ROW EXECUTE FUNCTION ownership_fixed_history()"]

REVERSE = ["DROP TRIGGER ownership_fixed_history ON ownership_cabinetlegalentity"]
REVERSE += [f"DROP TRIGGER ownership_fixed_org ON {table}" for table in reversed(TENANT_TABLES)]
REVERSE += [f"DROP TRIGGER ownership_no_delete ON {table}" for table in reversed(ALL_TABLES)]
REVERSE += ["DROP FUNCTION ownership_fixed_history()", "DROP FUNCTION ownership_fixed_organization()", "DROP FUNCTION ownership_no_delete()"]
REVERSE += [f"ALTER TABLE {table} DROP CONSTRAINT {name}" for table, field, target, name in reversed(RELATIONS)]


class Migration(migrations.Migration):
    dependencies = [("ownership", "0001_initial")]
    operations = [PostgreSQLRunSQL(FORWARD, REVERSE)]
