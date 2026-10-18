# Chapter 022 — Grafana Dashboard Variables, Panels and Transformations Lab

**Part 05 — Grafana Dashboards and Visualization.** Offline Python 3.10+ policy validation with optional approved staging Grafana.

## 1. Project files

Copy the three complete JSON/Python blocks from [Chapter 022](../022-grafana-dashboard-design-variables-panels-transformations-production-visualization-patterns.md) into:

```text
chapter022/
  fixtures/dashboard.json
  scripts/dashboard_gate.py
  tests/test_dashboard_gate.py
```

## 2. Execute offline acceptance

```bash
cd chapter022
python3 scripts/dashboard_gate.py fixtures/dashboard.json
python3 -m unittest discover -s tests -v
```

Expected: PASS and 24 unit tests PASS.

## 3. Twelve failure drills

1. Invalid dashboard UID.
2. Missing dashboard title.
3. Refresh interval too short.
4. Missing cluster variable.
5. Duplicate variable.
6. Unbounded All/multi-select.
7. Unsupported variable type.
8. Duplicate panel ID.
9. Wrong datasource UID.
10. Invalid panel grid position.
11. Empty or oversized PromQL.
12. Missing cluster scope in `up` query.

Modify only local fixture copies and document expected vs actual gate behavior.

## 4. Optional staging integration

Import the JSON into an authorized Grafana folder. Verify datasource UID, template variable resolution, query inspector, no-data handling and transformations. Test both healthy and degraded target scenarios. Inspect actual access permissions separately; the offline gate does not provide authorization.

## 5. DBRE incident tabletop

A PostgreSQL dashboard suddenly shows zero targets after a relabeling change. Determine whether the target is down, absent, filtered by a stale variable or inaccessible through the datasource. Investigate query inspector, inventory and scrape health before escalating.

## 6. Evidence

```text
UTC / operator:
Dashboard UID and owner:
Variable scope and cluster:
Panel types, units, transformations:
24 tests / 12 drills:
Optional Grafana staging result:
RCA / rollback / reviewer:
```

**Acceptance:** all 24 tests pass, unsafe dashboard fixture modifications fail the gate, and the operator explains why variables are not an authorization boundary.
