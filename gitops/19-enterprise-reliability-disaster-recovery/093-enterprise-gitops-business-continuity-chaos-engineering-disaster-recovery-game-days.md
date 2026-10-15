# Chapter 093 — Enterprise GitOps Business Continuity, Chaos Engineering and Disaster Recovery Game Days

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 19:** Enterprise Reliability, Disaster Recovery and Resilience  
**Chapter:** 093 / 100  
**Audience:** SRE, Platform Engineering, DBRE, Incident Command, Security and Release Engineering

> **Mandatory safety:** All fault injection is restricted to an approved disposable staging environment. Do not disrupt production DNS, databases, identity, Argo CD, shared nodes or customer traffic. Game-day scenarios are educational examples; operator approval and tested rollback are required.

## 1. Learning objectives

Design a business continuity plan (BCP) spanning people, processes, dependencies and technical recovery; apply hypothesis-driven chaos engineering; construct measurable game days; demonstrate incident coordination, safe fault containment, RTO/RPO evidence, recovery and failback; and score operational readiness.

## 2. Business continuity versus disaster recovery

Business continuity includes alternative operational procedures, communications, staffing, vendors, customer commitments, release freezes and manual workarounds. Disaster recovery is the technical restoration of systems and data. High availability minimizes interruptions within a failure domain. Chaos engineering tests resilience hypotheses under controlled, bounded faults.

A successful Argo CD sync does not prove business continuity: the app may still be unavailable, its data stale, or its users unable to authenticate. Test an actual business transaction.

## 3. Architecture and failure-domain model

```text
Business service + user journeys + SLOs
           |
   Incident command / BCP
           |
  Git + CI + registry + identity
           |
  Argo CD / Kubernetes / network
           |
  Stateful DB + secrets + storage
           |
  Traffic routing + user verification
           |
  Independent telemetry and evidence
```

Model independent and correlated failure domains: process, pod, node, AZ, region, cloud account, Git provider, identity provider, secrets provider and external dependencies. Include shared services that can make a multi-region architecture fail together.

## 4. Game-day operating model

**Hypothesis:** a specific fault should not violate a defined business SLO, or should recover within an approved RTO.  
**Steady state:** baseline error rate, latency, successful transactions, Argo CD reconciliation delay, replica lag and service availability.  
**Injection:** a narrowly scoped, reversible fault with an owner, maximum duration and independent safety monitor.  
**Observation:** compare steady state against fault-period and recovery metrics.  
**Recovery:** execute the documented runbook and verify user-facing transactions, not merely healthy Pods.  
**Learning:** publish evidence, corrective actions and next drill.

### Safety guardrails

- Confirm cluster context, namespace, ownership, workload labels, approvals and rollback before touching resources.
- Prefer simulation and tabletop exercises before real injection; use disposable resources and synthetic data.
- Predefine stop thresholds for errors, latency, data loss, blast radius and unexpected dependencies.
- Keep a safety officer independent from the injector; stop immediately if observability is lost.
- Do not test database failover without fencing guarantees, or delete the only viable backup.
- Never use production secrets or tokens in captured evidence.

## 5. Scenario selection and maturity ladder

| Level | Exercise | Required proof |
|---|---|---|
| 0 | Tabletop and dependency mapping | Owners, runbooks, communications |
| 1 | Synthetic endpoint failure | Alerting, containment, recovery |
| 2 | Disposable Pod/node failure | Placement and SLO evidence |
| 3 | Isolated dependency outage | Graceful degradation and retry |
| 4 | Clean-room restore | Verified data and GitOps bootstrap |
| 5 | Staging regional recovery | Fencing, cutover and failback |
| 6 | Approved production resilience testing | Separate formal change and executive risk approval |

Advance only when the prior level is demonstrably safe and repeatable.

## 6. Preflight for hands-on labs

