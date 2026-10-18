# Chapter 072 — Secure HTTP Authentication and API Client SRE/DBRE Lab

**Python 3.11+ | Standard library | Loopback integration tests | Synthetic credentials only**

## Architecture and safety
A Python client sends API-key or bearer-token credentials in headers to a disposable local \`ThreadingHTTPServer\` bound to \`127.0.0.1\` on an ephemeral port. The server simulates authentication, authorization, 429/503, redirects, malformed payloads and telemetry. No cloud services, real secrets, external network calls or production databases are used. **Plain HTTP is allowed only for the loopback fixture.** Production clients require verified HTTPS and trusted hosts.

## Files
\`\`\`text
ch072/
  secure_client.py
  test_secure_client.py
  .github/workflows/ch072-quality.yml  # optional template
\`\`\`

## 1. Application — secure_client.py
\`\`\`python
"""Loopback-only authenticated HTTP client; no production credentials."""
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

MAX_BODY = 8192
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
RETRYABLE = frozenset((429, 502, 503, 504))
POLICY = {
    "postgresql": ("replication_lag", "seconds"),
    "elasticsearch": ("search_latency", "milliseconds"),
    "kafka": ("consumer_lag", "messages"),
}

class ClientError(RuntimeError):
    pass

class AuthenticationError(ClientError):
    pass

class AuthorizationError(ClientError):
    pass

class RateLimitError(ClientError):
    pass

class ContractError(ClientError):
    pass

class TransportError(ClientError):
    pass

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

@dataclass(frozen=True)
class Credential:
    scheme: str
    secret: str

    def __post_init__(self) -> None:
        if self.scheme not in ("api_key", "bearer"):
            raise ValueError("unsupported authentication scheme")
        if not isinstance(self.secret, str) or not self.secret or len(self.secret) > 4096:
            raise ValueError("invalid credential")
        if any(ord(char) < 33 or ord(char) > 126 for char in self.secret):
            raise ValueError("invalid credential characters")

    def header(self) -> tuple[str, str]:
        if self.scheme == "api_key":
            return ("X-API-Key", self.secret)
        return ("Authorization", "Bearer " + self.secret)

    def __repr__(self) -> str:
        return "Credential(scheme=" + repr(self.scheme) + ", secret=<redacted>)"

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def parse_payload(raw: object, engine: str) -> Reading:
    if engine not in POLICY or not isinstance(raw, dict):
        raise ContractError("invalid telemetry")
    if set(raw) != {"engine", "service", "metric", "unit", "value"}:
        raise ContractError("invalid telemetry schema")
    service = raw["service"]
    if raw["engine"] != engine or not isinstance(service, str) or NAME.fullmatch(service) is None:
        raise ContractError("invalid telemetry source")
    metric, unit = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ContractError("invalid telemetry units")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ContractError("invalid metric type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ContractError("invalid metric value") from exc
    if not math.isfinite(number) or number < 0:
        raise ContractError("invalid metric value")
    return Reading(engine, service, number)

class SecureClient:
    def __init__(
        self, base_url: str, credential: Credential, *,
        attempts: int = 3, timeout: float = 1.0, max_delay: float = 0.1,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        parts = urlsplit(base_url)
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError("invalid port") from exc
        if (parts.scheme != "http" or parts.hostname != "127.0.0.1" or port is None
                or parts.username is not None or parts.password is not None
                or parts.path not in ("", "/") or parts.query or parts.fragment):
            raise ValueError("only local loopback fixture is allowed")
        if not isinstance(credential, Credential):
            raise TypeError("credential required")
        if type(attempts) is not int or not 1 <= attempts <= 5:
            raise ValueError("invalid retry budget")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 10:
            raise ValueError("invalid timeout")
        if type(max_delay) not in (int, float) or not math.isfinite(max_delay) or not 0 <= max_delay <= 2:
            raise ValueError("invalid delay")
        self.base_url = base_url.rstrip("/")
        self.credential = credential
        self.attempts = attempts
        self.timeout = timeout
        self.max_delay = max_delay
        self.sleep = sleep
        self.opener = build_opener(NoRedirect())

    def get(self, engine: str) -> Reading:
        if engine not in POLICY:
            raise ContractError("unknown engine")
        key, value = self.credential.header()
        request = Request(
            self.base_url + "/telemetry/" + engine,
            headers={key: value, "Accept": "application/json", "Cache-Control": "no-store"},
            method="GET",
        )
        for attempt in range(self.attempts):
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    if response.status != 200:
                        raise ClientError("unexpected status")
                    if response.headers.get_content_type() != "application/json":
                        raise ContractError("unexpected content type")
                    raw = response.read(MAX_BODY + 1)
                    if len(raw) > MAX_BODY:
                        raise ContractError("response too large")
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ContractError("invalid JSON") from exc
                return parse_payload(payload, engine)
            except HTTPError as exc:
                # Never echo the response body or Authorization header.
                if exc.code == 401:
                    raise AuthenticationError("authentication rejected") from None
                if exc.code == 403:
                    raise AuthorizationError("access denied") from None
                if exc.code not in RETRYABLE or attempt + 1 == self.attempts:
                    if exc.code == 429:
                        raise RateLimitError("rate limit exhausted") from None
                    raise ClientError("HTTP request failed") from None
            except (URLError, TimeoutError, OSError):
                if attempt + 1 == self.attempts:
                    raise TransportError("transport unavailable") from None
            # Deterministic bounded backoff for lab; production should add jitter
            # and account for Retry-After and a total end-to-end deadline.
            self.sleep(min(self.max_delay, 0.025 * (2 ** attempt)))
        raise AssertionError("unreachable")

def main() -> int:
    print("Run python -m unittest -v test_secure_client.py for local integration tests")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
\`\`\`

## 2. Integration and unit tests — test_secure_client.py
\`\`\`python
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from threading import Thread
import unittest

from secure_client import (
    AuthenticationError, AuthorizationError, ClientError, ContractError,
    Credential, RateLimitError, Reading, SecureClient, TransportError, parse_payload,
)

FIXTURES = {
    "postgresql": {"engine": "postgresql", "service": "pg-replica", "metric": "replication_lag", "unit": "seconds", "value": 45},
    "elasticsearch": {"engine": "elasticsearch", "service": "es-search", "metric": "search_latency", "unit": "milliseconds", "value": 650},
    "kafka": {"engine": "kafka", "service": "kafka-worker", "metric": "consumer_lag", "unit": "messages", "value": 10000},
}
FAKE_KEY = "synthetic-key-only"
FAKE_TOKEN = "synthetic-bearer-only"

class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address):
        super().__init__(address, Handler)
        self.calls = 0
        self.fail_status = 0
        self.fail_remaining = 0
        self.body_override = None
        self.content_type = "application/json"
        self.seen_auth = None
        self.force_redirect = False

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        self.server.calls += 1
        self.server.seen_auth = (self.headers.get("X-API-Key"), self.headers.get("Authorization"))
        if self.server.force_redirect:
            self.send_response(302)
            self.send_header("Location", "http://example.invalid/steal")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.server.fail_remaining:
            self.server.fail_remaining -= 1
            self.send_response(self.server.fail_status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        api_key = self.headers.get("X-API-Key")
        bearer = self.headers.get("Authorization")
        if api_key != FAKE_KEY and bearer != "Bearer " + FAKE_TOKEN:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Bearer realm="synthetic"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        engine = self.path.removeprefix("/telemetry/")
        if not self.path.startswith("/telemetry/") or engine not in FIXTURES:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(FIXTURES[engine]).encode() if self.server.body_override is None else self.server.body_override
        self.send_response(200)
        self.send_header("Content-Type", self.server.content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

@contextmanager
def server():
    srv = FixtureServer(("127.0.0.1", 0))
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv, f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=3)

class CredentialTests(unittest.TestCase):
    def test_api_key_header(self):
        self.assertEqual(Credential("api_key", FAKE_KEY).header(), ("X-API-Key", FAKE_KEY))

    def test_bearer_header(self):
        self.assertEqual(Credential("bearer", FAKE_TOKEN).header(), ("Authorization", "Bearer " + FAKE_TOKEN))

    def test_repr_redacted(self):
        self.assertNotIn(FAKE_TOKEN, repr(Credential("bearer", FAKE_TOKEN)))

    def test_reject_newlines(self):
        with self.assertRaises(ValueError):
            Credential("bearer", "token\\r\\nInjected: yes".replace("\\r", "\r").replace("\\n", "\n"))

    def test_bad_scheme(self):
        with self.assertRaises(ValueError):
            Credential("basic", "fake")

    def test_invalid_numeric(self):
        for value in (True, -1, math.nan, math.inf, "45"):
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    parse_payload({**FIXTURES["postgresql"], "value": value}, "postgresql")

    def test_schema_drift(self):
        with self.assertRaises(ContractError):
            parse_payload({**FIXTURES["postgresql"], "unit": "milliseconds"}, "postgresql")

class HTTPTests(unittest.TestCase):
    def test_api_key_success(self):
        with server() as (srv, base):
            result = SecureClient(base, Credential("api_key", FAKE_KEY)).get("postgresql")
            self.assertIsInstance(result, Reading)
            self.assertEqual(srv.seen_auth[0], FAKE_KEY)

    def test_bearer_success(self):
        with server() as (srv, base):
            result = SecureClient(base, Credential("bearer", FAKE_TOKEN)).get("kafka")
            self.assertEqual(result.value, 10000)
            self.assertEqual(srv.seen_auth[1], "Bearer " + FAKE_TOKEN)

    def test_401_terminal(self):
        with server() as (srv, base):
            with self.assertRaises(AuthenticationError):
                SecureClient(base, Credential("api_key", "wrong")).get("postgresql")
            self.assertEqual(srv.calls, 1)

    def test_403_terminal(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 403, 5
            with self.assertRaises(AuthorizationError):
                SecureClient(base, Credential("bearer", FAKE_TOKEN)).get("kafka")
            self.assertEqual(srv.calls, 1)

    def test_503_then_success(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 503, 1
            delays = []
            result = SecureClient(base, Credential("api_key", FAKE_KEY), sleep=delays.append).get("postgresql")
            self.assertEqual(result.value, 45)
            self.assertEqual(srv.calls, 2)
            self.assertEqual(len(delays), 1)

    def test_429_then_success(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 429, 2
            result = SecureClient(base, Credential("bearer", FAKE_TOKEN), sleep=lambda _: None).get("kafka")
            self.assertEqual(result.engine, "kafka")
            self.assertEqual(srv.calls, 3)

    def test_429_exhaustion(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 429, 10
            with self.assertRaises(RateLimitError):
                SecureClient(base, Credential("api_key", FAKE_KEY), sleep=lambda _: None).get("postgresql")
            self.assertEqual(srv.calls, 3)

    def test_503_exhaustion(self):
        with server() as (srv, base):
            srv.fail_status, srv.fail_remaining = 503, 10
            with self.assertRaises(ClientError):
                SecureClient(base, Credential("api_key", FAKE_KEY), sleep=lambda _: None).get("postgresql")
            self.assertEqual(srv.calls, 3)

    def test_redirect_rejected(self):
        with server() as (srv, base):
            srv.force_redirect = True
            with self.assertRaises(ClientError):
                SecureClient(base, Credential("bearer", FAKE_TOKEN)).get("postgresql")
            self.assertEqual(srv.calls, 1)

    def test_malformed_json(self):
        with server() as (srv, base):
            srv.body_override = b"{invalid"
            with self.assertRaises(ContractError):
                SecureClient(base, Credential("api_key", FAKE_KEY)).get("postgresql")
            self.assertEqual(srv.calls, 1)

    def test_wrong_content_type(self):
        with server() as (srv, base):
            srv.content_type = "text/plain"
            with self.assertRaises(ContractError):
                SecureClient(base, Credential("api_key", FAKE_KEY)).get("postgresql")

    def test_oversized(self):
        with server() as (srv, base):
            srv.body_override = b"x" * 10000
            with self.assertRaises(ContractError):
                SecureClient(base, Credential("api_key", FAKE_KEY)).get("postgresql")

    def test_no_external_host(self):
        for url in ("https://example.com", "http://localhost:80", "http://127.0.0.2:8000",
                    "http://user:pass@127.0.0.1:8000", "http://127.0.0.1:8000/evil"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    SecureClient(url, Credential("api_key", FAKE_KEY))

    def test_bad_options(self):
        with server() as (_, base):
            for attempts in (0, 6, True):
                with self.assertRaises(ValueError):
                    SecureClient(base, Credential("api_key", FAKE_KEY), attempts=attempts)
            for timeout in (0, math.nan, math.inf, True):
                with self.assertRaises(ValueError):
                    SecureClient(base, Credential("api_key", FAKE_KEY), timeout=timeout)

    def test_unknown_engine_no_request(self):
        with server() as (srv, base):
            with self.assertRaises(ContractError):
                SecureClient(base, Credential("api_key", FAKE_KEY)).get("mysql")
            self.assertEqual(srv.calls, 0)

    def test_closed_server_transport_failure(self):
        with server() as (_, base):
            client = SecureClient(base, Credential("api_key", FAKE_KEY), attempts=1)
        with self.assertRaises(TransportError):
            client.get("postgresql")

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 3. Execute
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q secure_client.py test_secure_client.py
python -m unittest -v test_secure_client.py
python secure_client.py
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, then \`py -m unittest -v test_secure_client.py\`. Local sockets must be permitted.

## 4. Optional quality gates
\`\`\`bash
python -m pip install 'pytest>=8,<10' 'ruff>=0.13,<0.15' 'bandit>=1.8,<2'
python -m pytest -v test_secure_client.py
ruff check secure_client.py test_secure_client.py
ruff format secure_client.py test_secure_client.py
ruff format --check secure_client.py test_secure_client.py
bandit -r secure_client.py -ll
\`\`\`
Apply formatter changes and review them before requiring \`--check\`. Use reviewed pinned versions in production.

## 5. CI template
\`\`\`yaml
name: chapter-072-auth
on: workflow_dispatch
jobs:
  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Require extracted files
        run: |
          test -f secure_client.py
          test -f test_secure_client.py
      - name: Run loopback tests
        run: python -m unittest -v test_secure_client.py
\`\`\`
This is a **template**, not an active workflow. Extract the Markdown source to files, pin reviewed GitHub Action commit SHAs, add approved security scanners, and validate before enabling. No real tokens should be injected into pull-request workflows.

## 6. Production incident drills
1. Wrong API key → 401, one request.
2. Insufficient bearer-token scope → simulated 403, no retry.
3. Gateway 503 once → bounded GET retry.
4. API rate limit 429 twice → bounded retry and recovery.
5. Persistent 429 → fail with sanitized rate-limit category.
6. Persistent 503 → fail after retry budget.
7. Untrusted 302 → redirect rejected without contacting target.
8. Malformed JSON → no retry.
9. Unexpected content type → contract failure.
10. Oversized response → reject before parsing.
11. Credential contains CR/LF → reject header injection.
12. Secret appears in object representation → regression test catches it.
13. Invalid host/URL credentials → reject before network request.
14. Closed fixture server → sanitized transport failure.
15. Simulate OAuth token expiry; document trusted reacquisition (no real token endpoint).
16. Simulate certificate rotation; document TLS validation (no local TLS server).
17. Confirm API-key/bearer values never appear in exception text or log output.
18. Restore healthy configuration and rerun all tests.

## 7. Runbooks
**401:** verify token expiry, key rotation, issuer/audience and token source; reacquire once through approved secret provider; never blindly retry.

**403:** compare required scopes with workload identity; apply least privilege and audit changes.

**429:** reduce concurrency/polling; implement bounded Retry-After/jitter policy and coordinate quotas.

**503:** check gateway/upstream saturation and error budget; cap retries and roll back if needed.

**TLS failure:** repair CA/hostname/certificate trust; do not disable verification.

**Credential exposure:** revoke/rotate immediately, restrict artifacts, inspect access logs and document impact.

**Rollback:** restore approved client and credential policy, rerun synthetic integration tests, verify production SLOs and record change approval.

## 8. 100-point assessment
| Area | Points |
|---|---:|
| API-key and bearer header handling | 15 |
| Credential validation and redaction | 15 |
| 401/403 terminal behavior | 15 |
| 429/503 bounded retries | 15 |
| Redirect, URL and response-contract security | 15 |
| Automated loopback integration tests | 15 |
| Incident runbooks, CI and rollback | 10 |

**Pass:** at least 90/100 with mandatory security controls passing. The lab does not implement a real OAuth authorization server, TLS endpoint or production credential store; those require provider-specific integration and threat review. Publication alone is not proof of test execution.
