from django.db import migrations
from ownership.migration_operations import PostgreSQLRunSQL


FORWARD = """
CREATE FUNCTION accounts_fixed_invitation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.membership_id IS DISTINCT FROM OLD.membership_id
       OR NEW.scope_digest IS DISTINCT FROM OLD.scope_digest
       OR NEW.token_hash IS DISTINCT FROM OLD.token_hash
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
       OR (OLD.used_at IS NOT NULL AND NEW.used_at IS DISTINCT FROM OLD.used_at)
       OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at) THEN
        RAISE EXCEPTION 'Invitation identity and terminal states are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER accounts_fixed_invitation BEFORE UPDATE ON accounts_invitation
FOR EACH ROW EXECUTE FUNCTION accounts_fixed_invitation();

CREATE FUNCTION accounts_fixed_contact() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.user_id IS DISTINCT FROM OLD.user_id OR NEW.email IS DISTINCT FROM OLD.email
       OR (OLD.activated_at IS NOT NULL AND NEW.activated_at IS DISTINCT FROM OLD.activated_at) THEN
        RAISE EXCEPTION 'Account enrollment is immutable in E2-05' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER accounts_fixed_contact BEFORE UPDATE ON accounts_accountcontact
FOR EACH ROW EXECUTE FUNCTION accounts_fixed_contact();
"""

REVERSE = """
DROP TRIGGER accounts_fixed_contact ON accounts_accountcontact;
DROP FUNCTION accounts_fixed_contact();
DROP TRIGGER accounts_fixed_invitation ON accounts_invitation;
DROP FUNCTION accounts_fixed_invitation();
"""


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial"), ("ownership", "0002_postgresql_ownership_guards")]
    operations = [PostgreSQLRunSQL(FORWARD, REVERSE)]
