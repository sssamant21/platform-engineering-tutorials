# Chapter 016 — PromQL Fundamentals, Selectors, Instant Vectors, Range Vectors and Query Semantics

**Part 04 — PromQL and Advanced Metrics**  
**Audience:** SRE/DBRE, observability platform, on-call engineers.  
**Prerequisites:** Chapters 011–015, Python 3.10+ for the offline lab.  
**Objective:** Read and construct safe PromQL selectors, distinguish instant/range vectors, understand lookback and staleness, and avoid common database observability query errors.

## 1. PromQL evaluation model

PromQL evaluates expressions at a timestamp. An instant query returns one result per matching time series at the chosen evaluation time; a range query API evaluates an expression at multiple timestamps across a step grid. These are **different from an instant vector selector** and a **range vector selector**.

```text
Prometheus TSDB -> label index -> series selection -> sample window
                                                     |
                              instant selector: latest valid sample
                              range selector: window of samples
                                                     |
                              functions/operators/aggregations
                                                     |
                              instant query or stepped range query API
```

A series identity is its metric name plus labels. Time series with different labels remain distinct even if their values match. Do not use patient identifiers, request IDs or unbounded SQL query strings as labels.

## 2. Core PromQL value types

| Type | Example | Meaning |
|---|---|---|
| Instant vector | `up{job="postgres"}` | one sample per selected series at evaluation time |
| Range vector | `up{job="postgres"}[5m]` | samples per selected series within a trailing window |
| Scalar | `42` | single floating-point value |
| String | `"hello"` | string literal; limited practical use |

A range vector cannot be used directly everywhere an instant vector is expected. Use `rate()`, `increase()`, `avg_over_time()`, `max_over_time()` or similar functions according to metric semantics.

## 3. Selectors and matchers

```promql
up
up{job="postgres"}
up{job!="redis"}
up{job=~"postgres|mongodb"}
up{environment!~"dev|test"}
{__name__=~"pg_.*",job="postgres"}
```

The four matcher operators are `=`, `!=`, `=~` and `!~`. Regex matchers are fully anchored in PromQL; `job=~"post"` does not match `postgres`, but `job=~"post.*"` does. Missing labels behave like empty values for matching purposes; a negative matcher can therefore include unlabeled series. Selectors without a metric name must contain at least one matcher that cannot match the empty string.

Prefer a specific metric name and bounded `job`/`instance`/`cluster` filters. Avoid broad regex selectors on high-cardinality metric namespaces. Verify that relabeling does not accidentally change expected identity.

## 4. Instant vectors, lookback and staleness

At evaluation time `T`, an instant selector normally uses the latest sample within the configured lookback delta (typically five minutes). It does not interpolate between samples. Prometheus staleness markers prevent previously stale series from silently remaining present after a target disappears. Exact behavior depends on scrape/discovery lifecycle and query context.

```text
Time (seconds)       100       300       500       550
up{job="postgres"}    1         1         1         ^
                                               latest=500
```

At `T=550`, `up{job="postgres"}` selects the latest non-stale sample. A selector may return no series when samples are too old or stale; this is different from returning numeric zero.

## 5. Range vectors and window boundaries

```promql
up{job="postgres"}[5m]
rate(http_requests_total{job="api"}[5m])
avg_over_time(node_load1[10m])
max_over_time(pg_stat_activity_count[15m])
```

A range selector includes samples in the interval **(T − window, T]**: the left boundary is excluded and right boundary included. A `[5m]` selector contains raw samples, not five minutes of pre-aggregated averages. Scrape gaps and stale markers affect the number of usable samples.

Use `rate()` for counters and `avg_over_time()` for gauges. Do not apply `rate()` to gauges or directly sum per-instance summary quantiles.

## 6. Query API and step semantics

```bash
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=up{job="postgres"}'
curl -G 'http://127.0.0.1:9090/api/v1/query_range' \
  --data-urlencode 'query=up{job="postgres"}' \
  --data-urlencode 'start=2026-10-17T12:00:00Z' \
  --data-urlencode 'end=2026-10-17T12:15:00Z' \
  --data-urlencode 'step=30s'
```

