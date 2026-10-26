"""Contract tests written from SPEC.md before implementation (RED first)."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import InventoryService, create_handler

KEY = 'demo-test-key'
CODE = 'PB-NPK16'


def payload(rid='REQ-0001', kind='IN', qty=10, note=''):
    return dict(request_id=rid, type=kind, item_code=CODE, quantity_kg=qty, note=note)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = InventoryService()

    def send(self, p):
        return self.svc.create_transaction(p)

    def test_empty_inventory_and_history_BR12(self):
        self.assertEqual(self.svc.inventory()['quantity_kg'], 0)
        self.assertEqual(self.svc.transactions(), [])

    def test_in_out_and_exact_zero_BR05_BR07(self):
        status, row = self.send(payload(qty=10))
        self.assertEqual(status, 201)
        self.assertEqual(row['balance_after_kg'], 10)
        status, row = self.send(payload('REQ-0002', 'OUT', 10))
        self.assertEqual((status, row['balance_after_kg']), (201, 0))
        self.assertEqual(len(self.svc.transactions()), 2)

    def test_out_of_stock_does_not_mutate_BR05(self):
        with self.assertRaisesRegex(Exception, 'INSUFFICIENT_STOCK'):
            self.send(payload(kind='OUT'))
        self.assertEqual(self.svc.transactions(), [])

    def test_duplicate_id_same_payload_safe_BR08(self):
        first = self.send(payload())
        second = self.send(payload())
        self.assertEqual(second, (200, first[1]))
        self.assertEqual(self.svc.inventory()['quantity_kg'], 10)
        self.assertEqual(len(self.svc.transactions()), 1)

    def test_duplicate_id_changed_quantity_conflict_BR08(self):
        self.send(payload())
        with self.assertRaisesRegex(Exception, 'DUPLICATE_REQUEST_ID'):
            self.send(payload(qty=11))

    def test_duplicate_id_changed_note_conflict(self):
        self.send(payload(note='A'))
        with self.assertRaisesRegex(Exception, 'DUPLICATE_REQUEST_ID'):
            self.send(payload(note='B'))

    def test_boolean_quantity_rejected(self):
        with self.assertRaisesRegex(Exception, 'INVALID_QUANTITY'):
            self.send(payload(qty=True))

    def test_fraction_zero_and_negative_rejected_BR04(self):
        for value in (0, -1, 1.5, '2', 10001):
            with self.subTest(value=value):
                with self.assertRaisesRegex(Exception, 'INVALID_QUANTITY'):
                    self.send(payload(qty=value))

    def test_bad_type_item_and_schema_BR02_BR03_BR11(self):
        for change, code in [({'type': 'out'}, 'INVALID_TYPE'),
                             ({'item_code': 'WRONG'}, 'ITEM_NOT_FOUND'),
                             ({'other': 42}, 'UNKNOWN_FIELD')]:
            with self.subTest(change=change):
                with self.assertRaisesRegex(Exception, code):
                    self.send({**payload(), **change})
        p = payload(); del p['request_id']
        with self.assertRaisesRegex(Exception, 'MISSING_FIELD'):
            self.send(p)

    def test_note_and_request_id_validation_BR08_BR09(self):
        for change, code in [({'note': 'a' * 201}, 'INVALID_NOTE'),
                             ({'note': 'bad\n'}, 'INVALID_NOTE'),
                             ({'request_id': 'x'}, 'INVALID_REQUEST_ID')]:
            with self.subTest(change=change):
                with self.assertRaisesRegex(Exception, code):
                    self.send({**payload(), **change})

    def test_capacity_limit_BR06(self):
        for n in range(100):
            self.send(payload(f'REQ-{n:04d}', qty=10000))
        self.assertEqual(self.svc.inventory()['quantity_kg'], 1000000)
        with self.assertRaisesRegex(Exception, 'CAPACITY_EXCEEDED'):
            self.send(payload('REQ-EXTRA', qty=1))
        self.assertEqual(len(self.svc.transactions()), 100)

    def test_concurrent_retry_atomic_BR07_BR08(self):
        outcomes = []
        def worker():
            outcomes.append(self.send(payload()))
        threads = [threading.Thread(target=worker) for _ in range(12)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(outcomes), 12)
        self.assertEqual(self.svc.inventory()['quantity_kg'], 10)
        self.assertEqual(len(self.svc.transactions()), 1)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), create_handler(InventoryService(), KEY))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def call(self, method, path, data=None, key=KEY, content_type='application/json'):
        headers = {'Content-Type': content_type}
        if key is not None: headers['X-API-Key'] = key
        req = Request(self.url + path, method=method, headers=headers,
                      data=(data if isinstance(data, bytes) else json.dumps(data).encode()) if data is not None else None)
        try:
            with urlopen(req, timeout=3) as resp:
                return resp.status, json.load(resp)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def test_auth_health_and_empty_BR01_BR12(self):
        self.assertEqual(self.call('GET', '/health', key=None), (200, {'status': 'ok'}))
        status, body = self.call('GET', '/inventory', key=None)
        self.assertEqual((status, body['error']['code']), (401, 'UNAUTHORIZED'))
        self.assertEqual(self.call('GET', '/transactions')[1], {'items': []})

    def test_post_success_and_retry_http_BR08(self):
        status, row = self.call('POST', '/transactions', payload('HTTP-0001', qty=5))
        self.assertEqual((status, row['balance_after_kg']), (201, 5))
        status, row = self.call('POST', '/transactions', payload('HTTP-0001', qty=5))
        self.assertEqual((status, row['balance_after_kg']), (200, 5))

    def test_json_media_and_unknown_method_BR11(self):
        self.assertEqual(self.call('POST', '/transactions', b'{broken')[1]['error']['code'], 'INVALID_JSON')
        self.assertEqual(self.call('POST', '/transactions', payload('HTTP-0002'), content_type='text/plain')[0], 415)
        self.assertEqual(self.call('PUT', '/inventory')[0], 405)
        self.assertEqual(self.call('GET', '/unknown')[0], 404)


if __name__ == '__main__':
    unittest.main()
