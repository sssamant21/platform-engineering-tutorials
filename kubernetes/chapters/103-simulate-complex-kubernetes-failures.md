# Chapter 103 — Simulate Complex Kubernetes Failures

**Track:** Kubernetes Administration · **Part 21 — Final Enterprise Kubernetes Capstone**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SREs, Kubernetes administrators, DBREs, incident commanders and platform engineers  
**Prerequisites:** Chapters 071–075, 096–102; disposable cluster from Chapter 101, PostgreSQL operator and test application from Chapter 102, GitOps, metrics/logs/traces, verified test backups and a second cluster for optional regional drills.

## Mission

Conduct a controlled chaos and disaster-recovery exercise across Kubernetes and a highly available stateful service. Diagnose faults using evidence, prevent cascading impact, make safe recovery decisions, verify customer-visible service health and produce an incident review.

**Critical safety rule:** every fault is authorized, scoped to disposable nonproduction resources, time-bounded and reversible. Never disable production control planes, delete production PVCs, corrupt real data, or create a split-brain database scenario for training.

## 1. Fault domains and failure model

```text
               Synthetic clients / SLOs
                        |
              Ingress / DNS / CNI
                        |
                 App Deployment
                        |
              Database write service
                        |
        +---------------+---------------+
        |               |               |
     Primary         Replica A       Replica B
        |               |               |
      CSI/PVC         CSI/PVC         CSI/PVC
        +---------------+---------------+
                        |
          GitOps / operator / Kubernetes API
                        |
            Cloud identity / network / zones
```

Failure testing must distinguish **fault injection**, **observed symptom**, **user impact**, **root/contributing causes**, **mitigation**, and **verified recovery**. A Kubernetes object reporting Ready does not prove application transactions succeed.

## 2. Lab 01 — Incident charter, scope and safety controls

Create a signed-off experiment plan:

```text
Experiment ID:
Owner and approver:
Primary/secondary clusters:
Namespace and test-only resources:
Affected service:
SLO, RTO, RPO and data-integrity targets:
Fault injection method:
Expected steady state:
Blast radius and duration:
Abort criteria:
Recovery/rollback:
Communication and on-call:
Evidence location:
```

Set a maximum experiment duration and an explicit stop signal. Confirm who has authority to terminate the exercise. If any required control is missing, do not proceed.

## 3. Lab 02 — Establish a clean baseline

```powershell
$Context = "<lab-context>"
$Namespace = "stateful-lab"
kubectl --context $Context get nodes -o wide
kubectl --context $Context get pods -n $Namespace -o wide
kubectl --context $Context get deployment,statefulset,svc,pvc -n $Namespace
kubectl --context $Context get pdb -A
kubectl --context $Context get events -A --sort-by=.lastTimestamp
```

Capture application synthetic transaction success, p95/p99 latency, error rate, throughput, database role/replication lag, WAL archive freshness, disk space, node capacity, Git revision and active alerts. Use UTC timestamps and redact credentials.

**Acceptance:** healthy baseline and recoverable test backup confirmed before fault injection.

## 4. Lab 03 — Define observability and experiment metrics

Track MTTD, mitigation time, recovery time, failed requests, latency impact, data loss, replication recovery, alert precision and operational actions. Define measurement boundaries in advance.

Sample evidence fields:

```text
Fault started (UTC):
First failed synthetic request:
Alert fired:
On-call acknowledged:
Mitigation initiated:
Service restored:
Database consistency verified:
Experiment ended:
RTO target vs observed:
RPO target vs observed:
```

Do not infer RPO from Pod restarts; compare committed test transactions with recovered data.

## 5. Lab 04 — Application readiness regression

In the disposable application, introduce a deliberately failing readiness probe through a test Git commit. Observe:
- Deployment conditions and ready endpoints.
- Ingress response and synthetic failures.
- Pod events and logs.
- GitOps revision and rollback.

```powershell
kubectl --context $Context get deployment,pods,svc,endpointslice -n $Namespace
kubectl --context $Context describe deployment <test-deployment> -n $Namespace
kubectl --context $Context get events -n $Namespace --sort-by=.lastTimestamp
```

**Recover:** revert through GitOps; validate end-to-end requests, not merely replica readiness.

## 6. Lab 05 — CPU/memory saturation and eviction risk

Deploy a bounded, low-priority stress workload **only** on disposable nodes with explicit resource limits, quotas and a timeout. Observe throttling, OOMKills, Pending Pods and node pressure. Avoid unbounded stress commands or deliberately exhausting a shared node.