The range-query API repeats evaluation of the expression every step. It does not convert `up` into a range vector type. Always bound time ranges, steps, series counts and query concurrency. Timestamps above are examples, not evidence of live data.

## 7. Operators and labels

```promql
sum by (job) (up)
count by (job) (up)
sum by (cluster) (rate(http_requests_total[5m]))
up{job="postgres"} == 0
up{job="postgres"} == bool 0
```

Comparison without `bool` filters out false matches; with `bool`, matching series receive 0/1 values (subject to vector matching). Aggregation can remove important labels: use `by` or `without` intentionally. Vector-vector operations match series by labels; `on()`, `ignoring()`, `group_left` and `group_right` are advanced constructs that require cardinality and uniqueness checks.

## 8. DBRE examples

```promql
up{job=~"postgres|mongodb|elasticsearch|redis"}
```

```promql
sum by (instance) (rate(pg_stat_database_xact_commit[5m]))
```

```promql
max by (instance) (redis_connected_clients)
```

```promql
absent_over_time(up{job="postgres",instance="pg-primary:9187"}[5m])
```

Exporter metric names vary by version/configuration. Verify actual `/metrics` output and exporter documentation before relying on example queries. `absent_over_time` is useful for missing expected targets, while `up == 0` detects failed scrapes of discovered targets.

## 9. Complete offline executable lab

The Python model below demonstrates a **subset** of selector behavior. It is **not** a PromQL parser or full Prometheus evaluator. In particular, it models a `null` sample as a simplified stale marker and omits PromQL operators, native histograms, subqueries, offsets, interpolation and full engine edge cases.

Create:

```text
chapter016/
  fixtures/instant.json
  fixtures/range.json
  scripts/selector_lab.py
  tests/test_selector_lab.py
```

### fixtures/instant.json

```json
{
  "query": {
    "kind": "instant",
    "metric": "up",
    "matchers": [
      {
        "label": "job",
        "op": "=",
        "value": "postgres"
      }
    ],
    "evaluation_time": 550,
    "lookback": 300
  },
  "series": [
    {
      "metric": "up",
      "labels": {
        "job": "postgres",
        "instance": "pg-a:9187",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          300,
          1
        ],
        [
          500,
          1
        ]
      ]
    },
    {
      "metric": "up",
      "labels": {
        "job": "postgres",
        "instance": "pg-b:9187",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          300,
          0
        ],
        [
          500,
          1
        ]
      ]
    },
    {
      "metric": "up",
      "labels": {
        "job": "redis",
        "instance": "redis-a:9121",
        "environment": "stage"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          300,
          1
        ],
        [
          500,
          1
        ]
      ]
    },
    {
      "metric": "db_connections",
      "labels": {
        "job": "postgres",
        "instance": "pg-a:9187",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          30
        ],
        [
          300,
          40
        ],
        [
          500,
          45
        ]
      ]
    },
    {
      "metric": "up",
      "labels": {
        "job": "mongo",
        "instance": "mongo-a:9216",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          150,
          null
        ]
      ]
    }
  ]
}
```

### fixtures/range.json

```json
{
  "query": {
    "kind": "range",
    "metric": "up",
    "matchers": [
      {
        "label": "environment",
        "op": "=~",
        "value": "prod"
      }
    ],
    "evaluation_time": 550,
    "window": 300
  },
  "series": [
    {
      "metric": "up",
      "labels": {
        "job": "postgres",
        "instance": "pg-a:9187",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          300,
          1
        ],
        [
          500,
          1
        ]
      ]
    },
    {
      "metric": "up",
      "labels": {
        "job": "postgres",
        "instance": "pg-b:9187",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          300,
          0
        ],
        [
          500,
          1
        ]
      ]
    },
    {
      "metric": "up",
      "labels": {
        "job": "redis",
        "instance": "redis-a:9121",
        "environment": "stage"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          300,
          1
        ],
        [
          500,
          1
        ]
      ]
    },
    {
      "metric": "db_connections",
      "labels": {
        "job": "postgres",
        "instance": "pg-a:9187",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          30
        ],
        [
          300,
          40
        ],
        [
          500,
          45
        ]
      ]
    },
    {
      "metric": "up",
      "labels": {
        "job": "mongo",
        "instance": "mongo-a:9216",
        "environment": "prod"
      },
      "samples": [
        [
          100,
          1
        ],
        [
          150,
          null
        ]
      ]
    }
  ]
}
```

