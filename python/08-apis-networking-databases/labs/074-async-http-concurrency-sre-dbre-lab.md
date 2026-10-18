# Chapter 074 — Async HTTP Clients and Concurrent API Operations SRE/DBRE Lab

**Python 3.11+ | httpx | asyncio | Local synthetic HTTP integration tests**

## 1. File tree
\`\`\`text
ch074/
  async_client.py
  test_async_client.py
  requirements.txt
\`\`\`
The fixture server binds to \`127.0.0.1\` on an ephemeral port. It returns synthetic PostgreSQL, Elasticsearch and Kafka telemetry. No external APIs, production credentials or databases are contacted.

## 2. requirements.txt
\`\`\`text
httpx>=0.27,<1
\`\`\`
This is an illustrative range; use reviewed, hash-pinned dependencies in production.

## 3. Complete client — async_client.py
\`\`\`python
"""Bounded asynchronous loopback HTTP telemetry collector."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import random
import re
from typing import Callable
from urllib.parse import urlsplit

import httpx

NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
POLICY = {
    "postgresql": ("replication_lag", "seconds"),
    "elasticsearch": ("search_latency", "milliseconds"),
    "kafka": ("consumer_lag", "messages"),
}
TRANSIENT = {429, 502, 503, 504}
MAX_BYTES = 8192

class APIError(RuntimeError): pass
class ContractError(APIError): pass

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

def validate(raw: object, engine: str) -> Reading:
    if engine not in POLICY or not isinstance(raw, dict):
        raise ContractError("invalid telemetry")
    if set(raw) != {"engine", "service", "metric", "unit", "value"}:
        raise ContractError("invalid schema")
    service = raw["service"]
    if raw["engine"] != engine or not isinstance(service, str) or NAME.fullmatch(service) is None:
        raise ContractError("invalid source")
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

class AsyncCollector:
    def __init__(
        self, base_url: str, *,
        concurrency: int = 2,
        attempts: int = 3,
        timeout_seconds: float = 1.0,
        max_delay: float = 0.05,
        sleep: Callable[[float], object] | None = None,
    ):
        parsed = urlsplit(base_url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("invalid port") from exc
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or port is None
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise ValueError("only local loopback URL allowed")
        if type(concurrency) is not int or not 1 <= concurrency <= 20:
            raise ValueError("invalid concurrency")
        if type(attempts) is not int or not 1 <= attempts <= 5:
            raise ValueError("invalid attempts")
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 10:
            raise ValueError("invalid timeout")
        if type(max_delay) not in (int, float) or not math.isfinite(max_delay) or not 0 <= max_delay <= 1:
            raise ValueError("invalid delay")
        self.base_url = base_url.rstrip("/")
        self.attempts = attempts
        self.max_delay = max_delay
        self.semaphore = asyncio.Semaphore(concurrency)
        self.inflight = 0
        self.peak_inflight = 0
        self.sleep = sleep or asyncio.sleep
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency),
            follow_redirects=False,
            trust_env=False,
        )

    async def __aenter__(self) -> AsyncCollector:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.client.aclose()

    async def fetch(self, engine: str) -> Reading:
        if engine not in POLICY:
            raise ContractError("unknown engine")
        async with self.semaphore:
            self.inflight += 1
            self.peak_inflight = max(self.peak_inflight, self.inflight)
            try:
                for attempt in range(self.attempts):
                    try:
                        async with self.client.stream(
                            "GET", self.base_url + "/telemetry/" + engine,
                            headers={"Accept": "application/json"},
                        ) as response:
                            status = response.status_code
                            if status in TRANSIENT:
                                if attempt + 1 == self.attempts:
                                    raise APIError("transient status exhausted")
                            elif status != 200:
                                raise APIError("nonretryable status")
                            else:
                                if response.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                                    raise ContractError("invalid content type")
                                data = bytearray()
                                async for chunk in response.aiter_bytes():
                                    data.extend(chunk)
                                    if len(data) > MAX_BYTES:
                                        raise ContractError("oversized response")
                                try:
                                    payload = response.json() if False else __import__("json").loads(data)
                                except (ValueError, UnicodeDecodeError) as exc:
                                    raise ContractError("invalid JSON") from exc
                                return validate(payload, engine)
                    except (httpx.TimeoutException, httpx.TransportError):
                        if attempt + 1 == self.attempts:
                            raise APIError("transport exhausted") from None
                    # Async backoff with jitter; no blocking time.sleep.
                    jitter = random.uniform(0.5, 1.0)
                    await self.sleep(min(self.max_delay, 0.01 * (2 ** attempt)) * jitter)
                raise AssertionError("unreachable")
            finally:
                self.inflight -= 1

    async def collect(self, engines: list[str], *, total_timeout: float = 5.0) -> list[Reading]:
        if not isinstance(engines, list) or len(engines) > 100:
            raise ValueError("invalid batch")
        if any(engine not in POLICY for engine in engines):
            raise ContractError("unknown engine")
        if type(total_timeout) not in (int, float) or not math.isfinite(total_timeout) or total_timeout <= 0:
            raise ValueError("invalid total timeout")
        async with asyncio.timeout(total_timeout):
            return await asyncio.gather(*(self.fetch(engine) for engine in engines))

async def main() -> None:
    print("Run python -m unittest -v test_async_client.py to exercise the local server")

if __name__ == "__main__":
    asyncio.run(main())
\`\`\`

## 4. Complete unit/integration tests — test_async_client.py
\`\`\`python
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from threading import Lock, Thread
import time
import unittest

from async_client import APIError, AsyncCollector, ContractError, validate

PAYLOADS = {
    "postgresql": {"engine":"postgresql","service":"pg-replica","metric":"replication_lag","unit":"seconds","value":45},
    "elasticsearch": {"engine":"elasticsearch","service":"es-search","metric":"search_latency","unit":"milliseconds","value":650},
    "kafka": {"engine":"kafka","service":"kafka-worker","metric":"consumer_lag","unit":"messages","value":10000},
}

class Fixture(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address):
        super().__init__(address, Handler)
        self.lock = Lock()
        self.active = 0
        self.peak = 0
        self.calls = 0
        self.fail_remaining = 0
        self.fail_status = 0
        self.delay = 0.0
        self.override = None
        self.content_type = "application/json"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): return
    def do_GET(self):
        with self.server.lock:
            self.server.calls += 1
            self.server.active += 1
            self.server.peak = max(self.server.peak, self.server.active)
            fail = self.server.fail_remaining > 0
            if fail:
                self.server.fail_remaining -= 1
        try:
            if self.server.delay:
                time.sleep(self.server.delay)
            if fail:
                self.send_response(self.server.fail_status)
                self.send_header("Content-Length","0")
                self.end_headers()
                return
            engine = self.path.removeprefix("/telemetry/")
            if not self.path.startswith("/telemetry/") or engine not in PAYLOADS:
                self.send_error(404)
                return
            body = json.dumps(PAYLOADS[engine]).encode() if self.server.override is None else self.server.override
            self.send_response(200)
            self.send_header("Content-Type",self.server.content_type)
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
        finally:
            with self.server.lock:
                self.server.active -= 1

@contextmanager
def server():
    srv = Fixture(("127.0.0.1",0))
    thread = Thread(target=srv.serve_forever,daemon=True)
    thread.start()
    try:
        yield srv, f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=3)

class ContractTests(unittest.TestCase):
    def test_valid(self):
        for engine,payload in PAYLOADS.items():
            self.assertEqual(validate(payload,engine).engine,engine)
    def test_bad_values(self):
        for value in (True,-1,math.nan,math.inf,"45"):
            with self.assertRaises(ContractError):
                validate({**PAYLOADS["postgresql"],"value":value},"postgresql")
    def test_bad_schema(self):
        with self.assertRaises(ContractError):
            validate({"invalid":1},"postgresql")
    def test_bad_unit(self):
        with self.assertRaises(ContractError):
            validate({**PAYLOADS["postgresql"],"unit":"ms"},"postgresql")

class AsyncIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_engines(self):
        with server() as (_,base):
            async with AsyncCollector(base) as collector:
                result = await collector.collect(list(PAYLOADS))
                self.assertEqual(len(result),3)

    async def test_bounded_concurrency(self):
        with server() as (srv,base):
            srv.delay = 0.03
            async with AsyncCollector(base,concurrency=2) as collector:
                result = await collector.collect(["postgresql"]*8)
                self.assertEqual(len(result),8)
                self.assertLessEqual(collector.peak_inflight,2)
                self.assertLessEqual(srv.peak,2)

    async def test_503_then_success(self):
        with server() as (srv,base):
            srv.fail_remaining,srv.fail_status=1,503
            async with AsyncCollector(base) as collector:
                self.assertEqual((await collector.fetch("postgresql")).value,45)
                self.assertEqual(srv.calls,2)

    async def test_429_then_success(self):
        with server() as (srv,base):
            srv.fail_remaining,srv.fail_status=1,429
            async with AsyncCollector(base) as collector:
                self.assertEqual((await collector.fetch("kafka")).value,10000)

    async def test_401_terminal(self):
        with server() as (srv,base):
            srv.fail_remaining,srv.fail_status=10,401
            async with AsyncCollector(base) as collector:
                with self.assertRaises(APIError):
                    await collector.fetch("postgresql")
                self.assertEqual(srv.calls,1)

    async def test_503_exhausted(self):
        with server() as (srv,base):
            srv.fail_remaining,srv.fail_status=10,503
            async with AsyncCollector(base,attempts=2) as collector:
                with self.assertRaises(APIError):
                    await collector.fetch("postgresql")
                self.assertEqual(srv.calls,2)

    async def test_malformed_json(self):
        with server() as (srv,base):
            srv.override=b"{bad"
            async with AsyncCollector(base) as collector:
                with self.assertRaises(ContractError):
                    await collector.fetch("postgresql")

    async def test_wrong_content_type(self):
        with server() as (srv,base):
            srv.content_type="text/plain"
            async with AsyncCollector(base) as collector:
                with self.assertRaises(ContractError):
                    await collector.fetch("postgresql")

    async def test_oversized(self):
        with server() as (srv,base):
            srv.override=b"x"*10000
            async with AsyncCollector(base) as collector:
                with self.assertRaises(ContractError):
                    await collector.fetch("postgresql")

    async def test_total_deadline(self):
        with server() as (srv,base):
            srv.delay=0.2
            async with AsyncCollector(base,timeout_seconds=1) as collector:
                with self.assertRaises(TimeoutError):
                    await collector.collect(["postgresql"],total_timeout=0.01)

    async def test_cancellation(self):
        with server() as (srv,base):
            srv.delay=0.2
            async with AsyncCollector(base) as collector:
                task=asyncio.create_task(collector.fetch("postgresql"))
                await asyncio.sleep(0.02)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertEqual(collector.inflight,0)

    async def test_bad_host(self):
        for url in ("https://example.com","http://localhost:8000","http://127.0.0.1:8000/evil"):
            with self.assertRaises(ValueError):
                AsyncCollector(url)

    async def test_bad_options(self):
        with server() as (_,base):
            for concurrency in (0,21,True):
                with self.assertRaises(ValueError):
                    AsyncCollector(base,concurrency=concurrency)

    async def test_unknown_engine(self):
        with server() as (srv,base):
            async with AsyncCollector(base) as collector:
                with self.assertRaises(ContractError):
                    await collector.fetch("mysql")
                self.assertEqual(srv.calls,0)

if __name__=="__main__":
    unittest.main()
\`\`\`

## 5. Run
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q async_client.py test_async_client.py
python -m unittest -v test_async_client.py
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, then \`py -m unittest -v test_async_client.py\`. The tests require loopback socket access.

## 6. CI template
\`\`\`yaml
name: chapter-074-async
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
      - name: Verify extracted files
        run: |
          test -f async_client.py
          test -f test_async_client.py
          test -f requirements.txt
      - name: Install
        run: python -m pip install -r requirements.txt
      - name: Tests
        run: python -m unittest -v test_async_client.py
\`\`\`
This is a template only. Extract Markdown source to files, pin reviewed action SHAs and dependency hashes, and validate on a trusted runner.

## 7. Incident drills
1. Inject 503 then recovery.
2. Inject 429 then recovery.
3. Inject persistent 503; confirm bounded attempts.
4. Inject 401; confirm no retry.
5. Increase parallel work; verify concurrency cap.
6. Simulate read timeout and global deadline.
7. Cancel an in-flight task; verify cleanup.
8. Return invalid JSON and content type.
9. Return oversized response and reject.
10. Return negative, boolean or NaN metrics.
11. Attempt untrusted host; reject before network call.
12. Introduce blocking \`time.sleep\` into coroutine in disposable branch; observe event-loop lag.
13. Reduce pool limits and inspect PoolTimeout behavior.
14. Add bounded queue producer/consumer as extension; verify backpressure.
15. Simulate shared 429 quota across pods; document distributed limiter.
16. Validate cancellation on service shutdown.

## 8. Production runbooks
**Queue overload:** cap admission, inspect processing rate, pause producers or shed noncritical work.

**Pool exhaustion:** compare semaphore, pool limits and upstream latency; right-size and bound worker count.

**429/503 storm:** reduce concurrency, add bounded jitter/backoff and coordinate API quota.

**Cancellation:** ensure task cleanup, close async clients and record incomplete work.

**Rollback:** restore approved async settings, rerun integration tests and verify SLO.

## 9. 100-point assessment
| Category | Points |
|---|---:|
| asyncio and async client architecture | 15 |
| Connection pools and concurrency limits | 20 |
| Timeouts, retries and cancellation | 20 |
| Input validation and response size controls | 15 |
| Real loopback integration tests | 15 |
| Runbooks, CI and security review | 15 |

**Pass:** at least 90/100 with independently executed tests and security checks. The lab demonstrates bounded concurrency and async retry but does not implement a full distributed rate limiter or production bounded queue; these are documented extension exercises. Publication is not proof of test execution.
