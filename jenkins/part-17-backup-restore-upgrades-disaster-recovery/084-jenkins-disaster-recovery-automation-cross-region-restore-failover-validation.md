# Chapter 084 — Jenkins Disaster Recovery Automation, Cross-Region Restore and Failover Validation

**Part 17 — Backup, Restore, Upgrades and Disaster Recovery**  
**Audience:** Jenkins SRE/DBRE, platform engineers, security, cloud DR and incident commanders  
**Prerequisites:** Chapters 081–083; disposable Jenkins LTS, separate DR region/account or lab cluster, immutable backup, tested key recovery and synthetic CI.

## Objectives

Design and validate Jenkins cross-region recovery with explicit single-writer fencing, encrypted replicated backups, reproducible infrastructure, DNS/webhook cutover, state reconciliation, measured RPO/RTO, rollback and audit evidence.

## 1. DR architecture and failure domains

```text
 Primary region                               Recovery region
 SCM → webhook/ingress                         isolated ingress (disabled)
             |                                         |
      Jenkins controller                         standby controller (stopped)
       single active writer                       separate JENKINS_HOME
             |                                         ^
    consistent encrypted backup → immutable object copy
             |                                         |
      manifest + checksum  →  copy + KMS/key policy + audit
             |                                         |
    primary agents                                DR agents (cold/warm)
             \_______________ DNS/webhook cutover _____/
```

**Critical constraint:** Jenkins OSS does not provide generic active-active controllers sharing one writable `JENKINS_HOME`. Never start the recovery controller until the primary writer is fenced or proven unable to write. Network partitions require a reliable fencing/authority mechanism, not merely a failed HTTP probe.

## 2. Recovery tiers

| Tier | Pattern | Tradeoff |
|---|---|---|
| Cold standby | IaC + backup, no running controller | lowest cost, longer RTO |
| Warm standby | prepared compute/images and isolated state, controller stopped | faster RTO, higher cost |
| Independent controller shards | separate Jenkins homes and job ownership | workload isolation, not shared-state HA |
| Active/passive | one active controller, fenced standby | operational complexity and consistency controls |

Choose based on approved business RTO/RPO and tested provider behavior. Do not promise zero data loss without proof.

## 3. Dependencies and ownership

Inventory: SCM webhook endpoints, DNS/ingress/TLS, SSO/LDAP/OIDC, credential store and Jenkins secret keys, container registry, artifact repository, Kubernetes agent pools, cloud quotas, persistent volumes, plugin/core/Java/JCasC versions, network/firewall, backup identity and object retention.

Define a DR incident commander, primary fencing owner, backup custodian, security approver, DNS/webhook owner, application CI owner and rollback authority.

## 4. RTO/RPO and recovery sequencing

RPO measures the gap between disaster time and latest verified recoverable state; RTO runs from declared incident start until validated critical Jenkins service. Include backup replication lag, storage provisioning, controller startup, identity, agents, webhook routing and synthetic Pipeline verification.

Illustrative objectives (not guarantees): RPO <=15 minutes; RTO <=60 minutes. Validate against actual backup cadence, transfer throughput, state size and cloud provisioning time.

## 5. Backup and key readiness

- Consistent, encrypted Jenkins home backup with versioned manifest and SHA-256.
- Separate encryption-key custody and least-privilege restore principal.
- Regionally accessible compatible Jenkins core/Java/plugin images and JCasC.
- Backup integrity and restore rehearsal in isolated target.
- Immutable retention and cross-account/cross-region copies where required.
- Last durable synthetic marker for data-loss reconciliation.

Do not copy raw secrets or `master.key` into Git, CI logs or public object stores. A snapshot alone does not prove application consistency.

## 6. DR runbook: failover

1. Declare incident; record UTC and incident ID.
2. Check whether primary is healthy, partitioned or compromised.
3. Authorize DR; **fence** primary writer using validated infrastructure authority.
4. Verify no active process can write the original Jenkins home.
5. Select latest verified recoverable backup and manifest.
6. Restore to **separate** DR volume and recover keys through approved channel.
7. Start one pinned compatible Jenkins controller with JCasC.
8. Validate RBAC/SSO, jobs, plugins, credentials and agent provisioning.
9. Run synthetic CI: checkout, test, artifact publish and digest.
10. Update DNS/webhook routing with documented TTL and replay procedure.
11. Reconcile queued builds, webhooks, artifacts and non-idempotent deployments.
12. Measure RTO/RPO; communicate recovery and residual risks.

Do not treat DNS switch as fencing; clients and webhooks may still reach the original endpoint until caches expire.

## 7. DR runbook: failback

1. Confirm primary infrastructure restored and root cause mitigated.
2. Freeze new mutations and capture current DR state consistently.
3. Fence DR controller before starting primary.
4. Restore/migrate the **authoritative** DR state to a clean primary volume.
5. Verify plugin/core/Java/JCasC and credential compatibility.
6. Start exactly one primary controller.
7. Validate synthetic CI, artifacts, RBAC and agent pools.
8. Move DNS/webhooks and reconcile delayed events.
9. Monitor agreed stabilization period; record sign-off.

**Never** fail back by starting a stale primary home while the DR controller continues writing. A two-way merge of Jenkins home is not a generic supported procedure.

## 8. Automation state machine

