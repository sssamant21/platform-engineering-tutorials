# Chapter 054 — Multi-Zone Availability and Failure Domains

**Track:** Kubernetes Administration · **Part 11 — High Availability and Disaster Recovery**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 021–025, 046–053; kubectl and Windows PowerShell; an approved staging cluster spanning at least two availability zones for placement tests

## 1. Production scenario

A Kubernetes platform runs across three availability zones. A cloud-networking failure removes one zone from service. The control plane remains available, but application replicas were concentrated on nodes in the affected zone, persistent volumes are zone-bound, and the cluster autoscaler cannot provision enough replacement capacity. Some applications become unavailable despite having multiple replicas.

**Goal:** design, inspect and validate multi-zone workload resilience while understanding the boundaries of Kubernetes scheduling, storage topology, networking, database quorum and capacity.

### Learning objectives

1. Identify node, rack, zone and region failure domains.
2. Understand zone labels and scheduler topology spread constraints.
3. Apply pod anti-affinity and topology spread to replicated workloads.
4. Distinguish hard and soft placement requirements and scheduling tradeoffs.
5. Evaluate zone-local PVs, CSI topology, and StatefulSet failover.
6. Assess zone-loss capacity, autoscaling and traffic routing.
7. Build a zone-failure tabletop and production recovery runbook.

## 2. Failure-domain architecture

```text
                 Regional Kubernetes cluster
                           |
             Stable API / ingress endpoints
                           |
          +----------------+----------------+
          |                |                |
        Zone A           Zone B           Zone C
       worker-a          worker-b         worker-c
       api pod 1         api pod 2        api pod 3
       db voter 1        db voter 2       db voter 3
       zonal PV A        zonal PV B       zonal PV C
          |                |                |
          +---- regional networking / DNS ---+
                           |
               Zone-loss failover plan
```

This is a conceptual design. A **regional** cluster spanning multiple zones can survive certain zone failures but does not automatically survive regional failure. Workload replicas, ingress, DNS, node provisioning, persistent storage, and data replication must be designed separately.

### Failure domains

| Failure domain | Examples | Typical mitigation |
|---|---|---|
| Container / Pod | Crash, OOM, liveness restart | Multiple healthy replicas |
| Worker node | Hardware, OS, kubelet, runtime | Replicas on different nodes |
| Availability zone | Power/network/storage impairment | Replicas and capacity across zones |
| Region | Regional cloud outage | Separate regional DR architecture |
| Shared dependency | DNS, ingress, database, identity | Redundant dependency design |
| Human/change | Misconfiguration, bad rollout | Progressive delivery, backups, change gates |

**Key point:** multiple replicas on one worker or one zone do not provide protection against that worker or zone failing.

## 3. Scheduling primitives and design tradeoffs

### Topology spread constraints

A topology spread constraint asks the scheduler to distribute matching Pods across domains such as `topology.kubernetes.io/zone` or `kubernetes.io/hostname`. The `maxSkew` value constrains imbalance; `whenUnsatisfiable` controls whether a new Pod stays Pending or may be scheduled despite imbalance.

- `DoNotSchedule`: hard placement requirement; can leave Pods Pending if eligible domains/capacity are unavailable.
- `ScheduleAnyway`: soft preference; can improve availability of replicas under pressure but may concentrate Pods.
- `minDomains`: can enforce an expected minimum count of eligible topology domains in supported Kubernetes versions; verify behavior and feature support for the target release.
- `nodeAffinityPolicy` and `nodeTaintsPolicy`: affect eligible domain calculations; check release support and exact scheduling semantics.

### Pod anti-affinity

`requiredDuringSchedulingIgnoredDuringExecution` prevents placement alongside selected Pods in a topology domain. `preferredDuringSchedulingIgnoredDuringExecution` expresses a preference. Hard anti-affinity can deadlock scheduling if insufficient nodes or zones exist.

### Storage topology

