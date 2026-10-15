# Chapter 095 — Enterprise GitOps Reliability, Disaster Recovery and Operational Resilience Capstone

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 19:** Enterprise Reliability, Disaster Recovery and Resilience — Final Capstone  
**Chapter:** 095 / 100  
**Audience:** SRE, Platform Engineering, DBRE, Security, Incident Command and Release Engineering

> **Safety:** Execute only on explicitly approved, disposable staging resources. No production fault injection, DNS changes, credential rotation, database promotion, destructive restore or volume deletion. A game-day controller and independent safety officer must have an immediate stop path.

## 1. Mission and learning outcomes

This capstone integrates Chapters 091–094 into a realistic recovery assessment. Demonstrate dependency-aware resilience architecture, high availability, verified backups, deterministic GitOps bootstrap, clean-room restore, consistent database recovery, single-writer fencing, cross-region recovery, failback, incident command and evidence-backed RPO/RTO.

**Success is measured by restored user transactions and verified data consistency, not only Kubernetes Ready or Argo CD Healthy.**

## 2. Capstone scenario

A fictional critical service runs on Kubernetes with GitLab pipelines, a protected GitOps repository, immutable OCI images, Argo CD, External Secrets, ingress, a stateful PostgreSQL database and independent telemetry. A primary-region control-plane impairment coincides with Git provider degradation and database replication lag. The team must determine whether to stay in-region or declare DR, recover trusted artifacts, restore a secondary environment and prove no split brain.

Use synthetic data and a lab-only secondary cluster. No claim is made that any particular enterprise currently deploys this architecture.

## 3. Reference architecture

```text
   GitLab + protected Git -------- DR mirror / signed artifact vault
             |                              |
   Primary Argo CD                    Standby Argo CD
             |                              |
   Primary Kubernetes                 Secondary Kubernetes
       app + DB writer                app + DB replica/restore
             |                              |
          FENCING + authoritative database lease
                         |
           approved traffic routing / DNS
                         |
          synthetic transactions + independent SLOs
```

GitOps source recovery, infrastructure recovery, secrets recovery, data recovery and user-facing traffic recovery have different dependencies and owners. A second cluster does not constitute DR until its critical dependencies and data restore are independently tested.

## 4. Recovery objectives and decision gates

| Gate | Required proof | Stop condition |
|---|---|---|
| G0 Authorization | Approved change, context, owners, rollback | Any unknown scope |
| G1 Steady state | Baseline SLO, revision and transaction | Missing observability |
| G2 Source integrity | Git mirror and immutable signed OCI digest | Mismatch or untrusted artifact |
| G3 Backup | Fresh encrypted backup and successful clean-room restore | Partial or stale backup |
| G4 Bootstrap | IaC, identity, CNI, CSI, CRDs, Argo CD and policy | Missing prerequisite |
| G5 Data | DB-native consistency, recovery point, checksums | Unverified data |
| G6 Fencing | Old writer demonstrably isolated | Dual writer possible |
| G7 Cutover | TLS, synthetic transaction, routing and SLO | User journey fails |
| G8 Failback | Reverse sync, fencing and recovery approval | Divergent authority |

RTO is measured from the business-approved incident start to first sustained successful user transaction. RPO measures the gap between failure boundary and last recoverable committed transaction. Sample targets must be negotiated, never assumed.

## 5. Lab preflight

```bash
export LAB_NS=gitops-capstone-lab
export RESTORE_NS=gitops-capstone-restored
export LAB_DEPLOY=synthetic-api
export LAB_HEALTH_URL=https://capstone.example.invalid/health
export LAB_BACKUP=lab095-backup
export LAB_RESTORE=lab095-restore
# LAB_REPO_URL must point to a disposable repository.
kubectl config current-context
kubectl cluster-info
kubectl -n "$LAB_NS" get pods,deploy,svc -o wide
kubectl -n argocd get applications -o wide
```

Require a written context allowlist, lab namespace ownership, incident ticket, independent observer, recovery owner and abort thresholds before running any test.

## 6. Hands-on capstone labs (18)

Every lab records hypothesis, operator, approved scope, command output, UTC start/end, expected and observed results, SLO effect, abort/rollback decision and evidence link.

### Lab 01 — Scope and BIA

**Procedure:** Inventory synthetic service, dependencies, owners, RPO/RTO, SLO and critical user journeys.

```bash
kubectl config current-context
kubectl -n "$LAB_NS" get deploy,svc,pods -o wide
```

**Pass criteria:** Approved business-impact and dependency matrix. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 02 — Baseline observability

**Procedure:** Record Argo CD sync, application health, synthetic requests and DB replication lag.

```bash
kubectl -n argocd get applications -o wide
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Pass criteria:** Timestamped steady state. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 03 — Failure-domain map

**Procedure:** Identify shared DNS, Git, registry, IAM, KMS, storage and region dependencies.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclasses
```

**Pass criteria:** Correlated failures documented. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 04 — Git recovery validation

**Procedure:** Restore a disposable protected mirror and verify revision, branch protection and commit provenance.

