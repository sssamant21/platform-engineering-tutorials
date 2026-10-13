# Chapter 099 — Production Change Management and SRE Runbooks

**Track:** Kubernetes Administration · **Part 20 — Advanced Platform Engineering and Production Operations**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SREs, Kubernetes administrators, platform engineers, incident commanders, change approvers  
**Prerequisites:** Chapters 011–020, 041–050, 071–098; kubectl, PowerShell, Git, approved GitOps workflow, observability dashboards, and a disposable staging cluster.

## Learning outcomes

Classify change risk, prepare evidence-based change requests, design safe deployment waves, perform production preflight checks, observe rollout health, decide rollback versus forward-fix, coordinate incident response, author actionable runbooks, and conduct post-change reviews. Practice the workflow in 16 hands-on labs without making unapproved production changes.

## 1. Production change management principles

A production change is any intentional modification that can affect availability, latency, data integrity, security, capacity or cost. Examples include Kubernetes upgrades, node pool changes, storage modifications, policy enforcement, network changes, application rollouts and operator upgrades.

**A successful `kubectl rollout status` means a Deployment rollout completed according to Kubernetes readiness rules. It does not prove end-to-end customer health.** Validate service-level indicators and dependencies separately.

The operating cycle:

```text
Request → risk assessment → design/review → preflight → approval
  → deploy/canary → observe → promote or rollback
  → verify → close → learn
```

Distinguish **standard** (preapproved low-risk), **normal** (reviewed) and **emergency** (time-critical with retrospective review) changes according to organizational policy. Never use emergency classification merely to bypass routine controls.

## 2. Change classification and risk scoring

Assess blast radius, reversibility, state/data impact, customer criticality, timing, dependency count, prior test evidence, security exposure and operational familiarity.

| Change | Typical risk | Special control |
|---|---|---|
| Stateless Deployment with canary | Lower, if proven | SLO-based promotion |
| Node group right-sizing | Medium | PDB/capacity validation |
| CNI or DNS configuration | High | Network recovery plan |
| CRD/operator upgrade | High | API compatibility and conversion plan |
| StatefulSet/storage migration | High | Backup/restore, data integrity |
| Control-plane upgrade | High | Supported version-skew and provider runbook |
| RBAC/admission policy enforcement | Medium–high | Positive/negative authorization tests |

These are examples, not universal risk ratings. Document who may approve each risk class and what independent review is required.

## 3. Lab 01 — Establish the change boundary

