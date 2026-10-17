# Chapter 084 — Hands-on Lab: Jenkins Cross-Region DR and Failover Validation

**Environment:** Disposable Jenkins controller, independent recovery namespace/region or simulated lab, synthetic credentials, verified backup copy and test DNS/webhook endpoints. No production cutover.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory regional dependencies | Diagram |
| 02 | Define DR roles and approval gates | RACI |
| 03 | Record RPO/RTO and failover policy | Decision |
| 04 | Capture core/Java/plugin/JCasC manifest | Manifest |
| 05 | Verify backup consistency and SHA-256 | Digest |
| 06 | Inspect cross-region copy/retention | Report |
| 07 | Review recovery key custody | Checklist |
| 08 | Provision isolated recovery storage | PVC |
| 09 | Verify authoritative primary fencing | Evidence |
| 10 | Execute DR preflight gate script | Result |
| 11 | Restore backup to separate DR volume | Restore |
| 12 | Start one compatible DR controller | Logs |
| 13 | Verify login/RBAC/credentials | Tests |
| 14 | Provision DR agents and run Pipeline | Build |
| 15 | Validate artifact checksum | Digest |
| 16 | Simulate test webhook/DNS cutover | Routing |
| 17 | Reconcile synthetic queued work | Ledger |
| 18 | Measure actual RTO/RPO | Timeline |
| 19 | Practice controlled failback in lab | Recovery |
| 20 | Complete 100-point scorecard/RCA/COA | Sign-off |

## 12 failure drills

1. Primary not fenced.
2. Backup older than RPO.
3. Backup checksum mismatch.
4. Recovery-region KMS denial.
5. Cross-region copy lag.
6. Snapshot/volume topology failure.
7. Plugin/Java/JCasC mismatch.
8. Credentials cannot decrypt.
9. DR agent capacity exhausted.
10. DNS/webhook misrouting.
11. Duplicate synthetic deployment event.
12. Failback attempts stale state.

## Executable DR preflight

```python
import json
from pathlib import Path

plan = json.loads(Path("dr-plan.json").read_text())
gates = ["primary_fenced", "backup_verified", "keys_available",
         "target_isolated", "approved"]
for gate in gates:
    if plan.get(gate) is not True:
        raise SystemExit(f"BLOCKED: {gate}")
print("Operator assertions PASS; verify external fencing evidence before action")
```

Use this intentionally blocked initial fixture:

```json
{
  "incident_id": "LAB-DR-084",
  "primary_fenced": false,
  "backup_verified": true,
  "keys_available": true,
  "target_isolated": true,
  "approved": false
}
```

Do not use Boolean assertions as a substitute for authoritative fencing checks.

## Diagnostic commands

```sh
kubectl get pods -n jenkins -o wide
kubectl get pvc -n jenkins
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl get pods -n jenkins-dr -o wide
kubectl get pvc -n jenkins-dr
```

## Recovery timing worksheet

```text
Disaster UTC:
Latest verified durable marker UTC:
Primary fenced UTC:
Restore start/end UTC:
Synthetic CI verified UTC:
DNS/webhook cutover UTC:
Measured RPO:
Measured RTO:
Backup and artifact integrity:
Active writer inventory:
Approval/rollback/COA/reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Primary fencing proven independently.
- [ ] Exactly one active controller writer.
- [ ] Verified backup restored to separate volume.
- [ ] Encryption keys and RBAC validated.
- [ ] Synthetic CI and artifacts successful.
- [ ] DNS/webhook and replay reconciled.
- [ ] Measured RPO/RTO recorded.
- [ ] Failback and reviewer sign-off completed.

**Related:** [Chapter 084 — Jenkins Disaster Recovery Automation, Cross-Region Restore and Failover Validation](../084-jenkins-disaster-recovery-automation-cross-region-restore-failover-validation.md).
