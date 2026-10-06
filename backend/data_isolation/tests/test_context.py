import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase
from data_isolation.context import record_scope, scope, serialize, signature


class CapabilityTests(SimpleTestCase):
    def test_canonical_signature_binds_every_claim(self):
        key = bytes(range(32))
        claims = dict(pid=1, xid='2', database='synthetic', role='web',
                      expires=3, statement='s', kind='record', user='a',
                      organization='b', cabinet='c', resource='synthetic_record', action='view')
        payload = serialize(claims)
        self.assertEqual(signature(key, payload), hmac.new(key, payload.encode(), hashlib.sha256).hexdigest())
        for field in claims:
            altered = {**claims, field: 'different'}
            self.assertNotEqual(signature(key, payload), signature(key, serialize(altered)))

    def test_nested_exception_cleanup(self):
        obj = SimpleNamespace(pk='synthetic')
        self.assertIsNone(scope.get())
        with record_scope(obj, obj, obj, obj, 'view'):
            before = scope.get()
            with self.assertRaises(RuntimeError):
                with record_scope(obj, obj, obj, obj, 'export'):
                    raise RuntimeError()
            self.assertEqual(scope.get(), before)
        self.assertIsNone(scope.get())
        with self.assertRaises(PermissionDenied):
            with record_scope(obj, obj, obj, obj, 'manage_access'):
                pass

    def test_concurrent_python_contexts_are_independent(self):
        from threading import Barrier
        barrier = Barrier(2)
        def work(value):
            obj = SimpleNamespace(pk=value)
            with record_scope(obj, obj, obj, obj, 'view'):
                barrier.wait(timeout=5)
                result = scope.get()['user']
            return result, scope.get()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(work, ['a', 'b'])), [('a', None), ('b', None)])
