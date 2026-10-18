# Chapter 034 — Custom Prometheus Exporter and Python Instrumentation Lab

**Part 07 — Exporters and Custom Instrumentation.** Offline metric contract gate and optional local Python exporter.

## 1. Files

Copy the complete blocks from [Chapter 034](../034-custom-prometheus-exporters-python-instrumentation-metric-design-cardinality-control.md):

```text
chapter034/
  exporter.py
  requirements.txt
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/metric_gate.py
  tests/test_metric_gate.py
```

## 2. Offline tests

```bash
cd chapter034
python3 scripts/metric_gate.py fixtures/healthy.json
if python3 scripts/metric_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 27 tests PASS.

## 3. Local exporter

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python exporter.py
# in another terminal:
curl -fsS http://127.0.0.1:9108/metrics | grep '^dbre_'
```

## 4. Twelve negative drills

1. Add request ID label.
2. Add SQL text label.
3. Remove counter `_total` suffix.
4. Remove histogram seconds suffix.
5. Reverse histogram buckets.
6. Duplicate histogram bucket.
7. Duplicate metric name.
8. Exceed series budget.
9. Make scrape timeout exceed interval.
10. Bind exporter to all interfaces.
11. Skip security review.
12. Skip rollback review.

## 5. DBRE incident tabletop

An Elasticsearch query exporter publishes per-query-text labels and causes high Prometheus ingestion load. Identify cardinality explosion, remove unsafe labels, compare series counts and restore dashboards.

## 6. Evidence

```text
UTC / operator / environment:
Metric contract / estimated series:
Healthy/degraded gate / 27 tests:
Local exporter /metrics:
12 negative drills:
Rollback / reviewer / score:
```

**Acceptance:** policy gate and unit tests pass; live scrape, dependency security and runtime overhead require separate verification.