### scripts/selector_lab.py

```python
#!/usr/bin/env python3
"""Offline PromQL selector teaching model, NOT a PromQL parser or engine."""
import json, math, re, sys
from pathlib import Path
NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
LABEL = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
OPS = {"=", "!=", "=~", "!~"}

def validate_selector(metric, matchers):
    if metric is not None and (not isinstance(metric, str) or not NAME.fullmatch(metric)):
        raise ValueError("invalid metric name")
    if not isinstance(matchers, list):
        raise ValueError("matchers must be a list")
    for m in matchers:
        if not isinstance(m, dict) or set(m) != {"label", "op", "value"}:
            raise ValueError("invalid matcher")
        if not isinstance(m["label"], str) or not LABEL.fullmatch(m["label"]):
            raise ValueError("invalid label")
        if m["op"] not in OPS or not isinstance(m["value"], str):
            raise ValueError("invalid matcher operator/value")
        if m["op"] in ("=~", "!~"):
            re.compile(m["value"])
    if metric is None and not any(m["op"] in ("=", "=~") and
       (m["value"] != "" if m["op"] == "=" else re.fullmatch(m["value"], "") is None)
       for m in matchers):
        raise ValueError("selector without metric must include nonempty matcher")

def matches(labels, matcher):
    actual = labels.get(matcher["label"], "")
    op, expected = matcher["op"], matcher["value"]
    if op == "=": return actual == expected
    if op == "!=": return actual != expected
    if op == "=~": return re.fullmatch(expected, actual) is not None
    return re.fullmatch(expected, actual) is None

def instant_vector(series, metric, matchers, evaluation_time, lookback=300):
    validate_selector(metric, matchers)
    if not isinstance(evaluation_time, (int, float)) or not math.isfinite(evaluation_time):
        raise ValueError("invalid evaluation time")
    if not isinstance(lookback, (int, float)) or not math.isfinite(lookback) or lookback <= 0:
        raise ValueError("invalid lookback")
    output = []
    for s in series:
        if metric is not None and s["metric"] != metric: continue
        if not all(matches(s["labels"], m) for m in matchers): continue
        eligible = [p for p in s["samples"] if
                    evaluation_time - lookback < p[0] <= evaluation_time]
        if not eligible: continue
        timestamp, value = max(eligible, key=lambda p: p[0])
        if value is None: continue  # teaching stand-in for a stale marker
        output.append({"metric": s["metric"], "labels": s["labels"],
                       "timestamp": timestamp, "value": value})
    return output

def range_vector(series, metric, matchers, evaluation_time, window):
    validate_selector(metric, matchers)
    if not isinstance(window, (int, float)) or not math.isfinite(window) or window <= 0:
        raise ValueError("invalid range")
    output = []
    for s in series:
        if metric is not None and s["metric"] != metric: continue
        if not all(matches(s["labels"], m) for m in matchers): continue
        points = [p for p in s["samples"] if evaluation_time - window < p[0] <= evaluation_time]
        if points: output.append({"metric": s["metric"], "labels": s["labels"], "samples": points})
    return output

def run(doc):
    kind = doc["query"]["kind"]
    metric = doc["query"].get("metric")
    matchers = doc["query"].get("matchers", [])
    ts = doc["query"]["evaluation_time"]
    if kind == "instant":
        return instant_vector(doc["series"], metric, matchers, ts,
                              doc["query"].get("lookback", 300))
    if kind == "range":
        return range_vector(doc["series"], metric, matchers, ts,
                            doc["query"]["window"])
    raise ValueError("kind must be instant or range")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 selector_lab.py fixtures/instant.json")
    try:
        print(json.dumps(run(json.loads(Path(sys.argv[1]).read_text())), indent=2))
    except (KeyError, TypeError, ValueError, OSError) as error:
        sys.exit(f"invalid lab input: {error}")
```