Capture cluster, cloud account/subscription/project, namespace, application owner, maintenance window, on-call coverage and SLO.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get deployments,statefulsets,daemonsets -A
kubectl get pdb -A
kubectl get events -A --sort-by=.lastTimestamp
```

**Acceptance:** target and rollback target are unambiguous. Stop if the context, identity, environment or ownership is uncertain.

## 4. Lab 02 — Write a complete change request

Use this template:

```text
Change ID:
Title:
Owner / technical reviewer / approver:
Environment, cluster and namespace:
Business purpose:
Scope and excluded systems:
Current state / desired state:
Risk and blast radius:
Dependencies and customer impact:
Implementation window (time zone):
Preflight checks:
Validation and SLO thresholds:
Rollback trigger and latest safe rollback time:
Rollback procedure and data implications:
Communication / escalation:
Evidence and audit links:
```

Include Git revision, image digest, IaC plan, affected Kubernetes resources, deployment method, expected duration and decision checkpoints. Avoid vague acceptance statements such as "looks good."

## 5. Lab 03 — Preflight health and capacity

```powershell
kubectl get nodes
kubectl top nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get pdb -A
kubectl get hpa -A
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp
```

Metrics Server is required for `kubectl top`. Check p95 latency, error rate, traffic, queue depth, replica availability, disk and memory pressure, API server responsiveness, backup freshness and ongoing incidents. Identify active change freezes and other deployments.

**Stop condition:** unresolved service degradation, insufficient capacity, missing rollback artifacts, failed backup validation or unavailable incident response coverage.

## 6. Lab 04 — Validate manifests and configuration

```powershell
kubectl diff -f .\manifests\
kubectl apply --dry-run=server -f .\manifests\
kubectl auth can-i patch deployments -n app-staging
```

Paths are examples; create the manifests directory first. Server dry-run may invoke admission webhooks and requires access to the target cluster; it does not guarantee runtime success. Validate schema, policy, image provenance, immutable fields, RBAC and namespace selection. In GitOps environments, use PR validation and apply approved changes through the reconciler rather than direct writes.

## 7. Lab 05 — Plan deployment waves and blast radius

Define canary cohort, traffic split, success criteria, soak duration and escalation owner. Start with a disposable staging application, then progress through canary and wider rollout only when approved. For high-risk infrastructure changes, separate failure domains (nodes, zones, regions or clusters).

```powershell
kubectl get deployments -n app-staging
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pdb -n app-staging
```

Do not infer traffic percentages from replica counts alone: routing, session affinity and request distribution may differ. Use service mesh/ingress traffic weighting where available and tested.

## 8. Lab 06 — Safe Deployment rollout

Create a disposable HTTP Deployment with readiness/startup probes and at least two replicas. Apply a reviewed image or configuration change.

```powershell
kubectl rollout status deployment/demo-api -n app-staging --timeout=180s
kubectl rollout history deployment/demo-api -n app-staging
kubectl get pods -n app-staging -o wide
kubectl describe deployment demo-api -n app-staging
```

These commands require a pre-created `app-staging` namespace and `demo-api` Deployment. Record generation, revision, ready replicas, events and image digest. Confirm actual application probes and synthetic transactions pass.

## 9. Lab 07 — Verify application SLOs

Before promotion, compare baseline and canary:
- Availability and HTTP error rate.
- p50/p95/p99 latency.
- Request throughput and saturation.
- CPU throttling, memory, restarts and Pending Pods.
- Database connection errors, queue lag and downstream health.
- Customer-critical synthetic transactions.

Define explicit abort thresholds and measurement windows in the change request; do not invent thresholds during an incident. Consider low traffic, seasonality and sample size before interpreting canary data.

## 10. Lab 08 — Rollback and forward-fix decision

Rollback is appropriate when the prior version is known safe and reverting does not break data/schema compatibility. Forward-fix may be safer when an irreversible migration, data transformation or external side effect has occurred.

```powershell
kubectl rollout history deployment/demo-api -n app-staging
kubectl rollout undo deployment/demo-api -n app-staging
kubectl rollout status deployment/demo-api -n app-staging --timeout=180s
```

Use the imperative rollback **only** for disposable or explicitly authorized environments. In GitOps, revert the offending commit through the approved emergency process; otherwise reconciliation may reapply the bad revision. For StatefulSets, database schema changes and CRDs, `rollout undo` may not be sufficient or available.

**Acceptance:** service health and data integrity are verified after rollback, not merely the Pod revision.

## 11. Lab 09 — Node maintenance and draining

```powershell
kubectl get pdb -A
kubectl describe node <node-name>
kubectl get pods -A -o wide
```

In a disposable cluster, practice a controlled drain only after confirming redundancy and eviction budgets:

```powershell
kubectl cordon <test-node-name>
kubectl drain <test-node-name> --ignore-daemonsets --delete-emptydir-data --timeout=5m
kubectl uncordon <test-node-name>
```

**Warning:** `--delete-emptydir-data` discards local ephemeral data, and drains can interrupt applications. Never run this on a production node as a tutorial exercise. Understand DaemonSets, static Pods, local storage, topology spread and PDB behavior before approving real maintenance.

## 12. Lab 10 — Stateful change readiness

For database/storage changes, add:
- Verified recoverable backup and restore point.
- Replication lag and failover ownership.
- Storage capacity, IOPS and throughput headroom.
- Data migration order and application compatibility.
- Fencing/split-brain prevention when relevant.
- Tested rollback boundaries and recovery time.
- Post-change consistency checks.

```powershell
kubectl get statefulsets,pvc -A
kubectl get storageclass
kubectl get pods -A -o wide
```

Do not treat a healthy StatefulSet as proof that application data is consistent. Prefer database-native validation.

## 13. Lab 11 — Network, DNS and admission changes

High-blast-radius changes require independent access paths and narrowly scoped tests. For NetworkPolicy, verify permitted and blocked traffic. For CoreDNS/CNI changes, verify resolution, service routing and external connectivity. For admission changes, test compliant and noncompliant manifests before enforcement.

```powershell
kubectl get networkpolicy -A
kubectl get pods -n kube-system
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get events -A --sort-by=.lastTimestamp
```

Never disable all admission controls or open all network traffic as a routine rollback.

## 14. Lab 12 — Change communications and command roles

For a planned high-risk change, assign:
- Change lead: implementation and stop/go decisions.
- Technical operator: executes approved steps.
- Independent verifier: validates SLOs and safety gates.
- Incident commander: takes over if the change becomes an incident.
- Communications lead: publishes stakeholder updates.
- Scribe: records timeline and decisions.

Example update:

```text
Change: CHG-1234
Window: 20:00–21:00 local time
Scope: staging Kubernetes node pool
Current phase: preflight passed / rollout underway
Customer impact: none observed
Next checkpoint: 20:20
Rollback trigger: defined SLO breach or capacity failure
Owner: platform on-call
```

Use actual timestamps, time zones and evidence in live communications.

## 15. Lab 13 — Incident during a change

In disposable staging, intentionally deploy a bad Service selector or failed readiness probe. Confirm alerting, stop the rollout, declare an incident if impact crosses the agreed threshold, and revert through Git.

Record detection, triage, command transfer, mitigation, rollback, service verification and closure. Preserve logs, events, Git revision, image digest and application metrics. Do not change multiple unrelated variables during diagnosis.

## 16. Lab 14 — Write a reusable SRE runbook

Runbook template:

```text
Title / owner / last review date
Trigger and severity
Symptoms and user impact
Prerequisites and required permissions
Safety warnings and stop conditions
Diagnosis commands and expected interpretation
Decision tree and escalation contacts
Mitigation and rollback commands
Data integrity and security checks
Post-recovery validation
Evidence to capture
Known limitations / references
```

A runbook must specify what the operator should expect from each command and what to do if the result differs. Avoid unexplained copy-paste commands, broad wildcards and unbounded delete operations.

## 17. Lab 15 — Game day and tabletop review

Simulate these scenarios without impacting production:
1. Deployment rollout passes but p95 latency worsens.
2. Node drain is blocked by PDBs.
3. GitOps restores an undesired manifest after manual rollback.
4. CRD/operator upgrade leaves a conversion webhook unavailable.
5. Stateful change completes but replication/data checks fail.

For each, record decision owner, stop condition, diagnostic evidence, rollback/forward-fix choice and recovery outcome. Evaluate whether the runbook worked for an engineer who did not author it.

## 18. Lab 16 — Final change acceptance

| Control | Required evidence |
|---|---|
| Authorization | Change ID, reviewer and approval |
| Scope | Cluster/context, namespace, revision, resources |
| Readiness | Baseline SLO, capacity, backups and dependencies |
| Deployment | GitOps sync or rollout evidence |
| Monitoring | Latency, errors, throughput, saturation |
| Recovery | Tested rollback and latest safe decision point |
| Communications | Timestamped updates and escalation |
| Verification | Application, security and data checks |
| Closure | Outcome, exceptions and follow-up owners |

**Acceptance checklist:**
- [ ] Change classification and blast radius reviewed.
- [ ] Preflight completed and stop conditions understood.
- [ ] Implementation and rollback steps independently reviewed.
- [ ] Canary/wave promotion tied to observed SLOs.
- [ ] On-call and stakeholder communications exercised.
- [ ] Failure simulation detected and mitigated in staging.
- [ ] Post-change application and data validation completed.
- [ ] Audit trail, timeline and lessons learned captured.
- [ ] Runbook independently tested.
- [ ] Runtime evidence and technical review recorded.

## 19. Production runbook: change failure response

1. **Stop** promotion and freeze related changes.
2. **Assess** user impact, severity and safety of rollback.
3. **Stabilize** by restoring known-good behavior or isolating the failing component.
4. **Communicate** incident ownership, impact and next update time.
5. **Diagnose** with metrics, logs, events, traces and recent changes.
6. **Recover** through approved rollback or forward-fix, preserving data integrity.
7. **Verify** service SLOs, dependencies, security and capacity.
8. **Close** only after monitoring confirms sustained recovery.
9. **Review** timeline, contributing factors, detection gaps and prevention actions without blame.

## 20. Cleanup and handoff

Remove disposable test workloads through their owning GitOps repository. Confirm no node remains cordoned, no test-only routing/policy remains active and no temporary resources incur ongoing cost. Preserve evidence and update runbook ownership/review dates. Never perform production drains, rollback or policy changes solely to complete these labs.

## Production takeaways

Safe change management is an engineering control, not a formality. A change is successful only when the intended outcome is achieved, the service remains within its reliability targets, security and data integrity are preserved, and operators retain a tested path to recovery.

**Draft status:** examples and labs have not been runtime-validated or independently reviewed.

**Next:** Chapter 100 — Advanced Production Recovery Project, the final capstone for Part 20.
