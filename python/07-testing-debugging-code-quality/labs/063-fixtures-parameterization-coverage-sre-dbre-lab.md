# Chapter 063 — Test Fixtures, Parameterization and Coverage Engineering SRE/DBRE Lab

**Python 3.11+ | pytest + pytest-cov | Offline and non-destructive**

## Layout
```text
ch063/
  telemetry_quality.py
  test_telemetry_quality.py
  .coveragerc
  requirements-dev.txt
```

## 1. Complete application: telemetry_quality.py
```python
"""Chapter 063: deterministic, offline SRE/DBRE telemetry quality gates."""
from __future__ import annotations
from dataclasses import dataclass
import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Mapping

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30.0, 120.0),
    "elasticsearch": ("search_latency", "milliseconds", 200.0, 500.0),
    "kafka": ("consumer_lag", "messages", 1000.0, 10000.0),
}
MAX_RECORDS = 100
MAX_BYTES = 65536

class TelemetryError(ValueError):
    pass

@dataclass(frozen=True)
class Reading:
    service: str
    engine: str
    value: float

def parse(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value"}:
        raise TelemetryError("invalid schema")
    service = raw["service"]
    engine = raw["engine"]
    if not isinstance(service, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service) is None:
        raise TelemetryError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise TelemetryError("invalid engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise TelemetryError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise TelemetryError("value must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise TelemetryError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise TelemetryError("value must be finite and nonnegative")
    return Reading(service, engine, number)

def severity(reading: Reading) -> str:
    if reading.engine not in POLICY or not math.isfinite(reading.value) or reading.value < 0:
        raise TelemetryError("invalid reading")
    _, _, warn, critical = POLICY[reading.engine]
    if reading.value >= critical:
        return "critical"
    if reading.value >= warn:
        return "warning"
    return "healthy"

def summarize(raw: object) -> dict[str, object]:
    if not isinstance(raw, list) or len(raw) > MAX_RECORDS:
        raise TelemetryError("expected list with at most 100 items")
    readings = [parse(item) for item in raw]
    if len({(r.engine, r.service) for r in readings}) != len(readings):
        raise TelemetryError("duplicate source")
    readings.sort(key=lambda r: (r.engine, r.service))
    counts = {level: 0 for level in ("healthy", "warning", "critical")}
    rows = []
    for item in readings:
        level = severity(item)
        counts[level] += 1
        rows.append({"service": item.service, "engine": item.engine,
                     "severity": level, "value": item.value})
    return {"schema_version": 1, "dry_run": True, "total": len(rows),
            "counts": counts, "results": rows}

def load_file(path: Path) -> object:
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise TelemetryError("invalid input file or size")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, parse_constant=lambda value: (_ for _ in ()).throw(TelemetryError("nonfinite JSON number")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TelemetryError("invalid JSON input") from exc

def fixtures() -> list[dict[str, object]]:
    return [
        {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
        {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
        {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000},
    ]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline test-coverage telemetry lab")
    parser.add_argument("--input", type=Path, help="Optional local JSON fixture file")
    args = parser.parse_args(argv)
    try:
        result = summarize(load_file(args.input) if args.input else fixtures())
    except TelemetryError:
        print("telemetry rejected: sanitized validation failure", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Complete pytest suite: test_telemetry_quality.py
```python
"""pytest fixture, parameterization, filesystem and environment coverage."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
import telemetry_quality as ops

@pytest.fixture(scope="session")
def policy_names():
    return tuple(sorted(ops.POLICY))

@pytest.fixture(scope="module")
def immutable_cases():
    return (("postgresql",30.0,120.0),("elasticsearch",200.0,500.0),("kafka",1000.0,10000.0))

@pytest.fixture
def pg_record():
    return {"service":"pg-replica","engine":"postgresql",
            "metric":"replication_lag","unit":"seconds","value":45}

@pytest.fixture
def records():
    return ops.fixtures()

@pytest.fixture
def fixture_file(tmp_path, records):
    file = tmp_path / "telemetry.json"
    file.write_text(json.dumps(records), encoding="utf-8")
    return file

@pytest.fixture
def lifecycle():
    events = ["setup"]
    yield events
    events.append("teardown")

@pytest.fixture
def environment(monkeypatch):
    monkeypatch.setenv("CH063_TEST_MODE", "synthetic")
    yield "synthetic"

def test_session_scope(policy_names):
    assert policy_names == ("elasticsearch","kafka","postgresql")

def test_module_scope(immutable_cases):
    assert len(immutable_cases) == 3

def test_function_fixture_isolated(pg_record):
    pg_record["value"] = 1
    assert pg_record["value"] == 1

def test_function_fixture_fresh(pg_record):
    assert pg_record["value"] == 45

def test_yield_fixture(lifecycle):
    assert lifecycle == ["setup"]

def test_monkeypatch_env(environment, monkeypatch):
    import os
    assert os.environ["CH063_TEST_MODE"] == environment

def test_tmp_path_load(fixture_file):
    assert len(ops.load_file(fixture_file)) == 3

def test_tmp_path_cli(fixture_file, capsys):
    assert ops.main(["--input",str(fixture_file)]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 3

@pytest.mark.parametrize("engine,metric,unit,warn,critical",[
    ("postgresql","replication_lag","seconds",30,120),
    ("elasticsearch","search_latency","milliseconds",200,500),
    ("kafka","consumer_lag","messages",1000,10000),
])
def test_boundaries(engine,metric,unit,warn,critical):
    for value,expected in ((0,"healthy"),(warn-0.01,"healthy"),
                           (warn,"warning"),(critical-0.01,"warning"),
                           (critical,"critical")):
        record={"service":"node","engine":engine,"metric":metric,"unit":unit,"value":value}
        assert ops.severity(ops.parse(record)) == expected

@pytest.mark.parametrize("bad",[True,"45",-1,float("nan"),float("inf"),float("-inf")])
def test_bad_values(pg_record,bad):
    pg_record["value"]=bad
    with pytest.raises(ops.TelemetryError): ops.parse(pg_record)

@pytest.mark.parametrize("change",[
    {"service":"=cmd"},{"engine":"mysql"},{"metric":"wrong"},
    {"unit":"ms"},{"password":"secret"},
])
def test_bad_schema(pg_record,change):
    with pytest.raises(ops.TelemetryError): ops.parse({**pg_record,**change})

def test_missing_key(pg_record):
    pg_record.pop("unit")
    with pytest.raises(ops.TelemetryError): ops.parse(pg_record)

def test_non_mapping():
    with pytest.raises(ops.TelemetryError): ops.parse([])

def test_bad_classification():
    with pytest.raises(ops.TelemetryError):
        ops.severity(ops.Reading("node","postgresql",-1))

def test_bad_classification_engine():
    with pytest.raises(ops.TelemetryError):
        ops.severity(ops.Reading("node","mysql",1))

def test_summary(records):
    result=ops.summarize(records)
    assert result["counts"]=={"healthy":0,"warning":1,"critical":2}
    assert result["total"]==3

def test_sorted(records):
    assert ops.summarize(records)["results"]==ops.summarize(list(reversed(records)))["results"]

def test_empty():
    assert ops.summarize([])["total"]==0

def test_nonlist():
    with pytest.raises(ops.TelemetryError): ops.summarize({})

def test_duplicate(pg_record):
    with pytest.raises(ops.TelemetryError): ops.summarize([pg_record,pg_record])

def test_too_many(pg_record):
    with pytest.raises(ops.TelemetryError): ops.summarize([pg_record]*101)

def test_missing_file(tmp_path):
    with pytest.raises(ops.TelemetryError): ops.load_file(tmp_path/"missing.json")

def test_oversize_file(tmp_path):
    p=tmp_path/"oversize.json"
    p.write_bytes(b" "* (ops.MAX_BYTES+1))
    with pytest.raises(ops.TelemetryError): ops.load_file(p)

def test_invalid_json(tmp_path):
    p=tmp_path/"broken.json"
    p.write_text("{broken",encoding="utf-8")
    with pytest.raises(ops.TelemetryError): ops.load_file(p)

def test_nonfinite_json(tmp_path):
    p=tmp_path/"nan.json"
    p.write_text('[NaN]',encoding="utf-8")
    with pytest.raises(ops.TelemetryError): ops.load_file(p)

def test_bad_utf8(tmp_path):
    p=tmp_path/"bytes.json"
    p.write_bytes(b"\xff")
    with pytest.raises(ops.TelemetryError): ops.load_file(p)

def test_main_default(capsys):
    assert ops.main([])==0
    assert json.loads(capsys.readouterr().out)["dry_run"]

def test_main_failure(tmp_path,capsys):
    assert ops.main(["--input",str(tmp_path/"missing.json")])==3
    assert "sanitized" in capsys.readouterr().err

def test_no_secrets(records):
    assert "password" not in json.dumps(ops.summarize(records))

def test_monkeypatch_policy(monkeypatch,pg_record):
    replacement={**ops.POLICY,"postgresql":("replication_lag","seconds",50,150)}
    monkeypatch.setattr(ops,"POLICY",replacement)
    assert ops.severity(ops.parse(pg_record))=="healthy"

```

## 3. Coverage configuration: .coveragerc
```ini
[run]
branch = True
source = telemetry_quality

[report]
show_missing = True
fail_under = 90
exclude_also =
    if __name__ == .__main__.:
```

## 4. Development dependencies: requirements-dev.txt
```text
pytest>=8,<10
pytest-cov>=5,<8
coverage>=7,<9
```
These are compatibility ranges for the training lab, not reproducible production pins. Generate and review a lockfile with exact versions and hashes before deployment.

## 5. Execute
Linux/macOS/WSL:
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m py_compile telemetry_quality.py test_telemetry_quality.py
python -m pytest -v
python -m pytest -q --cov=telemetry_quality --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=90
python telemetry_quality.py
```

Windows PowerShell:
```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q --cov=telemetry_quality --cov-branch --cov-report=term-missing --cov-fail-under=90
```

Expected synthetic summary: three records, one warning and two critical. The 90% coverage threshold is an **acceptance target**, not a measured result.

## 6. CI example: GitHub Actions
Save this optional workflow as `.github/workflows/python-ch063-quality.yml`:
```yaml
name: python-ch063-quality
on:
  push:
    paths:
      - 'python/07-testing-debugging-code-quality/**'
      - '.github/workflows/python-ch063-quality.yml'
  pull_request:
    paths:
      - 'python/07-testing-debugging-code-quality/**'
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Materialize lab source
        run: |
          echo "Copy the two Python fenced code blocks from the Chapter 063 lab into the working directory before enabling this workflow."
          exit 1
      - name: Install test tools
        run: python -m pip install pytest pytest-cov coverage
      - name: Test and coverage
        run: python -m pytest -q --cov=telemetry_quality --cov-branch --cov-fail-under=90
```
**Important:** The workflow above is an illustrative fail-closed scaffold because this tutorial publishes source inside Markdown. It intentionally fails until the lab code is materialized and the workflow is adapted to the actual repository paths. Do not enable it unchanged.

## 7. Failure injection and incident simulations
1. Verify function-scoped fixture isolation across tests.
2. Compare module/session fixtures and explain mutable-state hazards.
3. Use yield fixtures and demonstrate teardown after an assertion failure in a disposable test.
4. Create and read JSON via tmp_path.
5. Inject malformed JSON, non-UTF-8 bytes and nonfinite JSON constants.
6. Reject a file larger than 64 KiB.
7. Monkeypatch PostgreSQL warning threshold and verify classification changes.
8. Parameterize all three engines across healthy, warning and critical boundaries.
9. Reject booleans, strings, NaN, Infinity and negative metrics.
10. Reject duplicate sources and more than 100 records.
11. Run branch coverage and inspect missing paths.
12. Deliberately raise coverage threshold above observed score to verify the gate fails.
13. Reverse fixture order and verify deterministic reports.
14. Confirm no production datastore calls, credentials or writes.

## 8. Production runbooks
**Coverage gate failure:** identify uncovered safety paths, add negative tests and review exclusions.

**Fixture contamination:** isolate mutable fixtures and temporary files, rerun tests in randomized order.

**Cleanup failure:** ensure teardown is registered after resource creation and never targets production directories.

**CI drift:** pin Python and dependencies, compare coverage configuration and rerun cleanly.

**Rollback:** restore known-good tests and application code, rerun gates and record change approval.

## 9. 100-point assessment
| Area | Points |
|---|---:|
| Fixture scopes and isolation | 20 |
| Yield teardown and tmp_path | 15 |
| monkeypatch and parameterization | 20 |
| Branch coverage and 90% gate | 20 |
| Failure simulations | 15 |
| Production runbooks and rollback | 10 |

Target **90/100** with all safety tests passing. Publication does not imply that tests or coverage have been executed.
