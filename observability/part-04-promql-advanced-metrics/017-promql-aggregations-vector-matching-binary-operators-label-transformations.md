# Chapter 017 — PromQL Aggregations, Vector Matching, Binary Operators and Label Transformations

**Part 04 — PromQL and Advanced Metrics**  
**Audience:** Enterprise SRE/DBRE, platform observability, incident responders.  
**Prerequisites:** Chapter 016, Prometheus fundamentals, Python 3.10+.  
**Outcome:** Build correct aggregation and vector-matching queries, diagnose cardinality errors and protect cluster/instance identity during DBRE investigations.

## 1. Query processing architecture

```text
TSDB selectors -> instant vectors -> grouping/aggregation
                                   |
                    binary arithmetic/comparison
                                   |
                  label-aware vector matching
                                   |
               result cardinality / query output
```

Aggregation and binary vector matching are distinct operations. Aggregation reduces series by a chosen label grouping. Binary vector-vector operators require compatible matching keys, with uniqueness constraints. PromQL evaluates over floating-point and native-histogram samples; this chapter focuses on float samples and notes where histogram rules differ.

## 2. Aggregation operators

```promql
sum by (cluster) (rate(http_requests_total[5m]))
avg by (instance) (node_load1)
max by (cluster, instance) (pg_stat_activity_count)
count by (job) (up)
min without (pod, instance) (redis_connected_clients)
topk(5, sum by (instance) (rate(http_requests_total[5m])))
```

Core aggregators include `sum`, `min`, `max`, `avg`, `count`, `stddev`, `stdvar`, `group`, `count_values`, `quantile`, `topk`, `bottomk` and `limitk`/related experimental functionality depending on version. Aggregating `rate()` outputs is generally safer than calculating a rate on aggregated raw counters when instances reset independently.

**by** retains only named grouping labels; **without** drops named labels and retains the others. Always preserve tenancy, cluster, service and other isolation dimensions when required. Never accidentally aggregate staging with production.

## 3. Binary operators and comparisons

Arithmetic: `+`, `-`, `*`, `/`, `%`, `^`. Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`. Logical/set: `and`, `or`, `unless` for instant vectors. Native histogram support varies by operator; test actual Prometheus semantics before mixing types.

```promql
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
up{job="postgres"} == 0
up{job="postgres"} == bool 0
rate(http_requests_total{code=~"5.."}[5m]) / rate(http_requests_total[5m])
```

Comparison without `bool` filters out false matches; with `bool`, matched series return 0/1. An unmatched series does not become zero just because `bool` was specified. A zero denominator and missing series require deliberate handling; do not hide absence with fabricated healthy values.

## 4. Vector matching and cardinality

PromQL matches vectors using labels. Default matching uses the full relevant label set (excluding metric name), while `on(...)` limits the matching key and `ignoring(...)` excludes specified labels. For arithmetic/comparison operators, one-to-one matching requires uniqueness; explicit `group_left`/`group_right` enables one-to-many/many-to-one with constraints, not arbitrary many-to-many joins.

```promql
node_filesystem_avail_bytes{fstype!="tmpfs"}
/
on(instance, device, mountpoint)
node_filesystem_size_bytes{fstype!="tmpfs"}
```

```promql
sum by (cluster, instance) (rate(pg_stat_database_xact_commit[5m]))
/
on(cluster, instance)
sum by (cluster, instance) (rate(pg_stat_database_xact_commit[5m]) + rate(pg_stat_database_xact_rollback[5m]))
```

The DBRE example illustrates a transaction success fraction; verify metric names, reset behavior and empty denominator semantics against your exporter.

### Group modifiers

```promql
rate(http_requests_total[5m])
* on(namespace, pod) group_left(node)
kube_pod_info
```

Use `group_left` only when the right-hand side is unique per `(namespace,pod)`. Multiple `kube_pod_info` series per key can cause matching errors. Scope by cluster when combining multiple Kubernetes clusters.

## 5. Label transformations

```promql
label_replace(
  up{job="postgres"},
  "short_instance", "$1", "instance", "([^:]+):.*"
)
```

```promql
label_join(up{job="postgres"}, "target_key", "/", "job", "instance")
```

`label_replace()` derives a destination label using regex capture groups; `label_join()` joins label values. Avoid high-cardinality derived labels, collision with existing labels and unsafe use of raw identifiers. Query-time label transformation does not fix bad instrumentation at ingest time.

## 6. SRE/DBRE production scenarios

- PostgreSQL: aggregate commits and rollbacks by cluster/instance while preserving database ownership.
- MongoDB: compare exporter target coverage across replica set members, avoiding mixing clusters.
- Elasticsearch: group JVM heap and indexing signals by node and cluster; check exporter schemas.
- Redis: aggregate connected clients by instance and service tier, not across unrelated tenants.
- Kubernetes: join pod-level metrics to pod metadata using explicit uniqueness checks.

Example:

```promql
sum by (cluster, instance) (redis_connected_clients)
```

```promql
count by (cluster, job) (up == 0)
```

`count by (cluster,job)(up == 0)` counts **matching down series**, not the number of expected but undiscovered targets. Pair with inventory/absence monitoring.

## 7. Complete executable offline lab

This Python teaching model implements **a narrow float-only subset** of aggregation, one-to-one matching and comparison filtering. It is not a PromQL parser, does not model native histograms or Prometheus's full vector-matching/output-label rules, and deliberately raises on zero division rather than implementing IEEE-754 `Inf`/`NaN` behavior.

Create:

```text
chapter017/
  fixtures/aggregation.json
  fixtures/matching.json
  scripts/promql_model.py
  tests/test_promql_model.py
