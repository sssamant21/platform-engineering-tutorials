# Chapter 101 — Build a Production-Ready Kubernetes Cluster

**Track:** Kubernetes Administration · **Part 21 — Final Enterprise Kubernetes Capstone**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, cloud/platform engineers, security and reliability reviewers  
**Prerequisites:** Chapters 001–100; approved disposable AWS EKS, Azure AKS, GKE, or self-managed lab account; kubectl, PowerShell, Git, IaC tooling, and access to cloud billing, observability and identity systems.

## Project objective

Design, provision, harden and validate a production-*ready* Kubernetes cluster using repeatable infrastructure-as-code and evidence-based operational controls. **Production-ready** means the design and acceptance criteria are demonstrated in an authorized test environment; this chapter does not authorize direct production provisioning.

**Required outcomes:** reviewed architecture, reproducible build, least-privilege identity, secure network and storage, resilient node capacity, controlled add-ons, policy enforcement, monitoring, backup/restore, cost governance, change management and operational handoff.

## 1. Reference architecture

```text
                    Identity / SSO / Cloud IAM
                              |
                    Kubernetes API endpoint
                              |
              Managed or self-managed control plane
                              |
           +------------------+------------------+
           |                  |                  |
      Zone A nodes       Zone B nodes       Zone C nodes
           |                  |                  |
      System pools        App pools         Optional GPU
           +------------------+------------------+
                              |
                   CNI / DNS / Ingress / CSI
                              |
            Namespaces + RBAC + PSA + NetworkPolicy
                              |
                 GitOps-managed applications
                              |
        Metrics / Logs / Traces / Alerts / Backups
```

A managed control plane can reduce operational burden but does not eliminate responsibility for node pools, CNI, IAM, data protection, upgrades or workload resilience. For self-managed clusters, etcd quorum and control-plane backups become explicit operator responsibilities.

## 2. Project rules and safety

- Use a **disposable nonproduction account/project/subscription** with a documented budget and expiry.
- Obtain approval for network ranges, cloud IAM roles, public endpoints and billable resources.
- Pin Kubernetes, provider, module, add-on and container versions to supported releases.
- Never commit credentials, kubeconfigs, cloud secrets or unencrypted state files.
- Do not create a public, unrestricted API endpoint merely for convenience.
- Treat all cloud cost figures as provider-, region- and time-dependent; verify current rates.
- Keep an independent, reviewed break-glass access method.
- Record tests as **Not executed** until actually run; publication is not proof of validation.

## 3. Lab 01 — Requirements and service-level objectives

Create a design brief defining:
- Environment, provider, region and data residency.
- Target availability, latency, RPO and RTO.
- Expected node/workload count, peak traffic and growth.
- Security/compliance obligations and tenant isolation.
- Workload mix: stateless, stateful, batch and optional GPU.
- Change window, upgrade cadence, maintenance ownership and on-call.
- Cost ceiling, tagging and resource expiry.

**Acceptance:** reviewers approve measurable SLOs, failure domains and budget before provisioning.

## 4. Lab 02 — Choose deployment model and failure domains

Compare EKS, AKS, GKE and self-managed clusters against requirements. Document the shared-responsibility boundary and provider-specific constraints: node OS image, IAM/workload identity, CNI, load balancer, CSI, autoscaler, supported version skew and regional availability.

For HA, distribute suitable node pools across multiple zones where supported. Multiple zones alone do not guarantee app HA: enforce replica distribution, readiness, PDBs and sufficient spare capacity.

## 5. Lab 03 — Infrastructure-as-code repository

Suggested layout:

```text
kubernetes-platform/
  README.md
  docs/
    architecture.md
    adr/
    runbooks/
  infra/
    modules/
    environments/staging/
  clusters/
    staging/
      platform/
      apps/
  policies/
  monitoring/
  tests/
  evidence/
```

Use Terraform, OpenTofu, Pulumi, Bicep, CloudFormation or another approved IaC tool. Configure remote encrypted state with access controls, locking where supported, versioning and recovery. Protect the main branch and require plan review.

```powershell
git status
git diff --check
terraform fmt -check -recursive
terraform validate
terraform plan -out=staging.tfplan
```

Terraform commands are illustrative and require a configured root module and provider credentials. Treat saved plan files as sensitive; do not commit them.

## 6. Lab 04 — Provision networking

Design private subnets, pod/service CIDRs, nonoverlapping network ranges, outbound egress, private endpoints, DNS, NAT and ingress boundaries. Confirm whether the provider CNI uses VPC/VNet-native Pod IPs, overlays or delegated address ranges.

**Checks:** no unintended public nodes, restricted control-plane endpoint, network routes, DNS resolution, ingress TLS and egress allowlisting. Validate cross-zone and internet egress costs. Do not assume NetworkPolicy enforcement without checking the CNI.

## 7. Lab 05 — Create cluster and node pools

