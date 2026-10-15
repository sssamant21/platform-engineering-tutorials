# Chapter 094 — Enterprise GitOps Operational Readiness, Resilience Testing and Recovery Automation

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 19:** Enterprise Reliability, Disaster Recovery and Resilience  
**Chapter:** 094 / 100  
**Audience:** SRE, Platform Engineering, DBRE, Security, Incident Command and Release Engineering

> **Safety:** Use an explicitly approved disposable staging environment. The automation examples default to inspection, planning and dry-run; they do not authorize production mutation, data promotion, DNS changes or secret disclosure. Require change approval, context allowlists, operator confirmation and independently tested rollback.

## 1. Objectives

Build repeatable operational-readiness checks and resilience test gates; implement a fail-closed GitOps recovery pipeline; validate backup freshness and integrity, immutable artifacts, identity, control-plane bootstrap and database consistency; separate plan from execute; prove RTO/RPO; and produce an auditable production readiness decision.

## 2. Reliability automation principles

1. **Safe by default:** plan-only, read-only checks, least privilege, and no implicit production fallback.
2. **Deterministic:** pinned Git revisions, image digests, Helm chart versions, IaC and tool versions.
3. **Dependency aware:** identity/network/storage/CRDs before Argo CD Applications; data recovery before traffic cutover.
4. **Idempotent:** retries must not duplicate database promotion, credentials, DNS updates or destructive operations.
5. **Observable:** every gate writes structured status, UTC timestamps, actor and evidence.
6. **Reversible:** a documented abort path exists before each mutation.
7. **Human controlled:** high-impact changes require protected approvals; automation never silently promotes a second writer.

## 3. Reference architecture

```text
GitLab protected recovery pipeline
       |
       +-- validate context / approvals / policy
       +-- verify Git commit + OCI signatures
       +-- verify backup, KMS, secrets, restore point
       +-- PLAN (read-only; produce review artifact)
       +-- MANUAL APPROVAL
       +-- isolated staging restore + synthetic tests
       +-- DB fencing gate / data owner signoff
       +-- controlled regional recovery (separate approved workflow)
       +-- evidence + rollback + acceptance report
                 |
        Independent SLO monitoring
```

A passing Argo CD health check does not prove a business transaction, data consistency or recoverability. A backup marked Completed is insufficient without a clean-room restore.

## 4. Recovery readiness gates

| Gate | Evidence | Fail-closed rule |
|---|---|---|
| Environment | Exact context, namespace and account allowlist | Reject unknown target |
| Authorization | Change ID, operator, dual approval | No mutation without approval |
| Source integrity | Git revision, signed image digest | Reject mutable/unverified artifacts |
| Backup | Fresh, completed, encrypted, restorable | Reject stale/partial backup |
| Secrets | DR identity and key access | Never expose secret values |
| Bootstrap | Compatible CRDs, CSI, CNI, Argo CD | Restore dependencies in order |
| Data | DB-consistent recovery point and checksums | No promotion without validation |
| Fencing | Old writer demonstrably disabled | Stop on ambiguous authority |
| Service | TLS, DNS, synthetic read/write and SLO | No traffic shift on failed checks |
| Rollback | Owner, reverse plan, snapshot of current state | Stop if no safe abort path |

## 5. Example read-only preflight script

Save the following as `scripts/dr-preflight.sh`. It deliberately does not modify the cluster.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
: "${APPROVED_CONTEXT:?Set approved disposable context}"
: "${LAB_NS:?Set disposable namespace}"
: "${CHANGE_ID:?Set approved change ID}"
actual="$(kubectl config current-context)"
if [[ "$actual" != "$APPROVED_CONTEXT" ]]; then
  echo "BLOCKED: context $actual is not $APPROVED_CONTEXT" >&2
  exit 20
fi
kubectl get namespace "$LAB_NS" >/dev/null
kubectl auth can-i get deployments -n "$LAB_NS" | grep -qx yes
kubectl -n "$LAB_NS" get deploy,pods,svc
kubectl -n argocd get applications.argoproj.io -o wide
printf 'PASS change=%s context=%s namespace=%s time=%s\n' \
  "$CHANGE_ID" "$actual" "$LAB_NS" "$(date -u +%FT%TZ)"
```

**Negative tests:** unset `CHANGE_ID`, set a mismatched context, use a missing namespace, or remove read permission. Every case must return nonzero and make no mutation.

## 6. Example GitLab CI recovery gate

The example runs inspection and a manually approved **plan-only** stage. It is a template; pin a vetted image by digest, use a restricted runner, protected variables and an approved Kubernetes identity before enabling.

```yaml
stages: [validate, plan]
variables:
  GIT_STRATEGY: fetch
  RECOVERY_MODE: "plan"
