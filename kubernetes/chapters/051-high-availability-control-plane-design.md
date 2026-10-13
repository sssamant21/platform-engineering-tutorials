# Chapter 051 — High Availability Control Plane Design

**Track:** Kubernetes Administration · **Part 11 — High Availability and Disaster Recovery**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes platform architects, cluster administrators  
**Prerequisites:** Chapters 006–010, 021–025, 046–050; kubectl, Windows PowerShell; cluster-reader privileges; isolated HA test cluster for optional fault injection

## 1. Production scenario

A healthcare application platform must tolerate the loss of a control-plane VM or availability zone. The existing architecture has one API endpoint and three control-plane instances, but the team has not verified load-balancer health checks, etcd quorum placement, leader election, zone distribution or recovery procedures. A single control-plane outage must not turn into a prolonged management-plane outage or unsafe etcd recovery.

**Goal:** design, inspect and validate a highly available Kubernetes control plane with clearly defined failure domains, capacity assumptions, SLOs and recovery boundaries.

### Learning objectives

1. Explain redundant API servers, load balancing, scheduler and controller-manager leader election.
2. Compare stacked etcd and external etcd topologies.
3. Calculate quorum and fault tolerance for common etcd cluster sizes.
4. Assess availability-zone and network failure domains.
5. Inspect API health, component placement, leases and control-plane access.
6. Distinguish management-plane availability from application and data availability.
7. Build an HA acceptance plan, incident runbook and design decision record.

## 2. HA control-plane architecture

```text
        Operators / kubelets / controllers / GitOps
                         |
             Stable Kubernetes API endpoint
                         |
               TCP/TLS load balancer
                  /      |      \
                 /       |       \
          API server  API server  API server
             AZ-a        AZ-b       AZ-c
               |           |          |
       controller-manager and scheduler instances
            (one active leader per component)
               |           |          |
               +-----------+----------+
                           |
                    etcd quorum
             member-a   member-b   member-c
               AZ-a       AZ-b       AZ-c
                           |
                Kubernetes desired state

      Workers, CNI, CSI, ingress, apps and databases
         have their own availability requirements
```

**Note:** the diagram is conceptual. With **stacked etcd**, each control-plane host runs a local etcd member; with **external etcd**, etcd runs on a separate dedicated tier. A managed service may hide the control-plane topology entirely.

The API endpoint must remain stable through control-plane node changes. Its health checks should distinguish a healthy API server from a process that merely accepts TCP connections. TLS termination, certificates, DNS, internal/external exposure and client connectivity are part of the design.

## 3. Architecture choices and failure domains

| Dimension | Stacked etcd | External etcd |
|---|---|---|
| Placement | etcd co-located with control plane | Separate etcd hosts |
| Host count | Smaller footprint | More infrastructure |
| Failure coupling | Control-plane host and etcd member share fate | Separate fault domains possible |
| Operations | Simpler bootstrap, coupled maintenance | Independent etcd maintenance, more complexity |
| Recovery | Must consider both local control plane and etcd | Separate etcd and API tiers |
| Suitability | Common kubeadm HA pattern | Specialized large/strict isolation requirements |

**Design principles:** use an odd number of voting etcd members where practical, place members across independent failure domains, preserve low-latency reliable etcd networking, and avoid stretching etcd across high-latency geographic regions without vendor-supported design.

### etcd quorum arithmetic

For **N voting members**, quorum is `floor(N/2) + 1`. The maximum number of simultaneous voting-member failures tolerated is `N - quorum`.

| Voting members | Quorum | Failures tolerated |
|---:|---:|---:|
| 1 | 1 | 0 |
| 2 | 2 | 0 |
| 3 | 2 | 1 |
| 4 | 3 | 1 |
| 5 | 3 | 2 |
| 7 | 4 | 3 |

Adding a fourth member to a healthy three-member cluster does **not** improve failure tolerance. Adding members also increases operational and network costs. Never add an etcd member as an emergency guess when quorum is already lost.

