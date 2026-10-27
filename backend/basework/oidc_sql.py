"""Ограниченный автомат попытки OIDC; web не получает прямые права записи."""
GUARD = """
CREATE FUNCTION basework_oidc_immutable() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,public AS $$ BEGIN
 IF (to_jsonb(NEW)-ARRAY['claimed_at','ready_at','finished_at','binding_id','version','credential_hash'])
    IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['claimed_at','ready_at','finished_at','binding_id','version','credential_hash'])
 OR (OLD.claimed_at IS NOT NULL AND OLD.claimed_at IS DISTINCT FROM NEW.claimed_at)
 OR (OLD.ready_at IS NOT NULL AND (OLD.ready_at IS DISTINCT FROM NEW.ready_at
     OR OLD.binding_id IS DISTINCT FROM NEW.binding_id OR OLD.version IS DISTINCT FROM NEW.version
     OR OLD.credential_hash IS DISTINCT FROM NEW.credential_hash))
 OR (OLD.finished_at IS NOT NULL AND OLD.finished_at IS DISTINCT FROM NEW.finished_at)
 OR (NEW.ready_at IS NOT NULL AND (NEW.claimed_at IS NULL OR NEW.binding_id IS NULL
     OR NEW.version IS NULL OR NEW.credential_hash=''))
 OR (NEW.ready_at IS NULL AND (NEW.binding_id IS NOT NULL OR NEW.version IS NOT NULL OR NEW.credential_hash<>''))
 OR (NEW.finished_at IS NOT NULL AND NEW.ready_at IS NULL)
 THEN RAISE EXCEPTION 'Недопустимый переход OIDC' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION basework_oidc_immutable() FROM PUBLIC;
CREATE TRIGGER basework_oidc_immutable BEFORE UPDATE ON basework_oidcattempt
 FOR EACH ROW EXECUTE FUNCTION basework_oidc_immutable();
CREATE TRIGGER basework_no_delete BEFORE DELETE ON basework_oidcattempt
 FOR EACH ROW EXECUTE FUNCTION basework_no_delete();
"""

TRANSITION = """
CREATE FUNCTION basework_oidc_transition(operation text, body jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE a public.basework_oidcattempt%ROWTYPE; s public.account_security_accountsession%ROWTYPE;
BEGIN
 IF (mw_isolation.claims()->>'kind') IS DISTINCT FROM 'control'
 THEN RAISE EXCEPTION 'Требуется подписанный запрос OIDC' USING ERRCODE='42501'; END IF;
 IF operation='create' THEN
   IF body->>'state_hash' !~ '^[0-9a-f]{64}$' OR body->>'browser_hash' !~ '^[0-9a-f]{64}$'
     OR body->>'provider_hash' !~ '^[0-9a-f]{64}$'
   THEN RAISE EXCEPTION 'Недопустимая попытка' USING ERRCODE='23514'; END IF;
   INSERT INTO public.basework_oidcattempt(id,state_hash,browser_hash,provider_hash,nonce,verifier,
       created_at,expires_at,credential_hash)
     VALUES((body->>'id')::uuid,body->>'state_hash',body->>'browser_hash',body->>'provider_hash',
       body->>'nonce',body->>'verifier',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+INTERVAL '5 minutes','')
     RETURNING * INTO a;
 ELSIF operation='claim' THEN
   UPDATE public.basework_oidcattempt SET claimed_at=CURRENT_TIMESTAMP
     WHERE state_hash=body->>'state_hash' AND browser_hash=body->>'browser_hash'
       AND provider_hash=body->>'provider_hash' AND claimed_at IS NULL AND expires_at>CURRENT_TIMESTAMP
     RETURNING * INTO a;
 ELSIF operation='ready' THEN
   UPDATE public.basework_oidcattempt SET ready_at=CURRENT_TIMESTAMP,
       binding_id=(body->>'binding_id')::uuid,version=(body->>'version')::bigint,
       credential_hash=body->>'credential_hash'
     WHERE id=(body->>'id')::uuid AND browser_hash=body->>'browser_hash' AND claimed_at IS NOT NULL
       AND ready_at IS NULL AND finished_at IS NULL AND expires_at>CURRENT_TIMESTAMP
     RETURNING * INTO a;
 ELSIF operation='finish' THEN
   SELECT * INTO a FROM public.basework_oidcattempt
     WHERE id=(body->>'id')::uuid AND browser_hash=body->>'browser_hash'
       AND ready_at IS NOT NULL AND finished_at IS NULL AND expires_at>CURRENT_TIMESTAMP FOR UPDATE;
   IF a.id IS NULL THEN RETURN NULL; END IF;
   SELECT session.* INTO s FROM public.account_security_accountsession session
     JOIN public.basework_identitybinding binding ON binding.id=a.binding_id AND binding.user_id=session.user_id
     JOIN public.account_security_accountsecurity state ON state.user_id=session.user_id
     WHERE session.id=(body->>'session_id')::uuid AND binding.revoked_at IS NULL
       AND session.revoked_at IS NULL AND session.level='full' AND session.expires_at>CURRENT_TIMESTAMP
       AND session.created_at>=a.ready_at AND session.version=a.version AND state.version=a.version
       AND NOT state.recovery_required AND session.credential_hash=a.credential_hash;
   IF s.id IS NULL THEN RAISE EXCEPTION 'Нет действующей сессии OIDC' USING ERRCODE='23514'; END IF;
   INSERT INTO public.basework_federatedsession(session_id,binding_id) VALUES(s.id,a.binding_id);
   UPDATE public.basework_oidcattempt SET finished_at=CURRENT_TIMESTAMP WHERE id=a.id;
 ELSE RAISE EXCEPTION 'Неизвестный переход OIDC' USING ERRCODE='23514';
 END IF;
 RETURN a.id;
END $$;
REVOKE ALL ON FUNCTION basework_oidc_transition(text,jsonb) FROM PUBLIC;
"""
