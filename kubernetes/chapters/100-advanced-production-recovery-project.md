# Chapter 100 — Advanced Production Recovery Project

**Track:** Kubernetes Administration · **Part 20 — Advanced Platform Engineering and Production Operations (Final Capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes SREs, incident commanders, platform engineers, on-call operators  
**Prerequisites:** Chapters 071–099, two disposable nonproduction clusters for cross-cluster drills, GitOps, monitoring, kubectl, PowerShell, a test workload and a documented backup/restore mechanism.

## Mission and learning objectives

Lead a realistic, controlled Kubernetes recovery exercise spanning workload failure, policy regression, operator/controller degradation, GPU scheduling, persistent data recovery and regional failover. Practice command, evidence collection, decision-making, safe rollback, recovery verification and post-incident improvements.

**Important:** This is a lab project, not authorization to cause production outages. All fault injection must be scoped to disposable environments, with a named owner, rollback path and spending limits. Production recovery procedures must follow approved change and incident processes.

## 1. Recovery architecture and dependencies

```text
                   Incident Commander
                         |
       +-----------------+-----------------+
       |                 |                 |
    Detection         Mitigation        Communications
       |                 |                 |
  Metrics/logs       GitOps rollback     Stakeholders
  Events/traces      App/cluster restore  Timeline
       |                 |                 |
       +-----------------+-----------------+
                         |
                Recovery verification
                         |
        SLOs + data integrity + security + cost
```

Recovery may require several independent systems: Kubernetes control plane, cloud identity, CNI, DNS, storage, admission webhooks, GitOps, operator controllers, secrets, external databases and traffic routing. A Running Pod is not proof of successful service recovery.

## 2. Lab environment and guardrails

Prepare:
- **Cluster A:** disposable primary staging cluster.
- **Cluster B:** disposable recovery cluster, preferably another failure domain.
- **Application:** stateless HTTP API plus optional disposable stateful service.
- **GitOps:** Argo CD or Flux, version pinned.
- **Monitoring:** metrics, logs, synthetic health checks and alerts.
- **Backups:** recoverable, independently validated test data.
- **Identity:** least-privilege operator and emergency access roles.
- **Fault budget:** no intentional control-plane destruction, cloud quota exhaustion, production network changes or irreversible data deletion.

Define explicit RTO, RPO, availability and latency targets *before* starting; values must reflect the exercise and service requirements, not be invented during the drill.

## 3. Lab 01 — Create incident charter and roles

Assign incident commander, technical lead, communications lead, scribe and independent verifier. Record start/stop time, cluster identities, owner approval, escalation path, test data scope and rollback authorization.

```text
Exercise ID:
Environment / cluster IDs:
Business service:
Incident commander:
Technical operators:
Safety officer / verifier:
RTO / RPO targets:
SLO and abort thresholds:
Approved failure injections:
Rollback and escalation:
Evidence location:
```

**Acceptance:** every participant understands stop conditions and can identify the correct cluster.

## 4. Lab 02 — Establish a healthy baseline

```powershell
kubectl config get-contexts
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get deployment,statefulset,svc,ingress -A
kubectl get pdb -A
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp
```

Record baseline synthetic transaction success, p95 latency, error rate, request throughput, replica availability, backup age, Git revision, operator status and cost/capacity. `kubectl top` is optional and requires Metrics Server. Use a timestamped evidence bundle; redact credentials and sensitive application data.

## 5. Lab 03 — Observability and alert acceptance

Configure a synthetic request probe and dashboards for service availability, latency, errors, restarts, Pending Pods, GitOps drift, operator reconciliation and backup freshness.

Inject a **non-destructive** test alert using an approved synthetic condition. Verify alert delivery, on-call ownership, timestamps, runbook link and acknowledgement. An alert rule that exists but was never triggered is not a validated alert.

**Evidence:** alert fired, notification received, incident opened and baseline captured.

## 6. Lab 04 — Application configuration outage

In Cluster A's disposable namespace, introduce a bad Service selector through a reviewed test Git commit. Confirm healthy Pods remain but the Service has no ready backends.

```powershell
kubectl --context <cluster-a> get deployment,svc,endpointslice -n recovery-lab
kubectl --context <cluster-a> describe svc demo-api -n recovery-lab
kubectl --context <cluster-a> get events -n recovery-lab --sort-by=.lastTimestamp
```

**Recover:** revert the bad Git commit and reconcile. Confirm EndpointSlices contain ready backends and the synthetic request succeeds. Record time to detect and time to restore user-visible service.

## 7. Lab 05 — Deployment failure and rollback

In the disposable test workload, deploy an intentionally invalid image digest or failing readiness configuration. Observe rollout conditions, logs, events and application health.

```powershell
kubectl --context <cluster-a> rollout status deployment/demo-api -n recovery-lab --timeout=180s
kubectl --context <cluster-a> describe deployment demo-api -n recovery-lab
kubectl --context <cluster-a> get pods -n recovery-lab -o wide
```

**Recover:** revert through GitOps. An imperative `kubectl rollout undo` can be overwritten by GitOps and must not be the default recovery method. Verify service SLOs and that the intended image digest is restored.

## 8. Lab 06 — Node disruption and workload rescheduling

Inspect topology, requests, PDBs and node capacity. In a disposable cluster with proven redundancy, cordon and drain **one test node**.

```powershell
kubectl --context <cluster-a> get nodes -L topology.kubernetes.io/zone
kubectl --context <cluster-a> get pdb -A
kubectl --context <cluster-a> get pods -A -o wide
```

Only after explicit approval:

```powershell
kubectl --context <cluster-a> cordon <test-node>
kubectl --context <cluster-a> drain <test-node> --ignore-daemonsets --timeout=5m
kubectl --context <cluster-a> uncordon <test-node>
```

Do not add `--force` or `--delete-emptydir-data` merely to make the drain succeed. Stop and investigate PDBs or local data constraints. Confirm rescheduling, zone distribution, latency and redundancy.

## 9. Lab 07 — Admission-policy regression

In staging, introduce a narrowly scoped policy that rejects a deliberately noncompliant test manifest, then test a compliant manifest. Simulate a policy rollout regression using a safe test-only namespace selector rather than cluster-wide denial.

Inspect:

```powershell
kubectl --context <cluster-a> get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl --context <cluster-a> get events -n recovery-lab --sort-by=.lastTimestamp
kubectl --context <cluster-a> auth can-i create deployments -n recovery-lab
```

**Recover:** revert the faulty policy in Git, validate that compliant workloads are admitted and that intentionally unsafe workloads remain denied. Never disable admission security globally as a quick fix.

## 10. Lab 08 — Operator and CRD reconciliation failure

Choose a disposable operator or custom controller from Chapter 096. Create a CR with a safe invalid dependency; capture status conditions, `observedGeneration`, controller logs and reconciliation errors.

```powershell
kubectl --context <cluster-a> get crds
kubectl --context <cluster-a> get deployments -A
kubectl --context <cluster-a> get events -A --sort-by=.lastTimestamp
```

**Recover:** repair the test CR or dependency, verify fresh observed generation and child-resource health. Do not delete the CRD or strip finalizers to bypass cleanup. Include webhook availability and RBAC checks if relevant.

## 11. Lab 09 — GPU workload recovery (optional hardware track)

If approved GPU nodes are available, simulate a Pending Pod using a deliberately incorrect node selector. Check events, GPU allocatable capacity, device-plugin status and node taints.

```powershell
kubectl --context <cluster-a> get nodes -L node-pool,gpu_type
kubectl --context <cluster-a> describe pod <gpu-test-pod> -n recovery-lab
kubectl --context <cluster-a> get daemonsets -A
```

**Recover:** restore correct placement via Git and validate container-level GPU visibility and framework CUDA availability. A healthy node or successful host `nvidia-smi` does not prove application CUDA readiness. If no GPU hardware is available, mark this track **Not executed**, not Passed.

## 12. Lab 10 — Stateful recovery and data integrity

Use disposable, non-sensitive test data. Capture a database-native backup or supported snapshot, write a known test record, and rehearse restoration **to a separate recovery instance/namespace**, not over the source.

Record backup identifier, restore timestamp, checksum or record count, database consistency result and recovery duration. Verify encryption keys and required secrets are available.

**RPO** measures acceptable data loss; **RTO** measures acceptable service recovery time. A snapshot existing is not proof it can be restored. Do not delete or corrupt production data for this exercise.

## 13. Lab 11 — GitOps control-plane unavailability

Simulate a safe client-side Git repository connectivity issue or pause reconciliation for a **test-only** application according to the chosen GitOps controller's supported procedures. Observe drift detection and change propagation behavior.

**Recover:** restore repository access or resume reconciliation, verify intended Git revision and application health. Document emergency access and how out-of-band changes are reconciled back into Git. Do not uninstall shared Argo CD/Flux controllers.

## 14. Lab 12 — Cluster API connectivity incident

Use a test-only invalid kubeconfig context or temporary client-side network restriction; do not disable the actual control plane. Capture authentication, DNS, network and API connectivity diagnostics. Verify that existing workloads may continue serving even while management operations fail, but avoid assuming controller recovery remains available.

**Recover:** restore valid access, recheck authorization and inspect reconciliation backlog. Clearly distinguish simulated client access loss from a real API server outage.

## 15. Lab 13 — Multi-cluster service recovery

Deploy the same disposable stateless service to Clusters A and B. Verify B is independently healthy before switching **test-only** traffic routing from A to B.

```powershell
kubectl --context <cluster-a> get deployment,svc -n recovery-lab
kubectl --context <cluster-b> get deployment,svc -n recovery-lab
kubectl --context <cluster-b> rollout status deployment/demo-api -n recovery-lab --timeout=180s
```

Measure detection, traffic shift, recovery and failback times. Validate DNS/client caching and TLS. Stateful failover requires application-specific replication checks and fencing; **never** permit two writable primaries simply because both clusters are available.

## 16. Lab 14 — Compound incident simulation

In a disposable environment, combine two safe faults: bad application Service selector in A and a blocked GitOps reconciliation for the test app. Require the incident commander to choose between repairing GitOps first or using a documented, audited break-glass mitigation.

Record hypotheses, decisions, blast radius, mitigation sequence, evidence and SLO outcomes. Avoid introducing more faults once safety thresholds are crossed. Restore Git as source of truth before closure.

## 17. Lab 15 — Recovery verification and acceptance gates

For every scenario, check:

| Gate | Verification |
|---|---|
| User-visible health | Synthetic requests succeed |
| Application reliability | Latency, error rate and throughput within agreed targets |
| Kubernetes state | Desired/ready replicas, no unexplained Pending Pods |
| GitOps consistency | Intended commit reconciled, no unresolved drift |
| Security | RBAC, admission and network boundaries preserved |
| Data integrity | Restore/replication consistency verified where applicable |
| Capacity | Redundancy and scheduling headroom restored |
| Observability | Alerts clear for the right reasons |
| Cost | Temporary cloud resources identified and cleaned |
| Evidence | Timeline, logs, commands, approvals and reviewer captured |

Do not declare success solely because all Pods are Running. If a gate fails, mark recovery incomplete and record the remaining risk.

## 18. Lab 16 — Incident timeline and blameless review

Prepare a timestamped timeline:

```text
T0    Fault introduced / first impact
T1    Monitoring detected degradation
T2    Incident declared and commander assigned
T3    Initial hypothesis and evidence
T4    Mitigation selected
T5    Change reverted / service restored
T6    SLO and data integrity verified
T7    Incident closed / follow-ups assigned
```

Calculate MTTD = T1−T0 and MTTR using the organization's defined start/end boundaries; report RTO/RPO outcomes against predeclared targets. Document contributing factors, detection gaps, decision tradeoffs, what worked, and actionable owners/due dates. Avoid attributing failure to individuals.

## 19. Lab 17 — Recovery automation and guardrails

Design automation that gathers context and validates recovery without executing destructive operations automatically:

```powershell
$Context = "<cluster-a>"
$Namespace = "recovery-lab"
kubectl --context $Context get nodes
kubectl --context $Context get pods -n $Namespace -o wide
kubectl --context $Context get events -n $Namespace --sort-by=.lastTimestamp
kubectl --context $Context get deployment,svc,endpointslice -n $Namespace
```

For production automation, add explicit context allowlists, dry-run capability, audit logging, approvals, bounded retries, timeouts and stop conditions. Do not auto-remove finalizers, delete PVCs or switch database primaries without application-specific safety controls.

## 20. Lab 18 — Final capstone review

**Required deliverables:**
1. Incident charter and safety approvals.
2. Architecture and dependency diagram.
3. Baseline dashboards and test evidence.
4. Fault-injection plan with stop conditions.
5. Scenario-by-scenario runbooks and results.
6. Git revisions and change/rollback history.
7. Recovery time and data integrity evidence.
8. Multi-cluster failover/failback record.
9. Cost and cleanup verification.
10. Blameless review with owned corrective actions.

**Acceptance checklist:**
- [ ] All mandatory exercises executed in authorized nonproduction environments.
- [ ] Optional GPU track accurately marked Pass/Fail/Not executed.
- [ ] Monitoring detected application-impacting failures.
- [ ] Incident roles, communications and escalation rehearsed.
- [ ] GitOps rollback and recovery verified.
- [ ] Operator, policy and node recovery controls tested.
- [ ] Backup restore and data consistency independently verified.
- [ ] Multi-cluster failover measured against predefined RTO/RPO.
- [ ] No unresolved security bypasses or unsafe resource deletions.
- [ ] Service-level recovery confirmed by application metrics.
- [ ] Evidence reviewed and signed off by an independent engineer.

## 21. Cleanup and handoff

Revert all test Git commits, remove only disposable resources, confirm nodes are uncordoned, restore normal GitOps reconciliation and policy settings, and verify no test-only traffic routing remains. Check provider billing for temporary clusters, disks, load balancers and GPU nodes. Preserve required logs and evidence according to retention policy.

Never delete a production CRD, PVC, namespace, node pool, snapshot or backup to complete this project.

## 22. Part 20 summary

Chapters 096–100 cover Kubernetes API extensions, GPU platforms, multi-cluster fleets, change management and recovery engineering. The capstone integrates these topics into measurable operational practice.

**Part 20 writing milestone:** all five chapters are drafted. Publication does not imply execution, acceptance or independent technical review.

**Next:** Chapter 101 — Build a Production-Ready Kubernetes Cluster, beginning Part 21 — Final Enterprise Kubernetes Capstone.
