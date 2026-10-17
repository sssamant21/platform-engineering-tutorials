# Chapter 018 — PromQL Rate, Increase, Histograms, Quantiles and Latency Analysis

**Part 04 — PromQL and Advanced Metrics**  
**Audience:** Enterprise SRE/DBRE, application and observability engineers.  
**Prerequisites:** Chapters 016–017, Prometheus metrics fundamentals, Python 3.10+.  
**Outcome:** Interpret counter rates and resets, calculate error fractions, understand histogram bucket semantics and design reliable latency/error SLO queries.

## 1. Architecture: from samples to reliability decisions

```text
HTTP / DB operation -> instrumented counter or histogram
                                   |
                           Prometheus scrape
                                   |
                         TSDB range selector
                                   |
              rate / increase / histogram_quantile
                                   |
                        aggregate by service
                                   |
                     dashboard / SLO / alert
```

Use counters for cumulative events and histograms for distributions. A counter can reset on restart; a gauge can increase or decrease. Histogram quantiles approximate a distribution and require correct bucket aggregation. Instrumentation and scrape intervals determine the quality of all downstream analysis.

## 2. rate(), irate() and increase()

```promql
rate(http_requests_total[5m])
irate(http_requests_total[5m])
increase(http_requests_total[1h])
sum by (service) (rate(http_requests_total[5m]))
```

`rate()` estimates per-second average counter increase over the range and adjusts for counter resets and extrapolates to the range boundaries. `irate()` uses the last two samples and is noisier; use primarily for exploratory high-frequency graphs, not slow-burn alerting. `increase()` estimates total increase over the selected window, including extrapolation. Both `rate()` and `increase()` can produce noninteger estimates for integer counters.

**Important:** `sum(rate(counter[5m]))` is preferable to `rate(sum(counter)[5m])`: compute reset-aware rates **before** aggregating distinct series. A simple delta divided by elapsed time is useful for teaching but is **not equivalent** to Prometheus's extrapolation algorithm.

## 3. Classic histogram architecture

Classic histograms export cumulative `_bucket{le="..."}`, `_sum` and `_count` series. Each bucket includes all observations at or below its upper bound. The `+Inf` bucket equals the observation count. Buckets must be monotonically cumulative; incorrect aggregation can break quantile calculations.

```promql
sum by (le, service) (rate(http_request_duration_seconds_bucket[5m]))
```

```promql
histogram_quantile(
  0.95,
  sum by (le, service) (rate(http_request_duration_seconds_bucket[5m]))
)
```

```promql
sum by (service) (rate(http_request_duration_seconds_sum[5m]))
/
sum by (service) (rate(http_request_duration_seconds_count[5m]))
```

The last expression estimates mean duration; it is **not** p95. Histograms use interpolation within bucket boundaries; wide buckets can make quantile estimates imprecise. Native histograms use different sample representation and can be queried with compatible functions/aggregation depending on Prometheus version and enabled features. Validate deployment-specific native histogram semantics.

## 4. Quantile design and accuracy

`histogram_quantile(0.95, ...)` estimates the 95th percentile from bucket rates. Do not average per-instance p95 values to calculate service p95; aggregate bucket rates first and then calculate the quantile.

Example: 100 observations, cumulative bucket counts 40 at 100 ms, 85 at 250 ms, 96 at 500 ms, 99 at 1 s and 100 at +Inf. The estimated p95 lies between 250 and 500 ms. A classic histogram with poor bucket placement cannot precisely reconstruct the original observations.

Choose buckets near SLO thresholds, avoid unbounded labels and estimate series multiplication: number of histogram buckets × label combinations × instances. Review exemplar and trace integration separately.

## 5. Error fraction and burn-rate semantics

```promql
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
/
sum by (service) (rate(http_requests_total[5m]))
```

For a 99.9% availability SLO, the error budget fraction is 0.001. Burn rate is observed error fraction divided by the budget fraction. Use sufficiently long windows and minimum-traffic safeguards to reduce noise. Distinguish server errors from expected client errors and define DBRE-specific failure classes.

```promql
(
  sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(http_requests_total[5m]))
) / 0.001
```

This example assumes the same metric/label scope in numerator and denominator. A zero denominator can produce NaN/Inf or missing output; do not silently interpret it as zero errors or a healthy service.

## 6. DBRE-specific query patterns

PostgreSQL transaction throughput:

```promql
sum by (cluster, instance) (rate(pg_stat_database_xact_commit[5m]))
```

Redis operations rate, where exporter provides command counters:

