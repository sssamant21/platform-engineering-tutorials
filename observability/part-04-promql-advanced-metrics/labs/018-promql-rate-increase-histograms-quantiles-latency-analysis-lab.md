# Chapter 018 — PromQL Rate, Increase, Histograms and Latency Analysis Lab

**Scope:** Offline Python 3.10+ deterministic teaching model; optional authorized read-only Prometheus query checks.

## 1. Prepare

Copy all three complete fixture/code blocks from [Chapter 018](../018-promql-rate-increase-histograms-quantiles-latency-analysis.md) into:

```text
chapter018/
  fixtures/healthy.json
  scripts/latency_lab.py
  tests/test_latency_lab.py
```

## 2. Execute

```bash
cd chapter018
python3 scripts/latency_lab.py fixtures/healthy.json
python3 -m unittest discover -s tests -v
```

Expected: 245 request delta, 8 error delta, ~0.81667 observed request/sec, p95 ~0.47727 seconds, error-budget FAIL, latency threshold PASS, 20 tests PASS.

## 3. Twelve controlled failure drills

1. Counter reset.
2. Duplicate timestamp.
3. Negative counter value.
4. Only one sample.
5. Sparse sample window.
6. Missing +Inf bucket.
7. Nonmonotonic bucket.
8. Invalid quantile.
9. Inconsistent histogram count.
10. Zero request delta.
11. Invalid error budget.
12. Zero analysis window.

These are fixture-only drills. Explain where the simplified model differs from Prometheus extrapolation.

## 4. Optional read-only Prometheus checks

```bash
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=rate(prometheus_http_requests_total[5m])'
```

Verify the metric exists for the deployed version. Do not claim this was executed against production.

## 5. Evidence and acceptance

```text
UTC / operator:
Counter and reset:
Histogram buckets / p95 / mean:
Error fraction and burn rate:
20 tests / 12 drills:
Exporter and metric schema:
SLO owner / RCA / COA / reviewer:
```

**Acceptance:** 20 tests pass, counter reset and bucket validation are demonstrated, error-budget failure is interpreted correctly and PromQL limitations are documented.
