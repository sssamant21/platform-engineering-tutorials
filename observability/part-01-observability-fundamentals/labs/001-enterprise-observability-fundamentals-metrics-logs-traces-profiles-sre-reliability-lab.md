# Chapter 001 — Executable SRE/DBRE Observability Lab

**Scope:** Local, non-destructive synthetic observability validation; Python 3.10+. No cloud credentials or production endpoints.

## Setup

Create `chapter001/fixtures`, `chapter001/scripts` and `chapter001/tests`. Copy the complete `assess.py`, `healthy.json`, `degraded.json` and `test_assess.py` source blocks from [Chapter 001](../001-enterprise-observability-fundamentals-metrics-logs-traces-profiles-sre-reliability.md).

## Run

```bash
cd chapter001
python3 scripts/assess.py fixtures/healthy.json
python3 -m unittest discover -s tests -v
if python3 scripts/assess.py fixtures/degraded.json; then
  echo "FAIL: degraded fixture accepted"; exit 1
else
  echo "PASS: degraded fixture rejected"
fi
```

Expected healthy fixture exits 0. Degraded fixture exits nonzero due to availability, latency and correlation failures. Four automated tests should pass when files are copied correctly.

## Operational drills

1. Calculate allowed errors for 99.9% of 10,000 requests.
2. Explain why 200 failures exceed the budget.
3. Identify trace/log correlation mismatch.
4. Separate p95 diagnostic breach from availability accounting.
5. Identify metric labels that would expose patient identifiers.
6. Describe how Elasticsearch storage saturation affects search latency.
7. Design a telemetry pipeline outage alert.
8. Define the owner and escalation for missing data.

## Acceptance evidence

```text
Environment:
Python version:
Healthy fixture exit code:
Degraded fixture exit code:
Unit test results:
Error budget calculation:
Privacy/cardinality review:
Incident drill notes:
Reviewer:
```

- [ ] Healthy synthetic fixture passes.
- [ ] Degraded synthetic fixture is rejected.
- [ ] Four unit tests pass.
- [ ] SLI/SLO calculations are correct.
- [ ] Correlation and sensitive-data safeguards documented.
- [ ] Production applicability reviewed separately.

**Next:** Chapter 002 — Observability Signals, Telemetry Pipelines and Context Propagation.
