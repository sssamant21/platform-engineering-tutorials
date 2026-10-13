# Chapter 105 — Kubernetes Administrator and SRE Final Assessment

**Track:** Kubernetes Administration · **Part 21 — Final Enterprise Kubernetes Capstone (Final Chapter)**  
**Status:** Draft — assessment has not been administered, runtime-validated or independently reviewed  
**Audience:** Kubernetes administrators, SREs, platform engineers, DBREs and technical reviewers  
**Prerequisites:** Chapters 001–104; approved disposable lab clusters, GitOps, monitoring, an HA stateful application, verified backups and an independent assessor.

## Purpose

This is the final, **performance-based** assessment for the complete 105-chapter Kubernetes Administration and SRE learning path. It measures the ability to design, administer, troubleshoot, secure, upgrade and recover Kubernetes platforms using evidence-based engineering practice.

**Publication of the curriculum does not mean an individual has passed this assessment.** Completion requires an actual lab run, evidence submission and independent review.

## 1. Assessment contract

**Recommended assessment window:** 2 days of hands-on work plus independent review. Adjust for lab infrastructure and candidate experience.

**Scoring:** 100 points total, with a recommended passing threshold of **80/100**, subject to all critical safety gates. A candidate scoring 90 points but violating a critical data-safety rule does not pass.

**Critical safety gates:**
- No production-impacting fault injection without explicit authorization.
- No deletion of live data/PVCs/backups or unsafe removal of finalizers.
- No exposure of secrets, unrestricted privileged access or permanent policy bypass.
- No split-brain database writes or unsafe primary promotion.
- No false claims of completed tests, backups, restores or incident recovery.
- No irreversible control-plane change without a supported recovery plan.

Use only authorized nonproduction resources. Assessors should record a **Fail** for any critical safety violation and halt unsafe exercises.

## 2. Assessment domains and weights

| Domain | Points | Demonstrated capability |
|---|---:|---|
| Architecture, cluster build and IaC | 12 | Reproducible, resilient cluster design |
| Workloads, scheduling and capacity | 10 | Controllers, probes, PDBs, topology, scaling |
| Networking, DNS and ingress | 10 | CNI, Services, TLS, policies, diagnosis |
| Security and governance | 12 | IAM/RBAC, workload identity, admission, GitOps |
| Storage and stateful reliability | 12 | CSI, replication, backups, PITR, fencing |
| Observability and SLOs | 10 | Metrics, logs, traces, alerting, error budgets |
| Incident response and troubleshooting | 14 | Evidence-driven mitigation and communication |
| Upgrades, DR and production operations | 12 | Version skew, recovery, change control |
| Documentation, review and handoff | 8 | Runbooks, reproducibility, ownership |
| **Total** | **100** | |

## 3. Candidate lab environment

Provision a disposable cluster based on Chapter 101, the HA PostgreSQL exercise from Chapter 102, and the incident/upgrade simulations from Chapters 103–104. A second test cluster is recommended for fleet and DR work.

Required components:
- At least two worker nodes; multiple zones where supported.
- Dedicated test namespaces and resource quotas.
- A stateless HTTP application with synthetic probes.
- A supported PostgreSQL operator and disposable database.
- A CSI driver with recoverable storage and verified backups.
- GitOps controller, monitoring and alert delivery.
- Scoped identities for administrator, developer and auditor roles.
- IaC repository and evidence storage.

If a feature is unavailable (for example, GPU or multi-zone topology), mark that subtest **Not executed** and assess using a documented alternate scenario. Do not silently award points for untested behavior.

## 4. Exercise 01 — Architecture and failure-domain review (6 points)

Produce an architecture diagram identifying control plane, nodes, availability zones, CNI, DNS, ingress, CSI, identities, GitOps, backups and observability.

