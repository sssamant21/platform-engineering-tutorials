# Chapter 099 — Enterprise GitOps Final Project: Failure Simulation, Disaster Recovery and Production Reliability Validation

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 20:** Final Enterprise GitOps Capstone  
**Chapter:** 099 / 100  
**Audience:** SRE, Platform Engineering, DBRE, Security, Incident Command and Release Engineering

> **Safety:** All injected faults, backups, restores, writer fencing and traffic changes are restricted to approved disposable staging systems. Never simulate outages on production infrastructure or promote a database without verified old-writer fencing and independent approval. The command examples are mostly observational; scenario injection requires an environment-specific, reviewed implementation.

## 1. Mission and learning outcomes

Validate the architecture built in Chapters 096–098 against realistic failures: application disruption, node/AZ loss, Git and registry outages, Argo CD degradation, DNS/identity failures, resource saturation, backup/restore, stateful data consistency, regional recovery and failback. Produce measured service-level evidence, observed RPO/RTO, runbook outcomes and a defensible go/no-go decision.

## 2. Reliability test reference architecture

```text
 Approved game-day controller + independent safety officer
                          |
    +---------------------+----------------------+
    |                     |                      |
 Primary lab cluster    Git/OCI dependencies   DR lab cluster
 Argo CD + API + DB     signed mirror/escrow   Argo CD + restored DB
    |                     |                      |
    +--------- independent synthetic probes ------+
                          |
             SLI/SLO and RPO/RTO recorder
                          |
                 incident evidence + RCA
```

No cluster should be considered recovered solely because Pods are Running or Argo CD reports Healthy. Validate authenticated, end-to-end business transactions and the authoritative database recovery point.

## 3. Hypothesis-driven test method

For each scenario, define: **hypothesis**, **steady-state SLI**, **fault scope**, **duration**, **safety stop**, **expected behavior**, **observations**, **recovery action**, **cleanup**, **owner** and **evidence**.

Example hypothesis: losing one synthetic API replica in a multi-replica staging deployment will not breach the approved availability SLO, and the service will regain target replica count within the measured recovery window. A failed hypothesis is useful evidence, not a reason to continue injection.

## 4. Game-day authorization gates

| Gate | Required evidence | Stop condition |
|---|---|---|
| A1 | Explicit lab context and resource allowlist | Unknown cluster |
| A2 | Change approval and independent safety officer | Missing approver |
| A3 | Steady-state transaction and telemetry | Blind or unhealthy baseline |
| A4 | Bounded injection and rollback | Fault cannot be reversed |
| A5 | Complete restorable backup | Unverified restore point |
| A6 | Data owner and writer fencing | Split-brain risk |
| A7 | Secondary capacity and artifact provenance | Untrusted or unavailable recovery |
| A8 | Final transaction, data integrity and RPO/RTO | Unverified recovery |

## 5. RTO, RPO and SLO measurement

**RTO:** agreed incident start to sustained successful user transaction on the recovered service.  
**RPO:** failure boundary minus timestamp of the latest recoverable committed transaction.  
**Error budget:** eligible failures allowed by the approved SLO over the measurement window; record actual request counts and burn rates.  
**Reconciliation lag:** time between approved Git change and verified healthy running revision.

For a 99.9% availability objective, the allowed error fraction is 0.001. A successful infrastructure recovery that breaches business RTO or loses more data than allowed RPO is still a failed DR exercise.

## 6. Safe preflight

```bash
export LAB_NS=gitops-reliability-lab
export RESTORE_NS=gitops-reliability-restored
export LAB_DEPLOY=synthetic-api
export LAB_BACKUP=lab099-backup
export LAB_RESTORE=lab099-restore
export LAB_HEALTH_URL=https://lab.example.invalid/health
export DR_HEALTH_URL=https://dr-lab.example.invalid/health
export APPROVED_CONTEXT=replace-with-approved-disposable-context
test "$(kubectl config current-context)" = "$APPROVED_CONTEXT"
kubectl -n "$LAB_NS" get deploy,pods,svc -o wide
kubectl -n argocd get applications -o wide
```

URLs and names are placeholders; substitute only verified synthetic endpoints and a staging backup. A recovery operator must not proceed when a variable is unset or points to production.

## 7. Hands-on resilience labs (18)

Record exact UTC timestamps, hypothesis, scope, operator, independent observer, stop condition, evidence, measured impact, rollback and final business transaction for each lab.

### Lab 01 — Readiness and change authorization

**Exercise:** Verify staging context, blast radius, owner, stop threshold and approved recovery point.

```bash
kubectl config current-context
kubectl -n "$LAB_NS" get deploy,pods,svc -o wide
```

**Acceptance:** Independent safety approval. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 02 — Capture steady state

**Exercise:** Record synthetic transaction, error rate, p95 latency, Argo CD sync and database health.

```bash
curl --fail --show-error --max-time 5 "$LAB_HEALTH_URL"
kubectl -n argocd get applications -o wide
```