```bash
git clone --mirror "$LAB_REPO_URL" ./lab095-mirror.git
git -C ./lab095-mirror.git fsck --full
```

**Pass criteria:** Trusted desired-state source. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 05 — OCI supply-chain recovery

**Procedure:** Verify exact image digests and chart references in secondary registry.

```bash
kubectl -n "$LAB_NS" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[*].image}{"\n"}{end}'
```

**Pass criteria:** Immutable signed artifact inventory. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 06 — Secret/KMS readiness

**Procedure:** Test DR identity against mock secret provider without exporting secret values.

```bash
kubectl -n "$LAB_NS" get serviceaccount
kubectl -n "$LAB_NS" get externalsecret
```

**Pass criteria:** Approved identity and decrypt capability. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 07 — Backup verification

**Procedure:** Inspect representative namespace-scoped Velero backup and database-native backup recovery point.

```bash
velero backup get
velero backup describe "$LAB_BACKUP" --details
```

**Pass criteria:** Fresh complete restorable backup. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 08 — Cold cluster bootstrap

**Procedure:** Provision an isolated cluster using pinned IaC and validate CNI, CSI, DNS, policy and CRDs.

```bash
kubectl get nodes -o wide
kubectl get crd | grep argoproj
```

**Pass criteria:** Bootstrap prerequisites ready. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 09 — Argo CD restoration

**Procedure:** Restore CRDs, AppProjects, repository access and Applications in dependency order.

```bash
kubectl -n argocd get deploy,sts,pods
kubectl -n argocd get appprojects,applications
```

**Pass criteria:** Healthy reconciliation against approved Git revision. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 10 — Kubernetes clean-room restore

**Procedure:** Restore disposable backup into a separate namespace with mapping and verify status.

```bash
velero restore create "$LAB_RESTORE" --from-backup "$LAB_BACKUP" --namespace-mappings "$LAB_NS:$RESTORE_NS" --wait
velero restore describe "$LAB_RESTORE" --details
```

**Pass criteria:** No collision and clean restore. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 11 — Database integrity

**Procedure:** Restore synthetic data using DB-native recovery and validate transaction counts and checksum.

```bash
kubectl -n "$RESTORE_NS" get pods,svc
kubectl -n "$RESTORE_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Pass criteria:** Data owner signs recovery point. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 12 — Single-writer fencing

**Procedure:** Simulate primary isolation and verify second writer cannot start until old writer is fenced.

```bash
kubectl -n "$LAB_NS" get endpointslices
kubectl -n "$RESTORE_NS" get endpointslices
```

**Pass criteria:** Explicit fencing evidence. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 13 — Git outage game day

**Procedure:** Inject a mock Git outage in a disposable Argo CD installation and observe stale reconciliation.

```bash
kubectl -n argocd get applications -o wide
kubectl -n argocd get pods -o wide
```

**Pass criteria:** Alert and controlled recovery. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 14 — Registry outage game day

**Procedure:** Use a synthetic missing image and validate safe image recovery by digest.

```bash
kubectl -n "$LAB_NS" describe deploy "$LAB_DEPLOY"
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -20
```

**Pass criteria:** Release blocked without user data impact. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 15 — AZ capacity loss

**Procedure:** Tabletop an AZ failure; in dedicated lab test workload rescheduling and PDB constraints.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
kubectl -n "$LAB_NS" get pdb,pods -o wide
```

**Pass criteria:** Capacity and failover evidence. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 16 — Regional cutover rehearsal

**Procedure:** Restore synthetic app to secondary isolated cluster and verify TLS, DNS and business transaction without production routing.

```bash
curl --fail --show-error --max-time 5 "$LAB_HEALTH_URL"
kubectl -n "$RESTORE_NS" get pods,svc
```

**Pass criteria:** Measured user-facing recovery. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 17 — Failback and rollback

**Procedure:** Validate reverse replication plan, source revision parity, old-writer fence and abort gate.

```bash
git rev-parse HEAD
kubectl -n argocd get applications -o wide
```

**Pass criteria:** Safe reversible operation. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

### Lab 18 — Final incident simulation

**Procedure:** Execute approved combined scenario, score gates, collect RTO/RPO, communications and RCA.

```bash
date -u +%FT%TZ
kubectl -n "$LAB_NS" get pods,svc -o wide
```

**Pass criteria:** Signed final capstone report. **Safety/rollback:** halt on unexpected context, dependency failure, data inconsistency or blast-radius expansion. Restore only the explicitly changed disposable resources.

## 7. Twenty troubleshooting scenarios

| # | Symptom | Initial investigation | Containment and verified recovery |
|---|---|---|---|
| 1 | Git mirror stale | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 2 | Git provider unreachable | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 3 | OCI digest missing | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 4 | Image signature invalid | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 5 | Argo CD repo-server crash | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 6 | Application controller backlog | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 7 | Redis connection failure | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 8 | Kubernetes API unavailable | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 9 | CRD version mismatch | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 10 | External Secrets failing | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 11 | KMS decrypt denied | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 12 | CSI snapshot unavailable | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 13 | Velero partial restore | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 14 | DB transaction checksum mismatch | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 15 | Replication lag exceeds RPO | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 16 | Old primary not fenced | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 17 | Ingress/TLS mismatch | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 18 | DNS cutover stale | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 19 | DR capacity exhausted | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |
| 20 | Telemetry blind spot | Capture Git revision, events, logs, SLI, owner and failure domain | Follow approved runbook; prove business transaction, data integrity and no unauthorized mutation |