Explain:
1. Why a single cluster may or may not meet the required SLO.
2. How workloads survive one node failure.
3. How stateful data is protected.
4. What changes for EKS, AKS, GKE or self-managed Kubernetes.
5. What cannot be guaranteed by Kubernetes alone.

**Pass evidence:** design decisions, blast-radius analysis, cost/risk tradeoffs and review notes.

## 5. Exercise 02 — Reproducible cluster build (6 points)

Provision a disposable cluster from reviewed IaC. Pin provider and module versions, secure state and document cloud account, region and cost controls.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -A
```

**Pass evidence:** IaC plan, applied revision, cluster inventory, node readiness and documented cleanup plan. Do not publish credentials or state secrets.

## 6. Exercise 03 — Workload lifecycle and probes (5 points)

Deploy a test HTTP application with startup, readiness and liveness probes. Demonstrate rollout, failed readiness, safe rollback and restored synthetic request success.

```powershell
kubectl get deployment,replicaset,pods -n assessment-lab
kubectl rollout history deployment/demo-api -n assessment-lab
kubectl rollout status deployment/demo-api -n assessment-lab --timeout=180s
kubectl get events -n assessment-lab --sort-by=.lastTimestamp
```

The namespace and Deployment must exist before execution. In GitOps, rollback through an approved commit rather than relying on imperative undo.

## 7. Exercise 04 — Scheduling, capacity and disruption (5 points)

Diagnose a deliberately Pending Pod caused by a bad selector or taint mismatch. Demonstrate requests/limits, quotas, topology spread and PDB interpretation. Assess safe node maintenance without violating availability.

```powershell
kubectl get pods -n assessment-lab -o wide
kubectl get pdb -A
kubectl get nodes --show-labels
kubectl describe pod <pending-test-pod> -n assessment-lab
```

**Pass evidence:** correct root cause, scoped remediation and restored placement. Do not bypass PDBs or force a drain.

## 8. Exercise 05 — Service networking and DNS (5 points)

Diagnose a Service selector/EndpointSlice mismatch and a separate test DNS resolution problem. Verify ClusterIP behavior, ingress TLS, allowed service paths and network-policy enforcement.

```powershell
kubectl get svc,endpointslice,ingress -n assessment-lab
kubectl get networkpolicy -A
kubectl get pods -n kube-system
```

**Pass evidence:** working HTTPS transaction, corrected endpoints and both positive and negative access-control tests.

## 9. Exercise 06 — Network isolation and incident diagnosis (5 points)

Apply a scoped test NetworkPolicy that denies an unauthorized flow while preserving approved application dependencies. Diagnose using Pod events, CNI flow logs or equivalent telemetry.

**Pass evidence:** documented traffic matrix, allowed/denied tests and proof the CNI enforces policy. A timeout alone does not establish why traffic failed.

## 10. Exercise 07 — Identity, RBAC and least privilege (6 points)

Configure test administrator, developer and auditor access. Verify developer permissions are namespace-scoped and that the auditor cannot modify workloads or read sensitive Secrets.

```powershell
kubectl auth can-i get pods -n assessment-lab
kubectl auth can-i create deployments -n assessment-lab
kubectl auth can-i get secrets -n assessment-lab
kubectl get rolebindings -n assessment-lab
```

Execute authorization tests under the relevant test identities, not merely under cluster-admin. **Pass evidence:** allowed and denied operations, identity provenance and absence of static cloud keys in Pods.

## 11. Exercise 08 — Admission and supply-chain policy (6 points)

Demonstrate Pod Security Admission or an approved policy engine rejecting a deliberately privileged test manifest while allowing a compliant workload. Validate image digest pinning, registry allowlisting and secret handling.

**Pass evidence:** admission results, scoped exceptions, policy revision and documented webhook outage behavior. No permanent bypasses.

## 12. Exercise 09 — GitOps drift and controlled change (6 points)

Introduce a safe staging-only drift, detect it, and restore the intended Git revision. Demonstrate review/approval, change scope, rollback and audit trail.

**Pass evidence:** pull request or change record, reconciler status, revision before/after, synthetic service verification and evidence of controlled permissions.

## 13. Exercise 10 — CSI, persistent storage and restore (6 points)

Provision a disposable PVC, write test data, restart the workload and verify persistence. Restore from a supported snapshot or database-native backup to a separate target.

```powershell
kubectl get storageclass
kubectl get csidrivers
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp
```

**Pass evidence:** durable data and checksum/record-count verification. A PVC Bound status alone is insufficient.

## 14. Exercise 11 — HA PostgreSQL and data safety (6 points)

Using a supported operator:
- Identify primary and replicas.
- Inspect replication state and lag.
- Explain synchronous versus asynchronous durability.
- Demonstrate a safe planned switchover in staging.
- Verify one writable primary, client reconnect and committed test data.
- Restore a backup/PITR copy to an isolated instance.

On the primary:

```sql
SELECT pg_is_in_recovery();
SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

