# Chapter 085 — Hands-on Capstone Lab: Backup, Upgrade and DR Acceptance

**Environment:** Disposable Jenkins LTS, isolated backup/restore storage, separate DR namespace or region, synthetic credentials, SCM and artifacts. **Never** run destructive tests in production.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller, agents, storage and dependencies | Matrix |
| 02 | Record core/Java/plugin/JCasC versions | Manifest |
| 03 | Approve RPO/RTO and abort criteria | Decision |
| 04 | Baseline synthetic CI, queue and agent startup | Dashboard |
| 05 | Map security identities and key custody | Access review |
| 06 | Verify single-writer authority | Infrastructure proof |
| 07 | Quiesce/stop test writer | Timeline |
| 08 | Create consistent encrypted backup | Backup ID |
| 09 | Verify checksum and immutable retention | Integrity |
| 10 | Check offsite copy and key recovery | Policy |
| 11 | Restore backup to isolated state | Restore |
| 12 | Validate jobs, RBAC and synthetic credentials | Tests |
| 13 | Pin candidate core/Java/plugins/JCasC | Manifest |
| 14 | Build candidate and resolve dependencies | Image |
| 15 | Run staging Pipeline and agent tests | Build |
| 16 | Inject JCasC/plugin regression in staging | Failure |
| 17 | Fence candidate and restore prior state | Rollback |
| 18 | Simulate primary-region outage | Incident |
| 19 | Prove primary fencing and DR approval | Audit |
| 20 | Restore DR state and validate critical CI | Recovery |
| 21 | Cut over synthetic DNS/webhooks | Routing |
| 22 | Reconcile work and execute controlled failback | Ledger |
| 23 | Measure RPO/RTO, SLO impact and cost | Worksheet |
| 24 | Score 100-point acceptance, RCA/COA and sign-off | Report |

## 24 failure drills

1. Missed backup.
2. Inconsistent snapshot.
3. Corrupted archive.
4. Object deletion/retention misconfiguration.
5. KMS decrypt denial.
6. Cross-region replication lag.
7. Restore storage quota.
8. Plugin dependency conflict.
9. Java/core incompatibility.
10. JCasC schema error.
11. RBAC privilege regression.
12. Credential decryption mismatch.
13. Agent remoting failure.
14. Shared-library/Pipeline regression.
15. Controller crash during upgrade.
16. Primary not fenced.
17. DR ingress/DNS outage.
18. DR node quota exhaustion.
19. Artifact registry outage.
20. Duplicate webhook replay.
21. RPO breach.
22. RTO breach.
23. Stale primary failback.
24. Suspected backup/key compromise.

## Executable recovery estimator

```python
from math import ceil

backup_gib = 120
effective_mib_per_s = 80
other_minutes = 24
transfer_minutes = backup_gib * 1024 / effective_mib_per_s / 60
estimated_rto = transfer_minutes + other_minutes
print(f"Transfer: {transfer_minutes:.1f} minutes")
print(f"Estimated RTO: {estimated_rto:.1f} minutes")
print("Illustrative 60-minute RTO:", estimated_rto <= 60)
```

Expected estimate: 25.6-minute transfer, 49.6-minute total. This is a **model**, not an observed RTO.

## Failover preflight gate

```python
import json
from pathlib import Path

plan = json.loads(Path("dr-plan.json").read_text())
required = ["approved", "primary_fenced", "backup_verified",
            "keys_available", "target_isolated"]
blocked = [name for name in required if plan.get(name) is not True]
if blocked:
    raise SystemExit("BLOCKED: " + ", ".join(blocked))
print("Operator assertions PASS; separately verify authoritative fencing evidence")
```

## 100-point scorecard

| Domain | Maximum |
|---|---:|
| Architecture, dependencies, RACI, objectives | 10 |
| Backup consistency, encryption, integrity, retention | 20 |
| Isolated restore and key recovery | 15 |
| Core/plugin/Java/JCasC upgrade compatibility | 15 |
| Rollback and single-writer fencing | 15 |
| Regional failover/failback and synthetic CI | 15 |
| RPO/RTO, observability, RCA/COA and sign-off | 10 |
| **Total** | **100** |

Suggested pass 85 plus all mandatory gates in Chapter 085.

## Evidence template

```text
UTC / change/incident ID:
Lab namespace, owner and approval:
Core/Java/plugins/JCasC:
Backup ID/checksum/retention/encryption:
Key recovery and isolated restore:
Authoritative fencing evidence:
Staging upgrade and rollback:
Synthetic CI, RBAC and artifact digest:
DR cutover and event reconciliation:
Failback authoritative state:
Measured RPO/RTO and SLO impact:
Drills passed/failed/blocked:
Score and mandatory gates:
Cleanup / RCA / COA / reviewer:
```

## Acceptance checklist

- [ ] 24 exercises attempted with evidence.
- [ ] 24 drills completed or explicitly blocked.
- [ ] Consistent encrypted backup verified.
- [ ] Restore performed in isolated state.
- [ ] Core/Java/plugin/JCasC compatibility reviewed.
- [ ] Upgrade rollback validated.
- [ ] Single active writer proven.
- [ ] Regional DR and failback exercised.
- [ ] Synthetic CI and credentials verified.
- [ ] RPO/RTO, scorecard and sign-off recorded.

**Related:** [Chapter 085 — Jenkins Enterprise Backup, Upgrade and Disaster Recovery Acceptance Capstone](../085-jenkins-enterprise-backup-upgrade-disaster-recovery-acceptance-capstone.md).
