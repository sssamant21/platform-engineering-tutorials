# Chapter 019 — Advanced PromQL Subqueries and Recording Rule Governance Lab

**Part 04 — PromQL and Advanced Metrics.** Offline Python 3.10+ policy gate plus optional authorized promtool/live rule review.

## 1. Project layout

Copy the four complete fixture and source blocks from [Chapter 019](../019-advanced-promql-subqueries-recording-rules-query-performance-slo-engineering.md) into:

```text
chapter019/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/rule_gate.py
  tests/test_rule_gate.py
```

## 2. Execute policy acceptance

```bash
cd chapter019
python3 scripts/rule_gate.py fixtures/healthy.json
if python3 scripts/rule_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe rule accepted"; exit 1
else
  echo "PASS: unsafe rule rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 20 unit tests PASS.

## 3. Twelve failure drills

1. Duplicate recording-rule name.
2. Invalid metric name.
3. Empty expression.
4. Missing rule owner.
5. Missing review signoff.
6. Missing test signoff.
7. Cluster isolation not verified.
8. Evaluation interval too short.
9. Estimated input series over budget.
10. Invalid range-window duration.
11. Sensitive patient identifier label.
12. Missing or invalid rule object.

These drills modify local JSON only. Record risk, detection, containment, owner and rollback for each.

## 4. Optional Prometheus integration

On an authorized staging environment, create a rule YAML from the chapter example and use compatible `promtool check rules` and `promtool test rules`. Capture tool version and output. Compare recorded results with raw queries, including reset/low-traffic/absence cases. Do not reload production configuration without change approval.

## 5. SRE/DBRE incident tabletop

A new PostgreSQL SLO recording rule accidentally drops `cluster`, creating cross-region aggregation. At the same time a subquery dashboard uses a very fine step and triggers query timeouts. Investigate tenant isolation, query cost, SLO correctness and rollback. Document the blast radius and evidence for safe redeployment.

## 6. Evidence

```text
UTC / operator / environment:
Rule name / owner / query budget:
Cluster and tenant label preservation:
Subquery window / step:
Healthy/degraded gate / 20 tests:
12 failure drills:
Optional promtool version / results:
SLO owner / RCA / COA / reviewer:
```

**Acceptance:** offline gate and 20 tests pass, degraded rule policy is rejected, and query performance/label-isolation risks are explained. Production deployment requires separate live verification.
