"""AgriStock demo REST API. All values are synthetic and in-memory."""
import hmac
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ITEM_CODE = 'PB-NPK16'
ITEM_NAME = 'Phân NPK 16-16-8'
VALID_ID = re.compile(r'^[A-Za-z0-9_-]{8,64}$')


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


class InventoryService:
    def __init__(self):
        self._balance = 0
        self._rows = []
        self._seen = {}
        self._lock = threading.Lock()

    def inventory(self):
        with self._lock:
            return dict(item_code=ITEM_CODE, name=ITEM_NAME, unit='kg', quantity_kg=self._balance)

    def transactions(self):
        with self._lock:
            return [dict(row) for row in self._rows]

    def create_transaction(self, data):
        if not isinstance(data, dict):
            raise ApiError(422, 'INVALID_JSON', 'JSON body must be an object')
        allowed = {'request_id', 'type', 'item_code', 'quantity_kg', 'note'}
        required = {'request_id', 'type', 'item_code', 'quantity_kg'}
        if required - data.keys():
            raise ApiError(422, 'MISSING_FIELD', 'Required field missing')
        if data.keys() - allowed:
            raise ApiError(422, 'UNKNOWN_FIELD', 'Unknown fields not permitted')
        rid = data['request_id']
        if not isinstance(rid, str) or not VALID_ID.fullmatch(rid):
            raise ApiError(422, 'INVALID_REQUEST_ID', 'request_id must be 8-64 ASCII characters [A-Za-z0-9_-]')
        if data['item_code'] != ITEM_CODE:
            raise ApiError(404, 'ITEM_NOT_FOUND', 'Item not found')
        kind = data['type']
        if kind not in ('IN', 'OUT'):
            raise ApiError(422, 'INVALID_TYPE', 'type must be IN or OUT')
        qty = data['quantity_kg']
        if type(qty) is not int or not 1 <= qty <= 10000:
            raise ApiError(422, 'INVALID_QUANTITY', 'quantity_kg must be an integer from 1 to 10000')
        note = data.get('note', '')
        if not isinstance(note, str) or len(note) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in note):
            raise ApiError(422, 'INVALID_NOTE', 'note must be <=200 characters without control characters')
        actor = 'warehouse-clerk'
        signature = (kind, ITEM_CODE, qty, note, actor)
        with self._lock:
            if rid in self._seen:
                old_sig, old_result = self._seen[rid]
                if old_sig != signature:
                    raise ApiError(409, 'DUPLICATE_REQUEST_ID', 'request_id already used with different payload')
                return 200, dict(old_result)
            if kind == 'OUT' and qty > self._balance:
                raise ApiError(409, 'INSUFFICIENT_STOCK', 'Insufficient stock')
            if kind == 'IN' and self._balance + qty > 1_000_000:
                raise ApiError(409, 'CAPACITY_EXCEEDED', 'Warehouse capacity exceeded')
            self._balance += qty if kind == 'IN' else -qty
            row = dict(id=len(self._rows) + 1, request_id=rid, type=kind,
                       item_code=ITEM_CODE, quantity_kg=qty, note=note,
                       actor=actor, balance_after_kg=self._balance)
            self._rows.append(row)
            self._seen[rid] = (signature, row)
            return 201, dict(row)


def create_handler(service, api_key):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # do not log credentials or payloads

        def send_json(self, status, body):
            raw = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def dispatch(self):
            try:
                if self.path not in ('/health', '/inventory', '/transactions'):
                    raise ApiError(404, 'NOT_FOUND', 'Route not found')
                if self.command not in ('GET', 'POST') or (self.command == 'POST' and self.path != '/transactions'):
                    raise ApiError(405, 'METHOD_NOT_ALLOWED', 'Method not allowed')
                if self.command == 'GET' and self.path == '/health':
                    return self.send_json(200, {'status': 'ok'})
                supplied = self.headers.get('X-API-Key', '')
                if not api_key or not hmac.compare_digest(supplied, api_key):
                    raise ApiError(401, 'UNAUTHORIZED', 'API key required')
                if self.command == 'GET' and self.path == '/inventory':
                    return self.send_json(200, service.inventory())
                if self.command == 'GET' and self.path == '/transactions':
                    return self.send_json(200, {'items': service.transactions()})
                if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                    raise ApiError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Content-Type must be application/json')
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 65536:
                        raise ValueError()
                    data = json.loads(self.rfile.read(size).decode('utf-8'))
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    raise ApiError(400, 'INVALID_JSON', 'Invalid JSON or body size')
                status, result = service.create_transaction(data)
                return self.send_json(status, result)
            except ApiError as exc:
                return self.send_json(exc.status, {'error': {'code': exc.code, 'message': exc.message}})
            except Exception:
                return self.send_json(500, {'error': {'code': 'INTERNAL_ERROR', 'message': 'Internal server error'}})

        def do_GET(self): self.dispatch()
        def do_POST(self): self.dispatch()
        def do_PUT(self): self.dispatch()
        def do_DELETE(self): self.dispatch()
        def do_PATCH(self): self.dispatch()

    return Handler


def main():
    key = os.environ.get('APP_API_KEY')
    if not key:
        raise SystemExit('Set APP_API_KEY to a non-empty demo secret before starting')
    port = int(os.environ.get('PORT', '8000'))
    server = ThreadingHTTPServer(('127.0.0.1', port), create_handler(InventoryService(), key))
    print(f'AgriStock demo running at http://127.0.0.1:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