```promql
sum by (instance, cmd) (rate(redis_commands_processed_total[5m]))
```

Elasticsearch request latency, if a compatible instrumented histogram exists:

```promql
histogram_quantile(
  0.99,
  sum by (le, cluster) (rate(db_request_duration_seconds_bucket{database="elasticsearch"}[5m]))
)
```

These are **illustrative**. Exporter metric names vary; `db_request_duration_seconds_bucket` is a proposed custom instrumentation name rather than a standard Elasticsearch exporter metric. Check actual exporter output before adopting any rule.

## 7. Production safeguards

1. Bound histogram labels; never use raw SQL text, user IDs, session IDs or request IDs.
2. Use counter rates with sufficient sample density and account for resets.
3. Preserve `le` when aggregating classic histogram buckets.
4. Avoid combining incompatible bucket boundaries without review.
5. Separate service latency from scrape duration and query execution latency.
6. Validate high-cardinality impact and recording-rule query cost.
7. Test missing data, low traffic, denominator zero and exporter restarts.
8. Protect query APIs, enforce retention and review alerts against SLO policy.

## 8. Complete executable offline lab

The following Python code models **observed counter deltas** and **classic histogram linear interpolation**, not the full Prometheus query engine. It deliberately does not implement Prometheus extrapolation, native histograms or special floating-point behavior.

Create:

```text
chapter018/
  fixtures/healthy.json
  scripts/latency_lab.py
  tests/test_latency_lab.py
```

### fixtures/healthy.json

```json
{
  "window_seconds": 300,
  "counters": {
    "requests": [
      [
        0,
        100
      ],
      [
        60,
        160
      ],
      [
        120,
        210
      ],
      [
        180,
        15
      ],
      [
        240,
        75
      ],
      [
        300,
        135
      ]
    ],
    "errors": [
      [
        0,
        3
      ],
      [
        60,
        5
      ],
      [
        120,
        7
      ],
      [
        180,
        0
      ],
      [
        240,
        2
      ],
      [
        300,
        4
      ]
    ]
  },
  "histogram": {
    "buckets": [
      {
        "le": 0.1,
        "cumulative": 40
      },
      {
        "le": 0.25,
        "cumulative": 85
      },
      {
        "le": 0.5,
        "cumulative": 96
      },
      {
        "le": 1,
        "cumulative": 99
      },
      {
        "le": "+Inf",
        "cumulative": 100
      }
    ],
    "sum": 23.5,
    "count": 100
  },
  "slo": {
    "error_budget_fraction": 0.01,
    "latency_target_seconds": 0.5
  }
}
```

### scripts/latency_lab.py

```python
#!/usr/bin/env python3
"""Deterministic teaching model, not PromQL's extrapolation or native histograms."""
import json, math, sys
from pathlib import Path

def counter_delta(samples):
    if len(samples) < 2: raise ValueError("at least two samples required")
    last_t = None
    delta = 0.
    previous = None
    for t, value in samples:
        if not all(type(x) in (int,float) and math.isfinite(x) for x in (t,value)):
            raise ValueError("invalid sample")
        if value < 0 or (last_t is not None and t <= last_t):
            raise ValueError("invalid counter or timestamps")
        if previous is not None:
            delta += value - previous if value >= previous else value
        previous, last_t = value, t
    return delta

def simple_rate(samples):
    duration = samples[-1][0] - samples[0][0]
    if duration <= 0: raise ValueError("invalid duration")
    return counter_delta(samples) / duration

def bucket_quantile(q, buckets):
    if not isinstance(q,(int,float)) or not math.isfinite(q) or not 0 <= q <= 1:
        raise ValueError("invalid quantile")
    if not buckets or buckets[-1]["le"] != "+Inf":
        raise ValueError("missing +Inf bucket")
    last_bound, last_count = 0., 0.
    normalized = []
    for item in buckets:
        bound = math.inf if item["le"] == "+Inf" else item["le"]
        count = item["cumulative"]
        if type(bound) not in (int,float) or type(count) not in (int,float) or not math.isfinite(count) or count < last_count or bound <= last_bound:
            raise ValueError("invalid bucket sequence")
        normalized.append((bound,count))
        last_bound,last_count = bound,count
    if last_count <= 0: return math.nan
    if q == 1: return normalized[-2][0]
    rank = q * last_count
    lower_bound, lower_count = 0., 0.
    for bound,count in normalized:
        if count >= rank:
            if math.isinf(bound): return lower_bound
            if count == lower_count: return bound
            return lower_bound + (bound - lower_bound) * (rank - lower_count) / (count - lower_count)
        lower_bound,lower_count = bound,count
    return math.nan

def analyze(d):
    duration = d["window_seconds"]
    if type(duration) not in (int,float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid window")
    requests = counter_delta(d["counters"]["requests"])
    errors = counter_delta(d["counters"]["errors"])
    if errors > requests or requests <= 0: raise ValueError("invalid error fraction")
    h=d["histogram"]
    if h["count"] != h["buckets"][-1]["cumulative"] or h["count"] <= 0 or h["sum"] < 0:
        raise ValueError("inconsistent histogram")
    slo=d["slo"]
    budget=slo["error_budget_fraction"]
    if type(budget) not in (int,float) or not 0 <= budget <= 1:
        raise ValueError("invalid error budget")
    target=slo["latency_target_seconds"]
    if type(target) not in (int,float) or target <= 0:
        raise ValueError("invalid latency target")
    return {"request_delta":requests,"error_delta":errors,
            "simple_request_rate_per_second":round(simple_rate(d["counters"]["requests"]),5),
            "error_fraction":round(errors/requests,5),
            "latency_p95_seconds_approx":round(bucket_quantile(.95,h["buckets"]),5),
            "mean_latency_seconds":round(h["sum"]/h["count"],5),
            "error_budget_pass":errors/requests <= budget,
            "latency_p95_pass":bucket_quantile(.95,h["buckets"]) <= target}

if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 latency_lab.py fixtures/healthy.json")
    try: print(json.dumps(analyze(json.loads(Path(sys.argv[1]).read_text())),indent=2))
    except (OSError,KeyError,TypeError,ValueError) as e: sys.exit(f"invalid fixture: {e}")
```