dr_validate:
  stage: validate
  image: registry.example.invalid/platform/kubectl@sha256:REPLACE_WITH_VERIFIED_DIGEST
  script:
    - test "$RECOVERY_MODE" = "plan"
    - bash scripts/dr-preflight.sh
  artifacts:
    when: always
    expire_in: 7 days
    paths: [recovery-evidence/]
dr_plan:
  stage: plan
  image: registry.example.invalid/platform/kubectl@sha256:REPLACE_WITH_VERIFIED_DIGEST
  when: manual
  allow_failure: false
  needs: [dr_validate]
  script:
    - test "$RECOVERY_MODE" = "plan"
    - echo "PLAN ONLY — review recovery dependencies, backups, owners and rollback"
  rules:
    - if: '$CI_COMMIT_REF_PROTECTED == "true"'
```

Do not treat `when: manual` alone as sufficient authorization: enforce protected environments, restricted runners, protected branches and appropriate approval policy. Keep actual recovery execution in a separately reviewed workflow with explicit, bounded parameters.

## 7. Hands-on labs — 18 operational exercises

All exercises require a recorded hypothesis, expected result, exact context, UTC timestamp, rollback owner, evidence artifact and stop condition. Substitute only disposable resources.

### Lab 01 — Operational inventory

**Procedure:** Discover cluster, GitOps apps, critical namespaces and recovery owners.

```bash
kubectl config current-context
kubectl -n argocd get applications,applicationsets,appprojects
kubectl get nodes -o wide
```

**Acceptance:** Inventory has owners, dependencies and classification. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 02 — Readiness baseline

**Procedure:** Measure healthy workload, sync state, available replicas and SLO evidence.

```bash
kubectl -n "$LAB_NS" get deploy,pods,svc
kubectl -n argocd get applications -o wide
```

**Acceptance:** Baseline timestamp and expected steady state. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 03 — Read-only preflight script

**Procedure:** Implement context allowlist, namespace check and fail-closed dependency probes.

```bash
test "$(kubectl config current-context)" = "$APPROVED_CONTEXT"
kubectl get namespace "$LAB_NS"
```

**Acceptance:** Script refuses unapproved context. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 04 — Artifact verification

**Procedure:** Confirm pinned Git revision, image digests and signature policy before restore.

```bash
git rev-parse HEAD
kubectl -n "$LAB_NS" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[*].image}{"\n"}{end}'
```

**Acceptance:** Immutable release manifest saved. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 05 — Backup freshness gate

**Procedure:** Check Velero backup completion, errors and age against RPO target.

```bash
velero backup get
velero backup describe "$LAB_BACKUP" --details
```

**Acceptance:** Stale or partial backup blocks recovery. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 06 — Secrets readiness gate

**Procedure:** Verify external secret reconciliation and DR key grants without printing secret values.

```bash
kubectl -n "$LAB_NS" get externalsecrets -o wide
kubectl -n "$LAB_NS" get serviceaccounts
```

**Acceptance:** Secret availability verified securely. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 07 — Argo CD dependency ordering

**Procedure:** Review AppProject, CRD, controller, repo-server and Application dependencies.

```bash
kubectl -n argocd get deploy,sts,pods
kubectl get crd | grep argoproj
```

**Acceptance:** Bootstrap graph and version lock documented. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 08 — CI recovery pipeline lint

**Procedure:** Run a local or protected pipeline syntax validation on a staging recovery workflow.

```bash
git diff --check
git status --short
```

**Acceptance:** Pipeline cannot bypass approval. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 09 — Dry-run Kubernetes apply

**Procedure:** Use server-side dry run only on disposable namespace manifests; detect RBAC and schema failures.

```bash
kubectl apply --dry-run=server -n "$LAB_NS" -f ./lab-manifests/
```

**Acceptance:** Zero unexpected mutations. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 10 — Recovery plan mode

**Procedure:** Generate planned operations, dependencies, approvals and estimated impact without executing.

```bash
printf '%s\n' 'PLAN ONLY: validate context, backup, owners, restore target, and rollback'
```

**Acceptance:** Plan artifact reviewed by second operator. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 11 — Clean-room restore

**Procedure:** Restore disposable namespace resources to isolated destination using approved backup.

```bash
velero restore create "$LAB_RESTORE" --from-backup "$LAB_BACKUP" --namespace-mappings "$LAB_NS:$RESTORE_NS" --wait
velero restore describe "$LAB_RESTORE" --details
```

**Acceptance:** No collisions and restore reports success. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 12 — Data consistency verification

**Procedure:** Compare synthetic application record counts and checksums to recorded recovery point.

```bash
kubectl -n "$RESTORE_NS" get pods,svc -o wide
kubectl -n "$RESTORE_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Acceptance:** Data owner signs consistency proof. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 13 — Writer fencing gate

