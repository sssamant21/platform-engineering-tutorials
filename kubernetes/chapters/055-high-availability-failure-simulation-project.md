# Chapter 055 — High Availability Failure Simulation Project

**Track:** Kubernetes Administration · **Part 11 — High Availability and Disaster Recovery (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 051–054; kubectl, Windows PowerShell; an approved multi-worker staging cluster; isolated namespace for controlled evictions

## 1. Production scenario and objective

A regional Kubernetes cluster runs across three availability zones. A simulated zone failure removes one worker pool, an application replica and one database voter. The Kubernetes API remains reachable, but application readiness degrades and a replacement Pod cannot schedule due to zonal storage and capacity constraints. The incident team must determine whether control-plane/etcd quorum remains intact, restore safe application availability and demonstrate recovery against SLO, RPO and RTO targets.

**Goal:** integrate control-plane HA, etcd quorum, PodDisruptionBudgets, graceful shutdown, topology spread, storage and application recovery into a measurable acceptance project.

### Project deliverables

1. HA topology and failure-domain inventory.
2. Control-plane and etcd quorum decision worksheet.
3. Stateful backup, replication and failover readiness checklist.
4. Isolated replicated workload with PDB and topology spread.
5. Controlled Eviction API test and request/availability evidence.
6. Zone-failure tabletop with recovery decisions.
7. SLI/SLO, RPO/RTO and post-incident acceptance package.

## 2. Reference architecture

```text
           Stable Kubernetes API endpoint
                     |
             HA API servers
                     |
        etcd voters across 3 AZs
                     |
          Regional worker pools
          /         |         \
        AZ-A       AZ-B       AZ-C
        api-1      api-2      api-3
        db-1       db-2       db-3
        PV-A       PV-B       PV-C
          \         |         /
            Service / Ingress
                     |
          Synthetic availability probe
```

This diagram represents an intended design, **not evidence that any particular managed cluster exposes its control-plane topology**. EKS/AKS/GKE control planes are provider-managed; use provider documentation and metrics for HA guarantees.

### Explicit failure objectives

| Failure | Desired outcome | Separate dependency |
|---|---|---|
| One application Pod | Remaining replicas serve traffic | Readiness, endpoint routing |
| One worker node | Replacement Pod becomes Ready | Capacity, PDB, storage |
| One availability zone | Critical application continues | Cross-zone placement and capacity |
| One of three etcd voters | Quorum remains | Surviving voter health |
| Two of three etcd voters | Quorum lost | Disaster recovery required |
| Regional outage | Not covered by zonal HA | Multi-region DR |

## 3. Safety, approvals and environment

**No destructive control-plane or etcd fault injection is performed in this chapter.** All live mutation exercises are limited to an approved staging namespace. The optional Eviction API test terminates only a named demo Pod. Do not stop etcd members, shut down cloud zones, delete worker nodes or disrupt production infrastructure for this tutorial.

```powershell
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl auth can-i create deployments -n default
```

Record environment, approval, owner, rollback authority, intended RTO/RPO and baseline customer-facing SLIs.

## 4. Lab 1 — Inventory HA topology and failure domains

```powershell
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -A -o wide
kubectl get deployments,statefulsets -A
kubectl get pdb -A -o wide
kubectl get pv
kubectl get storageclasses
kubectl get ingress -A
```

**Expected:** document zone placement, replicas, storage topology, disruption budgets, ingress and shared dependencies. For managed control planes, note that control-plane Nodes and etcd members may not be visible.

### Required worksheet

| Component | Current topology | Single-zone-loss risk | Owner |
|---|---|---|---|
| Kubernetes API | Provider/self-managed | Endpoint/LB or quorum | Platform |
| etcd | Provider/3 voters/etc. | Majority placement | Platform |
| Application API | Replicas per zone | Insufficient survivors | Application |
| Database | Voters/replicas per zone | Quorum, leader, RPO | DBRE |
| Storage | Zonal/regional PV | Attachment and restore | Storage |
| Ingress | Controller/LB zones | Routing after failure | Networking |
| Autoscaling | Node pools/subnets/quotas | No spare capacity | Platform |

## 5. Lab 2 — Validate API and leader-election evidence

```powershell
kubectl get --raw /livez
kubectl get --raw /readyz
kubectl get --raw /version
kubectl -n kube-system get leases
kubectl get nodes -o wide
```

**Expected:** current API availability and observable Lease state. A successful check proves present reachability, **not** resilience to an AZ outage. Scheduler/controller-manager Lease names and access vary by provider.

### Control-plane acceptance

- API endpoint and load balancer have documented redundancy.
- Control-plane health checks use appropriate readiness semantics.
- Scheduler/controller-manager leader election is understood.
- etcd voting-member placement and quorum guarantees are documented.
- Backup and provider recovery responsibilities are identified.
- API errors, latency and leader-change monitoring are available.

## 6. Lab 3 — etcd quorum and disaster-recovery tabletop

**Scenario A:** a three-member etcd cluster loses one voter. Two remain healthy. **Decision:** preserve quorum and recover the failed member; do not restore a snapshot unnecessarily.

**Scenario B:** a second voter fails before the first returns. Only one remains. **Decision:** stop maintenance, declare loss of quorum and invoke the approved disaster-recovery procedure. Do not force new cluster formation or perform ad hoc member removal.

### Quorum worksheet

| Voting members | Majority | Failures tolerated |
|---:|---:|---:|
| 1 | 1 | 0 |
| 3 | 2 | 1 |
| 5 | 3 | 2 |

**Required evidence:** latest verified snapshot age, encryption/access controls, restore-test date, RPO/RTO, application data consistency requirements, etcd topology and authorized recovery owner.

For managed EKS/AKS/GKE, etcd is provider-managed; do not attempt to run etcdctl against inaccessible managed control-plane infrastructure.

## 7. Lab 4 — Deploy a multi-zone HA demo

**Approved staging cluster only.** Save `ch055-ha.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch055
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-web
  namespace: ch055
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ha-web
  template:
    metadata:
      labels:
        app: ha-web
    spec:
      terminationGracePeriodSeconds: 30
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ha-web
      containers:
        - name: web
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ha-web
  namespace: ch055
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: ha-web
---
apiVersion: v1
kind: Service
metadata:
  name: ha-web
  namespace: ch055
spec:
  selector:
    app: ha-web
  ports:
    - port: 80
      targetPort: 80
```

```powershell
kubectl apply -f .\ch055-ha.yaml
kubectl -n ch055 rollout status deployment/ha-web --timeout=180s
kubectl -n ch055 get pods -o wide
kubectl -n ch055 get pdb ha-web -o wide
kubectl -n ch055 get endpointslices -l kubernetes.io/service-name=ha-web
kubectl get nodes -L topology.kubernetes.io/zone
```

**Expected:** three Ready Pods and a PDB that ordinarily allows one voluntary disruption. Verify Pod-to-node-to-zone mapping; **topology spread does not guarantee three distinct zones** unless eligible domains and constraints support that outcome.

## 8. Lab 5 — Controlled voluntary Pod failure test

This lab uses the **Eviction API** on one demo Pod; it does not simulate a real zone outage. Confirm all three Pods are Ready and `disruptionsAllowed` is at least one.

```powershell
kubectl -n ch055 get pdb ha-web -o wide
$pod = (kubectl -n ch055 get pods -l app=ha-web -o jsonpath='{.items[0].metadata.name}')
kubectl -n ch055 get pod $pod -o wide
```

Submit one eviction request:

```powershell
$body = '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"' + $pod + '","namespace":"ch055"}}'
$body | Set-Content -Path .\ch055-eviction.json -Encoding utf8
kubectl create --raw "/api/v1/namespaces/ch055/pods/$pod/eviction" -f .\ch055-eviction.json
```

Observe recovery:

```powershell
kubectl -n ch055 get pods -o wide
kubectl -n ch055 get pdb ha-web -o wide
kubectl -n ch055 rollout status deployment/ha-web --timeout=180s
kubectl -n ch055 get endpointslices -l kubernetes.io/service-name=ha-web
kubectl -n ch055 get events --sort-by=.lastTimestamp
```

**Expected:** the eviction is accepted if the PDB allows it; the Deployment replaces the Pod and eventually returns to three Ready replicas. If eviction is rejected, do not bypass the PDB. Diagnose readiness, PDB status and capacity.

### Application availability evidence

Run an approved synthetic HTTP probe against the Service or ingress throughout the test, collecting timestamps, request successes, errors and latency. Pod readiness alone does **not** establish zero request failures.

## 9. Lab 6 — Zone-loss capacity and stateful recovery assessment

This is a **tabletop**; do not stop a zone.

### Example capacity

| Zone | Available CPU units | Workload requests |
|---|---:|---:|
| A | 16 | 10 |
| B | 16 | 10 |
| C | 16 | 10 |
| Total | 48 | 30 |

After losing Zone B, surviving nominal capacity is 32 CPU units versus 30 units of original requests, leaving only 2 units before system reservations, fragmentation and scheduling constraints. Determine whether critical services fit and whether autoscaling can add nodes before RTO expires.

### Stateful failure exercise

A three-voter database has one voter per zone. Zone B fails, leaving two voters. Evaluate:
1. Whether a leader remains or can be elected.
2. Whether replication is healthy enough for safe writes.
3. Whether a lost zonal PV can be reattached elsewhere (often it cannot).
4. Whether replacement requires a fresh PV and database-native replica rebuild.
5. Whether a second zone failure would lose quorum.
6. Whether backup/restore evidence meets RPO and RTO.

**Expected:** database-specific failover decisions; do not treat StatefulSet replica count as proof of database quorum or consistency.

## 10. Lab 7 — Combined HA incident simulation tabletop

**Scenario:** Zone B is unavailable. One API replica and one database voter are lost. The Kubernetes API remains reachable, but a replacement API Pod is Pending due to topology constraints, the node autoscaler cannot add capacity due to subnet IP exhaustion, and application latency increases.

### Read-only incident diagnostics

```powershell
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -A -o wide
kubectl get pdb -A -o wide
kubectl get pvc -A
kubectl get pv
kubectl get events -A --sort-by=.lastTimestamp
kubectl get --raw /readyz
```

### Required incident actions

1. Establish incident command and measure customer-facing SLI impact.
2. Confirm surviving API endpoint and control-plane/etcd quorum.
3. Identify impacted zones, Pods, volumes, ingress targets and database members.
4. Freeze unrelated maintenance and avoid evicting additional quorum members.
5. Resolve capacity/IP blockers or activate preapproved standby node pools.
6. Allow stateless replicas to recover only where topology constraints permit.
7. Execute database-approved failover and replication recovery.
8. Verify application HTTP success, latency and database transactions.
9. Confirm remaining redundancy and ability to tolerate further failures.
10. Record RTO, RPO, data loss (if any), and corrective actions.

**Expected:** a response that distinguishes control-plane health, application availability and data consistency, with no unsafe etcd or database mutations.

## 11. SLO and recovery acceptance

Define objectives **before** running the exercise. Example targets below are illustrative and must be adapted to business requirements.

| Measure | Example target | Evidence |
|---|---|---|
| API server reachability | Remains reachable during one-zone loss | Independent synthetic API checks |
| Application request success | At least 99.9% during test window | HTTP probe time series |
| Application p95 latency | Within agreed degraded-mode SLO | Monitoring dashboard |
| Replica recovery time | Within 5 minutes | Pod and event timestamps |
| Database RPO | No acknowledged-write loss | DB replication/transaction evidence |
| Database RTO | Within approved recovery objective | DB service health timestamps |
| etcd quorum | Majority preserved for single-voter failure | Provider/etcd member evidence |
| Backup recoverability | Verified restore within defined cadence | Restore-test record |

A successful controlled Pod eviction is **not** proof that a zone outage or etcd disaster recovery will meet these targets. Record which tests were actually executed versus tabletop only.

## 12. Production HA incident runbook

### Prepare

1. Inventory failure domains, replicas, etcd voters, PDBs, PVs and capacity.
2. Define API, application and database SLIs plus RPO/RTO.
3. Verify backup/restore, DB failover and control-plane recovery ownership.
4. Ensure monitoring remains available outside the affected zone.
5. Confirm change approvals and abort criteria.

### Detect and contain

1. Determine whether the failure is Pod, node, zone, control-plane or regional.
2. Freeze unrelated upgrades and disruptive maintenance.
3. Preserve etcd and database quorum; avoid force deletion and unsafe member changes.
4. Identify customer impact and communicate degraded-mode expectations.

### Recover

1. Restore API/LB connectivity if required.
2. Recover worker capacity and subnet/IP availability.
3. Restore stateless replicas and verify ingress/Service routing.
4. Recover databases using approved replication, failover and storage procedures.
5. Confirm SLO recovery, data consistency and monitoring coverage.

### Close

Record fault scope, detection delay, actual recovery duration, RPO/RTO, residual risk, corrective actions, owners and next test date.

## 13. Failure and recovery decision matrix

| Failure | Expected behavior | Safe recovery |
|---|---|---|
| One API server fails | Other API servers continue | LB/instance remediation |
| One of three etcd voters fails | Quorum remains | Quorum-preserving member recovery |
| Two of three etcd voters fail | Quorum lost | Approved disaster recovery |
| One app Pod evicted | PDB permits if healthy capacity exists | Replacement and readiness |
| Zone outage | Surviving replicas serve if correctly distributed | Capacity and traffic recovery |
| Zonal PV unavailable | Pod may remain Pending | DB-native replica rebuild/restore |
| PDB blocks eviction | Maintenance pauses | Restore healthy replicas |
| Autoscaler cannot provision | Replacement capacity unavailable | Quota/subnet/node pool remediation |
| Regional outage | Regional cluster unavailable | Separate multi-region DR |

## 14. Capstone evidence package

Create a review package containing:

- HA architecture and failure-domain map.
- Cluster version, node/zone inventory and control-plane ownership.
- etcd quorum worksheet and disaster recovery decision tree.
- PDB, topology spread and application placement evidence.
- Staging deployment, eviction request and recovery timestamps.
- Synthetic request success and latency evidence.
- Database quorum, replication, PV topology and backup/restore evidence.
- Zone-loss capacity and autoscaling constraints.
- Incident tabletop timeline and runbook decisions.
- RPO/RTO/SLO acceptance results, exceptions and review sign-off.

## 15. Part 11 acceptance checklist

- [ ] Chapter 051: HA control-plane design and leader election assessed.
- [ ] Chapter 052: etcd quorum, member recovery and snapshot DR distinguished.
- [ ] Chapter 053: PDB and graceful termination behavior reviewed.
- [ ] Chapter 054: multi-zone placement, storage and capacity assessed.
- [ ] Control-plane and application availability measured separately.
- [ ] Staging HA workload deployed and Pod-to-zone placement verified.
- [ ] Controlled Eviction API test performed safely.
- [ ] Application synthetic monitoring collected during eviction.
- [ ] Database quorum and zonal PV recovery decisions documented.
- [ ] Zone outage tabletop completed without production fault injection.
- [ ] RPO, RTO, SLIs, monitoring and runbook acceptance documented.
- [ ] Independent technical review and runtime validation completed before marking Lab Validated.

**Part 11 writing milestone:** Chapters 051–055 drafted; runtime validation and technical review remain pending.

## 16. Cleanup

```powershell
kubectl -n ch055 get deployment,pdb,service,pods
kubectl delete namespace ch055
Remove-Item .\ch055-eviction.json -ErrorAction SilentlyContinue
```

This chapter does not cordon, drain or delete worker nodes and does not mutate etcd or production control-plane resources. Confirm no demo resources remain after the lab.

## 17. References

- [Kubernetes HA Topology Options](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ha-topology/)
- [Kubernetes etcd Operations](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [etcd Disaster Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)

**Next:** Chapter 056 — Kubernetes Metrics, Logs and Events (Part 12).
