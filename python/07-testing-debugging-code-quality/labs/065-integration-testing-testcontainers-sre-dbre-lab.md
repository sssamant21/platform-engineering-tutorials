# Chapter 065 — Integration Testing and Testcontainers SRE/DBRE Lab

**Python 3.11+ | pytest + Docker + PostgreSQL + Redis | Disposable resources only**

## File layout
```text
ch065/
  telemetry_service.py
  test_unit.py
  test_integration.py
  pytest.ini
  requirements-dev.txt
```

## 1. Complete application: telemetry_service.py
```python
"""Chapter 065 — isolated PostgreSQL + Redis integration service (Python 3.11+)."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Protocol

class InputError(ValueError): pass
class ConflictError(RuntimeError): pass

@dataclass(frozen=True)
class Sample:
    source: str
    engine: str
    metric: str
    value: float

class Store(Protocol):
    def insert_once(self, event_id: str, sample: Sample) -> bool: ...
    def fetch(self, event_id: str) -> Sample | None: ...
    def count(self) -> int: ...

class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
    def delete(self, key: str) -> None: ...

def validate(raw: object) -> Sample:
    if not isinstance(raw, dict) or set(raw) != {"source", "engine", "metric", "value"}:
        raise InputError("invalid schema")
    source, engine, metric, value = (raw[k] for k in ("source", "engine", "metric", "value"))
    if not isinstance(source, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", source):
        raise InputError("invalid source")
    expected = {"postgresql":"replication_lag_seconds", "redis":"used_memory_bytes"}
    if not isinstance(engine, str) or engine not in expected or metric != expected[engine]:
        raise InputError("invalid engine or metric")
    if type(value) not in (int, float):
        raise InputError("invalid value type")
    try: value = float(value)
    except (OverflowError, ValueError) as exc: raise InputError("invalid value") from exc
    if not math.isfinite(value) or value < 0:
        raise InputError("invalid value")
    return Sample(source, engine, metric, value)

def event_key(sample: Sample) -> str:
    canonical = json.dumps(sample.__dict__, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def severity(sample: Sample) -> str:
    warn, critical = ((30, 120) if sample.engine == "postgresql" else (1000000, 10000000))
    return "critical" if sample.value >= critical else "warning" if sample.value >= warn else "healthy"

class TelemetryService:
    def __init__(self, store: Store, cache: Cache) -> None:
        self.store, self.cache = store, cache
    def ingest(self, raw: object) -> dict[str, object]:
        sample = validate(raw)
        key = event_key(sample)
        inserted = self.store.insert_once(key, sample)
        # Cache is derived data: a cache failure must not roll back a committed DB write.
        result = {"event_id": key, "inserted": inserted, "severity": severity(sample)}
        try:
            self.cache.set("event:" + key, json.dumps(result, sort_keys=True), 60)
        except Exception:
            pass  # Training policy: best-effort cache; real systems must record a metric.
        return result
    def lookup(self, key: str) -> Sample | None:
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise InputError("invalid event key")
        # PostgreSQL is authoritative; Redis must not hide database changes.
        return self.store.fetch(key)

class PostgresStore:
    def __init__(self, connection) -> None:
        self.connection = connection
    def insert_once(self, event_id: str, sample: Sample) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO telemetry_events (event_id, source, engine, metric, value) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (event_id) DO NOTHING RETURNING event_id",
                (event_id, sample.source, sample.engine, sample.metric, sample.value),
            )
            inserted = cursor.fetchone() is not None
        self.connection.commit()
        return inserted
    def fetch(self, event_id: str) -> Sample | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT source, engine, metric, value FROM telemetry_events WHERE event_id=%s",
                           (event_id,))
            row = cursor.fetchone()
        return Sample(row[0], row[1], row[2], float(row[3])) if row else None
    def count(self) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM telemetry_events")
            return int(cursor.fetchone()[0])

class RedisCache:
    def __init__(self, client) -> None:
        self.client = client
    def get(self, key: str) -> str | None:
        return self.client.get(key)
    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.client.set(name=key, value=value, ex=ttl_seconds)
    def delete(self, key: str) -> None:
        self.client.delete(key)

```