**Procedure:** Use a simulated DB role or lease to prove old writer is isolated before any promotion.

```bash
kubectl -n "$LAB_NS" get endpointslices,svc
kubectl -n "$RESTORE_NS" get endpointslices,svc
```

**Acceptance:** Single-writer invariant enforced. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 14 — Synthetic transaction gate

**Procedure:** Execute end-to-end read/write against disposable recovery service.

```bash
curl --fail --silent --show-error --max-time 5 "$LAB_HEALTH_URL"
```

**Acceptance:** Health and business transaction pass. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 15 — Recovery observability

**Procedure:** Measure detection, reconcile delay, error rate and no-data alerts using independent telemetry.

```bash
kubectl -n argocd get applications -o wide
kubectl -n "$RESTORE_NS" get pods -o wide
```

**Acceptance:** Measured RTO and observed RPO recorded. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 16 — Rollback automation rehearsal

**Procedure:** Test explicit rollback approval and reverse-order restoration without touching production.

```bash
git status --short
kubectl config current-context
```

**Acceptance:** Rollback gate fails closed on uncertainty. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 17 — Audit and evidence packaging

**Procedure:** Create signed evidence checklist with change ID, UTC timestamps, revisions, backup ID and reviewers.

```bash
date -u +%FT%TZ
git rev-parse HEAD
```

**Acceptance:** Evidence complete and secrets redacted. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

### Lab 18 — Unattended negative tests

**Procedure:** Test failure modes: wrong context, missing backup, stale snapshot, denied identity, duplicate writer, missing approval.

```bash
test "$(kubectl config current-context)" = "$APPROVED_CONTEXT" && echo 'context OK'
```

**Acceptance:** All unsafe conditions halt before mutation. **Abort:** unexpected environment, resource scope, credential exposure, data-authority ambiguity or failed synthetic check. Record evidence and corrective action.

## 8. Troubleshooting — 20 recovery automation failures

| # | Failure | Signal | Operator response |
|---|---|---|---|
| 1 | Wrong kube context | Preflight context mismatch | Stop immediately; require allowlisted context and human approval |
| 2 | Missing namespace | kubectl NotFound | Create only approved disposable destination after review |
| 3 | RBAC denied | Forbidden | Verify least-privilege DR role; never use cluster-admin shortcut |
| 4 | Backup stale | Age exceeds RPO | Block restore; select validated recovery point |
| 5 | Backup partial | Velero PartiallyFailed | Review item errors and re-run isolated restore |
| 6 | Object storage denied | AccessDenied | Verify bucket policy, role and KMS grants |
| 7 | Restore collision | AlreadyExists | Use isolated target or approved resource mapping |
| 8 | CRD absent | No matches for kind | Bootstrap matching CRD/controller first |
| 9 | Argo CD unhealthy | Unknown or Degraded | Inspect controller, repo-server, repository credentials and events |
| 10 | Git mirror behind | Missing revision | Block promotion; verify refs and provenance |
| 11 | OCI digest unavailable | ImagePullBackOff | Recover signed artifact in secondary registry |
| 12 | Image policy rejected | Admission denied | Validate signature and trust root |
| 13 | ExternalSecret not ready | SecretSyncError | Check workload identity and provider connectivity |
| 14 | CSI class unavailable | Snapshot unsupported | Use compatible driver or native DB backup |
| 15 | Restore checksum mismatch | Synthetic data differs | Quarantine restore and retry from consistent point |
| 16 | Dual writer possible | Old primary not fenced | Abort promotion; enforce authoritative lease/fence |
| 17 | Synthetic check fails | 5xx or incorrect response | Hold traffic; diagnose service/data dependencies |
| 18 | Telemetry unavailable | No data | Use independent probe; do not claim success |
| 19 | Approval missing | Protected job blocked | Keep automation in plan mode |
| 20 | Rollback ambiguous | Unknown data authority | Stop and escalate to DB owner and incident commander |