**Acceptance:** Timestamped baseline. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 03 — SLO and error-budget worksheet

**Exercise:** Calculate budget consumption using real request counts and approved objective.

```bash
date -u +%FT%TZ
kubectl -n "$LAB_NS" get hpa,pdb
```

**Acceptance:** Defined abort threshold. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 04 — Pod disruption experiment

**Exercise:** In disposable namespace test one replica loss with fault tool and verify readiness.

```bash
kubectl -n "$LAB_NS" get pods -o wide
kubectl -n "$LAB_NS" get pdb
```

**Acceptance:** Resilience within SLO. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 05 — Node/AZ failure tabletop

**Exercise:** Simulate node and AZ outage on paper; review topology, PDB and capacity.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
kubectl -n "$LAB_NS" get pods -o wide
```

**Acceptance:** Placement and failover design. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 06 — Git provider outage

**Exercise:** Use isolated test Git endpoint and pause access; observe Argo CD stale revision.

```bash
kubectl -n argocd get applications -o wide
kubectl -n argocd get pods -o wide
```

**Acceptance:** Safe source recovery. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 07 — OCI registry outage

**Exercise:** Use a synthetic unavailable image and recover approved signed digest.

```bash
kubectl -n "$LAB_NS" describe deploy "$LAB_DEPLOY"
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Acceptance:** Image availability restored. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 08 — Argo CD controller disruption

**Exercise:** In isolated controller installation simulate one replica loss; measure reconciliation.

```bash
kubectl -n argocd get deploy,sts,pods
kubectl -n argocd get applications -o wide
```

**Acceptance:** Reconciliation lag within target. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 09 — DNS and ingress fault

**Exercise:** Tabletop resolver outage and test disposable endpoint routing in lab.

```bash
kubectl -n "$LAB_NS" get ingress,svc,endpointslices
kubectl -n kube-system get deploy coredns
```

**Acceptance:** Fail-safe traffic handling. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 10 — Secrets/identity failure

**Exercise:** Expire only a mock secret or synthetic workload identity and verify alerts.

```bash
kubectl -n "$LAB_NS" get externalsecrets
kubectl -n "$LAB_NS" get serviceaccounts
```

**Acceptance:** No secret exposure and graceful recovery. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 11 — Resource saturation

**Exercise:** Apply bounded synthetic load to disposable API; observe autoscaling and stop guardrails.

```bash
kubectl -n "$LAB_NS" top pods
kubectl -n "$LAB_NS" get hpa,resourcequota
```

**Acceptance:** Alert and capacity response. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 12 — Backup inventory and restore point

**Exercise:** Verify complete Velero backup and database-native PITR boundary.

```bash
velero backup get
velero backup describe "$LAB_BACKUP" --details
```

**Acceptance:** Fresh consistent recovery point. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 13 — Clean-room restore

**Exercise:** Restore namespace-scoped synthetic workload to isolated destination.

```bash
velero restore create "$LAB_RESTORE" --from-backup "$LAB_BACKUP" --namespace-mappings "$LAB_NS:$RESTORE_NS" --wait
velero restore describe "$LAB_RESTORE" --details
```

**Acceptance:** Restored resource integrity. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 14 — Database consistency and fencing

**Exercise:** Verify synthetic checksums, replication lag and old-primary isolation before simulated promotion.

```bash
kubectl -n "$RESTORE_NS" get pods,svc
kubectl -n "$RESTORE_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Acceptance:** Exactly one authoritative writer. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 15 — Regional recovery dry run

**Exercise:** Rebuild secondary lab cluster from pinned Git and OCI artifacts; verify application and data.

```bash
kubectl config get-contexts
kubectl -n argocd get applications -o wide
```

**Acceptance:** Measured RPO/RTO. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 16 — Synthetic traffic cutover

**Exercise:** Test secondary lab endpoint only; validate TLS, auth, read/write and observability.

```bash
curl --fail --show-error --max-time 5 "$DR_HEALTH_URL"
date -u +%FT%TZ
```

**Acceptance:** User journey restored. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 17 — Failback and rollback

**Exercise:** Validate reverse replication, fencing and approved GitOps revision before returning traffic.

```bash
git rev-parse HEAD
kubectl -n "$LAB_NS" get deploy,pods,svc
```

**Acceptance:** No dual writer or stale config. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

### Lab 18 — Blind game day and report

**Exercise:** Safety officer selects bounded fault; team runs incident command and produces evidence.

```bash
date -u +%FT%TZ
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Acceptance:** Signed 100-point scorecard. **Stop/rollback:** terminate the bounded experiment on unexpected scope, SLO violation, telemetry loss or ambiguous data authority; restore the original disposable lab state and retain evidence.

## 8. Twenty troubleshooting scenarios

