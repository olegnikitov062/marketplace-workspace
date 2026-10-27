"""Only the separately authorized E2-09 rehearsal; no main-beta entrypoint."""
import os
import urllib.request
import urllib.error


def main():
    from tools.financial_rehearsal import marker, expect, PROJECT
    marker()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from tools.financial_web_contract import verify
    expect(settings.ISOLATION_ENABLED and settings.ACCESS_CONTROL_ENABLED and settings.ACCOUNT_SECURITY_ENABLED)
    with connection.cursor() as cursor:
        cursor.execute("SELECT session_user,current_user,current_database(),current_setting('cluster_name')")
        expect(cursor.fetchone() == ('mw_beta_web','mw_beta_web','mw_beta',PROJECT))
        verify(cursor)
    for path, expected in (('/api/v1/health/live',200),('/api/v1/health/ready',200),
                           ('/auth/session',401),('/auth/login',405),('/auth/mfa/login/',200),
                           ('/api/v1/access/platform/status/',403)):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5) as response:
                actual = response.status
        except urllib.error.HTTPError as error:
            actual = error.code
        expect(actual == expected)
    print('E2-09 limited-login ACL/RLS metadata and six network checks PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('E2-09 runtime verification failed; no response or credential data disclosed') from None