```

### fixtures/aggregation.json

```json
{
  "query": {
    "kind": "aggregate",
    "op": "sum",
    "by": [
      "cluster"
    ]
  },
  "vector": [
    {
      "labels": {
        "cluster": "east",
        "instance": "pg-a",
        "job": "postgres"
      },
      "value": 12
    },
    {
      "labels": {
        "cluster": "east",
        "instance": "pg-b",
        "job": "postgres"
      },
      "value": 18
    },
    {
      "labels": {
        "cluster": "west",
        "instance": "pg-c",
        "job": "postgres"
      },
      "value": 7
    }
  ]
}
```

### fixtures/matching.json

```json
{
  "query": {
    "kind": "binary",
    "op": "/",
    "on": [
      "cluster",
      "instance"
    ]
  },
  "left": [
    {
      "labels": {
        "cluster": "east",
        "instance": "pg-a",
        "metric": "used"
      },
      "value": 40
    },
    {
      "labels": {
        "cluster": "east",
        "instance": "pg-b",
        "metric": "used"
      },
      "value": 60
    }
  ],
  "right": [
    {
      "labels": {
        "cluster": "east",
        "instance": "pg-a",
        "metric": "capacity"
      },
      "value": 100
    },
    {
      "labels": {
        "cluster": "east",
        "instance": "pg-b",
        "metric": "capacity"
      },
      "value": 120
    }
  ]
}
```

### scripts/promql_model.py

```python
#!/usr/bin/env python3
"""Offline educational subset of PromQL aggregation and vector matching."""
import json, math, re, sys
from pathlib import Path

def labels_key(labels, on=None, ignoring=None):
    if on is not None and ignoring is not None:
        raise ValueError("on and ignoring are mutually exclusive")
    if on is not None:
        return tuple(sorted((k, labels.get(k, "")) for k in on))
    return tuple(sorted((k, v) for k, v in labels.items() if k not in (ignoring or [])))

def aggregate(vector, op, by=None, without=None):
    if (by is None) == (without is None):
        raise ValueError("specify exactly one of by or without")
    if op not in ("sum", "avg", "min", "max", "count"):
        raise ValueError("unsupported aggregate")
    groups = {}
    for item in vector:
        if not math.isfinite(item["value"]):
            raise ValueError("nonfinite sample")
        labels = item["labels"]
        group = {k: v for k, v in labels.items() if k in by} if by is not None else {
            k: v for k, v in labels.items() if k not in without}
        key = tuple(sorted(group.items()))
        groups.setdefault(key, []).append(item["value"])
    out = []
    for key, values in sorted(groups.items()):
        result = {"sum": sum(values), "avg": sum(values) / len(values),
                  "min": min(values), "max": max(values), "count": len(values)}[op]
        out.append({"labels": dict(key), "value": result})
    return out

