# Chapter 071 — Reliable HTTP API Client SRE/DBRE Lab

**Python 3.11+ | Standard library only | Local loopback integration tests | No cloud credentials**

## 1. Lab topology
\`\`\`text
Python client (urllib.request)
  -> loopback HTTP server (127.0.0.1, ephemeral port)
  -> synthetic /health and /telemetry/{postgresql,elasticsearch,kafka}
  -> fault injection: 503, 429, 401, malformed JSON, bad schema, oversized body
  -> unittest integration tests + mock backoff
\`\`\`
Do not expose the fixture server publicly. No production databases or remote APIs are contacted.

## 2. Complete API client — api_client.py
\`\`\`python
"""Bounded, validated, loopback-only HTTP client for synthetic SRE telemetry."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 16384
METRICS = {
    "postgresql": ("replication_lag", "seconds"),
    "elasticsearch": ("search_latency", "milliseconds"),
    "kafka": ("consumer_lag", "messages"),
}
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
RETRYABLE = frozenset((429, 502, 503, 504))

class APIError(RuntimeError):
    pass

class ContractError(APIError):
    pass

class TransportError(APIError):
    pass

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def validate_payload(raw: object, engine: str) -> Reading:
    if engine not in METRICS:
        raise ContractError("unknown engine")
    if not isinstance(raw, dict) or set(raw) != {"engine", "service", "metric", "unit", "value"}:
        raise ContractError("invalid schema")
    service = raw["service"]
    if raw["engine"] != engine or not isinstance(service, str) or NAME.fullmatch(service) is None:
        raise ContractError("invalid source")
    metric, unit = METRICS[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ContractError("invalid metric or unit")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ContractError("invalid numeric type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ContractError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise ContractError("invalid numeric value")
    return Reading(engine, service, number)

class Client:
    def __init__(
        self,
        base_url: str,
        *,
        attempts: int = 3,
        timeout: float = 1.0,
        max_delay: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ):
        parsed = urlsplit(base_url)
        # Only loopback fixture server is allowed; production code needs HTTPS + trusted hosts.
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.path not in ("", "/")
                or parsed.port is None):
            raise ValueError("base URL must be loopback http://127.0.0.1:<port>")
        if type(attempts) is not int or not 1 <= attempts <= 5:
            raise ValueError("attempts must be 1..5")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 10:
            raise ValueError("timeout must be finite and 0..10 seconds")
        if type(max_delay) not in (int, float) or not math.isfinite(max_delay) or not 0 <= max_delay <= 2:
            raise ValueError("max_delay must be finite and 0..2 seconds")
        self.base_url = base_url.rstrip("/")
        self.attempts = attempts
        self.timeout = timeout
        self.max_delay = max_delay
        self.sleep = sleep
        self.opener = build_opener(NoRedirect())

    def get(self, engine: str) -> Reading:
        if engine not in METRICS:
            raise ContractError("unknown engine")
        request = Request(
            self.base_url + "/telemetry/" + engine,
            headers={"Accept": "application/json", "User-Agent": "ch071-offline-lab/1"},
            method="GET",
        )
        for attempt in range(self.attempts):
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    if response.status != 200:
                        raise APIError("unexpected success status")
                    if response.headers.get_content_type() != "application/json":
                        raise ContractError("unexpected content type")
                    raw = response.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise ContractError("response too large")
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ContractError("invalid JSON") from exc
                return validate_payload(payload, engine)
            except HTTPError as exc:
                if exc.code not in RETRYABLE or attempt + 1 == self.attempts:
                    raise APIError(f"HTTP status {exc.code}") from None
            except (URLError, TimeoutError, OSError):
                if attempt + 1 == self.attempts:
                    raise TransportError("transport unavailable") from None
            delay = min(self.max_delay, 0.05 * (2 ** attempt))
            self.sleep(delay)
        raise AssertionError("unreachable")

def main() -> int:
    print("Run python -m unittest -v test_api_client.py to exercise the local server")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
\`\`\`

## 3. Complete fixture server and integration tests — test_api_client.py
\`\`\`python
"""Real local HTTP integration tests with deterministic fault injection."""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from threading import Thread
import unittest

from api_client import APIError, Client, ContractError, Reading, TransportError, validate_payload

PAYLOADS = {
    "postgresql": {"engine": "postgresql", "service": "pg-replica", "metric": "replication_lag", "unit": "seconds", "value": 45},
    "elasticsearch": {"engine": "elasticsearch", "service": "es-search", "metric": "search_latency", "unit": "milliseconds", "value": 650},
    "kafka": {"engine": "kafka", "service": "kafka-worker", "metric": "consumer_lag", "unit": "messages", "value": 10000},
}

class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address):
        super().__init__(address, Handler)
        self.fail_status = 0
        self.fail_remaining = 0
        self.override_body = None
        self.override_content_type = None
        self.calls = 0

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # Suppress synthetic test traffic.

    def do_GET(self):
        self.server.calls += 1
        if self.server.fail_remaining > 0:
            self.server.fail_remaining -= 1
            self.send_response(self.server.fail_status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/health":
            payload = b'{"ok":true}'
        elif self.path.startswith("/telemetry/") and self.path.split("/")[-1] in PAYLOADS:
            payload = json.dumps(PAYLOADS[self.path.split("/")[-1]]).encode("utf-8")
        else:
            self.send_error(404)
            return
        if self.server.override_body is not None:
            payload = self.server.override_body
        self.send_response(200)
        self.send_header("Content-Type", self.server.override_content_type or "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

@contextmanager
def server():
    instance = FixtureServer(("127.0.0.1", 0))
    thread = Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance, f"http://127.0.0.1:{instance.server_port}"
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)

class ContractTests(unittest.TestCase):
    def test_all_engines(self):
        for engine, payload in PAYLOADS.items():
            with self.subTest(engine=engine):
                self.assertEqual(validate_payload(payload, engine).engine, engine)

    def test_bad_schema(self):
        with self.assertRaises(ContractError):
            validate_payload({"bad": 1}, "postgresql")

    def test_unknown_engine(self):
        with self.assertRaises(ContractError):
            validate_payload(PAYLOADS["postgresql"], "mysql")

    def test_mismatched_engine(self):
        with self.assertRaises(ContractError):
            validate_payload(PAYLOADS["postgresql"], "kafka")

    def test_bad_unit(self):
        with self.assertRaises(ContractError):
            validate_payload({**PAYLOADS["postgresql"], "unit": "milliseconds"}, "postgresql")

    def test_bad_metric(self):
        with self.assertRaises(ContractError):
            validate_payload({**PAYLOADS["postgresql"], "metric": "wrong"}, "postgresql")

    def test_bad_service(self):
        with self.assertRaises(ContractError):
            validate_payload({**PAYLOADS["postgresql"], "service": "../secret"}, "postgresql")

    def test_bad_values(self):
        for value in (True, -1, math.nan, math.inf, "45"):
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    validate_payload({**PAYLOADS["postgresql"], "value": value}, "postgresql")

class HTTPIntegrationTests(unittest.TestCase):
    def test_get_all_engines(self):
        with server() as (_, base):
            client = Client(base, sleep=lambda _: None)
            for engine in PAYLOADS:
                with self.subTest(engine=engine):
                    self.assertIsInstance(client.get(engine), Reading)

    def test_503_then_success(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 503, 1
            delays = []
            result = Client(base, sleep=delays.append).get("postgresql")
            self.assertEqual(result.value, 45)
            self.assertEqual(srv.calls, 2)
            self.assertEqual(len(delays), 1)

    def test_429_then_success(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 429, 2
            result = Client(base, sleep=lambda _: None).get("kafka")
            self.assertEqual(result.engine, "kafka")
            self.assertEqual(srv.calls, 3)

    def test_401_not_retried(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 401, 5
            with self.assertRaises(APIError):
                Client(base, sleep=lambda _: None).get("postgresql")
            self.assertEqual(srv.calls, 1)

    def test_503_exhausted(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 503, 5
            with self.assertRaises(APIError):
                Client(base, attempts=3, sleep=lambda _: None).get("postgresql")
            self.assertEqual(srv.calls, 3)

    def test_invalid_json(self):
        with server() as (srv, base):
            srv.override_body = b"{not-json"
            with self.assertRaises(ContractError):
                Client(base).get("postgresql")
            self.assertEqual(srv.calls, 1)

    def test_invalid_content_type(self):
        with server() as (srv, base):
            srv.override_content_type = "text/plain"
            with self.assertRaises(ContractError):
                Client(base).get("postgresql")

    def test_oversized(self):
        with server() as (srv, base):
            srv.override_body = b"x" * 20000
            with self.assertRaises(ContractError):
                Client(base).get("postgresql")

    def test_schema_error_not_retried(self):
        with server() as (srv, base):
            srv.override_body = b'{"invalid":true}'
            with self.assertRaises(ContractError):
                Client(base).get("postgresql")
            self.assertEqual(srv.calls, 1)

    def test_invalid_base_host(self):
        for base in ("https://example.com", "http://localhost:8080",
                     "http://127.0.0.2:8080", "http://127.0.0.1:8080/evil"):
            with self.subTest(base=base):
                with self.assertRaises(ValueError):
                    Client(base)

    def test_invalid_options(self):
        with server() as (_, base):
            for attempts in (0, 6, True):
                with self.assertRaises(ValueError):
                    Client(base, attempts=attempts)
            for timeout in (0, -1, math.nan, math.inf, True):
                with self.assertRaises(ValueError):
                    Client(base, timeout=timeout)

    def test_unknown_engine_no_request(self):
        with server() as (srv, base):
            with self.assertRaises(ContractError):
                Client(base).get("mysql")
            self.assertEqual(srv.calls, 0)

    def test_transport_failure(self):
        # Deterministic invalid port after the local fixture is closed.
        with server() as (_, base):
            client = Client(base, attempts=1)
        with self.assertRaises(TransportError):
            client.get("postgresql")

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 4. Run
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q api_client.py test_api_client.py
python -m unittest -v test_api_client.py
python api_client.py
\`\`\`
Windows: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, then \`py -m unittest -v test_api_client.py\`. The tests open an ephemeral loopback port and require local socket permissions.

## 5. Optional pytest, lint and CI
\`\`\`bash
python -m pip install 'pytest>=8,<10' 'ruff>=0.13,<0.15'
python -m pytest -v test_api_client.py
ruff check api_client.py test_api_client.py
ruff format api_client.py test_api_client.py
ruff format --check api_client.py test_api_client.py
\`\`\`
CI workflow template (not activated; source blocks must be extracted and dependencies pinned):
\`\`\`yaml
name: chapter-071-http
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify extracted source
        run: |
          test -f api_client.py
          test -f test_api_client.py
      - name: Local HTTP integration tests
        run: python -m unittest -v test_api_client.py
\`\`\`
Production CI must use reviewed immutable action SHAs, approved dependencies and isolated runners.

## 6. Failure injection and troubleshooting
1. Force one \`503\`, confirm retry and recovery.
2. Force two \`429\` responses, confirm bounded retry.
3. Force \`401\`, confirm no retry.
4. Force repeated \`503\`, confirm retry exhaustion.
5. Return malformed JSON and reject without retry.
6. Return unexpected content type and reject.
7. Return a 20KB response and reject at 16KB cap.
8. Return invalid units, engine and service identifiers.
9. Pass NaN, Infinity, boolean and negative metric values.
10. Attempt remote host, credentials in URL or untrusted path.
11. Close fixture server before request and confirm transport error.
12. Reduce timeout and investigate latency without increasing retry storms.
13. Simulate an untrusted redirect; ensure redirect policy rejects it.
14. Verify no secrets or raw payloads appear in diagnostics.

## 7. Production runbooks
**High 5xx:** inspect gateway/upstream health, cap retry amplification, use bounded backoff and restore known-good deployment.

**429 storm:** reduce concurrency, honor rate limits, coordinate with service owner and validate quotas.

**Auth 401/403:** inspect scopes and credential lifecycle; rotate through approved secrets system; never blind retry.

**Schema drift:** compare versioned contract, patch parser, add regression tests and roll back if necessary.

**Transport/TLS failure:** inspect DNS, route, CA trust, proxy and service endpoint; never disable TLS verification.

**Rollback:** restore approved client/configuration, rerun loopback integration tests, verify production SLO and record change approval.

## 8. 100-point acceptance
| Area | Points |
|---|---:|
| HTTP fundamentals and status semantics | 15 |
| Strict JSON and numeric validation | 20 |
| Retry policy and bounded timeouts | 20 |
| Real loopback integration tests | 20 |
| Security controls and diagnostics | 10 |
| Incident drills, CI and runbooks | 15 |

**Pass:** 90/100 with all mandatory security controls passing. Publication is not evidence of successful test execution.