A dynamically provisioned PV may be tied to one zone. `WaitForFirstConsumer` volume binding helps coordinate scheduling and volume provisioning, but it **does not** make a zonal volume portable during a zone outage. Stateful HA typically requires application-level replication, appropriately designed storage, and a safe failover process.

## 4. Lab prerequisites and safety

Labs 1–3 and 6–7 are read-only or tabletop. Labs 4–5 create only namespaced test resources in an approved staging cluster. No nodes or zones are deliberately failed. Do not use this chapter to simulate cloud-zone failure in production.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl auth can-i create deployments -n default
```

**Environment gate:** verify that nodes have accurate zone labels and that the cluster has at least two usable zones. If the lab runs in a single-zone environment, perform placement analysis only; do not claim multi-zone acceptance.

## 5. Lab 1 — Inventory nodes, zones and workloads

```powershell
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get nodes -L topology.kubernetes.io/region
kubectl get nodes -o custom-columns=NAME:.metadata.name,ZONE:.metadata.labels.topology\.kubernetes\.io/zone,READY:.status.conditions[-1].status
kubectl get pods -A -o wide
kubectl get deployments,statefulsets -A
```

**Expected:** node distribution and workload placement are visible. Do not rely on the example JSONPath custom column's final condition as a definitive Ready check because condition ordering is not guaranteed; use `kubectl describe node` or an explicit condition query for operational health.

### Record

- number of Ready worker nodes in each zone;
- critical workloads with all replicas in one zone;
- singleton controllers or ingress endpoints;
- worker pools and instance-type availability;
- zone-specific storage and network dependencies.

## 6. Lab 2 — Review topology spread and anti-affinity

```powershell
kubectl get deployments -A -o yaml
kubectl get statefulsets -A -o yaml
kubectl get pods -A -o wide
kubectl get pdb -A -o wide
```

For each critical workload, inspect `spec.template.spec.topologySpreadConstraints`, `affinity.podAntiAffinity`, node selectors, taints/tolerations, and resource requests.

**Expected:** a written assessment of hard versus soft placement and whether available zones can satisfy the requested replicas. Avoid copying full manifests containing sensitive environment variables into incident tickets.

### Worked example

Three replicas across three eligible zones with `maxSkew: 1` and `DoNotSchedule` should be spread so no zone receives more than one replica while all zones are eligible and have capacity. If a zone becomes unavailable, strict constraints or other scheduling restrictions may prevent replacements. Evaluate desired behavior during failure, not only steady state.

## 7. Lab 3 — Inventory zonal storage and StatefulSet constraints

```powershell
kubectl get storageclasses -o wide
kubectl get pv -o wide
kubectl get pvc -A
kubectl get statefulsets -A -o wide
kubectl get csinodes
kubectl get csidrivers
```

For a selected PV, inspect `spec.nodeAffinity`, access modes, reclaim policy and CSI driver:

```powershell
$pv = "REPLACE_WITH_SELECTED_PV"
kubectl describe pv $pv
```

**Expected:** understand which volumes can attach only in specific zones and which applications depend on them. Do not detach, delete or rebind production PVs as a lab.

### DBRE acceptance questions

1. Does the database replicate across independent zones?
2. Can a surviving replica be safely promoted?
3. What happens to quorum if a zone is lost?
4. Are backups and restore targets available outside the affected zone?
5. Can a PVC be provisioned in a surviving zone without data loss?
6. What are the application's actual RPO and RTO?

**Important:** a Pod rescheduled to a healthy zone cannot necessarily mount its previous zonal volume. Stateful recovery may require replication or restoring data to a new volume.

## 8. Lab 4 — Deploy a topology-aware stateless service

**Staging only.** Save `ch054-app.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch054
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zone-aware-api
  namespace: ch054
spec:
  replicas: 3
  selector:
    matchLabels:
      app: zone-aware-api
  template:
    metadata:
      labels:
        app: zone-aware-api
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: zone-aware-api
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
  name: zone-aware-api
  namespace: ch054
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: zone-aware-api
---
apiVersion: v1
kind: Service
metadata:
  name: zone-aware-api
  namespace: ch054
