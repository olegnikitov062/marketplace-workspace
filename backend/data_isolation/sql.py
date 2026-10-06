"""PostgreSQL-only policy DDL. No extensions, role creation or key generation.

Control-plane SQL is admitted only as an exact application-signed statement.
Synthetic records additionally require live row-level scope/action authorization.
The migrator and fixed SECURITY DEFINER implementation are trusted operators.
"""
CONTROL_TABLES = (
    'ownership_user', 'ownership_organization', 'ownership_membership', 'ownership_cabinet',
    'accounts_accountcontact', 'accounts_invitation', 'accounts_attemptbucket', 'accounts_authdenial',
    'django_session',
    'account_security_accountsecurity', 'account_security_loginchallenge',
    'account_security_authenticator', 'account_security_trusteddevice',
    'account_security_accountsession', 'account_security_recoverycode',
    'account_security_recoverypermit', 'account_security_exportpermit', 'account_security_securityevent',
    'access_control_platformroleassignment', 'access_control_grant',
    'access_control_supportwindow', 'access_control_exportbinding',
)
DENIED_TABLES = ('ownership_legalentity', 'ownership_brand',
                 'ownership_sourceconnection', 'ownership_cabinetlegalentity')
RECORD_TABLE = 'access_control_syntheticrecord'
TABLES = (*CONTROL_TABLES, *DENIED_TABLES, RECORD_TABLE)
TRUSTED_TRIGGERS = (
    'security_links_ownership_membership', 'security_links_ownership_organization',
    'security_user_revoked', 'access_revoke_grant', 'access_revoke_member',
    'access_revoke_org', 'access_revoke_cabinet', 'access_revoke_platform',
    'access_revoke_record', 'access_owner_lock', 'access_last_owner',
)