### tests/test_latency_lab.py

```python
import copy
import json
import math
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from latency_lab import counter_delta,simple_rate,bucket_quantile,analyze
class LatencyTests(unittest.TestCase):
    def data(self):
        return json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def test_requests_delta(self): self.assertEqual(counter_delta(self.data()["counters"]["requests"]),245)
    def test_errors_delta(self): self.assertEqual(counter_delta(self.data()["counters"]["errors"]),8)
    def test_simple_rate(self): self.assertAlmostEqual(simple_rate(self.data()["counters"]["requests"]),245/300)
    def test_hist_p95(self): self.assertAlmostEqual(bucket_quantile(.95,self.data()["histogram"]["buckets"]),.5-(1/11)*.25)
    def test_hist_p50(self): self.assertGreater(bucket_quantile(.5,self.data()["histogram"]["buckets"]),.1)
    def test_mean(self): self.assertEqual(analyze(self.data())["mean_latency_seconds"],.235)
    def test_error_fraction(self): self.assertAlmostEqual(analyze(self.data())["error_fraction"],round(8/245,5))
    def test_error_budget_fail(self): self.assertFalse(analyze(self.data())["error_budget_pass"])
    def test_latency_pass(self): self.assertTrue(analyze(self.data())["latency_p95_pass"])
    def test_counter_reset(self): self.assertEqual(counter_delta([[0,10],[10,2],[20,7]]),9)
    def test_insufficient_samples(self):
        with self.assertRaises(ValueError): counter_delta([[0,1]])
    def test_duplicate_timestamp(self):
        with self.assertRaises(ValueError): counter_delta([[0,1],[0,2]])
    def test_negative_counter(self):
        with self.assertRaises(ValueError): counter_delta([[0,1],[1,-1]])
    def test_no_inf_bucket(self):
        with self.assertRaises(ValueError): bucket_quantile(.95,[{"le":1,"cumulative":5}])
    def test_nonmonotonic_bucket(self):
        b=self.data()["histogram"]["buckets"]
        b[2]["cumulative"]=3
        with self.assertRaises(ValueError): bucket_quantile(.95,b)
    def test_invalid_quantile(self):
        with self.assertRaises(ValueError): bucket_quantile(1.1,self.data()["histogram"]["buckets"])
    def test_zero_requests(self):
        d=self.data()
        d["counters"]["requests"]=[[0,1],[300,1]]
        with self.assertRaises(ValueError): analyze(d)
    def test_invalid_count(self):
        d=self.data()
        d["histogram"]["count"]=99
        with self.assertRaises(ValueError): analyze(d)
    def test_invalid_window(self):
        d=self.data()
        d["window_seconds"]=0
        with self.assertRaises(ValueError): analyze(d)
    def test_bad_budget(self):
        d=self.data()
        d["slo"]["error_budget_fraction"]=1.5
        with self.assertRaises(ValueError): analyze(d)
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter018
python3 scripts/latency_lab.py fixtures/healthy.json
python3 -m unittest discover -s tests -v
```