```powershell
kubectl --context $Context top nodes
kubectl --context $Context top pods -n $Namespace
kubectl --context $Context describe nodes
kubectl --context $Context get events -n $Namespace --sort-by=.lastTimestamp
```

Metrics Server is required for `top`. **Recover:** remove the test load via GitOps and verify scheduling, application SLO and headroom.

## 7. Lab 06 — Scheduling conflict and topology pressure

Create a disposable Pod with an impossible node selector and observe the scheduler event:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: scheduling-fault
  namespace: stateful-lab
spec:
  nodeSelector:
    lab.example.com/nonexistent: "true"
  containers:
    - name: pause
      image: registry.k8s.io/pause:3.10
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
```

```powershell
kubectl --context $Context apply --dry-run=server -f .\scheduling-fault.yaml
kubectl --context $Context describe pod scheduling-fault -n $Namespace
```

The dry-run validates admission only; **apply to the disposable namespace** through the approved workflow to observe Pending behavior. Recover by deleting the test Pod or reverting Git, then confirm other workloads remain unaffected.

## 8. Lab 07 — Node drain and disruption budgets

Inspect PDBs, topology spread, local storage and available capacity. On a disposable node with approved redundancy:

```powershell
kubectl --context $Context get pdb -A
kubectl --context $Context get pods -A -o wide
kubectl --context $Context cordon <test-node>
kubectl --context $Context drain <test-node> --ignore-daemonsets --timeout=5m
kubectl --context $Context uncordon <test-node>
```

**Do not** add `--force` or `--delete-emptydir-data` just to force completion. A blocked drain can be correct safety behavior. Verify service availability and database replica placement before and after.

## 9. Lab 08 — DNS and service discovery failure

In a disposable namespace, alter only a test Service name or selector via GitOps; avoid changing cluster-wide CoreDNS. Observe lookup failures, missing EndpointSlices and client retry behavior.

```powershell
kubectl --context $Context get svc,endpointslice -n $Namespace
kubectl --context $Context get pods -n kube-system
kubectl --context $Context get events -n $Namespace --sort-by=.lastTimestamp
```

**Recover:** restore service configuration, verify DNS and TLS endpoints and measure client reconnection. Do not use public exposure or broad NetworkPolicy exceptions as a workaround.

## 10. Lab 09 — NetworkPolicy isolation regression

Apply a test-only deny policy to a **dedicated label-selected Pod cohort** in the disposable namespace. Test permitted and denied flows, then revert the policy.

Before the experiment, verify the installed CNI actually enforces NetworkPolicy. Network timeouts alone are insufficient evidence of policy enforcement; correlate with CNI flow logs or equivalent.

**Acceptance:** fault remains scoped and baseline security boundaries are restored.

## 11. Lab 10 — Storage provisioning and attach failure

Simulate a PVC stuck Pending by requesting a nonexistent StorageClass for a disposable PVC. Do not detach or delete real database volumes.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: invalid-class-test
  namespace: stateful-lab
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: deliberately-missing-class
  resources:
    requests:
      storage: 1Gi
```

Inspect PVC events and CSI logs. Recover by removing the test PVC and provisioning with an approved StorageClass. Verify the production-style database PVCs were not affected.

## 12. Lab 11 — Database replica degradation

Using the chosen PostgreSQL operator's **supported test procedure**, temporarily isolate or stop **one non-primary replica** in staging, only after confirming the operator's HA and quorum requirements.

Collect:

```sql
-- On the primary:
SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- On a standby:
SELECT status, latest_end_lsn, latest_end_time
FROM pg_stat_wal_receiver;
```

Observe replication lag, WAL retention and whether write availability changes under the configured synchronous commit policy. **Recover:** restore replica operation and verify catch-up without introducing a second primary.

## 13. Lab 12 — Primary switchover and fencing

Perform an **operator-supported planned switchover** in disposable staging. Record old/new primary, client errors, reconnection time, replication state and committed transaction continuity.

Do not equate Pod deletion with safe database failover. If operator fencing, quorum or storage safety is uncertain, run a tabletop rather than fault injection. Abort immediately if two writable primaries are suspected.

## 14. Lab 13 — GitOps and operator compound failure

Combine two **test-scoped** faults: a bad application configuration commit and a paused application-specific GitOps reconciliation. Diagnose whether the source-of-truth, GitOps controller, operator or workload is responsible.

**Recover:** restore Git repository accessibility/reconciliation first where safe, then revert the bad commit and validate operator convergence. Do not uninstall shared controllers or delete CRDs/finalizers to accelerate recovery.

## 15. Lab 14 — API access and identity failure

Use a deliberately invalid **test kubeconfig context** or expired disposable credential to simulate operator loss of API access. Observe authorization/connectivity diagnostics and the distinction between management access and existing workload operation.

