# Chapter 011 — Hands-on Lab: SRE Fleet Metrics Transformation

## Goal
Read synthetic node CPU metrics from local JSON, validate data, filter by threshold, rank nodes by CPU usage and emit a deterministic JSON report. No cloud or Kubernetes API access.

## Prerequisites
Python 3.10+; standard library only.

## Step 1 — Create `fleet.json`
```json
[
  {"node": "node-c", "cpu_pct": 96},
  {"node": "node-a", "cpu_pct": 45},
  {"node": "node-b", "cpu_pct": 88},
  {"node": "node-d", "cpu_pct": 88}
]
```

## Step 2 — Create `fleet_rank.py`
```python
"""Read-only ranking of simulated CPU metrics."""
import argparse
import json
import math
from pathlib import Path


def percentage(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected numeric percentage") from exc
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise argparse.ArgumentTypeError("percentage must be finite and in [0,100]")
    return value


def validate(records: object) -> list[dict]:
    if not isinstance(records, list) or not records:
        raise ValueError("expected a nonempty JSON array")
    clean = []
    seen = set()
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"entry {index} must be an object")
        name, cpu = record.get("node"), record.get("cpu_pct")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"entry {index}: invalid node")
        if name in seen:
            raise ValueError(f"duplicate node: {name}")
        if isinstance(cpu, bool) or not isinstance(cpu, (int, float)):
            raise ValueError(f"{name}: invalid cpu_pct")
        if not math.isfinite(cpu) or not 0 <= cpu <= 100:
            raise ValueError(f"{name}: cpu_pct must be finite and in [0,100]")
        seen.add(name)
        clean.append({"node": name, "cpu_pct": cpu})
    return clean


def analyze(records: object, threshold: float = 80) -> dict:
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("invalid threshold")
    if not math.isfinite(threshold) or not 0 <= threshold <= 100:
        raise ValueError("invalid threshold")
    nodes = validate(records)
    ranked = sorted(nodes, key=lambda item: (-item["cpu_pct"], item["node"]))
    high = [item for item in ranked if item["cpu_pct"] >= threshold]
    return {
        "node_count": len(nodes),
        "threshold_pct": threshold,
        "above_threshold_count": len(high),
        "above_threshold": high,
        "ranked_nodes": ranked,
        "average_cpu_pct": round(sum(item["cpu_pct"] for item in nodes) / len(nodes), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only fleet CPU ranking")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--threshold", type=percentage, default=80)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            records = json.load(source)
        report = analyze(records, args.threshold)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_fleet_rank.py`
```python
import argparse
import unittest
from fleet_rank import analyze, percentage, validate

def node(name="a", cpu=50):
    return {"node": name, "cpu_pct": cpu}

class FleetRankTests(unittest.TestCase):
    def test_sort_descending(self):
        report = analyze([node("a", 30), node("b", 90)])
        self.assertEqual(report["ranked_nodes"][0]["node"], "b")
    def test_tie_breaker(self):
        report = analyze([node("z", 80), node("a", 80)])
        self.assertEqual(report["ranked_nodes"][0]["node"], "a")
    def test_threshold_inclusive(self):
        self.assertEqual(analyze([node(cpu=80)])["above_threshold_count"], 1)
    def test_average(self):
        self.assertEqual(analyze([node("a", 20), node("b", 40)])["average_cpu_pct"], 30)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate([node(), node()])
    def test_empty(self):
        with self.assertRaises(ValueError):
            validate([])
    def test_nan(self):
        with self.assertRaises(ValueError):
            validate([node(cpu=float("nan"))])
    def test_bool(self):
        with self.assertRaises(ValueError):
            validate([node(cpu=True)])
    def test_missing(self):
        with self.assertRaises(ValueError):
            validate([{"node": "a"}])
    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            validate([node(cpu=101)])
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            analyze([node()], threshold=-1)
    def test_parser_nan(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            percentage("nan")

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python fleet_rank.py --input fleet.json
python fleet_rank.py --input fleet.json --threshold 90
python -m unittest -v test_fleet_rank.py
python -m py_compile fleet_rank.py
```
Expected: four nodes, three at or above 80%, one at or above 90%, average CPU 79.25%, descending ranking with node-b before node-d for the tie. Twelve unit tests should pass.

## Step 5 — Failure injection
1. Duplicate a node name: reject input.
2. Set `cpu_pct` to 101 or null: reject input.
3. Use an empty list: reject input.
4. Supply `--threshold nan`: reject CLI argument.
5. Use a missing file path: show a readable error.

## Interpretation
These are **synthetic instantaneous CPU percentages**; they are not observed live utilization and do not demonstrate sustained overload. The tool does not change any infrastructure.

## Acceptance checklist
- [ ] Correct descending rank and stable tie breaker
- [ ] Inclusive threshold filtering
- [ ] Correct average
- [ ] Twelve tests pass
- [ ] Invalid inputs rejected
- [ ] No production access required

## Cleanup
Delete only lab files created locally.