Provision the control plane and at least one dedicated system pool plus application pool where supported. Select machine types from measured CPU/memory requirements and DaemonSet overhead. Document maximum node count and autoscaling guardrails.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl describe nodes
```

**Acceptance:** nodes join with expected versions, zones, labels, taints and allocatable capacity. Node Ready is necessary but not sufficient.

## 8. Lab 06 — Identity, RBAC and workload identity

Configure human access through approved SSO/federation, least-privilege RBAC and short-lived credentials. Use cloud workload identity rather than static keys for Pods wherever supported.

```powershell
kubectl auth can-i get pods -A
kubectl get serviceaccounts -A
kubectl get clusterrolebindings
kubectl get roles,rolebindings -A
```

Test a permitted operation and a denied privilege escalation with a non-admin test identity. Avoid broad ClusterRoleBindings to `cluster-admin` and default service-account token access.

## 9. Lab 07 — Security baseline and policy-as-code

Enable appropriate Pod Security Admission labels, enforce non-root workloads and restricted capabilities, require approved registries and resource requests, and deploy scoped Kyverno/Gatekeeper policies if supported.

```powershell
kubectl get namespaces --show-labels
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get networkpolicy -A
```

Use audit/warn before enforcement. Validate compliant and deliberately noncompliant manifests. Define webhook outage behavior, exemptions and emergency access without globally bypassing security.

## 10. Lab 08 — DNS, ingress, certificates and networking

Install/version-pin the approved ingress controller or Gateway API implementation, cert management, CoreDNS integration and CNI configuration. Configure TLS with trusted certificates, health probes, rate limiting where needed and controlled egress.

**Positive tests:** internal DNS resolution, approved service-to-service connection and external HTTPS transaction. **Negative tests:** cross-tenant connection denied and unapproved ingress rejected. Confirm network policy actually blocks traffic, not merely that a request times out.

## 11. Lab 09 — Storage and data protection

Install provider-supported CSI drivers and StorageClasses; document reclaim policy, expansion, encryption, snapshots, topology and backup responsibilities.

```powershell
kubectl get storageclass
kubectl get csidrivers
kubectl get pv,pvc -A
kubectl get volumesnapshot -A
```

VolumeSnapshot resources require relevant CRDs and controllers; an API error does not mean the cloud account has no snapshots. Use a disposable PVC to test dynamic provisioning, persistence after Pod restart, snapshot and restore to a *separate* volume. Never delete production PVCs as a lab.

## 12. Lab 10 — GitOps bootstrap and add-on ownership

Bootstrap Argo CD or Flux with a scoped, reviewed repository. Reconcile platform add-ons in dependency order: CNI/DNS/CSI prerequisites, admission controllers, monitoring, ingress and applications. Avoid competing ownership between Helm, GitOps and operators.

```powershell
kubectl get deployments -A
kubectl get crds
kubectl get events -A --sort-by=.lastTimestamp
```

**Acceptance:** approved Git changes converge, drift is detected and a test rollback restores desired state. Record controller identities and emergency recovery procedure if GitOps is unavailable.

## 13. Lab 11 — Observability and actionable alerts

Install a supported metrics/logs/traces stack. Instrument:
- Cluster/API availability and node readiness.
- Pod restarts, OOMKills, Pending Pods and saturation.
- CNI/DNS/ingress and storage health.
- Application request success, p95 latency and throughput.
- GitOps sync, admission webhook and certificate health.
- Backup freshness and cost anomalies.

```powershell
kubectl get pods -A
kubectl top nodes
kubectl top pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

`kubectl top` requires Metrics Server. Trigger one synthetic alert and confirm notification to the correct on-call team. A dashboard existing does not prove alert acceptance.

## 14. Lab 12 — Availability, PDBs and topology

Deploy a disposable app with multiple replicas, readiness/startup probes, anti-affinity or topology spread and a suitable PDB. Validate that it tolerates one test-node drain without violating the defined availability target.

```powershell
kubectl get deployments -A
kubectl get pdb -A
kubectl get nodes -L topology.kubernetes.io/zone
```

Only perform a drain on a disposable node with approved safeguards; do not use `--force` or delete local data to bypass blockers. Account for capacity to survive an expected failure domain.

## 15. Lab 13 — Capacity, autoscaling and cost controls

Measure CPU/memory requests vs observed p95 usage, node allocatable resources, idle capacity, workload scheduling constraints and cost drivers. Configure node autoscaler/Karpenter/provider-managed scaling only after documenting min/max bounds and cloud quota.

Separate **estimated allocated cost** from **actual billed cost**. Track compute, storage, control-plane fees, load balancers, NAT, cross-zone transfer, logging and backups. A request reduction is not a verified saving until billable capacity or charges decrease.

## 16. Lab 14 — Backup, restore and disaster recovery

Define and verify:
- Provider control-plane/etcd recovery responsibility.
- Kubernetes configuration source-of-truth and restore order.
- Persistent volume and database-native backups.
- Secrets and encryption-key recovery.
- RPO/RTO and recovery site readiness.
- DNS/traffic failover and split-brain prevention.

