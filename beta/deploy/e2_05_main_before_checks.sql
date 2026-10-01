-- Read-only C2 backup verification. No raw rows, contacts or credentials.
-- Expected BEFORE accounts migrations; refuse a changed/nontechnical database.
SET TIME ZONE 'UTC';
DO $$
DECLARE tables text[];
BEGIN
    IF current_database() NOT IN ('mw_beta', 'mw_beta_test_e2_05_main_before') THEN
        RAISE EXCEPTION 'Unexpected backup-check database';
    END IF;
    SELECT array_agg(tablename::text ORDER BY tablename) INTO tables
        FROM pg_tables WHERE schemaname='public';
    IF tables IS DISTINCT FROM ARRAY['django_content_type','django_migrations']::text[] THEN
        RAISE EXCEPTION 'Expected untouched E2-03 technical schema only';
    END IF;
    IF (SELECT count(*) FROM django_migrations) <> 2
       OR EXISTS(SELECT 1 FROM django_migrations WHERE app <> 'contenttypes')
       OR (SELECT array_agg(name::text ORDER BY name) FROM django_migrations)
          IS DISTINCT FROM ARRAY['0001_initial','0002_remove_content_type_name']::text[] THEN
        RAISE EXCEPTION 'Unexpected migration history';
    END IF;
END $$;
SELECT json_build_object(
    'contenttypes_rows', (SELECT count(*) FROM django_content_type),
    'contenttypes_fingerprint', (SELECT md5(coalesce(string_agg(row_to_json(t)::text, E'\n' ORDER BY t.id), '')) FROM django_content_type t),
    'migration_rows', (SELECT count(*) FROM django_migrations),
    'migration_fingerprint', (SELECT md5(coalesce(string_agg(row_to_json(t)::text, E'\n' ORDER BY t.id), '')) FROM django_migrations t)
);