FUNCTIONS = r"""
CREATE FUNCTION mw_isolation.hmac(message text, secret bytea) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog AS $$
DECLARE inner_pad bytea := decode(repeat('36',64),'hex');
        outer_pad bytea := decode(repeat('5c',64),'hex'); i integer;
BEGIN
  IF octet_length(secret)<>32 THEN RETURN NULL; END IF;
  FOR i IN 0..31 LOOP
    inner_pad := set_byte(inner_pad,i,get_byte(inner_pad,i) # get_byte(secret,i));
    outer_pad := set_byte(outer_pad,i,get_byte(outer_pad,i) # get_byte(secret,i));
  END LOOP;
  RETURN encode(sha256(outer_pad || sha256(inner_pad || convert_to(message,'UTF8'))),'hex');
END $$;

CREATE FUNCTION mw_isolation.claims() RETURNS jsonb LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,mw_isolation AS $$
DECLARE p text; s text; c jsonb; k bytea; expected text; difference integer := 0; i integer;
BEGIN
  p := current_setting('mw.isolation_payload',true);
  s := current_setting('mw.isolation_signature',true);
  IF p IS NULL OR length(p)>4096 OR s IS NULL OR length(s)<>64 THEN RETURN NULL; END IF;
  SELECT secret INTO k FROM mw_isolation.key WHERE singleton;
  IF k IS NULL THEN RETURN NULL; END IF;
  expected := mw_isolation.hmac(p,k);
  FOR i IN 1..64 LOOP
    difference := difference | (ascii(substr(s,i,1)) # ascii(substr(expected,i,1)));
  END LOOP;
  IF difference<>0 THEN RETURN NULL; END IF;
  c := p::jsonb;
  IF (c->>'pid')::integer<>pg_backend_pid() OR c->>'xid'<>txid_current()::text
     OR c->>'database'<>current_database() OR c->>'role'<>session_user
     OR (c->>'expires')::bigint < extract(epoch FROM clock_timestamp())
     OR (c->>'expires')::bigint > extract(epoch FROM clock_timestamp())+15
     OR c->>'statement'<>encode(sha256(convert_to(current_query(),'UTF8')),'hex')
     OR c->>'kind' NOT IN ('control','record') THEN RETURN NULL; END IF;
  IF NOT (c ?& ARRAY['pid','xid','database','role','expires','statement','kind','request'])
     THEN RETURN NULL; END IF;
  RETURN c;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN NULL;
END $$;

CREATE FUNCTION mw_isolation.record_allowed(r jsonb, operation text, c jsonb)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid; sid uuid; org uuid; cab uuid; requested_action text; at_time timestamptz := clock_timestamp();
BEGIN
  IF c->>'kind'<>'record' OR c->>'resource'<>'synthetic_record' THEN RETURN false; END IF;
  actor := (c->>'user')::uuid; sid := (c->>'session')::uuid;
  org := (c->>'organization')::uuid; cab := (c->>'cabinet')::uuid; requested_action := c->>'action';
  IF actor IS NULL OR sid IS NULL OR org IS NULL OR cab IS NULL OR requested_action IS NULL
    OR requested_action NOT IN ('view','export','change') OR operation NOT IN ('select','update')
    OR (operation='update' AND requested_action<>'change')
    OR r->>'organization_id'<>org::text OR r->>'cabinet_id'<>cab::text
    OR r->>'archived_at' IS NOT NULL THEN RETURN false; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.ownership_cabinet b JOIN public.ownership_organization o
      ON o.id=b.organization_id WHERE b.id=cab AND o.id=org
      AND b.archived_at IS NULL AND o.archived_at IS NULL) THEN RETURN false; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.account_security_accountsession s
      JOIN public.ownership_user u ON u.id=s.user_id
      JOIN public.account_security_accountsecurity st ON st.user_id=u.id
      WHERE s.id=sid AND u.id=actor AND u.is_active AND u.archived_at IS NULL
      AND u.password NOT LIKE '!%' AND s.level='full' AND s.revoked_at IS NULL
      AND s.version=st.version AND NOT st.recovery_required
      AND s.expires_at>at_time AND s.last_seen>at_time-interval '1 hour'
      AND NOT EXISTS(SELECT 1 FROM public.accounts_accountcontact ct
                     WHERE ct.user_id=u.id AND ct.activated_at IS NULL)
      AND (s.authenticator_id IS NULL OR EXISTS(SELECT 1 FROM public.account_security_authenticator a
           WHERE a.id=s.authenticator_id AND a.user_id=u.id AND a.confirmed AND a.revoked_at IS NULL))
      AND (s.trusted_device_id IS NULL OR EXISTS(SELECT 1 FROM public.account_security_trusteddevice d
           JOIN public.account_security_authenticator a ON a.id=d.authenticator_id
           WHERE d.id=s.trusted_device_id AND d.user_id=u.id AND d.revoked_at IS NULL
           AND d.version=st.version AND d.credential_hash=s.credential_hash AND d.expires_at>at_time
           AND a.user_id=u.id AND a.confirmed AND a.revoked_at IS NULL))
      AND (s.authenticator_id IS NOT NULL OR NOT (
           EXISTS(SELECT 1 FROM public.ownership_membership m JOIN public.ownership_organization o
                  ON o.id=m.organization_id WHERE m.user_id=u.id AND m.role='owner'
                  AND m.state='active' AND m.archived_at IS NULL AND o.archived_at IS NULL)
           OR EXISTS(SELECT 1 FROM public.account_security_authenticator a
                     WHERE a.user_id=u.id AND a.confirmed AND a.revoked_at IS NULL)
           OR EXISTS(SELECT 1 FROM public.access_control_platformroleassignment p
                     WHERE p.user_id=u.id AND p.revoked_at IS NULL)))) THEN RETURN false; END IF;
  RETURN EXISTS(SELECT 1 FROM public.access_control_grant g
    JOIN public.ownership_membership m ON m.id=g.membership_id
    WHERE g.organization_id=org AND m.organization_id=org AND m.user_id=actor
      AND m.state='active' AND m.archived_at IS NULL AND g.revoked_at IS NULL
      AND g.resource='synthetic_record' AND g.action=requested_action
      AND (g.cabinet_id IS NULL OR g.cabinet_id=cab)
      AND NOT EXISTS(SELECT 1 FROM public.access_control_platformroleassignment p
                     WHERE p.user_id=actor AND p.revoked_at IS NULL))
    OR (requested_action='view' AND EXISTS(SELECT 1 FROM public.access_control_grant g
      JOIN public.access_control_platformroleassignment p ON p.id=g.platform_id
      JOIN public.access_control_supportwindow w ON w.grant_id=g.id
      JOIN public.account_security_accountsession s ON s.id=w.session_id
      WHERE p.user_id=actor AND p.revoked_at IS NULL AND g.revoked_at IS NULL
        AND g.organization_id=org AND (g.cabinet_id IS NULL OR g.cabinet_id=cab)
        AND g.resource='synthetic_record' AND g.action='view'
        AND w.session_id=sid AND w.revoked_at IS NULL AND w.expires_at>at_time
        AND s.created_at>at_time-interval '4 hours' AND s.last_seen>at_time-interval '15 minutes'
        AND NOT EXISTS(SELECT 1 FROM public.ownership_membership m WHERE m.user_id=actor)));
EXCEPTION WHEN invalid_text_representation THEN RETURN false;
END $$;

CREATE FUNCTION mw_isolation.allowed(table_name text, row_data jsonb, operation text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mw_isolation AS $$
DECLARE c jsonb; org uuid; actor uuid; row_org uuid;
BEGIN
  c := mw_isolation.claims();
  IF c IS NULL THEN RETURN false; END IF;
  IF table_name='access_control_syntheticrecord' THEN
    RETURN mw_isolation.record_allowed(row_data,operation,c);
  END IF;
  IF c ? 'organization' THEN
    org := (c->>'organization')::uuid;
    actor := (c->>'user')::uuid;
    IF org IS NULL OR actor IS NULL THEN RETURN false; END IF;
    IF table_name='ownership_organization' THEN
      row_org := (row_data->>'id')::uuid;
      -- A personal identity can discover its own memberships and determine
      -- whether MFA is mandatory in another organization before choosing one.
      IF operation='select' AND EXISTS(SELECT 1 FROM public.ownership_membership m
          WHERE m.organization_id=row_org AND m.user_id=actor) THEN RETURN true; END IF;
    ELSIF table_name='ownership_membership' THEN
      IF operation='select' AND row_data->>'user_id'=actor::text THEN RETURN true; END IF;
      row_org := (row_data->>'organization_id')::uuid;
    ELSIF table_name IN ('ownership_cabinet','access_control_grant','account_security_exportpermit') THEN
      row_org := (row_data->>'organization_id')::uuid;
    ELSIF table_name='accounts_invitation' THEN
      SELECT organization_id INTO row_org FROM public.ownership_membership
        WHERE id=(row_data->>'membership_id')::uuid;
    ELSIF table_name='access_control_supportwindow' THEN
      SELECT organization_id INTO row_org FROM public.access_control_grant
        WHERE id=(row_data->>'grant_id')::uuid;
    ELSIF table_name='access_control_exportbinding' THEN
      SELECT organization_id INTO row_org FROM public.account_security_exportpermit
        WHERE id=(row_data->>'permit_id')::uuid;
    ELSE
      RETURN true;
    END IF;
    RETURN row_org IS NOT NULL AND row_org=org;
  END IF;
  -- The exact signed control-plane statement supplies the predicate, including
  -- pre-login authentication and fixed cascading revocations. No arbitrary
  -- SQL query can reuse that capability to enumerate a different row set.
  RETURN true;
EXCEPTION WHEN invalid_text_representation THEN RETURN false;
END $$;

CREATE FUNCTION mw_isolation.export_cabinet(permit uuid, actor uuid, requested_session uuid)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE result uuid;
BEGIN
  IF mw_isolation.claims() IS NULL THEN RETURN NULL; END IF;
  SELECT r.cabinet_id INTO result FROM public.account_security_exportpermit p
    JOIN public.access_control_exportbinding b ON b.permit_id=p.id
    JOIN public.access_control_syntheticrecord r ON r.id=b.record_id
    WHERE p.id=permit AND p.user_id=actor AND p.session_id=requested_session
      AND p.revoked_at IS NULL AND p.expires_at>clock_timestamp();
  RETURN result;
END $$;
"""


