"""Фиксированные операции администратора, без прямых DML-прав web на назначения."""

FUNCTIONS = r"""
CREATE FUNCTION public.basework_authorize_admin(target uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE c jsonb := mw_isolation.claims(); actor uuid; sid uuid; at_time timestamptz;
BEGIN
  IF current_setting('transaction_isolation') <> 'read committed' OR c IS NULL
     OR c->>'kind' IS DISTINCT FROM 'control' THEN
    RAISE EXCEPTION 'BaseWork: доступ запрещён' USING ERRCODE='42501';
  END IF;
  actor := (c->>'user')::uuid; sid := (c->>'session')::uuid;
  IF actor IS NULL OR sid IS NULL THEN
    RAISE EXCEPTION 'BaseWork: доступ запрещён' USING ERRCODE='42501';
  END IF;
  PERFORM id FROM public.ownership_user WHERE id IN (actor,target) ORDER BY id FOR UPDATE;
  PERFORM id FROM public.basework_administrator WHERE user_id=actor AND revoked_at IS NULL FOR SHARE;
  PERFORM id FROM public.access_control_platformroleassignment WHERE user_id=actor AND revoked_at IS NULL FOR SHARE;
  at_time := clock_timestamp();
  IF NOT EXISTS(SELECT 1 FROM public.account_security_accountsession s
    JOIN public.ownership_user u ON u.id=s.user_id
    JOIN public.account_security_accountsecurity st ON st.user_id=u.id
    JOIN public.account_security_authenticator a ON a.id=s.authenticator_id AND a.user_id=u.id
    WHERE s.id=sid AND u.id=actor AND u.is_active AND u.archived_at IS NULL
      AND u.password NOT LIKE '!%' AND s.level='full' AND s.revoked_at IS NULL
      AND s.version=st.version AND NOT st.recovery_required
      AND s.expires_at>at_time AND s.created_at>at_time-interval '4 hours'
      AND s.last_seen>at_time-interval '15 minutes'
      AND s.password_confirmed_at>at_time-interval '5 minutes'
      AND s.factor_confirmed_at>at_time-interval '5 minutes'
      AND a.confirmed AND a.revoked_at IS NULL
      AND EXISTS(SELECT 1 FROM public.basework_administrator b WHERE b.user_id=u.id AND b.revoked_at IS NULL)
      AND EXISTS(SELECT 1 FROM public.access_control_platformroleassignment p WHERE p.user_id=u.id AND p.revoked_at IS NULL)
      AND NOT EXISTS(SELECT 1 FROM public.ownership_membership m WHERE m.user_id=u.id)
      AND NOT EXISTS(SELECT 1 FROM public.accounts_accountcontact ct WHERE ct.user_id=u.id AND ct.activated_at IS NULL)
      AND NOT EXISTS(SELECT 1 FROM public.basework_federatedsession f
        JOIN public.basework_identitybinding b ON b.id=f.binding_id
        WHERE f.session_id=s.id AND (b.revoked_at IS NOT NULL OR b.user_id<>u.id))
      AND (s.trusted_device_id IS NULL OR EXISTS(SELECT 1 FROM public.account_security_trusteddevice d
        JOIN public.account_security_authenticator da ON da.id=d.authenticator_id
        WHERE d.id=s.trusted_device_id AND d.user_id=u.id AND d.revoked_at IS NULL
          AND d.version=st.version AND d.credential_hash=s.credential_hash AND d.expires_at>at_time
          AND da.user_id=u.id AND da.confirmed AND da.revoked_at IS NULL))) THEN
    RAISE EXCEPTION 'BaseWork: требуется подтверждённый администратор' USING ERRCODE='42501';
  END IF;
END $$;

CREATE FUNCTION public.basework_set_application(target uuid, app text, enabled boolean) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  PERFORM public.basework_authorize_admin(target);
  IF app IS NULL OR app NOT IN ('faq','rooms') OR enabled IS NULL
    OR target=(mw_isolation.claims()->>'user')::uuid
    OR NOT EXISTS(SELECT 1 FROM public.ownership_user u WHERE u.id=target AND u.is_active AND u.archived_at IS NULL)
    OR NOT EXISTS(SELECT 1 FROM public.account_security_securityevent e WHERE e.user_id=target AND e.kind='basework_personal_created')
    OR EXISTS(SELECT 1 FROM public.accounts_accountcontact ct WHERE ct.user_id=target)
    OR EXISTS(SELECT 1 FROM public.ownership_membership m WHERE m.user_id=target)
    OR EXISTS(SELECT 1 FROM public.basework_administrator b WHERE b.user_id=target AND b.revoked_at IS NULL)
    OR EXISTS(SELECT 1 FROM public.access_control_platformroleassignment p WHERE p.user_id=target AND p.revoked_at IS NULL) THEN
    RAISE EXCEPTION 'BaseWork: недопустимое назначение' USING ERRCODE='42501';
  END IF;
  IF enabled THEN
    INSERT INTO public.basework_applicationaccess(id,user_id,application,created_at,revoked_at)
      SELECT gen_random_uuid(),target,app,clock_timestamp(),NULL
      WHERE NOT EXISTS(SELECT 1 FROM public.basework_applicationaccess WHERE user_id=target AND application=app AND revoked_at IS NULL);
  ELSE
    UPDATE public.basework_applicationaccess SET revoked_at=clock_timestamp()
      WHERE user_id=target AND application=app AND revoked_at IS NULL;
  END IF;
END $$;
"""

SIGNATURES = ('basework_authorize_admin(uuid)', 'basework_set_application(uuid,text,boolean)')
