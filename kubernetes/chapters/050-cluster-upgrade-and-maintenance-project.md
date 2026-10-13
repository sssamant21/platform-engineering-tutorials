# Chapter 050 — Cluster Upgrade and Maintenance Project

**Track:** Kubernetes Administration · **Part 10 — Node Operations and Troubleshooting (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers, Kubernetes administrators  
**Prerequisites:** Chapters 046–049; kubectl, Windows PowerShell; approved staging cluster; isolated multi-worker cluster for disruptive rehearsal

## 1. Production scenario and objective

A production Kubernetes cluster approaches its support deadline. The upgrade requires a control-plane version change, worker-node replacement, add-on compatibility verification and certificate lifecycle review. Workloads include replicated APIs, a StatefulSet database, ingress, CNI/CSI, admission webhooks and observability agents.

**Goal:** deliver an evidence-backed upgrade plan, execute a **safe node-maintenance rehearsal** in staging, and demonstrate post-maintenance availability and security. This chapter does not initiate an actual control-plane upgrade or rotate production certificates.

### Capstone outcomes

1. Inventory Node architecture, health, Leases and capacity.
2. Evaluate Kubernetes version skew, deprecated APIs and add-on compatibility.
3. Identify PKI, webhook and workload certificate rotation dependencies.
4. Assess PDBs, StatefulSet quorum, volume topology and surge capacity.
5. Rehearse cordon, PDB-aware drain and uncordon in an isolated cluster.
6. Demonstrate recovery from a blocked drain and failed workload admission.
7. Produce an upgrade runbook, rollback decision tree and acceptance evidence.

## 2. Project architecture

```text
Upgrade request / support deadline
             |
   Discovery and risk assessment
   Node health + API deprecations + certificates
             |
   Staging compatibility and recovery test
             |
   Change approval + backups + SLO baseline
             |
   Control-plane upgrade (provider-specific, not executed here)
             |
   CNI / CSI / DNS / admission compatibility validation
             |
   Worker rolling maintenance
      cordon -> PDB-aware drain -> upgrade/replace -> verify -> uncordon
             |
   Application, stateful storage, PKI and SLO acceptance
             |
   Observation, evidence, change closeout
```

**Critical boundaries:** a Node reporting `Ready=True` does not guarantee healthy applications; drain completion does not prove database failover; a control-plane upgrade may not support in-place downgrade; and a renewed certificate is not necessarily trusted by all clients.

## 3. Lab safety and required environment

Labs 1–4 and 7 are read-only or tabletop. Labs 5–6 perform mutations **only on an approved isolated staging cluster with at least two worker nodes**. Do not use a production cluster for a tutorial drain. A real upgrade must follow current provider-supported procedures and change approval.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl cluster-info
kubectl auth can-i patch nodes
kubectl auth can-i create pods/eviction -n default
```

Capture the current context in the change record. Confirm the target release is a supported upgrade hop before planning any actual version change.

## 4. Lab 1 — Cluster and node readiness inventory

```powershell
kubectl get nodes -o wide
kubectl get nodes -o custom-columns=NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion,OS:.status.nodeInfo.osImage
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
```

**Expected:** versions, runtime, node health, zones, workload distribution and resource usage are documented. `kubectl top` requires Metrics Server; use approved monitoring if unavailable.

Choose one worker for closer inspection:

```powershell
$node = "REPLACE_WITH_APPROVED_STAGING_WORKER"
kubectl describe node $node
kubectl get node $node -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{" reason="}{.reason}{"\n"}{end}'
kubectl -n kube-node-lease get lease $node -o yaml
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
```

**Acceptance:** Node conditions, taints, Lease renewal, kubelet version, runtime and assigned workload blast radius are understood before maintenance.

## 5. Lab 2 — Version, API and add-on compatibility assessment

```powershell
kubectl version
kubectl get --raw /version
kubectl api-versions
kubectl api-resources -o wide
kubectl get crds
kubectl get apiservices
kubectl -n kube-system get deployments,daemonsets -o wide
kubectl get csidrivers
kubectl get ingressclasses
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
```

**Expected:** current server/kubelet versions and critical APIs, CRDs and add-ons are inventoried. API resources may be unavailable or RBAC-restricted; record this as a gap, not a pass.

### Compatibility register

| Component | Evidence required | Acceptance gate |
|---|---|---|
| API server | Current and target release | Supported upgrade hop |
| Kubelet | Per-pool version inventory | Supported version skew |
| CNI and kube-proxy/eBPF | Installed versions and vendor matrix | Target compatible |
| CSI | Driver versions and storage tests | Attach/mount works |
| CoreDNS | Version and DNS smoke tests | Service discovery works |
| Admission webhooks | API versions, TLS, endpoints | New Pod admission works |
| Ingress/Gateway | Controller version and route tests | External traffic works |
| Autoscaler | Controller and API compatibility | Node provisioning works |
| GitOps/Helm/CRDs | Rendered manifests | No removed API dependencies |

**Do not select a target version from assumptions.** Use current Kubernetes version-skew policy and EKS/AKS/GKE/kubeadm documentation for the actual environment.

## 6. Lab 3 — Stateful safety, backups and PDB readiness

```powershell
kubectl get statefulsets -A
kubectl get pvc -A
kubectl get pv
kubectl get storageclasses
kubectl get pdb -A -o wide
kubectl get pods -A --field-selector=status.phase=Pending
```

**Expected:** stateful applications, storage classes, PV topology, disruption allowance and Pending workloads are identified.

### Required evidence

- etcd/control-plane recovery mechanism appropriate to the provider.
- Verified database backup **and restore rehearsal** for stateful applications.
- Database quorum, leader/follower roles and replication health.
- Storage attach/detach behavior and zone/node affinity.
- PDB selector, healthy Pods and `disruptionsAllowed`.
- Replacement/surge node capacity and topology spread.
- RPO/RTO and explicit owner approval.

**DBRE checkpoint:** a volume snapshot alone does not prove application-consistent recovery. Confirm database-specific backup and restore procedures.

## 7. Lab 4 — Certificate and admission readiness

```powershell
kubectl get csr
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get ingress -A
kubectl get secrets -A --field-selector type=kubernetes.io/tls
kubectl get apiservices
```

**Expected:** certificate renewal ownership, CSR status, admission webhook dependencies and application TLS inventory are documented. Never decode or print TLS private keys or kubeconfig credentials.

### PKI acceptance

1. Confirm control-plane certificate ownership (managed provider versus kubeadm).
2. Verify certificate expiry, issuer and SANs using authorized public certificate inspection.
3. Confirm webhook serving certificate and `caBundle` trust chain match.
4. Review kubelet CSR signer and approval process.
5. Confirm cert-manager or other renewal controllers are healthy if installed.
6. Document separate procedures for leaf renewal and CA rotation.

A successful control-plane upgrade does not guarantee webhook certificates or custom admission controllers remain compatible.

## 8. Lab 5 — Deploy a maintenance rehearsal workload

**Only in an isolated staging cluster.** Create `ch050-workload.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch050
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maintenance-api
  namespace: ch050
spec:
  replicas: 3
  selector:
    matchLabels:
      app: maintenance-api
  template:
    metadata:
      labels:
        app: maintenance-api
    spec:
      terminationGracePeriodSeconds: 20
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
  name: maintenance-api
  namespace: ch050
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: maintenance-api
---
apiVersion: v1
kind: Service
metadata:
  name: maintenance-api
  namespace: ch050
spec:
  selector:
    app: maintenance-api
  ports:
    - port: 80
      targetPort: 80
```

```powershell
kubectl apply -f .\ch050-workload.yaml
kubectl -n ch050 rollout status deployment/maintenance-api --timeout=180s
kubectl -n ch050 get pods -o wide
kubectl -n ch050 get pdb maintenance-api -o wide
kubectl -n ch050 get endpointslices -l kubernetes.io/service-name=maintenance-api
```

**Expected:** three Ready replicas and a measurable PDB allowance, typically one allowed disruption if all are healthy. If scheduling is uneven, do not force placement by modifying shared cluster policies. Choose an approved worker that hosts a test Pod **only after inventorying every other Pod on that worker**.

## 9. Lab 6 — Rehearse cordon, drain and recovery

**Disruption gate:** before running `kubectl drain`, inspect **all namespaces** on the selected worker. The command is node-wide and can evict unrelated Pods.

```powershell
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl get pdb -A
kubectl get node $node -o jsonpath='{.spec.unschedulable}'
```

Proceed only when:
- the node was schedulable before the exercise;
- every affected workload is approved for disruption;
- no local-PV/singleton/quorum risk exists;
- replacement capacity and PDB allowance are sufficient;
- rollback authority and observation metrics are available.

```powershell
kubectl cordon $node
kubectl get node $node
kubectl drain $node --ignore-daemonsets --timeout=5m
```

**Expected:** cordon blocks ordinary new scheduling; drain attempts PDB-aware eviction and may stop if unmanaged Pods, local ephemeral data, PDBs or storage constraints block it. **Do not automatically add `--force`, `--delete-emptydir-data` or `--disable-eviction`.**

After a successful drain:

```powershell
kubectl -n ch050 rollout status deployment/maintenance-api --timeout=180s
kubectl -n ch050 get pods -o wide
kubectl -n ch050 get pdb maintenance-api -o wide
kubectl -n ch050 get endpointslices -l kubernetes.io/service-name=maintenance-api
kubectl get node $node -o wide
```

**Expected:** eligible replacement Pods become Ready on other nodes. Verify application request success and latency using available synthetic checks/monitoring; ready replicas alone are not sufficient proof of service health.

This capstone **does not reboot, replace or upgrade** the node. After the simulated maintenance and explicit confirmation the node should return to service:

```powershell
kubectl uncordon $node
kubectl get node $node -o wide
```

If drain was blocked, do not bypass protections. Investigate the blocking Pod and decide whether to abort or extend the rehearsal. Uncordon only if this lab cordoned the node and it is safe to restore scheduling.

## 10. Lab 7 — Combined upgrade and certificate incident tabletop

**Scenario:** the control plane was upgraded successfully, but an admission webhook's certificate chain no longer matches its `caBundle`. New Pods fail admission. One worker remains cordoned after a drain blocked on a StatefulSet PDB, and a replacement database Pod cannot attach its volume in another zone.

### Evidence collection

```powershell
kubectl version
kubectl get nodes -o wide
kubectl get pdb -A -o wide
kubectl get statefulsets -A
kubectl get pvc -A
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get events -A --sort-by=.lastTimestamp
```

### Incident decisions

1. **Freeze additional upgrade stages** and establish incident command.
2. Separate webhook admission errors from storage scheduling and PDB failures.
3. Identify the webhook service, serving certificate issuer/SAN and CA trust configuration.
4. Restore supported webhook trust or roll forward the controller; avoid globally disabling admission security.
5. Preserve StatefulSet quorum and volume attachment safety; do not force-delete a potentially active database writer.
6. Add correctly zoned capacity or execute a DB-approved failover where appropriate.
7. Determine whether the cordoned node is safe to return to service; do not uncordon automatically.
8. Verify new Pods can be admitted and scheduled, databases can read/write, and customer-facing SLIs recover.
9. Document whether the supported recovery path is forward-fix, node-pool replacement or cluster rebuild.

**Rollback limitation:** managed Kubernetes control-plane upgrades often cannot be downgraded in place. Never promise `kubectl rollout undo` will revert a control-plane upgrade.

## 11. Production execution runbook

### Phase A — Preflight

1. Identify cluster, provider, release channel, source/target version and upgrade hop.
2. Review Kubernetes version skew, deprecated APIs, CRDs and add-on compatibility.
3. Confirm backup and restore tests, database quorum and storage topology.
4. Check PDBs, spare capacity, node pool surge and zone placement.
5. Inventory certificates, admission webhooks, workload identities and renewal owners.
6. Define baseline SLOs, error budget, alerting, on-call coverage and rollback authority.
7. Complete staging upgrade and obtain approvals.

### Phase B — Control plane and add-ons

1. Begin the approved maintenance window and change bridge.
2. Execute the **provider-specific** control-plane procedure.
3. Validate API server availability, authentication, RBAC and admission.
4. Upgrade CNI, CSI, CoreDNS, kube-proxy/eBPF and other add-ons in supported order.
5. Confirm networking, storage, DNS, ingress, autoscaling and observability.
6. Stop if admission, storage or application SLOs regress.

### Phase C — Worker node pools

1. Choose one approved worker/pool segment.
2. Confirm PDB allowance, quorum and replacement capacity.
3. Cordon and drain safely using the Eviction API.
4. Replace or upgrade the worker using the provider's supported workflow.
5. Verify Node Ready, fresh Lease, kubelet/runtime/CNI/CSI and application health.
6. Uncordon only if the node is healthy and intended to receive workloads.
7. Continue gradually, observing SLOs between batches.

### Phase D — Acceptance and closure

1. Verify API server and kubelet versions are within supported skew.
2. Confirm Deployments, StatefulSets, DaemonSets, Jobs and admission.
3. Test DNS, Service routing, ingress, network policies and volume operations.
4. Verify database reads/writes, replication, quorum and backup continuity.
5. Validate TLS, workload identity and security policies.
6. Confirm metrics, logs, tracing and alerts remain available.
7. Observe production SLIs for the agreed period and document actual change results.

## 12. Abort, rollback and recovery decision matrix

| Failure | Immediate action | Safe recovery path |
|---|---|---|
| Control-plane API degraded | Freeze further stages | Provider-supported forward-fix or cluster recovery |
| Webhook blocks Pod admission | Inspect cert/CA, service and controller | Repair webhook trust/controller |
| PDB blocks drain | Do not bypass automatically | Restore healthy replicas/add capacity |
| Stateful quorum at risk | Stop eviction | DB-approved failover/recovery |
| PV cannot attach | Preserve identity and volume ownership | Fix zone/CSI/attach constraints |
| Node NotReady after replacement | Keep node out of scheduling | Runtime/CNI/kubelet/provider investigation |
| Application error budget breached | Halt upgrade | Restore healthy capacity and service |
| Certificate trust mismatch | Stop rotation | Staged trust correction with validation |

**Do not confuse rollback of a Deployment with rollback of Kubernetes control-plane binaries, PKI or etcd state.** These have distinct recovery procedures and may not be reversible in place.

## 13. Capstone evidence package

Produce the following deliverables for technical review:

- **Cluster inventory:** version, provider, node pools, topology, runtime, Node conditions and Lease status.
- **Compatibility register:** target release, deprecated APIs, CRDs, CNI/CSI/DNS/admission/ingress versions.
- **Stateful readiness:** backup restore evidence, RPO/RTO, quorum, PV topology and PDB assessment.
- **PKI inventory:** certificate owners, expiry, trust chains, webhook and ingress renewal paths.
- **Maintenance record:** node selection, preflight, cordon/drain output, replacement readiness, uncordon decision.
- **Application acceptance:** Ready replicas, endpoints, customer-facing error/latency metrics, database transactions.
- **Incident report:** failed admission/drain scenario, root-cause hypothesis, mitigation, prevention and ownership.
- **Change closeout:** actual duration, observed impact, exceptions, pending actions and approvals.

## 14. Part 10 acceptance checklist

- [ ] Chapter 046: Node architecture, conditions, Leases and capacity reviewed.
- [ ] Chapter 047: PDB-aware maintenance and safe drain rehearsal completed.
- [ ] Chapter 048: version-skew, deprecated API and add-on compatibility assessed.
- [ ] Chapter 049: certificate and admission webhook trust reviewed.
- [ ] Supported target version and provider upgrade path verified.
- [ ] Backup and **restore** evidence documented.
- [ ] Stateful quorum and PV zone/attachment safety assessed.
- [ ] Spare capacity and PDB allowance confirmed.
- [ ] Rehearsal node restored to its intended scheduling state.
- [ ] Combined admission and storage incident drill completed.
- [ ] Application SLO acceptance and observation plan documented.
- [ ] Independent technical review and actual lab execution completed before marking Lab Validated.

**Part 10 writing milestone:** Chapters 046–050 drafted. Runtime validation and technical review remain pending.

## 15. Cleanup

After confirming the selected node is in its intended scheduling state:

```powershell
kubectl get node $node -o wide
kubectl -n ch050 get deployment,pdb,service,pods
kubectl delete namespace ch050
```

If the node remains cordoned, confirm whether this lab cordoned it and whether operations approves returning it to service. Never uncordon a node that was already unschedulable for another reason. Core inventory labs created no cluster resources.

## 16. References

- [Kubernetes Nodes](https://kubernetes.io/docs/concepts/architecture/nodes/)
- [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [Disruptions and PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes Deprecation Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [Kubernetes PKI](https://kubernetes.io/docs/setup/best-practices/certificates/)
- [Kubeadm Certificate Management](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-certs/)
- [EKS Update Cluster](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [AKS Upgrade Cluster](https://learn.microsoft.com/en-us/azure/aks/upgrade-cluster)
- [GKE Cluster Upgrades](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-upgrades)

**Next:** Chapter 051 — High Availability Control Plane Design (Part 11).