**Pass evidence:** role history, fencing guarantee, transaction checks and measured RPO/RTO. Any split-brain risk is an immediate stop.

## 15. Exercise 12 — SLOs, observability and alert acceptance (10 points)

Establish baseline request success, latency, throughput and saturation. Inject a safe application fault and prove an actionable alert reaches the correct on-call owner.

Required:
- Dashboard with cluster, namespace and workload identity.
- Error-budget/SLO interpretation.
- Metrics, logs, events and trace correlation where available.
- Synthetic probe before, during and after fault.
- Alert acknowledgement and runbook link.

**Pass evidence:** timestamped detection and recovery, not just a screenshot of an alert rule.

## 16. Exercise 13 — Complex incident command (8 points)

Run a controlled compound incident: a bad Service selector plus a Pending test Pod, optionally with one degraded non-primary database replica. The candidate must:
1. Declare severity and establish incident roles.
2. Freeze unrelated changes.
3. Gather evidence and prioritize customer impact.
4. Choose safe mitigation and communicate status.
5. Restore service and verify SLOs/data integrity.
6. Record timeline and contributing factors.

**Pass evidence:** incident notes, decisions, commands, metrics and blameless follow-ups. Assessors should not award full points for guess-based remediation without evidence.

## 17. Exercise 14 — Kubernetes upgrade and recovery plan (7 points)

Produce a source-to-target compatibility matrix covering Kubernetes, kubelet, CNI, CSI, DNS, admission, GitOps and database operator. Rehearse a provider-supported staging upgrade or a controlled canary node pool update.

**Pass evidence:** preflight, change approval, version skew validation, PDB/capacity checks, monitoring and post-upgrade application tests. Explain why managed control-plane downgrades may not be available.

## 18. Exercise 15 — Disaster recovery and failover (5 points)

Demonstrate a restore to a separate environment and, where feasible, test-only traffic cutover to a secondary cluster. Record RTO/RPO against predefined objectives, DNS/client behavior and database fencing considerations.

**Pass evidence:** restored application transactions, data integrity and clear failure-domain boundaries. A second cluster without recoverable data is not a complete DR solution.

## 19. Exercise 16 — Operational documentation and handoff (8 points)

Submit:
- Architecture and dependency diagram.
- IaC/GitOps source revisions.
- Change and incident records.
- SLO dashboard and alert acceptance.
- Backup/restore evidence.
- Upgrade and DR runbooks.
- Security/identity review.
- Cost baseline and cleanup record.
- Known risks and remediation owners.

Runbooks must contain trigger, safety warnings, diagnosis, expected results, mitigation, rollback, escalation and post-recovery validation. Independent reviewers should be able to reproduce the key checks.

## 20. Scenario-based oral review

The assessor selects at least five scenarios and asks for diagnosis, stop conditions and recovery reasoning:

