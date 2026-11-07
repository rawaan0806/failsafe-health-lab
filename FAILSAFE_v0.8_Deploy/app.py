"""Public WSGI entrypoint for FAILSAFE hackathon demo.

No patient data is collected, retained, or needed. All inputs/outputs are synthetic.
Use `gunicorn app:app` on hosted Linux; `python server.py` locally on Windows.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import monotonic
from urllib.parse import urlsplit

from server import calculate, calculate_trace, MAX_BODY
from outpatient import analyze as analyze_outpatient

ROOT = Path(__file__).resolve().parent
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/lab": ("lab.html", "text/html; charset=utf-8"),
    "/lab.html": ("lab.html", "text/html; charset=utf-8"),
    "/advanced": ("advanced.html", "text/html; charset=utf-8"),
    "/outpatient": ("outpatient.html", "text/html; charset=utf-8"),
    "/outpatient.html": ("outpatient.html", "text/html; charset=utf-8"),
    "/assets/outpatient.js": ("assets/outpatient.js", "text/javascript; charset=utf-8"),
    "/assets/outpatient.css": ("assets/outpatient.css", "text/css; charset=utf-8"),
    "/advanced.html": ("advanced.html", "text/html; charset=utf-8"),
    "/assets/lab.js": ("assets/lab.js", "text/javascript; charset=utf-8"),
    "/assets/styles.css": ("assets/styles.css", "text/css; charset=utf-8"),
    "/assets/home.js": ("assets/home.js", "text/javascript; charset=utf-8"),
    "/assets/favicon.svg": ("assets/favicon.svg", "image/svg+xml"),
    "/assets/simulation-screenshot.webp": ("assets/simulation-screenshot.webp", "image/webp"),
}

# One demo server, limited resources. This is not intended as a clinical service.
RECENT_REQUESTS = deque()
RATE_LOCK = Lock()
API_SLOTS = BoundedSemaphore(2)
RATE_WINDOW_SECONDS = 60
MAX_GLOBAL_API_CALLS = 45


def _response(start_response, status: str, payload: bytes, mime: str, *, api=False, extra=None):
    headers = [
        ('Content-Type', mime),
        ('Content-Length', str(len(payload))),
        ('X-Content-Type-Options', 'nosniff'),
        ('X-Frame-Options', 'DENY'),
        ('Referrer-Policy', 'no-referrer'),
        ('Permissions-Policy', 'camera=(), microphone=(), geolocation=()'),
        ('Cache-Control', 'no-store' if api else 'public, max-age=300'),
    ]
    if extra:
        headers.extend(extra)
    start_response(status, headers)
    return [payload]


def _json(start_response, status, data, *, extra=None):
    body = json.dumps(data, allow_nan=False, separators=(',', ':')).encode('utf-8')
    return _response(start_response, status, body, 'application/json; charset=utf-8', api=True, extra=extra)


def app(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET').upper()

    if method in ('GET', 'HEAD'):
        if path in FILES:
            filename, mime = FILES[path]
            payload = (ROOT / filename).read_bytes()
            return _response(start_response, '200 OK', payload if method == 'GET' else b'', mime)
        if path == '/health':
            return _json(start_response, '200 OK', {'ok': True, 'version': '1.3', 'synthetic_only': True})
        if path == '/favicon.ico':
            return _response(start_response, '204 No Content', b'', 'image/x-icon')
        return _json(start_response, '404 Not Found', {'error': 'Not found'})

    if method != 'POST':
        return _json(start_response, '405 Method Not Allowed', {'error': 'Method not allowed'}, extra=[('Allow', 'GET, HEAD, POST')])
    if path not in ('/api/simulate', '/api/trace', '/api/outpatient'):
        return _json(start_response, '404 Not Found', {'error': 'Not found'})

    # Only a JSON body from the same-origin app is needed. No CORS headers.
    if environ.get('CONTENT_TYPE', '').split(';', 1)[0].strip().lower() != 'application/json':
        return _json(start_response, '415 Unsupported Media Type', {'error': 'Use application/json'})
    origin = environ.get('HTTP_ORIGIN')
    if origin and urlsplit(origin).netloc.lower() != environ.get('HTTP_HOST', '').lower():
        return _json(start_response, '403 Forbidden', {'error': 'Cross-origin requests are not supported'})
    try:
        size = int(environ.get('CONTENT_LENGTH') or '-1')
    except ValueError:
        size = -1
    if not 0 < size <= MAX_BODY:
        return _json(start_response, '413 Content Too Large', {'error': 'Request missing or too large'})

    now = monotonic()
    with RATE_LOCK:
        while RECENT_REQUESTS and RECENT_REQUESTS[0] <= now - RATE_WINDOW_SECONDS:
            RECENT_REQUESTS.popleft()
        if len(RECENT_REQUESTS) >= MAX_GLOBAL_API_CALLS:
            return _json(start_response, '429 Too Many Requests', {'error': 'Demo is busy. Try again shortly.'}, extra=[('Retry-After', '30')])
        RECENT_REQUESTS.append(now)

    if not API_SLOTS.acquire(blocking=False):
        return _json(start_response, '503 Service Unavailable', {'error': 'Simulation engine is busy. Please try again.'}, extra=[('Retry-After', '3')])
    try:
        data = json.loads(environ['wsgi.input'].read(size))
        result = analyze_outpatient(data) if path == '/api/outpatient' else (calculate(data) if path == '/api/simulate' else calculate_trace(data))
        return _json(start_response, '200 OK', result)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        return _json(start_response, '400 Bad Request', {'error': str(exc)})
    except Exception:
        # Never show internal stack traces to public callers.
        return _json(start_response, '500 Internal Server Error', {'error': 'Unable to run simulation'})
    finally:
        API_SLOTS.release()

application = app
