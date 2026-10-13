# Chapter 098 — Multi-Cluster Administration and Fleet Management

**Track:** Kubernetes Administration · **Part 20 — Advanced Platform Engineering and Production Operations**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, platform engineers, cloud architects  
**Prerequisites:** Chapters 006–010, 041–050, 071–090, 091–097; kubectl, PowerShell, Git, read access to cloud cluster inventories, and at least two disposable clusters for the labs.

## Learning outcomes

Design multi-cluster fleet topology; inventory clusters and ownership; isolate credentials and permissions; standardize GitOps, admission policies and add-ons; compare networking and service discovery patterns; centralize observability; manage upgrades, cost and drift; exercise cross-cluster recovery; and produce a fleet operational readiness report.

## 1. Multi-cluster architecture

```text
                   Fleet governance / inventory
                             |
               +-------------+-------------+
               |                           |
         GitOps / Policy               Observability
               |                           |
      +--------+--------+         +--------+--------+
      |                 |         |                 |
   Cluster A         Cluster B    Metrics          Logs
  Region/Env A      Region/Env B   Traces           Alerts
      |                 |
  Namespaces         Namespaces
  Node pools         Node pools
  Workloads          Workloads
```

Each Kubernetes cluster has its own API server, control plane, etcd state, nodes, admission configuration and failure domain. A fleet management plane may coordinate them, but a fleet controller does not make separate clusters share a single scheduler or guarantee application failover.

**Choose multi-cluster when justified** by isolation, compliance, regional latency, failure domains, cloud portability, capacity constraints or upgrade risk. Consider the additional operational burden: more certificates, identities, upgrades, policies, observability and disaster recovery plans.

## 2. Fleet topology and tenancy decisions

| Pattern | Benefit | Risk/tradeoff |
|---|---|---|
| Separate staging and production clusters | Stronger change isolation | Environment drift |
| Regional active/passive | Recovery site available | Replication lag, standby cost |
| Regional active/active | Better locality and resilience | Data consistency, traffic control |
| Dedicated tenant clusters | Stronger tenant boundary | High operational cost |
| Multi-cloud fleet | Provider diversification | Identity/network/operations complexity |
| Hub-and-spoke management | Central governance | Management-plane dependency |

Document where applications, data, secrets and DNS live. Do not assume that deploying identical manifests into two clusters automatically creates a disaster recovery capability.

## 3. Lab 01 — Safe fleet inventory

Use two disposable clusters or approved non-production contexts. On Windows PowerShell:

```powershell
kubectl config get-contexts
kubectl config current-context
kubectl --context <staging-context> cluster-info
kubectl --context <dr-context> cluster-info
kubectl --context <staging-context> get nodes -o wide
kubectl --context <dr-context> get nodes -o wide
```

Replace placeholders with exact context names. Record cluster UID if available through your provider inventory, API endpoint, provider, region, Kubernetes version, CNI, node pools, owner, environment, cost center, backup policy and SLO.

**Acceptance:** every cluster has a unique identifier and documented operational owner. Never identify a cluster solely by a friendly context name, which may be reused.

## 4. Lab 02 — Kubeconfig and identity separation

```powershell
kubectl config view --minify
kubectl config get-users
kubectl --context <staging-context> auth can-i get pods -A
kubectl --context <dr-context> auth can-i get pods -A
```

Prefer short-lived identity federation (cloud SSO/OIDC) and least-privilege RBAC. Avoid embedding long-lived tokens and client keys in shared kubeconfig files. Treat kubeconfig as sensitive material: a malicious exec credential plugin can run local commands. Review external kubeconfig sources before merging them.

For EKS, AKS and GKE, use provider-supported identity integrations and confirm the intended cloud account/subscription/project before every change.

## 5. Lab 03 — Fleet metadata and ownership

Define a central inventory record:

```yaml
clusterId: staging-east-01
environment: staging
provider: aws
region: us-east-1
ownerTeam: platform
costCenter: engineering
criticality: nonproduction
gitopsRepository: platform-fleet
backupTier: standard
kubernetesVersion: REPLACE_WITH_OBSERVED_VERSION
```

This is an **inventory document**, not a Kubernetes API object. Store it in a controlled repository or CMDB. Include expiry/review dates, compliance tier, maintenance window, contact, dependencies and approved exception records. Reconcile inventory with provider APIs regularly to discover unmanaged clusters.

## 6. Lab 04 — Fleet GitOps repository layout

```text
fleet/
  clusters/
    staging-east/
      kustomization.yaml
      platform/
      apps/
    staging-west/
      kustomization.yaml
      platform/
      apps/
    production-east/
      kustomization.yaml
      platform/
      apps/
  base/
    monitoring/
    admission/
    namespaces/
  overlays/
    staging/
    production/
  policies/
  tests/
  evidence/
```