```bash
export LAB_NS=gitops-chaos-lab
export LAB_DEPLOY=synthetic-api
export LAB_HEALTH_URL=https://lab.example.invalid/health
export LAB_RESTORE=lab093-restore
kubectl config current-context
kubectl cluster-info
kubectl -n "$LAB_NS" get deploy,pods,svc -o wide
kubectl -n argocd get applications -o wide
```

The names and URLs above are placeholders. Use an isolated cluster, approved synthetic application, bounded test window, and explicit rollback procedure. Tools such as Chaos Mesh or Litmus may be used only after version, CRD, RBAC and namespace scope are reviewed.

## 7. Hands-on labs (18)

For **every** lab: write the hypothesis, owner, blast radius, steady-state baseline, abort condition, observation timestamps, expected result, recovery step and evidence location. The commands below are inspection/verification aids; fault creation requires an approved staging-specific implementation.

### Lab 01 — Establish recovery baseline

**Exercise:** Capture healthy application SLI, reconciliation lag, Git revision and recovery timestamps.

```bash
kubectl config current-context
kubectl -n argocd get applications -o wide
kubectl -n "$LAB_NS" get deploy,pods,svc -o wide
```

**Acceptance:** Baseline recorded before faults. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 02 — Dependency graph tabletop

**Exercise:** Map Git, registry, Argo CD, DNS, IdP, KMS, CNI, CSI, database and traffic manager.

```bash
kubectl -n argocd get deployments,statefulsets
kubectl get storageclass
```

**Acceptance:** Critical path and owners signed. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 03 — Game-day roles

**Exercise:** Assign incident commander, safety officer, observer, DB owner, platform operator and communications owner.

```bash
date -u +%FT%TZ
kubectl config get-contexts
```

**Acceptance:** RACI and stop word documented. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 04 — Synthetic service probe

**Exercise:** Run read and write synthetic checks against a disposable endpoint with bounded frequency.

```bash
curl --fail --silent --show-error --max-time 5 "$LAB_HEALTH_URL"
```

**Acceptance:** Known-good business transaction. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 05 — Git outage simulation

**Exercise:** In an isolated test Argo CD instance, revoke access to a mock Git endpoint; do not change real production credentials.

```bash
kubectl -n argocd get applications -o wide
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-repo-server
```

**Acceptance:** Staleness detected and recovered. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 06 — Registry outage simulation

**Exercise:** Point a disposable deployment at an intentionally unavailable test image; inspect events; restore original image digest.

```bash
kubectl -n "$LAB_NS" describe deployment "$LAB_DEPLOY"
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -20
```

**Acceptance:** Image pull alert and safe rollback. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 07 — Controller pod failure

**Exercise:** In a disposable Argo CD installation with verified redundancy, disrupt one pod through approved fault tool.

```bash
kubectl -n argocd get pods -o wide
kubectl -n argocd get deploy,sts,pdb
```

**Acceptance:** Queue and recovery measurements. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 08 — DNS failure tabletop

**Exercise:** Model resolver outage without altering cluster DNS; identify alternative checks and fail-safe routing.

```bash
kubectl -n kube-system get deploy coredns
kubectl -n "$LAB_NS" get svc,endpointslices
```

**Acceptance:** DNS dependency and contingency. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 09 — Network partition model

**Exercise:** Use a sandbox-only network-policy experiment with an allowlist and explicit automatic cleanup.

```bash
kubectl -n "$LAB_NS" get networkpolicy -o yaml
kubectl -n "$LAB_NS" get pods -o wide
```

**Acceptance:** Scope and recovery proven. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 10 — Node-loss rehearsal

