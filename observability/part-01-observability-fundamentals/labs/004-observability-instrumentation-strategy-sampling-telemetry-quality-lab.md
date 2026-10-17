# Chapter 004 — Hands-on Lab: Instrumentation, Sampling and Telemetry Quality

**Safety:** Local Python standard-library simulation using synthetic events. No production connections.

## Lab layout

```text
chapter004/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/quality_gate.py
  tests/test_quality_gate.py
```

Copy the complete source blocks from [Chapter 004](../004-observability-instrumentation-strategy-sampling-telemetry-quality.md).

## Execute

```bash
cd chapter004
python3 scripts/quality_gate.py fixtures/healthy.json
if python3 scripts/quality_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded telemetry accepted"; exit 1
else
  echo "PASS: degraded telemetry rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy fixture exits zero, degraded fixture nonzero, eight tests pass.

## Twelve targeted failure drills

1. Remove service owner.
2. Increase dropped events.
3. Reduce correlated logs.
4. Increase freshness p95.
5. Add patient_id metric label.
6. Exceed metric cardinality budget.
7. Set sampling probability above 1.
8. Remove schema version.
9. Set expected events to zero.
10. Make good/received events inconsistent.
11. Add authorization to sensitive fields.
12. Set invalid sampling strategy.

For each drill record validator output, expected mitigation and owner.

## Production tabletop

A Kubernetes service deploys new auto-instrumentation and introduces raw patient IDs as metric labels. Collector memory and backend ingestion cost rise while a 10% trace sampling policy misses rare failures. Describe containment, telemetry quality gaps, privacy response, safe rollback, and follow-up sampling policy.

## Evidence

```text
UTC / operator:
Instrumentation version:
Signal contract:
Healthy fixture result:
Degraded fixture result:
Eight unit tests:
12 failure drills:
Quality SLIs and thresholds:
Sampling/privacy review:
RCA / COA / reviewer:
```

- [ ] Healthy fixture passes.
- [ ] Degraded fixture rejected.
- [ ] Eight tests pass.
- [ ] Sampling strategy and tradeoffs documented.
- [ ] Quality SLIs reviewed.
- [ ] Sensitive fields and unbounded labels excluded.
- [ ] Real telemetry pipeline behavior validated separately before production claims.