Use Argo CD ApplicationSet or Flux Kustomization patterns only after validating version-specific security. Avoid a shared controller identity with unrestricted access to all production clusters when separate scoped identities suffice. Protect production overlays and cluster registration with reviews.

**Acceptance:** staging and DR clusters reconcile approved baselines while retaining documented regional differences.

## 7. Lab 05 — Configuration and drift detection

Compare API versions, installed CRDs, storage classes, admission policies, CNI and observability:

```powershell
kubectl --context <staging-context> version
kubectl --context <dr-context> version
kubectl --context <staging-context> get crds
kubectl --context <dr-context> get crds
kubectl --context <staging-context> get storageclass
kubectl --context <dr-context> get storageclass
kubectl --context <staging-context> get validatingwebhookconfigurations
kubectl --context <dr-context> get validatingwebhookconfigurations
```

Classify differences as intentional, unauthorized or unknown. Do not blindly apply a production configuration to DR: region, identity, storage class and endpoint differences may be required.

## 8. Lab 06 — Policy consistency and security posture

Across both clusters, compare:
- Namespace ownership labels and Pod Security Admission levels.
- Kyverno/Gatekeeper policies and their enforcement modes.
- RBAC and service account/cloud identity mappings.
- NetworkPolicy coverage and CNI enforcement.
- Image provenance, secrets integration and audit logging.
- Encryption, certificate lifecycle and API exposure.

```powershell
kubectl --context <staging-context> get networkpolicy -A
kubectl --context <dr-context> get networkpolicy -A
kubectl --context <staging-context> get clusterrolebinding
kubectl --context <dr-context> get clusterrolebinding
```

Use policy-as-code and conformance tests to measure parity; matching manifest names alone do not prove identical enforcement.

## 9. Lab 07 — Cross-cluster networking and DNS

Evaluate three separate concerns:
1. **User traffic routing:** DNS, global load balancing, CDN or traffic manager.
2. **Service-to-service connectivity:** private network, gateways or multi-cluster service discovery.
3. **Data replication:** database-specific mechanisms and recovery consistency.

A Kubernetes ClusterIP Service is not automatically reachable from another cluster. Multi-Cluster Services, service mesh or provider-specific integrations require supported implementations and explicit network/security setup. Document CIDR overlap, firewall rules, egress, certificates, health checks and regional failure behavior.

**Exercise:** demonstrate that an application in cluster A can reach a deliberately exposed and authorized endpoint in cluster B, with TLS verification and negative access control tests. Do not expose internal Services to the public internet merely to pass the lab.

## 10. Lab 08 — Fleet observability and alert routing

```powershell
kubectl --context <staging-context> get pods -A
kubectl --context <dr-context> get pods -A
kubectl --context <staging-context> get events -A --sort-by=.lastTimestamp
kubectl --context <dr-context> get events -A --sort-by=.lastTimestamp
```

Central telemetry should include cluster identity, provider, region, environment, namespace and workload. Alert on control-plane reachability, node readiness, workload SLOs, GitOps drift, admission failures, certificate expiry, storage pressure and backup freshness. Avoid duplicating identical alerts from every cluster without ownership and routing.

**Acceptance:** a test incident is attributed to the correct cluster and reaches the correct on-call owner.

## 11. Lab 09 — Upgrade waves and compatibility

Establish version policy, supported skew, add-on compatibility and maintenance windows. Upgrade in waves:
1. Disposable test.
2. Noncritical staging.
3. DR or canary production cluster (as appropriate).
4. Remaining production fleet.

For managed EKS/AKS/GKE, provider support windows, node images and control-plane sequencing differ. Validate CNI, CSI, DNS, admission webhooks, CRDs, GitOps agents and workload disruption budgets before each wave.

```powershell
kubectl --context <staging-context> get pdb -A
kubectl --context <staging-context> get nodes -o wide
kubectl --context <staging-context> get apiservices
```

Do not infer fleet compatibility from one healthy control plane. Preserve a documented rollback or forward-fix plan; managed control-plane downgrades are often unsupported.

## 12. Lab 10 — Backup and recovery boundaries

Backups must cover more than Kubernetes object manifests when applications have durable state. Inventory:
- etcd/control-plane backup responsibility (provider-managed vs self-managed).
- Persistent volume snapshots and cross-region availability.
- Database-native backups, replication and restore tests.
- Secrets and encryption key recovery.
- GitOps repositories, controller bootstrap and external dependencies.
- DNS, ingress and traffic-routing failover.

Define RPO/RTO per application. **A secondary cluster without current recoverable data does not meet a meaningful DR objective.** Use Chapters 071–075 and cloud-specific chapters for platform backup procedures.

