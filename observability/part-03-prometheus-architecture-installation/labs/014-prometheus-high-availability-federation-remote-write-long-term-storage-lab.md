# Chapter 014 — Prometheus HA, Federation, Remote Write and Long-Term Storage Lab

**Mode:** Offline Python 3.10+ synthetic design acceptance, plus optional architecture tabletop. No live infrastructure changes.

## 1. Project layout

Copy all four complete source blocks from [Chapter 014](../014-prometheus-high-availability-federation-remote-write-long-term-storage.md) into:

```text
chapter014/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/ha_gate.py
  tests/test_ha_gate.py
```

## 2. Positive, negative and unit tests

```bash
cd chapter014
python3 scripts/ha_gate.py fixtures/healthy.json
if python3 scripts/ha_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe HA design accepted"; exit 1
else
  echo "PASS: unsafe HA design rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy exits 0; degraded exits 1; 16 tests pass.

## 3. Twelve failure drills

1. Remove one Prometheus replica.
2. Put both replicas in one failure domain.
3. Reuse a replica external label.
4. Remove Alertmanager redundancy.
5. Increase remote-write pending queue to 90%.
6. Add failed remote-write samples.
7. Increase remote-write lag beyond freshness budget.
8. Reduce local retention below modeled backend outage.
9. Drop query availability below SLO.
10. Mark restore drill overdue.
11. Set queue limit to zero.
12. Supply invalid replica-label boolean.

Record risk, impacted telemetry, safe response and owner for each. These are fixture modifications only.

## 4. Enterprise incident tabletop

An Elasticsearch/PostgreSQL observability platform has two Prometheus scrapers, but both are deployed in the same zone. The long-term remote-write backend is unavailable for six hours; pending samples and lag rise. A zone outage removes both scrapers. Explain what can be recovered, which samples may be lost, what Alertmanager can still do and how to redesign failure domains, retention and query fallback.

## 5. Review and evidence

```text
UTC / operator / architecture owner:
Replicas / failure domains / replica labels:
Alertmanager topology:
Remote-write backlog and freshness:
Local retention / backend outage budget:
Federation selectors:
Long-term backend / tenant security:
Healthy/degraded checks:
16 unit tests / 12 drills:
RPO / RTO / restore evidence:
RCA / COA / reviewer:
```

**Acceptance:** synthetic tests and drills pass, remote-write limitations are accurately explained, HA design has independent failure domains and documented restore testing. Production acceptance requires separate live verification.