```text
READY → INCIDENT_DECLARED → APPROVED → PRIMARY_FENCED
      → BACKUP_VERIFIED → DR_RESTORED → DR_VALIDATED
      → ROUTING_CUTOVER → MONITORING → CLOSED
                           |
                           └→ ABORT / MANUAL_REVIEW
```

Automate preflight checks and evidence collection. Gate destructive actions and DNS changes on explicit approval. Automation must be idempotent, resumable, auditable and fail closed on uncertain fencing.

## 9. Executable lab preflight

Use a synthetic DR inventory, not real credentials:

```python
#!/usr/bin/env python3
import json
from pathlib import Path

required = ["incident_id", "primary_fenced", "backup_verified",
            "keys_available", "target_isolated", "approved"]
plan = json.loads(Path("dr-plan.json").read_text())
missing = [key for key in required if key not in plan]
if missing:
    raise SystemExit("Missing fields: " + ", ".join(missing))
gates = required[1:]
failed = [key for key in gates if plan[key] is not True]
if failed:
    raise SystemExit("BLOCKED gates: " + ", ".join(failed))
print("Preflight PASS (operator-provided assertions only; independently verify evidence)")
```

Example `dr-plan.json`:

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

This intentionally fails until approved evidence is recorded. A Boolean file **does not itself prove fencing**; production automation must query authoritative infrastructure controls.

## 10. Cross-region cloud design

**EKS/AWS:** Validate EBS snapshot copy/restore permissions, KMS key access in recovery region, S3 versioning/Object Lock, IAM roles, EKS node pools, DNS and load balancers, image registry access and service quotas.

**AKS/Azure:** Validate Azure Disk snapshots/backup copy semantics, regional availability, Key Vault/managed identity permissions, storage account immutability, AKS node pools, private DNS, ingress and quota.

Do not assume snapshot or backup resources are portable across regions without explicit provider support and testing.

## 11. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Primary still writable | fencing authority |
| 02 | Split-brain risk | active controller inventory |
| 03 | Latest backup stale | RPO/replication lag |
| 04 | Backup checksum mismatch | integrity |
| 05 | Recovery KMS decrypt denied | key policy |
| 06 | Cross-region object missing | replication |
| 07 | Snapshot unavailable | provider support |
| 08 | DR volume attach fails | zone/topology |
| 09 | DR controller startup fails | Java/core/plugin |
| 10 | JCasC drift | Git manifest |
| 11 | Credential decryption fails | keys |
| 12 | SSO/RBAC unavailable | identity dependency |
| 13 | Agents Pending | quota/node pools |
| 14 | Registry unavailable | regional dependency |
| 15 | SCM webhook wrong endpoint | routing |
| 16 | DNS cutover slow | TTL/caches |
| 17 | Duplicate deployment after replay | idempotency |
| 18 | Artifact checksum mismatch | repository integrity |
| 19 | RTO/RPO breach | timeline |
| 20 | Failback stale state | authoritative DR state |

## 12. Six operational runbooks

### A. Primary region outage
Confirm scope and fencing, declare DR, restore validated backup and verify critical CI before routing.

### B. Split-brain prevention
Stop cutover if fencing cannot be proven; isolate old writer, preserve logs, authorize one controller before resuming.

### C. Backup replication failure
Verify checksum, copy lag, KMS permissions and retention; choose last verified restore point and recalculate RPO.

### D. Recovery-region dependency outage
Check DNS, SSO, SCM, artifact repository, registry, quota and network; use approved alternatives and retest synthetic CI.

### E. Failed DR validation
Do not advertise recovery; capture first failing gate, correct isolated target, rerun checks and escalate if RTO exceeded.

### F. Controlled failback
Freeze, back up authoritative DR state, fence DR writer, restore clean primary, validate and switch routing with sign-off.

## 13. 100-point acceptance scorecard

| Category | Points |
|---|---:|
| Architecture, failure domains and ownership | 15 |
| Fencing and single-writer safety | 20 |
| Backup replication, encryption and integrity | 15 |
| Automated restore and reproducible infrastructure | 15 |
| Critical CI, credentials, agents and routing | 15 |
| RTO/RPO measurement and data reconciliation | 10 |
| Failback, RCA/COA and sign-off | 10 |
| **Total** | **100** |

Suggested pass 85/100, plus mandatory gates: **verified primary fencing**, one active writer, approved backup, isolated restore, credential/RBAC checks, synthetic Pipeline success and measured RTO/RPO. Any failed mandatory gate blocks acceptance.

## 14. Evidence template

```text
Incident ID / UTC / owner:
Primary health and authoritative fencing proof:
Approved DR decision:
Backup ID / timestamp / SHA-256 / region:
Core/Java/plugins/JCasC and key custody:
Recovery storage and isolated controller:
SCM/SSO/registry/artifact dependencies:
Synthetic CI / artifact digest:
DNS/webhook change and replay reconciliation:
Measured RPO/RTO:
Failback authoritative state and writer fencing:
Residual risks / RCA / COA / reviewer:
```

**Companion:** [Chapter 084 hands-on lab](labs/084-jenkins-disaster-recovery-automation-cross-region-restore-failover-validation-check.md).  
**Next:** Chapter 085 — Jenkins Enterprise Backup, Upgrade and Disaster Recovery Acceptance Capstone.
