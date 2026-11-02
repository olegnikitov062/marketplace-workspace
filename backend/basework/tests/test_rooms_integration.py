"""Django → подписанный HTTP → настоящий источник → временная SQLite."""
import os
import uuid
from unittest import skipUnless
from django.test import SimpleTestCase, override_settings
from basework import rooms
from tools.rooms_fixture import RoomsFixture


@skipUnless(os.environ.get('BASEWORK_ROOMS_TEST_SOURCE'), 'Для HTTP-интеграции укажите локальный тестовый источник')
class RoomsIntegrationTests(SimpleTestCase):
    def test_real_source_write_read_conflict_update_delete_and_retry(self):
        actor=str(uuid.uuid4())
        with RoomsFixture(actor) as source, override_settings(BASEWORK_ROOMS_URL=source.url,
                BASEWORK_ROOMS_KEY_FILE=str(source.key_file),BASEWORK_ROOMS_WRITES=True):
            body={'roomId':'big','title':'Вымышленная встреча','start':'2026-11-02T09:00:00+03:00','end':'2026-11-02T10:00:00+03:00'}
            operation=str(uuid.uuid4())
            first=rooms.exchange(actor,'POST','/api/events',body,operation)
            self.assertEqual(first[0],201)
            self.assertEqual(rooms.exchange(actor,'POST','/api/events',body,operation),first)
            self.assertEqual(rooms.exchange(actor,'POST','/api/events',body,str(uuid.uuid4()))[0],409)
            status,doc=rooms.exchange(actor,'GET','/api/events?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z',{},str(uuid.uuid4()))
            self.assertEqual(status,200); self.assertEqual(len(doc['events']),1)
            ev=doc['events'][0]
            self.assertTrue(ev['mine']); self.assertNotIn('owner',ev)
            path='/api/events/'+ev['id']
            update = {**body,'title':'Изменено','start':'2026-11-03T09:00:00+03:00','end':'2026-11-03T10:00:00+03:00','expectedRevision':ev['revision']}
            update_operation = str(uuid.uuid4())
            first_update = rooms.exchange(actor,'PUT',path,update,update_operation)
            self.assertEqual(first_update,(200,{'updated':1}))
            old_day = '/api/events?from=2026-11-02T00:00:00%2B03:00&to=2026-11-03T00:00:00%2B03:00'
            self.assertEqual(rooms.exchange(actor,'GET',old_day,{},str(uuid.uuid4()))[1]['events'],[])
            self.assertEqual(rooms.exchange(actor,'PUT',path,update,update_operation),first_update)
            self.assertEqual(rooms.exchange(actor,'DELETE',path,{'expectedRevision':ev['revision']},str(uuid.uuid4()))[0],409)
            doc=rooms.exchange(actor,'GET','/api/events?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z',{},str(uuid.uuid4()))[1]
            operation=str(uuid.uuid4()); body={'expectedRevision':doc['events'][0]['revision']}
            first=rooms.exchange(actor,'DELETE',path,body,operation)
            self.assertEqual(first,(200,{'deleted':1}))
            self.assertEqual(rooms.exchange(actor,'GET','/api/events?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z',{},str(uuid.uuid4()))[1]['events'],[])
            self.assertEqual(rooms.exchange(actor,'DELETE',path,body,operation),first)
            self.assertEqual(rooms.exchange(str(uuid.uuid4()),'GET','/api/events?from=2026-11-02T00:00:00Z&to=2026-11-09T00:00:00Z',{},str(uuid.uuid4()))[0],403)
