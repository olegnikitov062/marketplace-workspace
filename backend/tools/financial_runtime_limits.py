"""Guarded pre-suite limits check. Stricter session limits are acceptable."""
import json


def validate(values):
    if len(values) != 5 or any(type(value) is not int for value in values):
        raise ValueError('runtime_limits_shape')
    connections, statement_ms, lock_ms, idle_ms, clients = values
    if (connections != 20 or not 0 < statement_ms <= 15000 or
            not 0 < lock_ms <= 5000 or not 0 < idle_ms <= 20000 or
            not 1 <= clients <= 8):
        raise ValueError('runtime_limits_exceeded')
    return dict(max_connections=connections, statement_timeout_ms=statement_ms,
                lock_timeout_ms=lock_ms, idle_transaction_timeout_ms=idle_ms,
                client_connections=clients)


def main():
    from tools.financial_rehearsal import guard
    guard()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('max_connections')::int, "
                       "(SELECT setting::bigint FROM pg_settings WHERE name='statement_timeout'), "
                       "(SELECT setting::bigint FROM pg_settings WHERE name='lock_timeout'), "
                       "(SELECT setting::bigint FROM pg_settings WHERE name='idle_in_transaction_session_timeout'), "
                       "(SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend')")
        values = cursor.fetchone()
        try:
            report = validate(values)
        except ValueError:
            if len(values) == 5 and all(type(value) is int for value in values):
                # This fixed query returns only limits/counts, never rows or credentials.
                print(json.dumps({'runtime_limits':'FAIL','observed_numeric_values':values}))
            raise
    print(json.dumps({'runtime_limits':'PASS', **report}, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Financial runtime limits check failed; no secret or row data disclosed') from None
