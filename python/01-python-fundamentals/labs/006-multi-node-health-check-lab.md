# Chapter 006 — Hands-on Lab: Multi-Node SRE Health Check

## Scenario
Read a local JSON file of simulated node CPU measurements, iterate through every node, classify health, and produce a JSON summary. No cluster connection or credentials are required.

## Step 1 — Create `nodes.json`
```json
[
  {"name": "node-a", "cpu_pct": 35},
  {"name": "node-b", "cpu_pct": 79},
  {"name": "node-c", "cpu_pct": 94},
  {"name": "node-d", "cpu_pct": null}
]
```

## Step 2 — Create `fleet_check.py`
```python
"""Read-only fleet health check using local JSON input."""
import argparse
import json
import math
from pathlib import Path


def classify(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "unknown"
    if not math.isfinite(value) or not 0 <= value <= 100:
        return "unknown"
    if value >= 90:
        return "critical"
    if value >= 75:
        return "warning"
    return "healthy"


def analyze(nodes: list[dict]) -> dict:
    if not isinstance(nodes, list):
        raise ValueError("expected a JSON array")
    results = []
    counts = {key: 0 for key in ("healthy", "warning", "critical", "unknown")}
    seen = set()
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            raise ValueError(f"entry {index} must be an object")
        name = node.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"entry {index} requires a nonempty name")
        if name in seen:
            raise ValueError(f"duplicate node name: {name}")
        seen.add(name)
        cpu = node.get("cpu_pct")
        severity = classify(cpu)
        counts[severity] += 1
        results.append({"name": name, "cpu_pct": cpu, "severity": severity})
    overall = next((level for level in ("critical", "unknown", "warning")
                    if counts[level]), "healthy")
    return {"overall": overall, "counts": counts, "nodes": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local JSON fleet health checker")
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as handle:
            nodes = json.load(handle)
        result = analyze(nodes)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))
    return {"healthy": 0, "warning": 1, "critical": 2, "unknown": 3}[result["overall"]]


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_fleet_check.py`
```python
import unittest
from fleet_check import analyze, classify


class FleetCheckTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(classify(30), "healthy")
    def test_warning_boundary(self):
        self.assertEqual(classify(75), "warning")
    def test_critical_boundary(self):
        self.assertEqual(classify(90), "critical")
    def test_missing(self):
        self.assertEqual(classify(None), "unknown")
    def test_nan(self):
        self.assertEqual(classify(float("nan")), "unknown")
    def test_bool(self):
        self.assertEqual(classify(True), "unknown")
    def test_summary(self):
        report = analyze([{"name": "a", "cpu_pct": 40}, {"name": "b", "cpu_pct": 92}])
        self.assertEqual(report["counts"]["critical"], 1)
        self.assertEqual(report["overall"], "critical")
    def test_empty_fleet(self):
        self.assertEqual(analyze([])["nodes"], [])
    def test_duplicate_name(self):
        with self.assertRaises(ValueError):
            analyze([{"name": "a"}, {"name": "a"}])
    def test_invalid_entry(self):
        with self.assertRaises(ValueError):
            analyze([42])


if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Run
```bash
python fleet_check.py nodes.json
python -m unittest -v test_fleet_check.py
python -m py_compile fleet_check.py
```
The fixture contains healthy, warning, critical and unknown nodes. Overall severity is critical because critical takes precedence. The CLI exits 2 intentionally. Unit tests should report 10 passing tests.

## Step 5 — Failure injection
1. Set one CPU value to `101`; confirm it becomes unknown.
2. Duplicate a node name; confirm the tool rejects the fixture.
3. Replace the JSON array with a JSON object; confirm schema validation.
4. Use an invalid file path; confirm a readable error.
5. Restore the original fixture after each experiment.

## Design notes
The overall severity policy prioritizes critical over unknown over warning; this is an explicit example policy. Real monitoring should separately track telemetry freshness and completeness. The empty fleet returns healthy in this lab for algorithmic simplicity; **production tooling must treat an empty expected fleet as a configuration/coverage error**.

## Troubleshooting
- `FileNotFoundError`: verify working directory and fixture path.
- `JSONDecodeError`: validate JSON syntax (no trailing commas).
- Nonzero exit code: expected for critical or unknown classification.
- `ModuleNotFoundError`: run tests in the same directory as `fleet_check.py`.

## Acceptance checklist
- [ ] JSON fixture processed in order
- [ ] Four node statuses classified
- [ ] Ten tests pass
- [ ] Duplicate names rejected
- [ ] Invalid/missing telemetry handled
- [ ] No live infrastructure contacted

## Cleanup
Remove only the lab files you created.
