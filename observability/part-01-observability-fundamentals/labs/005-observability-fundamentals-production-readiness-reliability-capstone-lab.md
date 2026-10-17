# Chapter 005 — Enterprise Observability Fundamentals Production Capstone Lab

**Scope:** Synthetic offline acceptance of architecture, SLIs, signal quality, privacy and incident readiness. Python 3.10+ only; no production data or credentials.

## Setup

Copy the complete four source blocks from [Chapter 005](../005-observability-fundamentals-production-readiness-reliability-capstone.md) into:

```text
chapter005/
  fixtures/approved.json
  fixtures/rejected.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

## Execute

```bash
cd chapter005
python3 scripts/acceptance.py fixtures/approved.json
if python3 scripts/acceptance.py fixtures/rejected.json; then
  echo "FAIL: unsafe acceptance approved"; exit 1
else
  echo "PASS: unsafe acceptance denied"
fi
python3 -m unittest discover -s tests -v
```

Expected: approved fixture exits zero; rejected fixture nonzero; ten tests pass.

## Incident tabletop: patient-search latency

Synthetic scenario: patient-search API p95 rises from 180 ms to 3.5 s; Elasticsearch search rejections increase, disk queue depth spikes, Redis CPU approaches saturation and Collector drops 2% of records. Work through:

1. Verify API SLO and eligible-event denominator.
2. Separate application degradation from telemetry blind spots.
3. Identify Elasticsearch query/storage and Redis command hypotheses.
4. Use traces to isolate slow dependencies; confirm with infrastructure metrics.
5. Apply safe mitigation and preserve incident timeline.
6. Verify on-call, rollback, RCA and COA.

## Twelve negative tests

1. Missing service owner.
2. Missing telemetry owner.
3. Exceeded availability error budget.
4. Collector telemetry loss.
5. Broken trace/log correlation.
6. Patient ID in metric labels.
7. Unapproved export region.
8. Excessive retention.
9. Missing encryption.
10. Missing on-call route.
11. Missing runbook approval.
12. Telemetry freshness breach.

## Evidence and sign-off

```text
UTC / operator / reviewer:
Service owner / telemetry owner:
Synthetic positive and negative checks:
Ten unit tests:
SLO and error budget:
Trace/log correlation:
Telemetry completeness/drop/freshness:
Privacy/region/retention/RBAC:
Incident tabletop and eight runbooks:
Score / outstanding actions:
```

- [ ] Approved fixture passes.
- [ ] Rejected fixture fails.
- [ ] Ten automated tests pass.
- [ ] All mandatory security and governance gates reviewed.
- [ ] Incident tabletop documented.
- [ ] No claim of production certification without independent staging/production evidence.
