# Chapter 017 — PromQL Aggregation and Vector Matching Hands-on Lab

**Scope:** Offline Python 3.10+ teaching model plus optional read-only Prometheus queries.

## 1. Create files

Copy the four complete blocks from [Chapter 017](../017-promql-aggregations-vector-matching-binary-operators-label-transformations.md) into:

```text
chapter017/
  fixtures/aggregation.json
  fixtures/matching.json
  scripts/promql_model.py
  tests/test_promql_model.py
```

## 2. Run acceptance

```bash
cd chapter017
python3 scripts/promql_model.py fixtures/aggregation.json
python3 scripts/promql_model.py fixtures/matching.json
python3 -m unittest discover -s tests -v
```

Expected: east=30, west=7; matched ratios 0.4 and 0.5; 20 tests pass.

## 3. Twelve negative drills

1. Duplicate right-hand matching key.
2. Duplicate left-hand matching key.
3. Zero denominator.
4. Invalid aggregation operator.
5. Specify both `by` and `without`.
6. Match with missing RHS.
7. Compare without bool.
8. Compare with bool.
9. Use `on` and `ignoring` together.
10. Use an unsupported query kind.
11. Drop cluster from grouping and explain blast radius.
12. Review label transformation cardinality.

Record expected result, actual result and safe remediation.

## 4. Optional authorized Prometheus queries

```bash
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=sum by (job) (up)'
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=count by (job) (up == 0)'
```

Do not assume the local endpoint exists or represents production. Verify label identity and query costs.

## 5. Evidence

```text
UTC / operator:
Grouping and aggregation:
Matching keys and uniqueness:
Comparison bool/filter:
20 tests / 12 drills:
Cluster/tenant isolation review:
RCA / COA / reviewer:
```

**Acceptance:** 20 tests pass, duplicate matches are rejected, missing-series and bool behavior are understood. Full Prometheus semantics require a real PromQL engine.