def binary(left, right, op, on=None, ignoring=None, bool_mode=False):
    if op not in ("+", "-", "*", "/", "==", ">", "<"):
        raise ValueError("unsupported operator")
    lookup = {}
    for item in right:
        key = labels_key(item["labels"], on, ignoring)
        if key in lookup:
            raise ValueError("many-to-many matching is forbidden")
        lookup[key] = item
    seen = set()
    out = []
    for item in left:
        key = labels_key(item["labels"], on, ignoring)
        if key in seen:
            raise ValueError("many-to-many matching is forbidden")
        seen.add(key)
        other = lookup.get(key)
        if other is None:
            continue
        a, b = item["value"], other["value"]
        if op == "/" and b == 0:
            raise ValueError("division by zero in educational gate")
        value = {"+": lambda: a+b, "-": lambda: a-b, "*": lambda: a*b,
                 "/": lambda: a/b, "==": lambda: a == b,
                 ">": lambda: a > b, "<": lambda: a < b}[op]()
        if op in ("==", ">", "<"):
            if bool_mode:
                value = int(value)
            elif not value:
                continue
            else:
                value = a
        out.append({"labels": dict(item["labels"]), "value": value})
    return out

def run(doc):
    q = doc["query"]
    if q["kind"] == "aggregate":
        return aggregate(doc["vector"], q["op"], q.get("by"), q.get("without"))
    if q["kind"] == "binary":
        return binary(doc["left"], doc["right"], q["op"], q.get("on"),
                      q.get("ignoring"), q.get("bool", False))
    raise ValueError("unsupported query kind")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 promql_model.py fixtures/aggregation.json")
    try:
        print(json.dumps(run(json.loads(Path(sys.argv[1]).read_text())), indent=2))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        sys.exit(f"invalid lab input: {exc}")
```

### tests/test_promql_model.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from promql_model import aggregate,binary,labels_key,run
class ModelTests(unittest.TestCase):
    def fixture(self,name="aggregation.json"):
        return json.loads((ROOT/"fixtures"/name).read_text())
    def test_aggregate(self): self.assertEqual([x["value"] for x in run(self.fixture())],[30,7])
    def test_matching(self): self.assertEqual([x["value"] for x in run(self.fixture("matching.json"))],[.4,.5])
    def test_avg(self): self.assertEqual(aggregate(self.fixture()["vector"],"avg",by=["cluster"])[0]["value"],15)
    def test_count(self): self.assertEqual(aggregate(self.fixture()["vector"],"count",by=["cluster"])[0]["value"],2)
    def test_min(self): self.assertEqual(aggregate(self.fixture()["vector"],"min",by=["cluster"])[0]["value"],12)
    def test_max(self): self.assertEqual(aggregate(self.fixture()["vector"],"max",by=["cluster"])[0]["value"],18)
    def test_without(self): self.assertEqual(len(aggregate(self.fixture()["vector"],"sum",without=["instance","job"])),2)
    def test_invalid_group(self):
        with self.assertRaises(ValueError): aggregate([], "sum", by=["cluster"],without=["instance"])
    def test_invalid_op(self):
        with self.assertRaises(ValueError): aggregate([], "median", by=["cluster"])
    def test_missing_match(self):
        self.assertEqual(binary([{"labels":{"a":"1"},"value":1}],[], "+",on=["a"]),[])
    def test_duplicate_rhs(self):
        d=self.fixture("matching.json")
        with self.assertRaises(ValueError): binary(d["left"],d["right"]+d["right"],"/",on=["cluster","instance"])
    def test_duplicate_lhs(self):
        d=self.fixture("matching.json")
        with self.assertRaises(ValueError): binary(d["left"]+d["left"],d["right"],"/",on=["cluster","instance"])
    def test_zero_denominator(self):
        with self.assertRaises(ValueError): binary([{"labels":{},"value":1}],[{"labels":{},"value":0}],"/")
    def test_filter(self):
        self.assertEqual(binary([{"labels":{},"value":2}],[{"labels":{},"value":3}],">"),[])
    def test_bool(self):
        self.assertEqual(binary([{"labels":{},"value":2}],[{"labels":{},"value":3}],">",bool_mode=True)[0]["value"],0)
    def test_comparison_filter_preserves_left(self):
        self.assertEqual(binary([{"labels":{},"value":4}],[{"labels":{},"value":3}],">")[0]["value"],4)
    def test_ignoring(self):
        self.assertEqual(labels_key({"a":"1","b":"2"},ignoring=["b"]),(("a","1"),))
    def test_on(self):
        self.assertEqual(labels_key({"a":"1","b":"2"},on=["a"]),(("a","1"),))
    def test_invalid_on_ignoring(self):
        with self.assertRaises(ValueError): labels_key({},on=[],ignoring=[])
    def test_unsupported_kind(self):
        with self.assertRaises(ValueError): run({"query":{"kind":"scalar"}})
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter017
python3 scripts/promql_model.py fixtures/aggregation.json
python3 scripts/promql_model.py fixtures/matching.json
python3 -m unittest discover -s tests -v
```

