"""Явно включаемый локальный стенд браузерной приёмки. Не часть runtime/обычных тестов."""
import json
import os
import sys
import threading
import time
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
from django.test import LiveServerTestCase, override_settings
from django.utils import timezone
from django.core.signals import got_request_exception
from django.db import OperationalError
from ownership.models import User, Organization, Membership
from accounts.models import AccountContact
from basework.models import ApplicationAccess
from tools.rooms_fixture import RoomsFixture
from basework import rooms, services


fixture_lock = threading.RLock()


class SerializedFixtureHandler:
    """LiveServer делит одно in-memory соединение SQLite между потоками."""
    def __init__(self, application):
        self.application = LiveServerTestCase.static_handler(application)

    def __call__(self, environ, start_response):
        with fixture_lock:
            response = self.application(environ, start_response)
            try:
                yield from response
            finally:
                response.close()


@skipUnless(os.environ.get('BASEWORK_ROOMS_BROWSER_READY'), 'Стенд не запрошен')
@override_settings(STATIC_URL='/static/',MEDIA_URL='/media/')
class BrowserFixture(LiveServerTestCase):
    host='127.0.0.1'
    static_handler = SerializedFixtureHandler
    def _fixture_teardown(self):
        # Одноразовая in-memory БД уничтожается runner целиком. Штатный flush
        # несовместим с запретом удаления истории; защитные триггеры не отключаем.
        from django.db import connection
        self.assertEqual(connection.vendor,'sqlite')
        self.assertTrue(connection.is_in_memory_db())

    def test_browser(self):
        ready=Path(os.environ['BASEWORK_ROOMS_BROWSER_READY'])
        if ready.exists(): raise RuntimeError('Путь готовности должен быть новым')
        def report_exception(sender, **kwargs):
            error = sys.exc_info()[1]
            detail = str(error) if isinstance(error, OperationalError) else ''
            with ready.with_suffix('.errors').open('a', encoding='utf-8') as log:
                log.write(f'{type(error).__name__}: {detail}\n')
        got_request_exception.connect(report_exception, weak=False)
        self.addCleanup(got_request_exception.disconnect, report_exception)
        user=User.objects.create_user('rooms-synthetic','Synthetic-rooms-only-2026!')
        AccountContact.objects.create(user=user,email='rooms@example.invalid',activated_at=timezone.now())
        org=Organization.objects.create(name='Вымышленная организация')
        Membership.objects.create(user=user,organization=org,role='observer')
        access=ApplicationAccess.objects.create(user=user,application='rooms')
        control=ready.with_suffix('.control')
        original=rooms.exchange
        def exchange(actor,method,*args):
            mode=control.read_text().strip() if control.exists() else ''
            if mode=='down': raise rooms.SourceUnavailable()
            result=original(actor,method,*args)
            if mode=='lose-next-write' and method!='GET':
                control.write_text('normal')
                raise rooms.SourceUnavailable()
            return result
        with RoomsFixture(user.pk) as source, override_settings(BASEWORK_ROOMS_URL=source.url,BASEWORK_ROOMS_KEY_FILE=str(source.key_file),
                BASEWORK_ROOMS_WRITES=True,SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False,
                CSRF_TRUSTED_ORIGINS=['http://127.0.0.1:5195'],ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']), patch('basework.rooms.exchange',side_effect=exchange):
            ready.write_text(json.dumps({'url':self.live_server_url,'synthetic_only':True}))
            deadline=time.monotonic()+7200
            while time.monotonic()<deadline and not ready.with_suffix('.stop').exists():
                mode=control.read_text().strip() if control.exists() else ''
                if mode=='revoke':
                    with fixture_lock:
                        services.revoke_application(access.pk)
                    control.write_text('normal')
                time.sleep(.25)
        self.assertTrue(ready.with_suffix('.stop').exists(),'Браузерная приёмка остановлена по лимиту, результаты проверить отдельно')