## 2. Offline unit tests: test_unit.py
```python
"""Unit tests run offline, even without Docker."""
import unittest
from unittest.mock import Mock
from telemetry_service import InputError, Sample, validate, event_key, severity, TelemetryService

PG={"source":"pg-replica","engine":"postgresql","metric":"replication_lag_seconds","value":45}

class InMemoryStore:
    def __init__(self): self.rows={}
    def insert_once(self,key,sample):
        if key in self.rows: return False
        self.rows[key]=sample
        return True
    def fetch(self,key): return self.rows.get(key)
    def count(self): return len(self.rows)

class UnitTests(unittest.TestCase):
    def test_validate(self): self.assertEqual(validate(PG).value,45)
    def test_bad_schema(self):
        with self.assertRaises(InputError): validate({"bad":1})
    def test_bad_metric(self):
        with self.assertRaises(InputError): validate({**PG,"metric":"bad"})
    def test_bad_source(self):
        with self.assertRaises(InputError): validate({**PG,"source":"=cmd"})
    def test_bad_bool(self):
        with self.assertRaises(InputError): validate({**PG,"value":True})
    def test_bad_nan(self):
        with self.assertRaises(InputError): validate({**PG,"value":float("nan")})
    def test_bad_negative(self):
        with self.assertRaises(InputError): validate({**PG,"value":-1})
    def test_threshold(self):
        self.assertEqual(severity(validate({**PG,"value":120})),"critical")
    def test_key_deterministic(self):
        self.assertEqual(event_key(validate(PG)),event_key(validate(PG)))
    def test_idempotency(self):
        store=InMemoryStore()
        cache=Mock()
        service=TelemetryService(store,cache)
        self.assertTrue(service.ingest(PG)["inserted"])
        self.assertFalse(service.ingest(PG)["inserted"])
        self.assertEqual(store.count(),1)
        self.assertEqual(cache.set.call_count,2)
    def test_cache_failure_does_not_rollback(self):
        store=InMemoryStore()
        cache=Mock()
        cache.set.side_effect=RuntimeError("synthetic Redis outage")
        result=TelemetryService(store,cache).ingest(PG)
        self.assertTrue(result["inserted"])
        self.assertEqual(store.count(),1)
    def test_lookup(self):
        store=InMemoryStore()
        service=TelemetryService(store,Mock())
        key=service.ingest(PG)["event_id"]
        self.assertEqual(service.lookup(key),validate(PG))
    def test_bad_lookup(self):
        with self.assertRaises(InputError):
            TelemetryService(InMemoryStore(),Mock()).lookup("../etc/passwd")

if __name__=="__main__": unittest.main()

```

## 3. Disposable-container integration tests: test_integration.py
```python
"""Real disposable PostgreSQL/Redis integration tests. Requires Docker and opt-in."""
import os
import time
import uuid
import pytest

pytestmark=pytest.mark.integration

@pytest.fixture(scope="session", autouse=True)
def require_opt_in():
    if os.environ.get("CH065_RUN_CONTAINERS") != "1":
        pytest.skip("set CH065_RUN_CONTAINERS=1 to permit disposable Docker containers")
    if os.environ.get("CH065_ALLOW_DOCKER") != "I_UNDERSTAND":
        pytest.skip("explicit Docker permission not supplied")

@pytest.fixture(scope="session")
def pg_container(require_opt_in):
    from testcontainers.postgres import PostgresContainer
    # Training tags; pin image digests in an enterprise-controlled registry.
    with PostgresContainer("postgres:16-alpine") as container:
        yield container

@pytest.fixture(scope="session")
def redis_container(require_opt_in):
    from testcontainers.redis import RedisContainer
    with RedisContainer("redis:7-alpine") as container:
        yield container

@pytest.fixture
def postgres(pg_container):
    import psycopg
    # Each test uses its own DB transaction and truncates only disposable table.
    with psycopg.connect(pg_container.get_connection_url()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS telemetry_events ("
                           "event_id TEXT PRIMARY KEY, source TEXT NOT NULL,"
                           "engine TEXT NOT NULL, metric TEXT NOT NULL,"
                           "value DOUBLE PRECISION NOT NULL)")
            cursor.execute("TRUNCATE telemetry_events")
        conn.commit()
        yield conn
        conn.rollback()

@pytest.fixture
def redis(redis_container):
    import redis as redis_module
    client=redis_module.Redis(host=redis_container.get_container_host_ip(),
                              port=int(redis_container.get_exposed_port(6379)),
                              decode_responses=True, socket_connect_timeout=3,
                              socket_timeout=3)
    client.ping()
    prefix=f"ch065:{uuid.uuid4().hex}:"
    yield client,prefix
    # Only delete keys owned by this test; never FLUSHDB.
    for key in client.scan_iter(match=prefix+"*", count=100):
        client.delete(key)
    client.close()

@pytest.fixture
def service(postgres,redis):
    from telemetry_service import PostgresStore, RedisCache, TelemetryService
    client,prefix=redis
    class NamespacedCache(RedisCache):
        def set(self,key,value,ttl_seconds):
            super().set(prefix+key,value,ttl_seconds)
        def get(self,key):
            return super().get(prefix+key)
        def delete(self,key):
            super().delete(prefix+key)
    return TelemetryService(PostgresStore(postgres),NamespacedCache(client))

PG={"source":"pg-replica","engine":"postgresql","metric":"replication_lag_seconds","value":45}
REDIS={"source":"redis-cache","engine":"redis","metric":"used_memory_bytes","value":1200000}

def test_postgres_persistence(service):
    event=service.ingest(PG)
    assert event["inserted"]
    assert service.store.count()==1
    assert service.lookup(event["event_id"]).source=="pg-replica"

def test_idempotency(service):
    first=service.ingest(PG)
    second=service.ingest(PG)
    assert first["event_id"]==second["event_id"]
    assert first["inserted"] is True
    assert second["inserted"] is False
    assert service.store.count()==1

def test_redis_cache(service,redis):
    client,prefix=redis
    result=service.ingest(REDIS)
    key=prefix+"event:"+result["event_id"]
    assert client.exists(key)==1
    assert client.ttl(key)>0
    assert service.store.count()==1

def test_cache_outage_degrades_safely(service):
    from unittest.mock import Mock
    service.cache=Mock()
    service.cache.set.side_effect=ConnectionError("synthetic Redis failure")
    result=service.ingest(PG)
    assert result["inserted"]
    assert service.store.count()==1

def test_bad_input_has_no_side_effect(service):
    from telemetry_service import InputError
    with pytest.raises(InputError):
        service.ingest({**PG,"value":float("nan")})
    assert service.store.count()==0

```