def install(apps, editor):
    if editor.connection.vendor == 'sqlite':
        return  # Explicit offline tests only, never an RLS emulation.
    if editor.connection.vendor != 'postgresql':
        raise RuntimeError('Isolation requires PostgreSQL')
    with editor.connection.cursor() as cursor:
        cursor.execute('SELECT current_user')
        owner = editor.quote_name(cursor.fetchone()[0])
        cursor.execute("SELECT nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user) FROM pg_namespace WHERE nspname='mw_isolation'")
        existing = cursor.fetchone()
        if existing is not None:
            cursor.execute("SELECT (SELECT count(*) FROM pg_class WHERE relnamespace='mw_isolation'::regnamespace) + "
                           "(SELECT count(*) FROM pg_proc WHERE pronamespace='mw_isolation'::regnamespace)")
            if existing != (True,) or cursor.fetchone() != (0,):
                raise RuntimeError('Isolation schema is not a fresh operator-owned schema')
            cursor.execute("SELECT count(*) FROM pg_namespace n, LATERAL aclexplode(COALESCE(n.nspacl,acldefault('n',n.nspowner))) a "
                           "WHERE n.nspname='mw_isolation' AND a.grantee<>n.nspowner")
            if cursor.fetchone() != (0,):
                raise RuntimeError('Unexpected isolation schema privileges')
    if existing is None:
        editor.execute('CREATE SCHEMA mw_isolation')
    editor.execute('REVOKE ALL ON SCHEMA mw_isolation FROM PUBLIC')
    editor.execute('CREATE TABLE mw_isolation.key (singleton boolean PRIMARY KEY CHECK(singleton), secret bytea NOT NULL CHECK(octet_length(secret)=32))')
    editor.execute('REVOKE ALL ON mw_isolation.key FROM PUBLIC')
    editor.execute(FUNCTIONS, params=None)
    editor.execute('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA mw_isolation FROM PUBLIC')
    # Deferred checks run at COMMIT, outside the original signed statement.
    # Fixed trigger-only routines must see the complete invariant/revocation
    # set. Never elevate accounts_web_lock_only or access_web_subject: their
    # invoker identity is itself a required privilege boundary.
    for name in TRUSTED_TRIGGERS:
        editor.execute(f'ALTER FUNCTION public.{name}() SECURITY DEFINER')
        editor.execute(f'ALTER FUNCTION public.{name}() SET search_path=pg_catalog,public')
        editor.execute(f'REVOKE ALL ON FUNCTION public.{name}() FROM PUBLIC')
    for table in TABLES:
        editor.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY')
        editor.execute(f'ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY')
        editor.execute(f'CREATE POLICY isolation_operator ON public.{table} TO {owner} USING (true) WITH CHECK (true)')
        if table in DENIED_TABLES:
            continue
        for op in ('select', 'insert', 'update', 'delete'):
            expression = f"mw_isolation.allowed('{table}',to_jsonb({table}),'{op}')"
            clauses = f'WITH CHECK ({expression})' if op == 'insert' else f'USING ({expression})'
            if op == 'update':
                clauses += f' WITH CHECK ({expression})'
            editor.execute(f'CREATE POLICY isolation_{op} ON public.{table} FOR {op.upper()} {clauses}')


