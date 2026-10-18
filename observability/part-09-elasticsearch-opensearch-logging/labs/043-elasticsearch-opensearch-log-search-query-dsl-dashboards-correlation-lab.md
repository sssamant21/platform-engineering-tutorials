# Chapter 043 — Elasticsearch/OpenSearch Log Search, Query DSL and Correlation Lab

**Part 09 — Elasticsearch and OpenSearch Logging.** Synthetic logs only.

## Offline query governance

Create `healthy.json`, `query_gate.py` and `test_query_gate.py` from [Chapter 043](../043-elasticsearch-opensearch-log-search-query-dsl-dashboards-correlation.md) and run:

```bash
cd chapter043
python3 query_gate.py healthy.json
python3 -m unittest -v test_query_gate.py
```

Expected: PASS and 26 tests.

## Optional live staging lab

1. Record exact Elasticsearch or OpenSearch version.
2. Index synthetic application and PostgreSQL timeout events.
3. Run term, terms, range, match and match_phrase queries.
4. Run date_histogram aggregation and compare to source event counts.
5. Inspect `_profile` for a bounded test query.
6. Use PIT + search_after with a supported stable sort; validate no duplicates or missing results.
7. Build a saved search and dashboard with service/time filters.
8. Compare logs to independent application metrics and trace IDs.
9. Revert saved queries and confirm no data loss.

## Twelve negative drills

1. Wrong time field.
2. Unbounded time range.
3. Oversized fetch.
4. Leading wildcard.
5. Scripted query.
6. Missing service filter.
7. Sensitive _source field.
8. Missing RBAC review.
9. Unstable pagination.
10. Missing dashboard owner.
11. PIT expiration.
12. Search timeout due to storage pressure.

## Incident evidence

```text
UTC / operator / version:
Query DSL / index mappings:
Search and fetch latency / shards / disk:
PIT pagination results:
Dashboard and independent SLO comparison:
Offline gate / 26 tests:
Negative drills / rollback / reviewer:
```

The offline gate does not establish live query performance or production readiness.