spec:
  selector:
    app: zone-aware-api
  ports:
    - port: 80
      targetPort: 80
```

```powershell
kubectl apply -f .\ch054-app.yaml
kubectl -n ch054 rollout status deployment/zone-aware-api --timeout=180s
kubectl -n ch054 get pods -o wide
kubectl -n ch054 get pdb zone-aware-api -o wide
kubectl -n ch054 get endpointslices -l kubernetes.io/service-name=zone-aware-api
```

**Expected:** three Ready replicas if sufficient eligible zones and capacity exist. **Topology spread alone does not force three distinct zones in every configuration**; examine actual Pod-to-zone mapping before declaring acceptance.

## 9. Lab 5 — Verify distribution and diagnose Pending replicas

```powershell
kubectl -n ch054 get pods -o wide
kubectl -n ch054 describe deployment zone-aware-api
kubectl -n ch054 get events --sort-by=.lastTimestamp
kubectl get nodes -L topology.kubernetes.io/zone
```

Map each Pod's `spec.nodeName` to the Node's zone. Record replicas per zone and compare against the intended failure objective.

### Troubleshooting

| Symptom | Likely cause | Investigation |
|---|---|---|
| Pods Pending | Hard spread cannot be satisfied | Scheduler events and eligible zones |
| All Pods in one zone | Missing labels or constraints | Node labels, Pod selector |
| Replicas not Ready | Image/probe/network issue | Pod describe, logs |
| No replacement capacity | Autoscaler/pool limit | Node groups, quotas, cloud capacity |
| Pod stuck attaching volume | Zonal PV restriction | PV node affinity and CSI |
| PDB blocks maintenance | Healthy replicas below minimum | PDB status and readiness |
| Traffic still fails | Ingress or endpoint routing | Service/EndpointSlice and LB health |

**Do not remove hard spread rules blindly.** Decide whether temporary concentration is acceptable under an approved degraded-mode policy.

## 10. Lab 6 — Calculate zone-loss capacity

Use this **planning exercise** for a three-zone deployment:

| Zone | Normal worker capacity (CPU units) | Normal workload requests |
|---|---:|---:|
| A | 16 | 10 |
| B | 16 | 10 |
| C | 16 | 10 |
| Total | 48 | 30 |

If Zone A fails, the remaining capacity is 32 units and the original workload request total is 30 units. That leaves only 2 units of theoretical headroom before accounting for DaemonSets, system reservations, fragmentation, per-node scheduling constraints and surge needs.

### Capacity questions

1. Can surviving zones run the **required critical workload**, not necessarily every low-priority Pod?
2. Can the autoscaler add nodes in surviving zones quickly enough?
3. Are cloud quotas, instance types and subnet IPs sufficient?
4. Do PDBs, affinity and topology spread allow replacement placement?
5. Are ingress, NAT, DNS, databases and storage independently resilient?
6. Does the cluster preserve latency and throughput SLOs at degraded capacity?

**Expected:** a capacity worksheet with normal, one-zone-loss and recovery states, plus an explicit degraded-mode policy.

## 11. Lab 7 — Availability-zone outage tabletop

**Scenario:** Zone B becomes unavailable. One of three API Pods, one of three database voters, and a zonal PV are lost. The remaining API Pods are Ready, but the autoscaler cannot provision replacement nodes because a subnet is out of IP addresses. A database client reports timeouts.

### Read-only investigation

```powershell
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -A -o wide
kubectl get pdb -A -o wide
kubectl get pvc -A
kubectl get pv
kubectl get events -A --sort-by=.lastTimestamp
```

If the API endpoint is impaired, use independent provider metrics and monitoring rather than assuming all applications have stopped.

### Response sequence

1. Declare incident and identify affected zone and customer SLIs.
2. Confirm surviving control-plane and etcd quorum separately from application health.
3. Identify unavailable Pods, zonal PVs, ingress endpoints and database voters.
4. Freeze unnecessary maintenance and preserve surviving database quorum.
5. Resolve subnet IP/capacity blockers or activate preapproved standby capacity.
6. Allow stateless replicas to recover within safe placement constraints.
7. For stateful workloads, execute DB-approved promotion/recovery; do not force-mount unavailable volumes.
8. Verify database reads/writes, replication and application request success.
9. Assess whether the recovered cluster can withstand another failure.
10. Document actual RTO, RPO, capacity gaps and prevention actions.

**Expected:** a recovery plan that avoids data loss and explicitly identifies when zone-level resilience is insufficient.

## 12. Multi-zone design patterns

### Stateless APIs

Deploy multiple replicas, topology spread, readiness probes, safe shutdown, PDBs and adequate surviving capacity. Validate load balancer health and cross-zone traffic routing.

### Stateful databases

Use database-native replication and quorum across zones, anti-affinity where feasible, verified backups and documented promotion. PV topology must match the database's recovery design.

### Ingress and networking

Ensure ingress controllers and load balancers span failure domains, backend endpoints update correctly, network policies remain functional, and DNS dependencies are not concentrated in one zone.

### Cluster autoscaler and node pools

Maintain capacity options in multiple zones, sufficient quotas/subnet IPs, compatible node images, and a defined time-to-recover objective. A scale-up mechanism is not a substitute for guaranteed spare capacity when recovery time is strict.

### Multi-region disaster recovery

A multi-zone regional cluster does not meet a regional disaster recovery objective. Cross-region replication, backups, DNS failover, infrastructure recreation and application consistency require a separate design.

## 13. Production zone-failure runbook

### Prepare

1. Map critical workloads, storage and node pools to zones.
2. Define tolerated failure domain and degraded-mode SLOs.
3. Verify placement policies, PDBs, replacement capacity and quotas.
4. Confirm DB quorum, failover and backup/restore procedures.
5. Validate ingress, DNS and observability independence.

### Respond

1. Identify zone failure and freeze maintenance.
2. Verify control-plane/etcd quorum and surviving nodes.
3. Check application readiness, endpoints and data replication.
4. Restore capacity in surviving zones if possible.
5. Recover stateful services through application-approved procedures.
6. Monitor error rate, latency, replication lag and resource pressure.

### Recover and close

1. Rebalance workloads only after the zone and storage are stable.
2. Validate data consistency and safe return of database members.
3. Confirm PDBs, topology spread and spare capacity are restored.
4. Record incident RTO/RPO, lost capacity, customer impact and corrective actions.

## 14. Acceptance checklist

- [ ] Node, zone, region and shared-dependency failure domains mapped.
- [ ] Worker nodes and critical Pods inventoried by zone.
- [ ] Topology spread and anti-affinity policies reviewed.
- [ ] Hard versus soft scheduling tradeoffs documented.
- [ ] Zonal PV and StatefulSet recovery constraints assessed.
- [ ] Staging Deployment and PDB created.
- [ ] Actual Pod-to-zone distribution verified.
- [ ] One-zone-loss capacity and autoscaler limits calculated.
- [ ] Zone outage tabletop and database recovery decisions completed.
- [ ] Application SLI, RPO and RTO acceptance criteria documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 15. Cleanup

```powershell
kubectl -n ch054 get deployment,pdb,service,pods
kubectl delete namespace ch054
```

Do not remove node zone labels, PVs, StorageClasses or shared node-pool settings as part of this lab. The read-only exercises created no resources.

**Status:** Draft — runtime validation and technical review pending.

## 16. References

- [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Storage Classes and Volume Binding](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Kubernetes Cluster Autoscaling](https://kubernetes.io/docs/concepts/cluster-administration/node-autoscaling/)

**Next:** Chapter 055 — High Availability Failure Simulation Project (Part 11 capstone).