### tests/test_selector_lab.py

```python
import json
import re
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from selector_lab import instant_vector, range_vector, matches, validate_selector, run
class PromQLModelTests(unittest.TestCase):
    def fixture(self, name="instant.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())
    def test_instant_count(self): self.assertEqual(len(run(self.fixture())), 2)
    def test_instant_values(self): self.assertEqual([s["value"] for s in run(self.fixture())], [1,1])
    def test_range_count(self): self.assertEqual(len(run(self.fixture("range.json"))), 2)
    def test_range_left_open(self):
        d = self.fixture("range.json")
        self.assertEqual(run(d)[0]["samples"], [[300,1],[500,1]])
    def test_regex_full_match(self):
        self.assertTrue(matches({"job":"postgres"}, {"label":"job","op":"=~","value":"post.*"}))
    def test_regex_not_match(self):
        self.assertFalse(matches({"job":"postgres"}, {"label":"job","op":"=~","value":"post"}))
    def test_negative_match_missing_label(self):
        self.assertTrue(matches({}, {"label":"zone","op":"!=","value":"us-east"}))
    def test_missing_label_equals_empty(self):
        self.assertTrue(matches({}, {"label":"zone","op":"=","value":""}))
    def test_old_series_excluded(self):
        d=self.fixture()
        d["query"]["evaluation_time"]=900
        self.assertEqual(run(d),[])
    def test_stale_marker_excluded(self):
        d=self.fixture()
        d["query"]["metric"]="up"
        d["query"]["matchers"]=[{"label":"job","op":"=","value":"mongo"}]
        d["query"]["evaluation_time"]=200
        self.assertEqual(run(d),[])
    def test_bad_metric(self):
        with self.assertRaises(ValueError): validate_selector("bad-name", [])
    def test_bad_label(self):
        with self.assertRaises(ValueError):
            validate_selector("up", [{"label":"bad-label","op":"=","value":"x"}])
    def test_bad_regex(self):
        with self.assertRaises(re.error):
            validate_selector("up", [{"label":"job","op":"=~","value":"["}])
    def test_unbounded_selector(self):
        with self.assertRaises(ValueError): validate_selector(None, [])
    def test_empty_matcher_without_metric(self):
        with self.assertRaises(ValueError):
            validate_selector(None,[{"label":"job","op":"=","value":""}])
    def test_zero_range(self):
        with self.assertRaises(ValueError):
            range_vector([], "up", [], 500, 0)
    def test_invalid_kind(self):
        d=self.fixture()
        d["query"]["kind"]="scalar"
        with self.assertRaises(ValueError): run(d)
    def test_invalid_lookback(self):
        with self.assertRaises(ValueError): instant_vector([], "up", [], 500, 0)
    def test_not_equal(self):
        self.assertTrue(matches({"job":"redis"},{"label":"job","op":"!=","value":"postgres"}))
    def test_not_regex(self):
        self.assertTrue(matches({"job":"redis"},{"label":"job","op":"!~","value":"post.*"}))
if __name__ == "__main__":
    unittest.main()
```

### Execute

```bash
cd chapter016
python3 scripts/selector_lab.py fixtures/instant.json
python3 scripts/selector_lab.py fixtures/range.json
python3 -m unittest discover -s tests -v
```

Expected: two PostgreSQL `up` instant series with values 1; two PostgreSQL range series with samples after timestamp 250; **20 unit tests pass**. These are deterministic synthetic inputs, not a live Prometheus integration test.