## 9. Eight production recovery runbooks

### RB-01 Preflight and authorization

**Trigger, procedure and decision gate:** Confirm change ticket, incident authority, approved context, owners, blast radius, safe window and stop conditions. No approval means plan-only.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-02 Backup and recovery point selection

**Trigger, procedure and decision gate:** Inspect backup success, timestamp, object-store access, encryption key and database-consistent recovery boundary. Reject stale or incomplete backups.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-03 Control-plane bootstrap

**Trigger, procedure and decision gate:** Rebuild cluster prerequisites, identity, CNI/CSI, policy, secret controller and Argo CD in pinned order. Verify CRDs and AppProjects before Applications.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-04 Safe GitOps reconciliation

**Trigger, procedure and decision gate:** Check immutable source revision, target cluster and pruning settings. Enable synchronization only for approved isolated targets.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-05 Data restore and fencing

**Trigger, procedure and decision gate:** Restore data into isolated target, validate checksums and transactions, prove old-writer isolation and require dual authorization before promotion.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-06 Synthetic traffic recovery

**Trigger, procedure and decision gate:** Validate TLS, DNS, routing and user transactions. Shift traffic only after signed service and data checks.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-07 Rollback and abort

**Trigger, procedure and decision gate:** On unknown context, unexpected resource deletion, split-brain risk, missing telemetry or breached thresholds: stop, isolate, preserve evidence and escalate.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

### RB-08 Evidence and closure

**Trigger, procedure and decision gate:** Record actual RTO/RPO, commits, digests, backup IDs, operator actions, failed gates, RCA, follow-up owners and retest date.

**Validation:** collect time-stamped logs, health and synthetic checks, responsible owner, rollback status and signoff. Escalate immediately if the intended scope changes.

## 10. Automated test matrix

| Test | Expected outcome |
|---|---|
| Approved context + healthy dependencies | Readiness plan passes |
| Wrong context or missing change ID | Hard fail before API mutation |
| Missing/partial/stale backup | Restore execution blocked |
| Unverified Git or image digest | Deployment blocked |
| Secrets/KMS inaccessible | Recovery blocked without leaking values |
| Missing CRDs/CSI | Bootstrap gate fails with actionable error |
| Failed data checksum | No writer promotion |
| Old writer not fenced | No secondary promotion |
| Synthetic user transaction fails | No DNS/traffic cutover |
| Rollback owner absent | Execution blocked |
| Telemetry unavailable | No readiness acceptance |

## 11. RTO/RPO measurement

Capture four distinct timestamps: incident start, recovery declaration, restored data point, and first successful business transaction. RTO is measured against the business-approved start/end definition; RPO uses the latest recoverable committed state versus the failure boundary. Do not substitute Argo CD sync time for end-to-end recovery.

## 12. Acceptance scorecard (100 points)

| Area | Points |
|---|---:|
| Recovery ownership and dependency mapping | 10 |
| Environment and authorization gates | 15 |
| Source integrity and policy controls | 10 |
| Backup and restore verification | 15 |
| Bootstrap and GitOps reconciliation | 15 |
| Data consistency and fencing | 15 |
| Synthetic tests and SLO observability | 10 |
| Rollback, audit evidence and retest | 10 |
| **Total** | **100** |

**Pass:** 90/100 or higher **and** every mandatory gate: isolated approved scope, fail-closed authorization, restorable backup, single writer, consistent data, user-facing transaction, measured RPO/RTO, safe rollback.

## 13. Readiness report template

```text
Change/incident ID:
Environment and approved Kubernetes context:
Operator / reviewer / DB owner / incident commander:
Git commit / signed image digest / Helm version:
Backup ID / backup age / restore checksum:
KMS and secret recovery validation:
Bootstrap dependency checks:
Data consistency / writer fencing evidence:
Synthetic transaction / SLO baseline:
Start UTC / recovered UTC / measured RTO:
Failure boundary / restore point / measured RPO:
Rollback plan and test evidence:
Failed gates / exceptions / corrective actions:
Approval and next drill date:
```

## 14. Cleanup and definition of done

Remove only explicitly labeled disposable resources after verifying original traffic and authoritative data writer. Preserve backups and redacted evidence under the approved retention policy. Chapter completion requires a reproducible plan-only workflow, negative tests that stop before mutation, a successful clean-room restore, verified service and data integrity, and an owner-approved recovery assessment.

**Next:** Chapter 095 — Enterprise GitOps Reliability, Disaster Recovery and Operational Resilience Capstone.
