# Chapter 039 — Loki Alerting, Recording Rules and Retention Lab

**Part 08 — Centralized Logging with Loki.** Safe offline policy gate and optional staging ruler/compactor verification.

## Offline acceptance

Create `chapter039/policy.json`, `chapter039/policy_gate.py` and `chapter039/test_policy_gate.py` using the complete blocks in [Chapter 039](../039-loki-alerting-recording-rules-retention-enterprise-operations.md). Run:

```bash
cd chapter039
python3 policy_gate.py policy.json
python3 -m unittest -v test_policy_gate.py
```

Expected PASS and 18 unit tests.

## Staging integration

1. Provision a disposable Loki ruler with supported backend storage and Alertmanager route.
2. Apply the sample LogQL recording/alert rules after verifying the installed Loki version.
3. Generate synthetic error logs and compare recorded series with direct LogQL output.
4. Verify test-only Alertmanager notification, fallback and acknowledgement.
5. Configure compactor retention on a **disposable** bucket or filesystem; measure actual retained data age.
6. Roll back the rules and retention configuration; verify restoration.

## Twelve negative drills

1. Missing owner.
2. Retention unapproved.
3. Compactor review absent.
4. Deletion safety review absent.
5. Alert route unapproved.
6. Notification not tested.
7. Rollback untested.
8. Independent logging alert missing.
9. Invalid retention.
10. Missing rules.
11. Invalid severity.
12. Query range too broad.

## SRE/DBRE game day

Simulate a PostgreSQL timeout burst while Loki ingestion is degraded and compactor retention stalls. Use independent metrics to establish user impact, recover ingestion, verify rule evaluation and test alert delivery without paging production responders.

## Evidence

```text
UTC / operator / environment:
Loki version / ruler backend:
Rule query / evaluation / alert state:
Alertmanager test delivery:
Compactor / retention age:
Offline gate / 18 tests:
12 drills / rollback / reviewer / score:
```

**Acceptance:** offline tests pass; live ruler, retention and notification behavior require separate integration verification.