## 4. pytest.ini
```ini
[pytest]
markers =
    integration: requires explicit opt-in and disposable Docker containers
```

## 5. requirements-dev.txt
```text
pytest>=8,<10
testcontainers[postgres,redis]>=4,<5
psycopg[binary]>=3,<4
redis>=5,<7
```
Compatibility ranges are illustrative, not a tested lockfile. Pin exact versions and image digests in enterprise CI.

## 6. Run offline tests
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m py_compile telemetry_service.py test_unit.py test_integration.py
python -m pytest -v test_unit.py
```

## 7. Run integration tests (explicit Docker opt-in)
**Only on a trusted local machine or isolated CI runner with Docker installed.** Images may be downloaded. The fixtures create and remove containers and modify only disposable container data.

```bash
docker info
export CH065_RUN_CONTAINERS=1
export CH065_ALLOW_DOCKER=I_UNDERSTAND
python -m pytest -v -m integration test_integration.py
```

PowerShell:
```powershell
$env:CH065_RUN_CONTAINERS="1"
$env:CH065_ALLOW_DOCKER="I_UNDERSTAND"
py -3 -m pytest -v -m integration test_integration.py
```

Unset both variables afterward. Do not use production PostgreSQL or Redis endpoints. If no Docker access, run offline unit tests; integration tests skip by default.

## 8. CI template (trusted runner only)
```yaml
name: chapter-065-integration
on:
  workflow_dispatch:
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Materialize lab files
        run: |
          echo 'Extract telemetry_service.py, test_unit.py, test_integration.py, pytest.ini and requirements-dev.txt from Chapter 065 lab before enabling'
          exit 1
      - name: Install
        run: python -m pip install -r requirements-dev.txt
      - name: Unit tests
        run: python -m pytest -v test_unit.py
      - name: Container integration tests
        env:
          CH065_RUN_CONTAINERS: '1'
          CH065_ALLOW_DOCKER: I_UNDERSTAND
        run: python -m pytest -v -m integration test_integration.py
```
**Fail-closed scaffold:** This workflow intentionally stops until Markdown code blocks have been materialized into real files and the workflow has been reviewed. It is not a ready-to-run CI pipeline.

## 9. Incident simulations
1. Verify offline unit tests succeed without Docker.
2. Confirm integration tests skip without both opt-in flags.
3. Start PostgreSQL and Redis disposable containers with Testcontainers.
4. Validate PostgreSQL insert/read and duplicate idempotency.
5. Verify Redis PING, TTL and unique namespace cleanup.
6. Simulate a Redis write failure; verify committed PostgreSQL data remains.
7. Reject malformed telemetry before database writes.
8. Stop Docker and observe a clear startup failure on a disposable runner.
9. Force an invalid image tag and inspect image-pull failure.
10. Verify per-test PostgreSQL cleanup and Redis key-prefix isolation.
11. Check container shutdown after pytest, including failure paths.
12. Capture sanitized logs and record rollback evidence.

## 10. Runbooks
**Docker failure:** inspect daemon, permissions and image registry; retry only on trusted runners.

**PostgreSQL readiness:** inspect container logs and connection string, confirm correct driver and startup wait.

**Redis connectivity:** check mapped port and PING, confirm scoped key cleanup.

**Data contamination:** stop suite, confirm DSN points only to owned container, reset disposable resources.

**Rollback:** restore previous dependency/image pins, rerun unit and integration suites, obtain change approval.

## 11. 100-point acceptance assessment
| Category | Points |
|---|---:|
| Offline unit tests and validation | 20 |
| PostgreSQL disposable integration | 20 |
| Redis disposable integration | 20 |
| Fixture isolation, cleanup and readiness | 15 |
| CI safety and incident simulations | 15 |
| Runbooks, rollback and audit evidence | 10 |

**Pass:** 90/100, all safety tests passing, no live production connections, and independently verified container cleanup. Publication alone is not proof of execution.