## 8. Eight end-to-end incident runbooks

### RB-01 — Declare and govern incident

**Trigger, action and decision:** Incident commander verifies impact, RTO clock, release freeze, communications, ownership and explicit recovery authority.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-02 — Recover trusted desired state

**Trigger, action and decision:** Verify Git mirror, protected refs, signed commits, immutable OCI digests and Helm versions; block untrusted revisions.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-03 — Restore platform control plane

**Trigger, action and decision:** Provision isolated infrastructure and bootstrap IAM, CNI, CSI, DNS, policy, secrets, Argo CD CRDs, AppProjects and Applications.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-04 — Recover persistent data

**Trigger, action and decision:** Choose approved native database backup/PITR boundary, restore in isolation, validate transaction consistency and record measured RPO.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-05 — Fence and promote authoritative writer

**Trigger, action and decision:** Require independent proof old writer is blocked, DB owner authorization and exactly one promotion; abort on uncertainty.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-06 — Restore user traffic

**Trigger, action and decision:** Validate service health, TLS, synthetic read/write and observed client routing before approved traffic shift.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-07 — Stabilize and fail back

**Trigger, action and decision:** Observe error budget, reconcile Git, restore redundancy, reverse-replicate authoritative data and fence before reverse promotion.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

### RB-08 — Close incident and improve

**Trigger, action and decision:** Capture evidence, RTO/RPO, RCA, corrective actions, owners, deadlines, runbook revisions and next DR drill.

**Evidence and exit:** incident ID, owner, timestamps, approvals, command history, redacted logs, business synthetic result, RTO/RPO evidence, rollback state and signed handoff. Abort if any mandatory safety gate fails.

## 9. Final capstone scorecard (100 points)

| Category | Points | Required artifact |
|---|---:|---|
| Architecture, ownership and BIA | 10 | Dependency graph and RACI |
| HA and failure-domain resilience | 10 | AZ/region design and baseline |
| Git, CI and supply-chain recovery | 10 | Verified mirror, signed digest |
| Backup and clean-room restoration | 15 | Restore log and checksums |
| GitOps bootstrap and policy | 10 | Pinned rebuild transcript |
| Database integrity and fencing | 15 | Transaction and single-writer proof |
| Cutover, failback and RTO/RPO | 15 | Timed end-to-end evidence |
| Incident command and communications | 5 | Decision timeline |
| Runbooks, RCA and corrective actions | 10 | Reviewed closure packet |
| **Total** | **100** | |

**Acceptance:** 90/100 or above and **all** mandatory gates G0–G8. Any split-brain risk, unverified backup, unauthorized scope, missing recovery evidence or failed user transaction is an automatic fail regardless of score.

## 10. Capstone deliverables

1. Architecture and dependency map with failure domains and business criticality.
2. Business-approved RPO/RTO, SLO and recovery owner matrix.
3. Protected Git mirror and immutable artifact provenance evidence.
4. Backup inventory, encryption/key recovery and clean-room restore proof.
5. Reproducible Kubernetes and Argo CD bootstrap manifest/versions.
6. Data integrity, database restore point and old-writer fencing proof.
7. Cross-region cutover/failback plan with synthetic user validation.
8. Incident timeline, runbooks, redacted logs, scorecard, RCA and remediation backlog.

## 11. Incident evidence template

```text
Capstone ID / ticket:
Primary / secondary cluster and region:
Incident commander / safety officer / DB owner:
Approved context and namespace:
Git commit / image digest / chart version:
Fault hypothesis and injected scenario:
Baseline SLI / alert UTC:
Backup ID / data recovery point / checksum:
Old writer fencing evidence:
Recovery declaration UTC / business transaction restored UTC:
Measured RPO / RTO versus targets:
DNS and TLS verification:
Failback and rollback state:
Final score / failed gates:
RCA / corrective action / owner / due date:
Approvals / next drill:
```

## 12. Cleanup and production-readiness signoff

Return synthetic routing to the original lab service, verify a single authoritative database writer, confirm Argo CD desired-state revision and application SLO, then remove only labeled disposable recovery resources according to retention policy. Never delete the sole valid backup. Keep redacted evidence and corrective actions for audit.

**Part 19 completion criterion:** all five chapters (091–095) exist in the master index and the capstone passes the mandatory recovery gates in a controlled environment. Publishing the tutorial is not proof that a live organization has passed its DR drill.

**Next:** Chapter 096 — Enterprise GitOps Final Project: Platform Architecture, Requirements and Production Design, beginning Part 20 — Final Enterprise GitOps Capstone.