```powershell
kubectl config get-contexts
kubectl --context <lab-context> auth can-i get pods -n stateful-lab
kubectl --context <lab-context> cluster-info
```

Recover by restoring authorized identity. Do not disable the real API server, cloud IAM or shared OIDC provider.

## 16. Lab 15 — Backup and point-in-time recovery drill

Before testing, write uniquely timestamped disposable database records, record commit results and verify the backup/WAL archive chain. Restore to an **isolated database instance** using operator-supported PITR.

Compare restored transaction set with the selected recovery point and compute observed RPO/RTO. Validate checksum/row counts and application connectivity. Do not overwrite source data, delete backup objects or claim a snapshot is equivalent to PITR without database-specific evidence.

## 17. Lab 16 — Multi-cluster failover simulation

Deploy a disposable stateless application to a secondary test cluster and validate readiness before changing **test-only** traffic routing. Measure DNS caching, TLS, client retries and recovery time.

For PostgreSQL, use a tabletop or operator/database-supported cross-region failover process with replication verification, fencing and split-brain protection. **Never** start an independent writable primary without proving the original primary cannot accept writes.

## 18. Lab 17 — Cascading incident game day

Run a timed scenario in disposable staging:
1. A test Service selector breaks application traffic.
2. A separate test Pod becomes Pending due to a scheduling constraint.
3. One database replica reports lag.
4. The incident commander must triage user impact, stop changes and choose recovery order.

Only inject each additional fault if prior safety checks pass. The objective is coordinated diagnosis, not maximum destruction. Capture hypotheses, alerts, communications, command outputs and recovery evidence.

## 19. Lab 18 — Recovery acceptance and evidence

| Failure | Minimum evidence | Recovery gate |
|---|---|---|
| App rollout | Git revision, endpoints, synthetic probes | Service SLO restored |
| Resource pressure | Node/Pod metrics, events | Capacity and SLO restored |
| Scheduling | Scheduler events | Workload placed correctly |
| Node disruption | PDB, placement, availability | Failure tolerance preserved |
| DNS/network | Resolver/flow evidence | Correct paths restored |
| Storage | PVC/CSI events | Provisioning safe; data intact |
| Replication | WAL/role metrics | One primary, healthy replicas |
| GitOps/operator | Reconciliation and status | Desired state converged |
| API identity | Auth diagnostics | Authorized access restored |
| PITR | Restore log, checksum, timestamp | Data integrity verified |
| Regional drill | Traffic and fencing record | RTO/RPO measured |

**Final acceptance checklist:**
- [ ] All fault injections approved and scoped to disposable resources.
- [ ] Steady-state baseline and abort thresholds documented.
- [ ] Detection and on-call routing verified.
- [ ] Incidents triaged using evidence rather than guesses.
- [ ] No destructive shortcut or security bypass used.
- [ ] Database single-writer safety preserved.
- [ ] Backup/PITR restoration actually validated.
- [ ] Customer-visible service health measured after recovery.
- [ ] RTO/RPO results compared against original objectives.
- [ ] Independent reviewer evaluates evidence and outstanding risks.

## 20. Incident command and communication runbook

```text
1. Declare severity and identify incident commander.
2. Freeze unrelated changes and halt fault injection.
3. Identify customer impact and affected failure domains.
4. Gather logs, metrics, events, Git revision and database role.
5. Choose safe mitigation with a documented stop condition.
6. Communicate impact, owner and next checkpoint.
7. Recover through approved GitOps/operator/database procedures.
8. Verify SLOs, data integrity, security and capacity.
9. Preserve evidence and conduct a blameless review.
```

Maintain a timeline with UTC timestamps, responsible roles, observed effects and recovery decisions. Record both what worked and where documentation or tooling was insufficient.

## 21. Cleanup and cost controls

Revert test Git commits, remove disposable stress Pods and invalid PVCs, restore normal NetworkPolicies and test routing, uncordon only nodes changed by this exercise, and verify GitOps convergence. Check for billable snapshots, disks, load balancers, test clusters and GPU resources. Preserve approved incident evidence and backups according to retention rules.

## 22. Production takeaways

Complex Kubernetes incidents cross abstraction boundaries. Reliable recovery depends on application telemetry, infrastructure state, database replication and fencing, operator behavior, GitOps consistency, human coordination and tested backups. **Recover the service, not just the Kubernetes objects.**

**Draft status:** no fault injections or acceptance tests have been executed in this publication workflow.

**Next:** Chapter 104 — Upgrade, Recover and Validate a Production Cluster.
