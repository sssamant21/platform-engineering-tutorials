# Chapter 029 — Alert Quality, SLO Burn Rate and Noise Reduction Lab

**Part 06 — Alertmanager and Alert Engineering.** Python 3.10+ offline governance, optional staging Prometheus/Alertmanager.

## 1. Files

Copy the four complete fixture/source blocks from [Chapter 029](../029-alert-quality-engineering-noise-reduction-slo-burn-rate-alerts-incident-signal-design.md) into:

```text
chapter029/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/slo_gate.py
  tests/test_slo_gate.py
```

## 2. Run

```bash
cd chapter029
python3 scripts/slo_gate.py fixtures/healthy.json
if python3 scripts/slo_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 26 tests PASS.

## 3. SLO calculation drills

- For 99.9% SLO, error budget fraction = 0.001.
- If observed bad-request fraction is 0.0144, burn rate = 14.4×.
- One hour at 14.4× consumes about 2% of a 30-day budget.
- Six hours at 6× consumes about 5% of that budget.
- Compare both short and long windows, then consider traffic-volume gates and missing-series alerts.

## 4. Twelve failure drills

1. SLO set to 100%.
2. Missing service owner.
3. Missing runbook.
4. Missing backup receiver.
5. Unsafe no-data policy.
6. Low-traffic policy ignored.
7. Request ID used as alert label.
8. Burn rate zero.
9. Short window longer than long.
10. Missing severity.
11. Duplicate alert name.
12. Unreviewed notification route.

## 5. Optional staging validation

Load approved Prometheus-managed rules, validate with `promtool check rules`, simulate counters and request failures, and route only to local test receivers. Verify no-data, low traffic, short/long window, silence and recovery behavior. Roll back afterward.

## 6. DBRE tabletop

A PostgreSQL-backed API exceeds its error budget during a failover, then traffic becomes too low for stable ratio estimation. Determine user impact, restore a reliable page, apply a minimum-volume gate and design a separate missing-target alert.

## 7. Evidence

```text
UTC / operator / environment:
SLI and SLO math:
Burn-rate windows / minimum traffic:
Healthy/degraded gate / 26 tests:
12 drills / optional staging validation:
Incident timeline / rollback / reviewer:
```

**Acceptance:** 26 offline tests pass and degraded policy fails; live paging and SLO measurement require separate verification.
