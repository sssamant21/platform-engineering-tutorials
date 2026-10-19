# Chapter 087 — Prometheus and Alertmanager HA, Remote Write and Storage Lab

## Offline tests

Copy `healthy.json`, `ha_gate.py` and `test_ha_gate.py` from [Chapter 087](../087-prometheus-alertmanager-high-availability-remote-write-long-term-storage.md).

```bash
python3 ha_gate.py healthy.json
python3 -m unittest -v test_ha_gate.py
```

Expected PASS and 30 authored tests; record actual output.

## Staging failover game day

1. Deploy two Prometheus replicas in separate failure domains.
2. Confirm unique external labels and duplicate scrape behavior.
3. Configure remote write to an isolated receiver using TLS.
4. Measure queue backlog, receiver failures and WAL disk growth.
5. Configure Alertmanager peers and isolated test paging.
6. Simulate one Prometheus replica failure; verify local and remote SLO queries.
7. Simulate a bounded remote receiver outage; measure backlog and replay.
8. Simulate Alertmanager peer loss; verify delivery and silence consistency.
9. Review long-term storage, object store IAM, retention and cost.
10. Revert an approved change and capture independent recovery evidence.

## Negative drills

Reject label collisions, missing receivers, exhausted WAL disk, unsafe TLS, untested deduplication and incomplete failover evidence.

## Evidence worksheet

```text
Owner / change / UTC:
Replica and external labels:
Scrape and rule health:
Remote-write lag / WAL:
Alertmanager peers / staging page:
Object storage / retention:
Failure and recovery times:
SLO and DBRE signals:
Offline tests:
```

Synthetic PASS is not a live HA certification.
