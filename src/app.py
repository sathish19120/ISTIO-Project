"""Read-only shop demo. Routing, retries and faults belong to Istio, not this app."""
import json
import os
import socket
import threading
import time
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROLE = os.getenv('APP_ROLE', 'payment')
VERSION = os.getenv('APP_VERSION', 'v1')
PORT = int(os.getenv('PORT', '8080'))
PAYMENT_URL = os.getenv('PAYMENT_URL', 'http://payment:8080').rstrip('/')
COUNTERS = OrderedDict()
LOCK = threading.Lock()

def attempt_for(key):
    with LOCK:
        count = COUNTERS.pop(key, 0) + 1
        COUNTERS[key] = count
        while len(COUNTERS) > 1000:
            COUNTERS.popitem(last=False)
        return count

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_body(self, status, body, content_type='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Expected when an Istio timeout ends a request before the app finishes.
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/healthz', '/readyz'):
            self.send_body(200, {'status': 'ok', 'role': ROLE})
            return
        if ROLE == 'storefront':
            if path == '/':
                self.send_body(200, Path(__file__).with_name('index.html').read_bytes(),
                               'text/html; charset=utf-8')
            elif path.startswith('/api/'):
                self.forward()
            else:
                self.send_body(404, {'error': 'Use / or /api/pay'})
            return
        self.payment()

    def forward(self):
        started = time.monotonic()
        request_id = self.headers.get('x-request-id') or str(uuid.uuid4())
        headers = {'x-request-id': request_id}
        for name in ('x-canary', 'x-demo-fault', 'cookie', 'traceparent', 'tracestate'):
            if self.headers.get(name):
                headers[name] = self.headers[name]
        # The path is relative to a fixed upstream. No app-level routing or retries.
        req = Request(PAYMENT_URL + self.path[len('/api'):], headers=headers)
        try:
            with urlopen(req, timeout=8) as result:
                status, raw = result.status, result.read()
        except HTTPError as exc:
            status, raw = exc.code, exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            status, raw = 502, str(exc).encode()
        try:
            result = json.loads(raw)
            if not isinstance(result, dict):
                result = {'upstream_body': result}
        except (ValueError, UnicodeDecodeError):
            result = {'upstream_body': raw.decode(errors='replace')[:1000]}
        result.update(status=status, elapsed_ms=round((time.monotonic()-started)*1000),
                      request_id=request_id, storefront_pod=socket.gethostname())
        print(json.dumps({'event': 'forward', **result}), flush=True)
        self.send_body(status, result)

    def payment(self):
        parsed = urlsplit(self.path)
        if parsed.path not in ('/pay', '/preview', '/slow', '/flaky'):
            self.send_body(404, {'error': 'Unknown payment demo endpoint'})
            return
        query = parse_qs(parsed.query)
        request_id = self.headers.get('x-request-id') or str(uuid.uuid4())
        attempt = 1
        status = 200
        if parsed.path == '/slow':
            time.sleep(3)
        elif parsed.path == '/flaky':
            key = query.get('key', [request_id])[0][:200]
            attempt = attempt_for(key)
            status = 503 if attempt <= 2 else 200
        result = dict(service='payment', version=VERSION, pod=socket.gethostname(),
                      path=parsed.path, attempt=attempt, request_id=request_id,
                      message='Demo only. No payment was processed.',
                      received_canary=self.headers.get('x-canary'),
                      received_cookie=self.headers.get('cookie'))
        print(json.dumps({'event': 'payment', 'http_status': status,
                          'host': self.headers.get('host'), **result}), flush=True)
        self.send_body(status, result)

if __name__ == '__main__':
    print(json.dumps({'event': 'startup', 'role': ROLE, 'version': VERSION,
                      'port': PORT}), flush=True)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