## 10. Twenty-four hands-on exercises

1. Distinguish instant query from instant vector.
2. Distinguish range query API from range vector.
3. Inspect metric name/labels.
4. Query `up`.
5. Filter by `job`.
6. Filter by `instance`.
7. Use exact matcher.
8. Use negative matcher.
9. Use regex matcher.
10. Explain anchored regex.
11. Explain missing label matching.
12. Explain selectors without metric name.
13. Inspect lookback behavior.
14. Inspect staleness behavior.
15. Evaluate a five-minute range.
16. Explain left-open window.
17. Compare gauge and counter queries.
18. Apply `rate()` to counter.
19. Apply `avg_over_time()` to gauge.
20. Compare `==` with `== bool`.
21. Aggregate `sum by (job)`.
22. Run offline instant fixture.
23. Run offline range fixture and 20 tests.
24. Document production query review and evidence.

## 11. Twenty production failure scenarios

| # | Scenario | Root-cause direction |
|---|---|---|
| 01 | Query returns empty vector | labels/absence/lookback |
| 02 | Target DOWN shown as 0 | `up` scrape health |
| 03 | Missing target silently omitted | `absent_over_time` |
| 04 | Broad regex slow query | cardinality |
| 05 | Regex unexpectedly excludes job | anchoring |
| 06 | Negative matcher includes missing label | empty-label semantics |
| 07 | Range window too short | sparse samples |
| 08 | Rate missing after startup | insufficient samples |
| 09 | Counter reset misread | rate vs subtraction |
| 10 | Gauge used with rate | metric semantics |
| 11 | Stale series expected as zero | staleness |
| 12 | Scrape gaps distort trend | target history |
| 13 | Query range step too coarse | aliasing |
| 14 | Query range step too fine | load |
| 15 | Aggregation drops cluster | labels |
| 16 | Duplicate series | target identity |
| 17 | Summary quantiles aggregated | invalid math |
| 18 | Vector matching many-to-many | label uniqueness |
| 19 | Sensitive label exposure | privacy |
| 20 | Exporter metric renamed | version contract |

## 12. Eight production runbooks

**A. Empty PromQL result:** Verify metric exists, target discovery, labels, evaluation time, lookback and staleness.

**B. Incorrect availability:** Compare `up == 0` and missing-target inventory/absence; avoid treating absent as healthy.

**C. Query overload:** Reduce regex scope, range, step and concurrency; inspect cardinality and query logs.

**D. Counter-rate anomaly:** Check resets, sample density, counter semantics and scrape gaps.

**E. Gauge aggregation issue:** Confirm units, ownership, grouping labels and valid aggregation.

**F. Vector matching failure:** Inspect label sets, uniqueness and `on`/`ignoring` clauses before group modifiers.

**G. Exporter schema drift:** Compare exposed metric names and labels with dashboards/rules; roll back incompatible changes.

**H. PromQL change review:** Peer review query cost, correctness, absent behavior, test fixtures, alerts and rollback.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| Types, selectors and matchers | 20 |
| Lookback, staleness and windows | 20 |
| Operators, aggregations and DBRE queries | 20 |
| Executable lab and 20 tests | 20 |
| Production troubleshooting and runbooks | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Mandatory gates: distinguish absent from zero, demonstrate correct range boundaries, bound regex/cardinality, and pass all offline tests.

## 14. Evidence worksheet

```text
UTC / operator / Prometheus version:
Metric names and label contract:
Instant selector output:
Range selector output:
Lookback/staleness explanation:
Regex and missing-label review:
Counter/gauge query:
Offline 20 tests:
Incident scenario and runbook:
Reviewer / score / next action:
```

**Companion:** [Chapter 016 executable selector lab](labs/016-promql-fundamentals-selectors-instant-vectors-range-vectors-query-semantics-lab.md).

**Next:** Chapter 017 — PromQL Aggregations, Vector Matching, Binary Operators and Label Transformations.
