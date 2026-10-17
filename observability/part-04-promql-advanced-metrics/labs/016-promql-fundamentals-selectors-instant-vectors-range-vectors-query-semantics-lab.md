# Chapter 016 — PromQL Fundamentals and Selector Semantics Lab

**Part 04 — PromQL and Advanced Metrics.** Offline Python 3.10+; optional read-only Prometheus API exploration.

## 1. Prepare project

Copy the four full fixture/code blocks from [Chapter 016](../016-promql-fundamentals-selectors-instant-vectors-range-vectors-query-semantics.md) into:

```text
chapter016/
  fixtures/instant.json
  fixtures/range.json
  scripts/selector_lab.py
  tests/test_selector_lab.py
```

## 2. Run the executable lab

```bash
cd chapter016
python3 scripts/selector_lab.py fixtures/instant.json
python3 scripts/selector_lab.py fixtures/range.json
python3 -m unittest discover -s tests -v
```

Expected: two instant PostgreSQL `up` series, two range series, and 20 passing tests. The model is deliberately limited and should not be substituted for Prometheus's real query engine.

## 3. Twelve failure drills

1. Query a missing metric.
2. Query a missing label.
3. Use an anchored regex that does not match.
4. Use negative matcher on an absent label.
5. Evaluate after lookback expires.
6. Evaluate after a synthetic stale marker.
7. Set zero range window.
8. Set zero lookback.
9. Use an invalid metric name.
10. Use an invalid label name.
11. Use an invalid regex.
12. Attempt a selector without a metric and without a nonempty matcher.

For each, record expected semantics, actual fixture result and remediation.

## 4. Optional read-only live PromQL

```bash
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=up'
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=count by (job) (up)'
```

Use an authorized local endpoint only. Verify actual labels and target inventory before adapting queries.

## 5. Evidence

```text
UTC / operator:
Instant vector results:
Range vector results:
Matcher and regex cases:
Lookback and stale behavior:
20 unit tests / 12 drills:
Production query review:
RCA / COA / reviewer:
```

**Acceptance:** 20 unit tests pass; selector semantics and the model's limitations are explained; no live production queries are claimed.