## 4. Lab prerequisites and guardrails

Labs 1–7 are read-only, design or tabletop exercises. Optional destructive failure injection requires a separately approved, disposable HA cluster. Do not stop API servers, kill etcd members, modify load balancers or alter quorum in production for a tutorial.

```powershell
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl get nodes -o wide
kubectl auth can-i list leases.coordination.k8s.io -n kube-system
```

Capture cluster type (EKS, AKS, GKE or kubeadm), control-plane ownership, number of zones, load-balancer endpoint and approved monitoring sources.

## 5. Lab 1 — Inventory control-plane topology

```powershell
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get nodes -l node-role.kubernetes.io/control-plane -o wide
kubectl get nodes -l node-role.kubernetes.io/master -o wide
kubectl get pods -n kube-system -o wide
```

**Expected:** in self-managed clusters, control-plane Nodes and static Pods may be visible. Managed EKS/AKS/GKE control-plane hosts often do not appear in the user's Node inventory. **An empty control-plane Node list on a managed cluster is not evidence that the provider has no HA control plane.**

Record control-plane ownership, provider HA guarantees, API endpoint exposure, zone placement evidence and whether etcd is stacked or external. If topology is not visible, obtain the provider's architecture/SLA documentation rather than guessing.

## 6. Lab 2 — Inspect API endpoint and health probes

```powershell
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
kubectl get --raw /livez
kubectl get --raw /readyz
kubectl get --raw /version
```

**Expected:** a stable API endpoint and successful liveness/readiness checks. Access may be restricted or health endpoints may differ by version or provider. Avoid using `/readyz?verbose` as a publicly exposed unauthenticated diagnostic endpoint.

### Design verification

- Is the load balancer highly available across zones?
- Does its health check reflect API readiness rather than only TCP acceptance?
- Can clients resolve and reach the endpoint during a zone failure?
- Are TLS SANs valid for the stable endpoint?
- Is there sufficient API server capacity after one instance fails?
- Do control-plane security groups/firewalls permit required component traffic?

**Important:** a successful `kubectl get` proves current API reachability, not zone-failure resilience.

## 7. Lab 3 — Inspect leader election and component health

```powershell
kubectl -n kube-system get leases
kubectl -n kube-system get lease kube-controller-manager -o yaml
kubectl -n kube-system get lease kube-scheduler -o yaml
kubectl get --raw /readyz
```

**Expected:** on many self-managed clusters, leader-election Lease objects show holders and renewal timestamps. Lease names and visibility vary by Kubernetes version, deployment mode and managed provider; a missing Lease is not conclusive evidence of no leader election.

**Interpretation:** scheduler and controller-manager commonly run multiple instances with leader election; only the active leader performs certain reconciliation actions. API servers are active-active behind the endpoint. Do not infer scheduler/controller health solely from Lease freshness; correlate controller logs, work queues, Pending Pods and reconciliation outcomes.

## 8. Lab 4 — Evaluate etcd quorum and placement

This is a **design and inventory exercise**. On self-managed control planes, authorized administrators can inspect etcd member lists with `etcdctl` using the installation's documented endpoints and TLS credentials. Never paste etcd private keys or client certificates into chat or tickets.

