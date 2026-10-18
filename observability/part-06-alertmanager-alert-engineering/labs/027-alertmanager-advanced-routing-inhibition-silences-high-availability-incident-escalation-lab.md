# Chapter 027 — Alertmanager Advanced Routing, Silences, Inhibition and HA Lab

**Part 06 — Alertmanager and Alert Engineering.** Python 3.10+ offline governance lab; optional staging Alertmanager HA drill.

## 1. Project layout

Copy the four full fixture/Python blocks from [Chapter 027](../027-alertmanager-advanced-routing-inhibition-silences-high-availability-incident-escalation.md) into:

```text
chapter027/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

## 2. Execute

```bash
cd chapter027
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 26 tests PASS.

## 3. Twelve failure drills

1. HA peer count too low.
2. Insufficient healthy peers.
3. Missing fallback receiver.
4. Wrong DBRE route receiver.
5. Unscoped child matcher.
6. Unexpected route continue.
7. Missing service/cluster grouping.
8. Invalid repeat interval.
9. Broad inhibition equality.
10. Silence without owner.
11. Silence without expiration.
12. Missing backup escalation test.

Use copies of fixtures and record each detection.

## 4. Optional staging integration

Use Chapter 026's test-only receiver and an approved staging Alertmanager. Validate native YAML, team/fallback routes, narrow silences, inhibition equality, peer health, one-peer loss and safe rollback. Do not send production pages or modify production silences.

## 5. DBRE incident tabletop

An Alertmanager peer is isolated during PostgreSQL failover; a broad silence suppresses the only DBRE page and the primary receiver is unavailable. Restore backup escalation, constrain the silence, confirm peer recovery and document incident evidence.

## 6. Evidence

```text
UTC / operator / environment:
Route test cases / fallback:
Inhibition and silence audit:
HA peers / receiver test:
Healthy/degraded gate / 26 tests:
12 drills / incident timeline:
Rollback / reviewer / score:
```

**Acceptance:** offline gate and 26 tests pass, degraded fixture rejected, and HA/escalation readiness is separately verified in staging.