Expected: `sum by(cluster)` produces east=30, west=7; matched division produces 0.4 and 0.5; **20 tests pass**. Results are synthetic and must not be represented as live Prometheus validation.

## 8. Twenty-four hands-on exercises

1. Explain grouping semantics.
2. Query sum by cluster.
3. Query avg by instance.
4. Query min/max by node.
5. Query count by job.
6. Explain `without`.
7. Explain `topk`.
8. Compare rate-then-sum.
9. Test arithmetic operators.
10. Compare filter and bool.
11. Explain unmatched series.
12. Build one-to-one match.
13. Use `on()`.
14. Use `ignoring()`.
15. Diagnose duplicate RHS keys.
16. Diagnose duplicate LHS keys.
17. Review group_left uniqueness.
18. Review group_right uniqueness.
19. Transform label with label_replace.
20. Combine labels with label_join.
21. Preserve cluster isolation.
22. Run aggregation fixture.
23. Run matching fixture and 20 tests.
24. Peer-review DBRE PromQL and rollback.

## 9. Twenty production failure scenarios

| # | Failure | Diagnostic direction |
|---|---|---|
| 01 | cross-cluster aggregation | missing grouping |
| 02 | query returns empty | label mismatch |
| 03 | many-to-many matching | duplicate keys |
| 04 | group_left duplicates | RHS uniqueness |
| 05 | group_right duplicates | LHS uniqueness |
| 06 | metric name mismatch | exporter contract |
| 07 | wrong counter aggregation | reset handling |
| 08 | division by zero | denominator |
| 09 | missing series treated as zero | absence |
| 10 | bool query misunderstood | comparison semantics |
| 11 | label_replace collision | derived labels |
| 12 | label_join cardinality | label policy |
| 13 | regex too broad | query load |
| 14 | topk wrong scope | grouping |
| 15 | summary quantiles summed | invalid math |
| 16 | histogram types mixed | operator support |
| 17 | Redis tenants merged | isolation |
| 18 | PostgreSQL database identity lost | aggregation |
| 19 | Kubernetes metadata join mismatch | pod labels |
| 20 | high query CPU | cardinality/joins |

## 10. Eight production runbooks

**A. Wrong aggregate:** Check metric type, grouping labels, tenant/cluster scope and counter resets.

**B. Many-to-many error:** Inspect both vector label sets, unique matching keys and group modifiers; remove duplicates at source.

**C. Missing joined data:** Verify `on`/`ignoring`, exporter labels, staleness and expected target inventory.

**D. Invalid ratio:** Inspect denominator zeros, missing samples, counter semantics and compatible units.

**E. Label transformation issue:** Review regex capture groups, label collisions and cardinality; stage rollback.

**F. Query performance regression:** Bound selectors and time range, avoid expensive joins and review recording rules.

**G. DBRE incident query:** Preserve cluster/database/tenant labels, correlate exporter health and verify query interpretation.

**H. Production change review:** Require peer review, tests, evidence, query cost budget, alert impact and rollback plan.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Aggregations and grouping | 20 |
| Binary operators and comparisons | 20 |
| Vector matching and labels | 20 |
| Executable lab and 20 tests | 20 |
| DBRE troubleshooting and runbooks | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: preserve cluster identity, reject duplicate matching keys, explain absent-vs-zero and pass the automated tests.

## 12. Evidence worksheet

```text
UTC / operator / Prometheus version:
Aggregation output and grouping:
Vector matching keys:
Duplicate-key negative test:
Comparison filter/bool behavior:
Label transformation:
DBRE query correctness:
20 offline unit tests:
Incident runbook / reviewer / score:
```

**Companion:** [Chapter 017 executable lab](labs/017-promql-aggregations-vector-matching-binary-operators-label-transformations-lab.md).

**Next:** Chapter 018 — PromQL Rate, Increase, Histograms, Quantiles and Latency Analysis.