| # | Failure mode | First evidence | Containment and recovery |
|---|---|---|---|
| 1 | SLO alert not firing | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 2 | Pod restart storm | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 3 | PDB blocks node drain | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 4 | Secondary AZ no capacity | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 5 | Git provider outage | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 6 | Git mirror stale | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 7 | Registry image missing | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 8 | Artifact signature invalid | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 9 | Argo CD repo-server OOM | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 10 | Controller reconciliation backlog | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 11 | CoreDNS outage | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 12 | Ingress certificate expired | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 13 | ExternalSecret provider denied | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 14 | KMS key unavailable | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 15 | CPU throttling overload | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 16 | Velero backup incomplete | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 17 | Volume restore unsupported | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 18 | Database PITR inconsistent | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 19 | Old writer not fenced | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |
| 20 | Failback causes data divergence | Collect alerts, events, logs, SLI, Git revision, backup/data status | Follow owned runbook; validate synthetic transaction, source integrity and database consistency |

## 9. Eight operational runbooks

### RB-01 Declare and contain

**Trigger and procedure:** Incident commander verifies service impact, change authorization, SLO, scope, on-call roles and stop criteria; pause deployments.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-02 Platform fault response

**Trigger and procedure:** Identify Pod/node/AZ/control-plane issue, verify PDB and available capacity, restore replicas safely and recheck synthetic transaction.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-03 Git and artifact outage

**Trigger and procedure:** Preserve current workloads, verify signed mirror commit and image digest, recover trusted source without bypassing policy.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-04 Argo CD reconciliation failure

**Trigger and procedure:** Check controller, repo-server, Git credentials and Application diff; recover convergence without uncontrolled pruning.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-05 Secrets, DNS and network outage

**Trigger and procedure:** Validate identity, KMS, resolver, ingress and network policy; restore approved dependency while preserving audit evidence.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-06 Restore stateful service

**Trigger and procedure:** Select DB-consistent restore point, restore in isolation, compare checksums, fence old primary and verify single-writer invariant.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-07 Regional cutover and failback

**Trigger and procedure:** Authorize route change only after secondary service and data pass; measure RTO/RPO and fence on reverse promotion.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

### RB-08 Game-day closure

**Trigger and procedure:** Stop injections, confirm steady state, publish timeline, scores, root causes, remediation owners, deadlines and retest.

**Closeout evidence:** incident/change ID, owner, UTC timeline, signed revision/digest, observed SLI and RPO/RTO, recovery verification, rollback decision and next retest.

## 10. Fault-injection test matrix

| Experiment | Primary SLI | Required recovery proof |
|---|---|---|
| Pod loss | Request success and latency | Replica restored and transaction passes |
| Node/AZ impairment | Availability and scheduling | Surviving capacity and PDB verified |
| Git outage | Reconciliation age | Trusted mirror and expected Git revision |
| Registry outage | Image availability | Verified immutable image digest |
| Argo CD failure | Reconciliation lag | Desired/live convergence |
| DNS/ingress outage | Endpoint availability | TLS, routing and user journey |
| Secrets/KMS outage | Authentication success | Restored workload identity, no leak |
| Capacity saturation | p95 latency and error budget | Load reduction and stable service |
| Backup restore | RPO and data checksums | Consistent recovered transactions |
| Regional cutover | RTO and availability | Secondary service and single writer |
| Failback | Data consistency | Safe authoritative reverse promotion |

## 11. Reliability acceptance scorecard (100 points)

| Category | Points |
|---|---:|
| Game-day safety and change control | 15 |
| Baseline SLO and independent telemetry | 10 |
| Application/node/AZ fault resilience | 15 |
| Git/OCI/Argo CD dependency recovery | 15 |
| Identity/network/capacity recovery | 10 |
| Backup restore and data integrity | 15 |
| Regional failover, fencing and failback | 15 |
| RCA, communications and retest | 5 |
| **Total** | **100** |

**Pass:** 90/100 or more and all mandatory gates A1–A8. A split-brain possibility, unsafe injection, missing backup proof, failed synthetic transaction or unmeasured RPO/RTO automatically fails the exercise.

## 12. Incident/game-day evidence template

```text
Game-day ID / change approval:
Environment / approved Kubernetes context:
Incident commander / safety officer / DB owner:
Scenario / hypothesis / blast radius:
Baseline SLO and synthetic checks:
Fault start UTC / alert UTC / recovery UTC:
Git revision / OCI digest:
Backup ID / DB recovery point / checksums:
Writer fencing and promotion evidence:
Primary/secondary endpoint verification:
Observed RTO / observed RPO / error-budget use:
Rollback/failback and cleanup:
Final score / mandatory gates:
RCA / corrective actions / owners / due dates:
Approvers / next drill:
```

## 13. Cleanup and definition of done

Stop all fault injections, confirm original GitOps desired state, verify one authoritative database writer, restore lab traffic, re-run business transactions and remove only disposable resources according to approved retention policy. Preserve the last good backup and redacted evidence.

The final project is ready for Chapter 100 only when the team can reproduce its recovery workflow, explain observed failure modes, measure RPO/RTO, close critical safety gaps and present an auditable resilience report.

**Next:** Chapter 100 — Enterprise GitOps Final Assessment, Production Readiness Review and End-to-End Graduation Capstone.
