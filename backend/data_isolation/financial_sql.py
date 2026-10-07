"""Fixed financial operations, not a SQL signing or expression API.

The table has no web ACL. Trusted DEFINER functions explicitly enforce BOTH
ordinary and financial permissions. Operator RLS is not column authorization.
"""
from access_control.financial_guards import refuse_populated

FUNCTIONS = r"""
CREATE FUNCTION mw_isolation.finance_allowed(c jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid; sid uuid; org uuid; cab uuid; act text;
BEGIN
  IF current_setting('transaction_isolation') <> 'read committed'
     OR c IS NULL OR c->>'kind' IS DISTINCT FROM 'record'
     OR c->>'resource' IS DISTINCT FROM 'synthetic_record' THEN RETURN false; END IF;
  actor := (c->>'user')::uuid; sid := (c->>'session')::uuid;
  org := (c->>'organization')::uuid; cab := (c->>'cabinet')::uuid; act := c->>'action';
  IF actor IS NULL OR sid IS NULL OR org IS NULL OR cab IS NULL OR act IS NULL
     OR act NOT IN ('view','export','change') THEN RETURN false; END IF;
  IF EXISTS(SELECT 1 FROM public.access_control_platformroleassignment p
            WHERE p.user_id=actor AND p.revoked_at IS NULL) THEN RETURN false; END IF;
  IF NOT mw_isolation.record_allowed(jsonb_build_object(
      'organization_id',org,'cabinet_id',cab,'archived_at',NULL),
      CASE WHEN act='change' THEN 'update' ELSE 'select' END,c) THEN RETURN false; END IF;
  RETURN EXISTS(SELECT 1 FROM public.access_control_grant g
      JOIN public.ownership_membership m ON m.id=g.membership_id
      WHERE m.user_id=actor AND m.organization_id=org AND m.state='active' AND m.archived_at IS NULL
        AND g.organization_id=org AND (g.cabinet_id IS NULL OR g.cabinet_id=cab)
        AND g.resource='synthetic_finance' AND g.action=act
        AND g.revoked_at IS NULL AND g.platform_id IS NULL);
EXCEPTION WHEN invalid_text_representation THEN RETURN false;
END $$;

CREATE FUNCTION mw_isolation.finance_read(ids uuid[], requested_permit uuid DEFAULT NULL)
RETURNS TABLE(record_id uuid,revenue numeric,cost numeric,expenses numeric,payout numeric)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE c jsonb := mw_isolation.claims(); org uuid; cab uuid;
BEGIN
  IF NOT mw_isolation.finance_allowed(c) OR c->>'action' NOT IN ('view','export')
     OR ids IS NULL OR cardinality(ids)>100 OR array_position(ids,NULL) IS NOT NULL THEN
    RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='42501'; END IF;
  org := (c->>'organization')::uuid; cab := (c->>'cabinet')::uuid;
  -- Match the original immutable ordinary AND financial grants, not replacements.
  IF c->>'action'='export' THEN
    IF cardinality(ids)<>1 OR requested_permit IS NULL OR NOT EXISTS(
        SELECT 1 FROM public.account_security_exportpermit p
        JOIN public.access_control_exportbinding b ON b.permit_id=p.id
        JOIN public.access_control_grant g ON g.id=b.grant_id
        JOIN public.access_control_grant f ON f.id=b.finance_grant_id
        JOIN public.ownership_membership m ON m.id=f.membership_id
        WHERE p.id=requested_permit AND p.user_id=(c->>'user')::uuid
          AND p.session_id=(c->>'session')::uuid AND p.organization_id=org
          AND p.revoked_at IS NULL AND p.expires_at>clock_timestamp()
          AND b.record_id=ids[1] AND g.revoked_at IS NULL AND f.revoked_at IS NULL
          AND g.resource='synthetic_record' AND g.action='export'
          AND f.resource='synthetic_finance' AND f.action='export'
          AND g.membership_id=f.membership_id AND m.user_id=p.user_id
          AND m.organization_id=org AND m.state='active' AND m.archived_at IS NULL
          AND g.organization_id=org AND f.organization_id=org
          AND (g.cabinet_id IS NULL OR g.cabinet_id=cab)
          AND (f.cabinet_id IS NULL OR f.cabinet_id=cab)
          AND g.platform_id IS NULL AND f.platform_id IS NULL) THEN
      RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='42501'; END IF;
  ELSIF requested_permit IS NOT NULL THEN
    RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='42501';
  END IF;
  RETURN QUERY SELECT f.record_id,f.revenue,f.cost,f.expenses,f.payout
    FROM public.access_control_syntheticfinance f
    JOIN public.access_control_syntheticrecord r ON r.id=f.record_id
    WHERE f.organization_id=org AND f.cabinet_id=cab AND f.record_id=ANY(ids)
      AND r.organization_id=org AND r.cabinet_id=cab AND r.archived_at IS NULL
    ORDER BY f.record_id;
END $$;

CREATE FUNCTION mw_isolation.finance_write(requested_record uuid,
    new_revenue numeric,new_cost numeric,new_expenses numeric,new_payout numeric)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE c jsonb := mw_isolation.claims(); amount numeric;
BEGIN
  IF NOT mw_isolation.finance_allowed(c) OR c->>'action' IS DISTINCT FROM 'change' THEN
    RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='42501'; END IF;
  FOREACH amount IN ARRAY ARRAY[new_revenue,new_cost,new_expenses,new_payout] LOOP
    IF amount IS NULL OR NOT (amount BETWEEN 0 AND 999999999999.99) OR amount<>round(amount,2) THEN
      RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='42501'; END IF;
  END LOOP;
  UPDATE public.access_control_syntheticfinance f SET revenue=new_revenue,cost=new_cost,
      expenses=new_expenses,payout=new_payout
    WHERE f.record_id=requested_record AND f.organization_id=(c->>'organization')::uuid
      AND f.cabinet_id=(c->>'cabinet')::uuid
      AND EXISTS(SELECT 1 FROM public.access_control_syntheticrecord r WHERE r.id=f.record_id
        AND r.organization_id=f.organization_id AND r.cabinet_id=f.cabinet_id AND r.archived_at IS NULL);
  IF NOT FOUND THEN RAISE EXCEPTION 'Financial operation denied' USING ERRCODE='42501'; END IF;
END $$;
"""

PUBLIC_FUNCTIONS = ('finance_read(uuid[],uuid)', 'finance_write(uuid,numeric,numeric,numeric,numeric)')


def install(apps, editor):
    if editor.connection.vendor == 'sqlite':
        return  # Only application behavior, never an SQL financial proof.
    if editor.connection.vendor != 'postgresql':
        raise RuntimeError('Financial isolation requires PostgreSQL')
    editor.execute(FUNCTIONS, params=None)
    for signature in (*PUBLIC_FUNCTIONS, 'finance_allowed(jsonb)'):
        editor.execute(f'REVOKE ALL ON FUNCTION mw_isolation.{signature} FROM PUBLIC')


def uninstall(apps, editor):
    refuse_populated(apps, editor)
    if editor.connection.vendor == 'postgresql':
        for signature in (*PUBLIC_FUNCTIONS, 'finance_allowed(jsonb)'):
            editor.execute(f'DROP FUNCTION mw_isolation.{signature}')
