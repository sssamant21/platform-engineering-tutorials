# Chapter 073 — Resilient HTTP Sessions, Pagination and Circuit Breaker SRE/DBRE Lab

**Python 3.11+ | requests 2.x | Local HTTP integration tests | Synthetic data only**

## Architecture
\`\`\`text
Client(requests.Session + HTTPAdapter, retries disabled)
 -> GET /v1/telemetry?cursor=<opaque>&limit=2
 -> loopback ThreadingHTTPServer
 -> PostgreSQL/Elasticsearch/Kafka synthetic records
 -> retry/backoff + cursor validation + circuit breaker
\`\`\`
The server binds \`127.0.0.1\` on an ephemeral port. No external APIs, cloud credentials or production data are used.

## 1. requirements.txt
\`\`\`text
requests>=2.32,<3
\`\`\`
Use an approved lockfile with reviewed hashes in production.

## 2. Complete client — resilient_client.py
\`\`\`python
"""Offline-only resilient paginated API client with bounded retries and breaker."""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import time
from typing import Callable
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter

MAX_BODY = 16384
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
POLICY = {
    "postgresql": ("replication_lag", "seconds"),
    "elasticsearch": ("search_latency", "milliseconds"),
    "kafka": ("consumer_lag", "messages"),
}
RETRYABLE = frozenset((429, 502, 503, 504))

class APIError(RuntimeError): pass
class ContractError(APIError): pass
class CircuitOpen(APIError): pass

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

def validate(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"engine", "service", "metric", "unit", "value"}:
        raise ContractError("invalid schema")
    engine, service = raw["engine"], raw["service"]
    if not isinstance(engine, str) or engine not in POLICY:
        raise ContractError("invalid engine")
    if not isinstance(service, str) or NAME.fullmatch(service) is None:
        raise ContractError("invalid service")
    metric, unit = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ContractError("invalid metric or unit")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ContractError("invalid value type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ContractError("invalid value") from exc
    if not math.isfinite(number) or number < 0:
        raise ContractError("invalid value")
    return Reading(engine, service, number)

class Breaker:
    def __init__(self, threshold: int = 3, cooldown: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        if type(threshold) is not int or threshold < 1:
            raise ValueError("invalid threshold")
        if type(cooldown) not in (int, float) or not math.isfinite(cooldown) or cooldown <= 0:
            raise ValueError("invalid cooldown")
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.failures = 0
        self.opened_at: float | None = None
        self.probe_in_progress = False

    def before(self) -> None:
        if self.opened_at is None:
            return
        if self.clock() - self.opened_at < self.cooldown or self.probe_in_progress:
            raise CircuitOpen("circuit open")
        self.probe_in_progress = True

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None
        self.probe_in_progress = False

    def failure(self) -> None:
        self.failures += 1
        if self.probe_in_progress or self.failures >= self.threshold:
            self.opened_at = self.clock()
        self.probe_in_progress = False

    def release_probe(self) -> None:
        self.probe_in_progress = False

class Client:
    def __init__(
        self, base_url: str, *, attempts: int = 3, timeout: tuple[float, float] = (1.0, 1.0),
        max_delay: float = 0.2, sleep: Callable[[float], None] = time.sleep,
        breaker: Breaker | None = None,
    ):
        parts = urlsplit(base_url)
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError("invalid port") from exc
        if (parts.scheme != "http" or parts.hostname != "127.0.0.1" or port is None
                or parts.username is not None or parts.password is not None
                or parts.path not in ("", "/") or parts.query or parts.fragment):
            raise ValueError("loopback fixture URL required")
        if type(attempts) is not int or not 1 <= attempts <= 5:
            raise ValueError("invalid attempts")
        if (not isinstance(timeout, tuple) or len(timeout) != 2 or
                any(type(t) not in (int, float) or not math.isfinite(t) or not 0 < t <= 10 for t in timeout)):
            raise ValueError("invalid timeout")
        if type(max_delay) not in (int, float) or not math.isfinite(max_delay) or not 0 <= max_delay <= 2:
            raise ValueError("invalid max delay")
        self.base_url = base_url.rstrip("/")
        self.attempts, self.timeout, self.max_delay = attempts, timeout, max_delay
        self.sleep = sleep
        self.breaker = breaker or Breaker()
        self.session = requests.Session()
        self.session.trust_env = False  # Avoid environment proxies for loopback fixture.
        self.session.max_redirects = 0
        adapter = HTTPAdapter(pool_connections=2, pool_maxsize=2, pool_block=True, max_retries=0)
        self.session.mount("http://", adapter)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _page(self, cursor: str | None, limit: int) -> dict[str, object]:
        self.breaker.before()
        params: dict[str, str | int] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        for attempt in range(self.attempts):
            try:
                with self.session.get(
                    self.base_url + "/v1/telemetry", params=params, timeout=self.timeout,
                    allow_redirects=False, stream=True,
                    headers={"Accept": "application/json"},
                ) as response:
                    status = response.status_code
                    if status in RETRYABLE:
                        self.breaker.failure()
                        if attempt + 1 == self.attempts:
                            raise APIError("transient HTTP status exhausted")
                        delay = min(self.max_delay, 0.025 * (2 ** attempt))
                        self.sleep(delay)
                        # Each retry counts as an upstream failure; the breaker may
                        # open before retries are exhausted.
                        self.breaker.before()
                        continue
                    if status != 200:
                        self.breaker.release_probe()
                        raise APIError("nonretryable HTTP status")
                    body = response.raw.read(MAX_BODY + 1, decode_content=True)
                    if len(body) > MAX_BODY:
                        self.breaker.release_probe()
                        raise ContractError("response too large")
                    if response.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                        self.breaker.release_probe()
                        raise ContractError("invalid content type")
                try:
                    result = requests.models.complexjson.loads(body)
                except (ValueError, UnicodeDecodeError) as exc:
                    self.breaker.release_probe()
                    raise ContractError("invalid JSON") from exc
                if not isinstance(result, dict) or set(result) != {"items", "next_cursor"}:
                    self.breaker.release_probe()
                    raise ContractError("invalid page schema")
                self.breaker.success()
                return result
            except (requests.ConnectionError, requests.Timeout):
                self.breaker.failure()
                if attempt + 1 == self.attempts:
                    raise APIError("transport exhausted") from None
                self.sleep(min(self.max_delay, 0.025 * (2 ** attempt)))
                self.breaker.before()
        raise AssertionError("unreachable")

    def collect(self, *, limit: int = 2, max_pages: int = 10, max_items: int = 100) -> list[Reading]:
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("invalid limit")
        if type(max_pages) is not int or not 1 <= max_pages <= 50:
            raise ValueError("invalid max_pages")
        if type(max_items) is not int or not 1 <= max_items <= 1000:
            raise ValueError("invalid max_items")
        cursor: str | None = None
        seen: set[str] = set()
        identities: set[tuple[str, str]] = set()
        readings: list[Reading] = []
        for _ in range(max_pages):
            page = self._page(cursor, limit)
            items, next_cursor = page["items"], page["next_cursor"]
            if not isinstance(items, list) or len(items) > limit:
                raise ContractError("invalid page size")
            for raw in items:
                reading = validate(raw)
                identity = (reading.engine, reading.service)
                if identity in identities:
                    raise ContractError("duplicate telemetry identity")
                identities.add(identity)
                readings.append(reading)
                if len(readings) > max_items:
                    raise ContractError("item cap exceeded")
            if next_cursor is None:
                return readings
            if (not isinstance(next_cursor, str) or not 1 <= len(next_cursor) <= 128
                    or NAME.fullmatch(next_cursor) is None or next_cursor in seen):
                raise ContractError("invalid or repeated cursor")
            seen.add(next_cursor)
            cursor = next_cursor
        raise ContractError("page cap exceeded")
\`\`\`

## 3. Complete integration tests — test_resilient_client.py
\`\`\`python
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import unittest
from urllib.parse import parse_qs, urlsplit

from resilient_client import APIError, Breaker, CircuitOpen, Client, ContractError

ROWS = [
    {"engine":"postgresql","service":"pg-replica","metric":"replication_lag","unit":"seconds","value":45},
    {"engine":"elasticsearch","service":"es-search","metric":"search_latency","unit":"milliseconds","value":650},
    {"engine":"kafka","service":"kafka-worker","metric":"consumer_lag","unit":"messages","value":10000},
]

class Fixture(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address):
        super().__init__(address, Handler)
        self.calls = 0
        self.fail_status = 0
        self.fail_remaining = 0
        self.repeat_cursor = False
        self.override = None
        self.content_type = "application/json"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return
    def do_GET(self):
        self.server.calls += 1
        if self.server.fail_remaining:
            self.server.fail_remaining -= 1
            self.send_response(self.server.fail_status)
            self.send_header("Content-Length","0")
            self.end_headers()
            return
        parts = urlsplit(self.path)
        if parts.path != "/v1/telemetry":
            self.send_error(404)
            return
        params = parse_qs(parts.query)
        cursor = params.get("cursor", ["start"])[0]
        limit = int(params.get("limit", ["2"])[0])
        offset = {"start":0, "page2":2}.get(cursor, -1)
        if offset < 0:
            self.send_error(400)
            return
        next_cursor = "page2" if offset + limit < len(ROWS) else None
        if self.server.repeat_cursor:
            next_cursor = "page2"
        payload = {"items": ROWS[offset:offset+limit], "next_cursor": next_cursor}
        body = json.dumps(payload).encode() if self.server.override is None else self.server.override
        self.send_response(200)
        self.send_header("Content-Type", self.server.content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

@contextmanager
def server():
    srv = Fixture(("127.0.0.1",0))
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv, f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=3)

class ResilienceTests(unittest.TestCase):
    def test_pagination(self):
        with server() as (srv, base), Client(base, sleep=lambda _:None) as client:
            self.assertEqual(len(client.collect()),3)
            self.assertEqual(srv.calls,2)

    def test_503_recovery(self):
        with server() as (srv, base), Client(base, sleep=lambda _:None) as client:
            srv.fail_status, srv.fail_remaining = 503, 1
            self.assertEqual(len(client.collect()),3)
            self.assertEqual(srv.calls,3)

    def test_429_recovery(self):
        with server() as (srv, base), Client(base, sleep=lambda _:None) as client:
            srv.fail_status, srv.fail_remaining = 429, 1
            self.assertEqual(len(client.collect()),3)

    def test_401_terminal(self):
        with server() as (srv, base), Client(base, sleep=lambda _:None) as client:
            srv.fail_status, srv.fail_remaining = 401, 5
            with self.assertRaises(APIError):
                client.collect()
            self.assertEqual(srv.calls,1)

    def test_repeated_cursor(self):
        with server() as (srv, base), Client(base) as client:
            srv.repeat_cursor = True
            with self.assertRaises(ContractError):
                client.collect()

    def test_page_cap(self):
        with server() as (_, base), Client(base) as client:
            with self.assertRaises(ContractError):
                client.collect(max_pages=1)

    def test_item_cap(self):
        with server() as (_, base), Client(base) as client:
            with self.assertRaises(ContractError):
                client.collect(max_items=2)

    def test_bad_json(self):
        with server() as (srv, base), Client(base) as client:
            srv.override = b"{broken"
            with self.assertRaises(ContractError):
                client.collect()

    def test_bad_content_type(self):
        with server() as (srv, base), Client(base) as client:
            srv.content_type = "text/plain"
            with self.assertRaises(ContractError):
                client.collect()

    def test_oversized_body(self):
        with server() as (srv, base), Client(base) as client:
            srv.override = b"x" * 20000
            with self.assertRaises(ContractError):
                client.collect()

    def test_bad_base(self):
        for url in ("https://example.com","http://localhost:8080","http://127.0.0.1:8000/evil"):
            with self.assertRaises(ValueError):
                Client(url)

    def test_bad_options(self):
        with server() as (_, base):
            for attempts in (0,6,True):
                with self.assertRaises(ValueError):
                    Client(base,attempts=attempts)

    def test_breaker_opens_and_recovers(self):
        now = [0.0]
        breaker = Breaker(threshold=2,cooldown=5.0,clock=lambda:now[0])
        breaker.failure()
        breaker.failure()
        with self.assertRaises(CircuitOpen):
            breaker.before()
        now[0] = 5.0
        breaker.before()
        with self.assertRaises(CircuitOpen):
            breaker.before()
        breaker.success()
        breaker.before()
        self.assertEqual(breaker.failures,0)

    def test_breaker_reopens_on_failed_probe(self):
        now = [0.0]
        breaker = Breaker(threshold=1,cooldown=2.0,clock=lambda:now[0])
        breaker.failure()
        now[0] = 2.0
        breaker.before()
        breaker.failure()
        with self.assertRaises(CircuitOpen):
            breaker.before()

    def test_open_breaker_blocks_http(self):
        with server() as (srv, base):
            breaker = Breaker(threshold=1,cooldown=100.0)
            breaker.failure()
            with Client(base,breaker=breaker) as client:
                with self.assertRaises(CircuitOpen):
                    client.collect()
            self.assertEqual(srv.calls,0)

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 4. Run
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q resilient_client.py test_resilient_client.py
python -m unittest -v test_resilient_client.py
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, then \`py -m unittest -v test_resilient_client.py\`.

## 5. Optional CI quality gate
\`\`\`yaml
name: chapter-073-resilience
on: workflow_dispatch
jobs:
  integration:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Require extracted source
        run: |
          test -f resilient_client.py
          test -f test_resilient_client.py
          test -f requirements.txt
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Loopback integration tests
        run: python -m unittest -v test_resilient_client.py
\`\`\`
This is a template. Extract Markdown code blocks to files, pin reviewed GitHub Actions SHAs and dependency hashes, and test on an approved runner before enabling.

## 6. Incident drills
1. Inject one \`503\`; confirm retry and recovery.
2. Inject one \`429\`; confirm bounded retry.
3. Inject \`401\`; confirm terminal failure.
4. Inject persistent \`503\`; verify breaker opens.
5. Advance fake monotonic clock; verify half-open probe.
6. Fail half-open probe; verify breaker reopens.
7. Repeat cursor; verify loop detection.
8. Enforce one-page cap; verify fail-closed.
9. Enforce two-item cap; verify rejection.
10. Return malformed JSON and unexpected content type.
11. Return 20KB body; verify size limit.
12. Reject untrusted host and URL path.
13. Reject invalid numeric metric and duplicate identities.
14. Simulate connection pool pressure; inspect worker concurrency.
15. Simulate Retry-After and document a bounded policy extension.
16. Simulate TLS trust failure (conceptual; local fixture uses HTTP).
17. Simulate duplicate adapter/app retries and remove one layer.
18. Verify no cursor or credentials appear in diagnostics.

## 7. Production runbooks
**429/503 storm:** cap attempts, reduce concurrency, introduce bounded jitter and coordinate with API owner.

**Circuit OPEN:** verify upstream health, wait cooldown, allow controlled probe and avoid manual force-close during active incident.

**Cursor corruption:** stop ingestion, preserve sanitized page sequence, reconcile duplicates and resume from approved snapshot.

**Pool saturation:** inspect blocked acquisitions and worker count, adjust session-per-worker strategy and pool sizing.

**Rollback:** restore approved retry and pagination policy, rerun loopback integration tests and verify SLOs.

## 8. 100-point assessment
| Category | Points |
|---|---:|
| Session and connection pooling design | 15 |
| Pagination, cursor and data validation | 20 |
| Retry/backoff and 429/5xx behavior | 20 |
| Circuit breaker states and tests | 20 |
| Loopback integration tests and fault injection | 15 |
| Runbooks, security and CI controls | 10 |

**Pass:** 90/100 with required tests and security checks independently executed. This lab demonstrates deterministic backoff, not full production jitter, Retry-After date parsing, TLS or global deadlines. Publication is not execution evidence.