Expected: request delta 245, error delta 8, simple observed request rate ~0.81667/sec, error fraction ~3.27%, mean duration 235 ms, p95 approximation ~477.27 ms; the illustrative 1% error budget **fails** while 500 ms p95 threshold passes. **20 unit tests** should pass. This is synthetic data and does not demonstrate live Prometheus query correctness.

## 9. Twenty-four hands-on exercises

1. Distinguish counter and gauge.
2. Explain reset detection.
3. Query rate over five minutes.
4. Compare rate and irate.
5. Query increase over one hour.
6. Explain extrapolation.
7. Aggregate rate by service.
8. Avoid rate-after-sum.
9. Inspect classic bucket labels.
10. Validate +Inf bucket.
11. Validate cumulative monotonicity.
12. Compute histogram mean.
13. Compute histogram p50.
14. Compute histogram p95.
15. Explain bucket interpolation.
16. Design latency SLO buckets.
17. Compute HTTP error fraction.
18. Compute error budget burn rate.
19. Handle denominator zero.
20. Inspect PostgreSQL transaction rate.
21. Review Redis exporter schema.
22. Run offline histogram fixture.
23. Execute 20 tests and negative cases.
24. Peer-review SLO recording/alert rules.

## 10. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | Counter reset spike | restart/reset |
| 02 | Counter incorrectly treated as gauge | metric type |
| 03 | Rate over sparse samples | window size |
| 04 | Irate-based alert flapping | smoothing |
| 05 | Rate after sum masks reset | aggregation order |
| 06 | Missing +Inf bucket | instrumentation |
| 07 | Nonmonotonic buckets | exporter |
| 08 | Missing le label | aggregation |
| 09 | Mixed histogram schemas | bucket contract |
| 10 | p95 averaged across pods | invalid quantile math |
| 11 | Buckets too coarse | precision |
| 12 | Native histogram mismatch | version |
| 13 | Error ratio denominator zero | low traffic |
| 14 | Status classification wrong | SLI definition |
| 15 | High-cardinality histogram | labels |
| 16 | Wrong latency units | seconds/ms |
| 17 | Histogram sum reset | counter semantics |
| 18 | DB exporter metric missing | schema |
| 19 | Remote-write lag biases SLO | freshness |
| 20 | SLO alert too noisy | window/burn policy |

## 11. Eight production runbooks

**A. Counter reset anomaly:** Correlate process restarts, scrape gaps and rate windows; avoid raw counter subtraction.

**B. Missing histogram buckets:** Inspect exporter `/metrics`, bucket labels, scrape limits and relabeling.

**C. Incorrect p95/p99:** Verify aggregation by `le`, consistent units, bucket boundaries and histogram type.

**D. High latency incident:** Correlate SLO latency with DB waits, application traces, saturation and recent deploys.

**E. Error budget burn:** Validate numerator/denominator, traffic minimum, incident duration and paging thresholds.

**F. Cardinality regression:** Identify histogram label multiplication, fix instrumentation, assess TSDB/remote-write cost.

**G. DBRE exporter mismatch:** Verify version, metric schema and job labels; update recording rules with rollback.

**H. Query release review:** Test counter resets, low traffic, missing data, histogram math, performance and approvals.

## 12. 100-point assessment

| Area | Points |
|---|---:|
| Counter rate, increase and reset semantics | 20 |
| Histogram buckets, quantiles and mean | 20 |
| Error SLO and burn-rate design | 20 |
| Executable lab and 20 tests | 20 |
| Troubleshooting, runbooks and evidence | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: counter-reset correctness, preserve `le`, reject invalid buckets, document denominator-zero behavior and pass all offline tests.

## 13. Evidence worksheet

```text
UTC / operator / metric schema:
Counter reset example:
Rate/increase query and window:
Histogram buckets / p95 / mean:
Error fraction / budget / burn:
DBRE query and exporter version:
20 offline tests:
Failure drill / RCA / COA:
Reviewer / score / action:
```

**Companion:** [Chapter 018 executable lab](labs/018-promql-rate-increase-histograms-quantiles-latency-analysis-lab.md).

**Next:** Chapter 019 — Advanced PromQL Subqueries, Recording Rules, Query Performance and SLO Engineering.