**Exercise:** Drain only a disposable node in an isolated lab after verifying placement and PDBs; do not touch shared nodes.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
kubectl -n "$LAB_NS" get pdb,pods -o wide
```

**Acceptance:** Workload rescheduled and SLI restored. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 11 — Admission outage tabletop

**Exercise:** Simulate a webhook timeout on paper and test a disposable policy controller in a separate lab.

```bash
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
```

**Acceptance:** Failure policy understood. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 12 — Secrets dependency outage

**Exercise:** Use a mock secret backend or expired synthetic secret, not real credential rotation.

```bash
kubectl -n "$LAB_NS" get externalsecret
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -20
```

**Acceptance:** Secret refresh and alert verified. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 13 — Capacity saturation

**Exercise:** Run a bounded load test against a disposable deployment; stop before quota or SLO guardrails are exceeded.

```bash
kubectl -n "$LAB_NS" top pods
kubectl -n "$LAB_NS" get hpa,resourcequota
```

**Acceptance:** Threshold alert and auto-recovery. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 14 — Backup restore game day

**Exercise:** Restore a namespace-scoped synthetic Velero backup to a fresh destination; verify objects and checksums.

```bash
velero backup get
velero restore get
velero restore describe "$LAB_RESTORE" --details
```

**Acceptance:** Restore success independently verified. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 15 — Database writer fencing tabletop

**Exercise:** Use synthetic data and simulated authority tokens; prove that a second writer cannot be promoted before old writer fencing.

```bash
kubectl -n "$LAB_NS" get pods,svc,endpointslices
```

**Acceptance:** Single-writer invariant recorded. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 16 — Regional failover dry run

**Exercise:** Rebuild disposable service in secondary lab cluster, validate Git revision and data consistency; no live DNS changes.

```bash
kubectl config get-contexts
kubectl -n "$LAB_NS" get deployments -o wide
```

**Acceptance:** Measured recovery time and data loss. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 17 — Failback rehearsal

**Exercise:** Reconcile authoritative state and practice reverse traffic plan in staging; do not create dual writers.

```bash
git rev-parse HEAD
kubectl -n argocd get applications -o wide
```

**Acceptance:** Reversible, approved failback. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

### Lab 18 — Blind game day and assessment

**Exercise:** Safety officer selects one approved scenario, observers timestamp detection, mitigation, restore, communications and score.

```bash
date -u +%FT%TZ
kubectl -n "$LAB_NS" get pods,svc -o wide
```

**Acceptance:** Evidence-backed 100-point acceptance. **Rollback/abort:** stop any fault at the first unexpected scope or SLO breach, revert only the disposable test change, and re-run the business transaction.

## 8. Twenty troubleshooting scenarios

| # | Failure | Initial evidence | Response and recovery gate |
|---|---|---|---|
| 1 | Git provider unreachable | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 2 | Git mirror lag | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 3 | OCI registry unavailable | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 4 | Image signature mismatch | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 5 | Argo CD repo-server OOM | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 6 | Application controller backlog | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 7 | Redis unavailable | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 8 | Cluster API throttling | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 9 | CoreDNS failure | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 10 | Ingress certificate expiry | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 11 | External Secrets sync failure | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 12 | KMS access denied | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 13 | Admission webhook timeout | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 14 | AZ node eviction | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 15 | Storage volume attach failure | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 16 | Database replication lag | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 17 | Unfenced old primary | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 18 | Backup restore incomplete | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 19 | Telemetry outage | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |
| 20 | Secondary region capacity exhausted | Capture affected SLI, events, logs, revision and dependency health | Isolate blast radius; follow owner-approved runbook; prove user transaction and no data regression |

## 9. Eight production-grade runbooks

### RB-01 — Game-day authorization

**Trigger and execution:** Approve hypothesis, blast radius, fault owner, rollback, abort thresholds and evidence store; announce start and stop window.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-02 — Safety stop

**Trigger and execution:** On unknown context, production impact, data inconsistency, SLO breach or missing owner: halt injection, revert isolated changes, confirm user impact and escalate.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-03 — Git and registry failure

**Trigger and execution:** Check source reachability, pinned revision and digest; hold new releases, preserve running service, recover trusted mirror and validate provenance.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-04 — Argo CD degradation

**Trigger and execution:** Inspect controller/repo-server metrics, queues and events; restore capacity or connectivity and verify convergence without mass pruning.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-05 — Cluster and network impairment

**Trigger and execution:** Assess API, CNI, DNS, ingress and quotas; preserve control-plane evidence, use provider-supported recovery and run synthetic tests.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-06 — Secrets and identity outage

**Trigger and execution:** Validate IdP, KMS, workload identity and external secrets; recover approved DR credentials without logging plaintext.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-07 — Data recovery and fencing

**Trigger and execution:** Identify last consistent restore point, require old-writer isolation before promotion, verify transaction invariants and measured RPO.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

### RB-08 — Region failover and failback

**Trigger and execution:** Gate traffic cutover on verified service and data health, monitor clients, re-seed old region and re-establish a single authoritative writer.

**Evidence and closeout:** record incident/change ID, operator, UTC timestamps, approved command history, SLO changes, abort decisions, restored business transaction, owner signoff and follow-up action.

## 10. Incident communications and roles

| Role | Responsibility |
|---|---|
| Incident commander | Declares event, sets priority, authorizes recovery strategy |
| Safety officer | Independently monitors stop conditions and can halt test |
| Platform lead | Kubernetes, Argo CD, CI and artifact recovery |
| Database lead | Data integrity, restore point, fencing and single-writer proof |
| Security lead | Identity, secret recovery, approvals and audit |
| Communications lead | Stakeholder updates, status timeline and external coordination |
| Observer/scribe | Evidence, metrics, timestamps and corrective actions |

Use a fixed update cadence agreed during the preflight. Do not report “recovered” until a synthetic business transaction passes and relevant data invariants are verified.

## 11. Recovery metrics

- **Detection time:** first fault to actionable alert.
- **Mitigation time:** first actionable alert to contained customer impact.
- **Observed RTO:** declared incident start to verified restoration of the agreed service.
- **Observed RPO:** last recoverable committed transaction to failure boundary.
- **Reconciliation recovery:** desired Git revision to stable, healthy application state.
- **Error budget consumed:** failed requests over the measured window, using the service's approved SLI.
- **Operational readiness:** percentage of critical recovery steps successfully executed without undocumented intervention.

Do not substitute a green Pod or Argo CD Healthy status for an end-to-end service SLI.

## 12. Acceptance scorecard (100 points)

| Category | Points |
|---|---:|
| BCP scope, owners and dependency inventory | 15 |
| Hypotheses, baselines and safe blast radius | 15 |
| Detection, telemetry and synthetic checks | 15 |
| Fault containment and recovery execution | 15 |
| Backup, data integrity and writer fencing | 15 |
| Regional failover/failback evidence | 10 |
| Incident command and communications | 5 |
| RCA, remediation and retest plan | 10 |
| **Total** | **100** |

**Pass threshold:** at least 90/100 and all mandatory gates: approved isolated scope, working stop mechanism, verified application transaction, no plaintext secret exposure, no dual writer, measured RPO/RTO, and documented rollback.

## 13. Game-day evidence template

```text
Game-day ID / date / environment:
Business service and SLO:
Hypothesis and injected fault:
Change approval / safety officer:
Baseline and abort thresholds:
Start UTC / detection UTC / mitigation UTC / recovery UTC:
Observed RPO / observed RTO:
Argo CD revision / application health:
Synthetic transaction result:
Database consistency / fencing proof:
Rollback executed?:
Communications timeline:
Pass/fail and score:
Corrective actions / owners / due dates:
Next retest:
```

## 14. Cleanup and definition of done

Remove only explicitly identified disposable chaos resources after verifying the test application's steady state, authoritative database writer, GitOps revision and user-facing health. Preserve the approved evidence packet and audit trail. A game day is complete only when findings are assigned owners and deadlines, the recovery playbook is updated, and a follow-up test is scheduled.

**Next:** Chapter 094 — Enterprise GitOps Operational Readiness, Resilience Testing and Recovery Automation.