1. Pods Ready, but user requests time out.
2. A node is Ready, but GPU workloads cannot initialize CUDA.
3. PostgreSQL replicas lag and WAL storage fills.
4. A PDB blocks a node drain during upgrade.
5. A CRD conversion webhook is unavailable.
6. GitOps reverts a manual emergency fix.
7. A PVC cannot attach after a zone outage.
8. A cluster API is unavailable but existing traffic continues.
9. An admission policy blocks all new application Pods.
10. A regional failover risks two writable database primaries.
11. A new Kubernetes minor version breaks a CSI add-on.
12. Autoscaling increases node count without reducing latency.

The candidate must distinguish symptoms from evidence and avoid destructive shortcuts.

## 21. Scoring rubric

| Rating | Definition |
|---|---|
| Full credit | Correct, reproducible, evidence-backed, safe and independently verifiable |
| Partial credit | Mostly correct but missing noncritical evidence, coverage or clarity |
| No credit | Not executed, incorrect or unsupported claims |
| Critical failure | Unsafe operation, data integrity violation, secret exposure or falsified evidence |

**Recommended outcome rules:**
- **Pass:** at least 80/100 and every critical safety gate satisfied.
- **Conditional re-assessment:** 70–79/100 with no critical safety failure; retest failed domains.
- **Not yet passed:** below 70/100 or any critical safety failure.
- **Not assessed:** labs/evidence not executed or reviewed.

These thresholds are suggested for this tutorial, not an external certification standard.

## 22. Candidate evidence template

```text
Candidate ID:
Assessment date (UTC):
Cluster IDs / lab environment:
Assessor:
Git revision:
Exercise number:
Objective:
Commands or change steps:
Expected outcome:
Actual outcome:
Evidence links:
Observed SLO/RTO/RPO:
Safety checks:
Result: Pass / Partial / Fail / Not executed
Reviewer notes:
```

Preserve redacted logs, Git SHAs, cloud operation IDs, dashboards and database consistency checks. Never include tokens, private keys or real customer data.

## 23. Final readiness checklist

- [ ] Cluster built reproducibly with approved IaC.
- [ ] Workload scheduling and disruption controls demonstrated.
- [ ] Networking, DNS, TLS and isolation verified.
- [ ] Identity, RBAC and admission negative tests passed.
- [ ] GitOps drift and rollback rehearsed.
- [ ] Persistent data restored and verified.
- [ ] PostgreSQL single-writer safety demonstrated.
- [ ] Alerts fired and on-call routing confirmed.
- [ ] Compound incident resolved with evidence.
- [ ] Upgrade compatibility and recovery plan reviewed.
- [ ] DR objectives measured against actual results.
- [ ] Runbooks and handoff independently reviewed.
- [ ] Temporary infrastructure and cloud charges checked.
- [ ] No critical safety gate violated.

## 24. Curriculum completion and continuing practice

The 105-chapter path covers foundations, administration, workload lifecycle, scheduling, networking, storage, security, observability, cloud-managed Kubernetes, platform engineering, GitOps, reliability, disaster recovery and advanced production operations.

**Curriculum writing complete** means all 105 chapter drafts exist. **Training validated** means labs have been executed, defects corrected and reviewed. **Candidate qualified** means an individual passed this assessment with verifiable evidence. These are distinct milestones.

For ongoing development, schedule periodic incident game days, restore tests, version compatibility reviews, policy audits, cost reviews and runbook updates. Keep the assessment current with supported Kubernetes releases and provider guidance.

## 25. Final sign-off

```text
Assessment result:
Score: ___ / 100
Critical safety gates: Pass / Fail
Mandatory exercises completed:
Exceptions / not-executed items:
Evidence repository:
Assessor name and date:
Candidate acknowledgement:
Remediation items and owners:
Next review date:
```

**Final chapter of the Kubernetes Administration and SRE tutorial series.**  
**Draft status:** assessment has not been administered, runtime-validated or independently reviewed.