def uninstall(apps, editor):
    if editor.connection.vendor == 'sqlite':
        return
    # Rollback removes the security boundary. Require the separately prepared,
    # empty isolated test schema; never quietly downgrade a populated database.
    with editor.connection.cursor() as cursor:
        cursor.execute('SELECT EXISTS(SELECT 1 FROM public.ownership_user) OR EXISTS(SELECT 1 FROM public.ownership_organization)')
        if cursor.fetchone()[0]:
            from django.db.migrations.exceptions import IrreversibleError
            raise IrreversibleError('Populated isolation rollback prohibited')
    for table in TABLES:
        for op in ('operator', 'select', 'insert', 'update', 'delete'):
            if table in DENIED_TABLES and op != 'operator':
                continue
            editor.execute(f'DROP POLICY isolation_{op} ON public.{table}')
        editor.execute(f'ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY')
        editor.execute(f'ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY')
    for name in TRUSTED_TRIGGERS:
        editor.execute(f'ALTER FUNCTION public.{name}() SECURITY INVOKER')
        editor.execute(f'GRANT EXECUTE ON FUNCTION public.{name}() TO PUBLIC')
    editor.execute('DROP FUNCTION mw_isolation.allowed(text,jsonb,text)')
    editor.execute('DROP FUNCTION mw_isolation.export_cabinet(uuid,uuid,uuid)')
    editor.execute('DROP FUNCTION mw_isolation.record_allowed(jsonb,text,jsonb)')
    editor.execute('DROP FUNCTION mw_isolation.claims()')
    editor.execute('DROP FUNCTION mw_isolation.hmac(text,bytea)')
    editor.execute('DROP TABLE mw_isolation.key')
    editor.execute('DROP SCHEMA mw_isolation')