Restore disposable test data to a separate namespace/cluster and verify record counts/checksums and application correctness. A successful backup job without a tested restore does not satisfy this lab.

## 17. Lab 15 — Upgrade readiness and compatibility

Record Kubernetes minor version, support end dates, CNI/CSI/DNS, admission webhooks, operators, CRD served/storage versions and node images. Validate deprecated APIs and version skew before scheduling upgrades.

```powershell
kubectl version
kubectl get apiservices
kubectl get crds
kubectl get nodes -o wide
kubectl get pdb -A
```

Design canary/upgrade waves and a provider-supported recovery plan. Managed control-plane downgrades may not be supported; do not claim `terraform apply` reversal will downgrade a cluster safely.

## 18. Lab 16 — Security and reliability game day

In the disposable environment, run controlled negative tests:
1. Unauthorized tenant operation denied by RBAC.
2. Privileged workload denied by admission.
3. Cross-tenant network request denied.
4. Bad application rollout detected and reverted via GitOps.
5. One node drained while service remains healthy.
6. Backup restored and verified.
7. Alert reaches the correct owner.

Capture timestamps, API responses, application metrics and recovery time. If a control is not tested, mark it Not executed rather than Passed.

## 19. Lab 17 — Operational handoff and runbooks

Deliver these runbooks:
- Cluster/API access failure.
- Node NotReady and resource pressure.
- Pod Pending/CrashLoopBackOff/OOMKilled.
- DNS/CNI/ingress incident.
- PVC provisioning and storage latency.
- GitOps reconciliation and admission failure.
- Certificate expiration and credential rotation.
- Backup/restore and region failure.
- Cluster/node pool upgrade.
- Cost anomaly and scaling failure.

Each runbook needs owner, trigger, diagnostics, interpretation, stop conditions, escalation, mitigation, rollback and verification.

## 20. Lab 18 — Final acceptance report

| Domain | Evidence | Pass condition |
|---|---|---|
| Architecture | ADRs, diagram, provider choice | Reviewed against requirements |
| IaC | Reproducible plan/apply and state controls | Build repeatable |
| Networking | DNS, TLS, ingress, egress tests | Allowed flows work; denied flows blocked |
| Identity | RBAC and workload identity tests | Least privilege demonstrated |
| Policy | PSA/admission positive/negative tests | Enforcement demonstrated |
| Resilience | Node disruption and app SLO | Defined SLO maintained |
| Storage | Provision, backup, restore | Test data verified |
| Observability | Dashboard and synthetic alert | Alert delivered |
| GitOps | Reconcile and rollback | Intended revision restored |
| DR | RPO/RTO test evidence | Targets met |
| FinOps | Billing and capacity baseline | Costs attributed and budgeted |
| Operations | Runbooks, escalation, approvals | Independent reviewer signs off |

**Acceptance checklist:**
- [ ] All required labs executed in an authorized nonproduction environment.
- [ ] Cloud identity, budget, expiry and cleanup owner recorded.
- [ ] Cluster can be rebuilt from reviewed IaC and GitOps.
- [ ] Security and network isolation tested with negative controls.
- [ ] Node, storage and application recovery exercises passed.
- [ ] Backups actually restored and checked for integrity.
- [ ] Alerting and escalation paths verified.
- [ ] Cost and capacity limits documented.
- [ ] Operational runbooks reviewed by someone other than the author.
- [ ] Evidence and outstanding risks linked to immutable revisions.

## 21. Troubleshooting matrix

| Symptom | Check first | Typical cause |
|---|---|---|
| Nodes fail to join | IAM, bootstrap, networking, image | Incorrect identity/routes |
| Pods Pending | Events, requests, quotas, taints | Scheduling/capacity |
| DNS fails | CoreDNS, CNI, policy, upstream | Network or resolver |
| PVC Pending | CSI, StorageClass, topology, quotas | Provisioning constraints |
| API requests denied | RBAC, webhook, PSA | Authorization/admission |
| GitOps drift | Source revision, sync health, ownership | Competing controllers |
| SLO fails despite Ready Pods | App traces, dependencies, saturation | Service-level fault |
| Cost rises unexpectedly | Node-hours, NAT, LB, disks, logs | Non-CPU billable driver |

## 22. Cleanup and financial closeout

Use IaC to destroy **only** the disposable lab environment after preserving required evidence and confirming no shared dependencies. Review and remove orphaned disks, load balancers, snapshots, public IPs and GPU pools according to retention rules. Verify cloud billing and that no cluster resources remain chargeable. Do not run destructive cleanup against production.

## 23. Final capstone sequence

- **101:** Build a production-ready Kubernetes cluster.
- **102:** Deploy a highly available stateful application.
- **103:** Simulate complex Kubernetes failures.
- **104:** Upgrade, recover and validate the production cluster.
- **105:** Kubernetes Administrator and SRE Final Assessment.

**Draft status:** chapter and lab instructions are published but not executed or independently reviewed.

**Next:** Chapter 102 — Deploy a Highly Available Stateful Application.