## 13. Lab 11 — Controlled cross-cluster failover rehearsal

In disposable staging, deploy the same stateless demo application to clusters A and B. Use a test-only DNS/traffic-routing mechanism that can point to either endpoint. Record baseline health, shift traffic to B, validate service response and shift back.

```powershell
kubectl --context <staging-context> get deployment,svc -n demo
kubectl --context <dr-context> get deployment,svc -n demo
kubectl --context <dr-context> rollout status deployment/demo -n demo --timeout=180s
```

The demo namespace and Deployment must be created before these commands. For stateful workloads, do **not** simulate failover without replication consistency checks, fencing and split-brain prevention. DNS TTL, client caching and existing connections affect actual recovery time.

## 14. Lab 12 — Fleet incident: lost API connectivity

Simulate an unreachable cluster by using a **test-only invalid context or temporary client-side network restriction**, not by disabling a production API server. Observe monitoring, GitOps reconciliation errors and alert routing.

Capture:
- Detection time and affected cluster identity.
- Which workloads continue running despite management-plane loss.
- Whether changes and deployments are blocked.
- Recovery of authenticated API access.
- GitOps catch-up behavior after connectivity returns.
- Remaining risks if the control plane or network is truly unavailable.

A management-plane outage does not necessarily stop existing Pods, but can impair scheduling, controller actions and recovery.

## 15. Lab 13 — Fleet incident: configuration drift

Introduce a safe staging-only configuration drift (for example, an application label change) in one cluster. Verify detection through GitOps or conformance checks, identify the source revision and restore intended state. Confirm the other cluster remains unchanged.

**Acceptance:** drift is localized, explained and resolved without a global configuration overwrite.

## 16. Lab 14 — Capacity and FinOps across clusters

Collect node-hours, instance families, reserved/spot mix, storage, load balancers, egress and idle capacity per cluster. Compare regional costs and availability requirements using effective billing rates, not list prices.

```powershell
kubectl --context <staging-context> top nodes
kubectl --context <dr-context> top nodes
kubectl --context <staging-context> get nodes -L topology.kubernetes.io/zone
kubectl --context <dr-context> get nodes -L topology.kubernetes.io/zone
```

Metrics Server is required for `top`. Keep DR standby capacity and fault tolerance explicit; apparent idle spend may be an intentional resilience investment.

## 17. Lab 15 — Fleet governance acceptance

- [ ] Every cluster has a unique identity, owner, environment and inventory record.
- [ ] Cloud accounts/projects/subscriptions and credentials are segregated.
- [ ] GitOps scopes, production approvals and exception process tested.
- [ ] Security baselines and justified differences documented.
- [ ] Network and DNS paths validated with negative security controls.
- [ ] Telemetry and alerts include correct cluster attribution.
- [ ] Upgrade waves and add-on compatibility reviewed.
- [ ] Backups, keys and data restoration paths verified.
- [ ] Cross-cluster failover measured against stated RPO/RTO.
- [ ] API connectivity loss and drift recovery rehearsed.
- [ ] Shared and per-cluster costs reconciled.
- [ ] Runtime evidence and independent technical review recorded.

## 18. Fleet operations runbook

| Symptom | First checks | Recovery approach |
|---|---|---|
| Wrong cluster modified | Current context, audit events, Git revision | Stop changes, assess impact, restore intended state |
| One cluster unreachable | Identity, DNS, network, provider status | Restore access; avoid blind changes |
| GitOps fleet drift | Source revision, controller logs, permissions | Reconcile scoped approved changes |
| Regional application outage | Health, traffic manager, data replication | Execute application-specific DR runbook |
| Upgrade fails on one cluster | API compatibility, CNI/CSI, webhooks | Halt rollout wave, forward-fix or supported rollback |
| Cross-cluster traffic fails | DNS, TLS, routes, firewall, service health | Restore approved network path |
| Cost anomaly | Node-hours, egress, idle pools, storage | Identify billed driver and owner |

## 19. Cleanup and production guardrails

Remove only demo workloads and test routing objects created for this lab, via GitOps where applicable. Never delete production clusters, shared fleet registration, control-plane credentials, backups or cross-region infrastructure as a cleanup shortcut. Confirm no temporary load balancers, disks or test clusters remain billable.

## Production takeaways

Fleet management is not merely running `kubectl` against several contexts. It is the discipline of maintaining consistent identity, policy, upgrades, observability, cost attribution and recoverability across independent failure domains. Keep changes scoped, auditable and rehearsed.

**Draft status:** lab exercises have not been executed or independently reviewed in this publication workflow.

**Next:** Chapter 099 — Production Change Management and SRE Runbooks.