```powershell
kubectl get nodes -L topology.kubernetes.io/zone
kubectl -n kube-system get pods -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

Create a quorum worksheet for 3 and 5 voting members. Evaluate these scenarios:

1. One member/host fails.
2. One availability zone fails.
3. A network partition divides the voting members 2:1.
4. Two members in a three-member cluster fail.
5. A rolling maintenance operation removes one member while another is unhealthy.

**Expected:** a three-member cluster can retain quorum after one member failure, but not two. A partitioned minority must not be forced to write. Ensure the design does not place two of three voting members in a single failure domain if the objective is to tolerate loss of that domain.

### etcd safety rules

- Take and **restore-test** etcd snapshots using documented tooling.
- Protect snapshot encryption, access and storage.
- Check member health and quorum before planned maintenance.
- Avoid concurrent etcd member restarts without a reviewed sequence.
- Do not perform member removal/replacement or restore against production without an approved etcd-specific runbook.
- Understand that a snapshot restore can lose writes since the snapshot; reconcile Kubernetes object state and external systems afterward.

## 9. Lab 5 — Assess worker and workload HA separately

```powershell
kubectl get deployments -A
kubectl get statefulsets -A
kubectl get pdb -A -o wide
kubectl get pods -A -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pv
kubectl get storageclass
```

**Expected:** identify single-replica services, zone concentration, PDB constraints, PV affinity and insufficient surge capacity. Even a perfectly redundant API server does not make a single-replica database or zone-bound volume available after a zone failure.

### Application HA requirements

- Multiple healthy replicas with topology spread or anti-affinity where appropriate.
- Sufficient worker capacity in surviving zones.
- PDBs and graceful termination for voluntary maintenance.
- Service endpoints, ingress/load-balancer health and DNS resiliency.
- Database replication/quorum and documented failover.
- Storage availability and cross-zone attachment constraints.
- External dependencies such as Redis, Kafka, Elasticsearch and PostgreSQL have their own HA designs.

## 10. Lab 6 — Build an HA design decision record

Create a design review containing:

| Question | Required answer |
|---|---|
| Failure objective | Single host, single AZ or region failure? |
| Control-plane topology | Number of API servers and etcd voting members |
| API endpoint | LB, DNS, health check, TLS, client routing |
| etcd placement | Stacked/external, zones, quorum and latency |
| Component election | Scheduler/controller-manager redundancy |
| Capacity | Headroom after losing one component or zone |
| State protection | Snapshot frequency, restore test, RPO/RTO |
| Security | PKI ownership, API access, secrets and audit |
| Observability | API error rate, etcd leader changes, disk latency |
| Recovery | Runbook, owner, approvals and rollback limitations |

**Expected:** a design that names its tolerated failure explicitly. A three-AZ architecture may tolerate one AZ failure but not a regional outage. Region-level DR requires separate architecture and data recovery planning.

## 11. Lab 7 — Control-plane outage tabletop and acceptance

**Scenario:** a three-member stacked-etcd cluster spans three AZs. One AZ fails, removing one API server and one etcd voter. The API endpoint intermittently times out; application Pods already running continue to serve some traffic, but new Pods cannot be scheduled reliably.

### Read-only diagnostics

```powershell
kubectl config current-context
kubectl get --raw /readyz
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl -n kube-system get leases
kubectl get events -A --sort-by=.lastTimestamp
```

If the API is unavailable, these commands may fail. Use independent provider metrics, load-balancer health checks, host logs, etcd metrics and cloud status. Do not interpret a failed kubectl command as proof that all existing application Pods stopped.

### Response sequence

1. Establish incident command, timeline, impacted zones and customer SLIs.
2. Verify load-balancer target health and stable endpoint reachability.
3. Check surviving API servers and controller/scheduler leadership.
4. Confirm etcd quorum using authorized independent evidence.
5. Avoid restarting a healthy etcd member while only two of three remain.
6. Restore or replace the failed control-plane instance using the documented HA procedure.
7. Verify etcd membership and replication health before any further maintenance.
8. Validate API requests, controller reconciliation, scheduling and application readiness.
9. Assess data loss and restore needs only if quorum/storage was compromised.
10. Document root cause, alert gaps, RTO and prevention.

**Never restore etcd from a snapshot merely because one member failed while quorum is healthy.** Snapshot restore is a recovery operation with significant consistency and data-loss implications.

## 12. Control-plane HA monitoring and SLOs

| Signal | Why it matters | Example action |
|---|---|---|
| API server request success/latency | User and controller API availability | Investigate LB/API saturation |
| API server ready endpoints | Redundancy remaining | Restore unhealthy instance |
| etcd quorum/leader changes | Cluster state availability | Investigate member/network health |
| etcd disk fsync/commit latency | Consensus performance | Storage latency remediation |
| etcd DB size and alarms | Space exhaustion risk | Review compaction/defrag plan |
| Scheduler Pending Pod backlog | Placement control-loop health | Inspect leader and constraints |
| Controller reconciliation errors | Desired-state convergence | Controller logs/queues |
| Certificate expiration | API/component trust | Approved rotation |
| Node Lease freshness | Node-control communication | Node/API connectivity |
| App transaction SLIs | Customer availability | Workload-specific response |

Use provider-supported metrics in managed clusters; etcd internals may not be directly exposed. Define alert thresholds from measured baselines and availability objectives rather than copying arbitrary numbers.

## 13. Production incident runbook

### Detect and scope

1. Confirm API request failures, LB health, component alerts and user impact.
2. Identify affected zone/host and whether failures are isolated or regional.
3. Correlate API, etcd, controller-manager, scheduler and network metrics.
4. Determine whether applications continue serving despite management-plane disruption.

### Contain

1. Freeze nonessential cluster changes and maintenance.
2. Protect surviving etcd quorum; do not restart healthy voters.
3. Avoid broad node deletions, forced Pod deletion or unreviewed etcd member edits.
4. Ensure incident communications distinguish API unavailability from application outage.

### Recover

1. Restore LB target health or API server connectivity if the API tier is at fault.
2. For etcd issues, follow the **topology-specific** member recovery or disaster-recovery procedure.
3. Reestablish controller/scheduler leadership and API readiness.
4. Validate Pod scheduling, Node health and reconciliation.
5. Check workload SLIs, storage, ingress and data consistency.

### Close

Record failure domain, quorum evidence, RTO/RPO, API error budget, component versions, configuration changes, rollback decisions and follow-up architecture actions.

## 14. Failure and recovery matrix

| Failure | Expected HA behavior | Risk / recovery |
|---|---|---|
| One API server fails | LB routes to healthy servers | Check remaining capacity and readiness |
| Scheduler leader fails | New leader elected | Temporary scheduling delay |
| Controller-manager leader fails | New leader elected | Temporary reconciliation delay |
| One of three etcd voters fails | Quorum remains with two | Restore member before next failure |
| Two of three etcd voters fail | Quorum lost | Approved etcd disaster recovery |
| One AZ fails with 1 voter/AZ | Two voters retain quorum | Worker and storage capacity still required |
| LB fails | API endpoint unavailable | Redundant LB design/recovery |
| API server cert expires | Clients may reject TLS | Approved PKI rotation |
| Region fails | Regional cluster unavailable | Separate multi-region DR design |

## 15. Acceptance checklist

- [ ] Control-plane ownership and topology documented.
- [ ] Stable API endpoint and LB HA design reviewed.
- [ ] API server readiness and connectivity inspected.
- [ ] Scheduler/controller-manager leader election assessed.
- [ ] Stacked versus external etcd tradeoffs documented.
- [ ] Quorum arithmetic and AZ failure tolerance validated.
- [ ] etcd backup and restore test requirements recorded.
- [ ] Worker, storage and application HA assessed separately.
- [ ] HA monitoring signals and escalation ownership defined.
- [ ] Control-plane outage tabletop completed.
- [ ] RTO/RPO, runbook and design decision record produced.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 16. References

- [Kubernetes HA Topology Options](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ha-topology/)
- [Creating Highly Available Clusters with kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/)
- [Operating etcd Clusters](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/)
- [Kubernetes Leases](https://kubernetes.io/docs/concepts/architecture/leases/)
- [etcd FAQ and Quorum](https://etcd.io/docs/v3.5/faq/)
- [Kubernetes Disaster Recovery](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)

**Next:** Chapter 052 — etcd Operations, Quorum and Recovery.
