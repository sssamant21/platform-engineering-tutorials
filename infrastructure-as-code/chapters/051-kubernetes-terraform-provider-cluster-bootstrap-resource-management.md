# Chapter 051 — Kubernetes Infrastructure as Code Foundations, Terraform Provider and Cluster Resource Management

**Part 11 — Kubernetes and Helm | Chapter 051/120**  
**Audience:** SRE, DBRE, Kubernetes platform engineering, security and GitOps teams.  
**Prerequisites:** Chapters 001–035, Kubernetes administration, Terraform >=1.7, Python >=3.9; optional sandbox cluster.

> **Roadmap clarification:** The master curriculum defines **Part 11 (Chapters 051–055) as “Kubernetes and Helm”** but does **not** assign an exact Chapter 051 title. This chapter title is a newly selected foundation title, not an existing roadmap title.

> **Safety:** Mandatory exercises are offline Terraform \`terraform_data\` contracts, not live Kubernetes changes. The example Kubernetes provider resources are review-only. Do not use \`terraform apply\` against production clusters or store Kubernetes Secrets in Terraform state. Policy fixtures attest to declared inputs, **not actual cluster security**.

## 1. Learning objectives

Understand Kubernetes as a declarative API, Terraform as a desired-state controller, and the operational boundary between cloud infrastructure, Kubernetes cluster configuration, application deployment, Helm and GitOps. Configure Kubernetes and Helm providers securely; reason about namespaces, service accounts, RBAC, ConfigMaps, Secrets, resource quotas, network policy, deployments, StatefulSets, PV/PVC, CRDs, admission policy, server-side apply and drift. Build a repeatable, offline Terraform contract lab with negative policy tests, troubleshoot production SRE/DBRE incidents, and score an operational acceptance review.

## 2. Architecture and control-plane boundaries

~~~text
                 Git PR + policy + CI
                         |
              OIDC / scoped identity
                         |
         Terraform cloud-infrastructure root
             |                     |
       EKS / AKS / GKE          VPC / DNS / IAM
             |
         cluster ready
             |
       separate Kubernetes root
       provider pinned + scoped RBAC
             |
       namespaces, quotas, policies
             |
          Helm/GitOps stage
             |
     Deployments / StatefulSets
             |
     PVC / Services / Ingress
             |
      Metrics, traces, backups
~~~

**Avoid circular bootstrap:** A Terraform root that creates a cluster and configures the Kubernetes provider using outputs unknown until apply can fail during provider initialization. Use separate states and CI stages. Wait for API health, CNI, CoreDNS, CSI and RBAC readiness before the Kubernetes stage. Separate **platform ownership** (cluster and shared policies) from **application ownership** (workload manifests). Do not allow Terraform and Argo CD/Flux to reconcile the same field or resource without an explicit handoff.

## 3. Terraform Kubernetes provider fundamentals

The HashiCorp Kubernetes provider talks to the Kubernetes API using credentials and API discovery. Pin provider versions, validate compatibility, and supply an approved kubeconfig context or workload identity. Never rely on an implicit default context in CI. Authenticate with short-lived credentials; distinguish local workstation \`kubectl\` access from provider authentication. Keep remote state encrypted, access-controlled, locked and isolated by cluster/environment.

Resource examples include \`kubernetes_namespace_v1\`, \`kubernetes_service_account_v1\`, \`kubernetes_role_v1\`, \`kubernetes_role_binding_v1\`, \`kubernetes_resource_quota_v1\`, \`kubernetes_limit_range_v1\`, \`kubernetes_network_policy_v1\`, \`kubernetes_deployment_v1\`, \`kubernetes_service_v1\` and \`kubernetes_manifest\`. The manifest resource and CRD-backed types may require the CRD to exist **before** planning, so stage CRDs separately. Confirm current schema before applying.

### Provider ownership and drift

Terraform plans against state and observed API objects; Kubernetes controllers can mutate defaulted fields, labels, annotations and replicas. HPA may change replicas while Terraform tries to enforce a fixed value. GitOps controllers can create oscillating drift if they own the same resource. Define field ownership, avoid broad \`ignore_changes\` that conceals security drift, and use an agreed change process for import, move, delete and replace. Do not use Terraform state as the only inventory or recovery mechanism.

## 4. Namespace isolation and multitenancy

Namespaces partition namespaced resources but are not security boundaries by themselves. Implement RBAC least privilege, namespace quotas, LimitRanges, network policy with CNI enforcement, Pod Security Admission (restricted where compatible), service-account token handling, resource requests/limits and per-team access. Kubernetes NetworkPolicy is generally additive and requires a supporting CNI; default-deny ingress **and** egress where appropriate, then allow DNS and required application/database paths explicitly. Test real connectivity.

| Control | Failure mode | Verification |
|---|---|---|
| RBAC | accidental cluster-admin grants | \`kubectl auth can-i\` as target identity |
| NetworkPolicy | default deny breaks DNS or DB | controlled egress probe |
| ResourceQuota | new pods remain Pending | \`kubectl describe resourcequota\` |
| LimitRange | unexpected defaults or rejected pods | admission errors and requests/limits |
| Pod Security | privileged workload rejected | admission audit/warn/enforce |
| Service account | default identity overprivileged | token/automount and role bindings |
| StorageClass/PVC | wrong zone, reclaim or expansion | PVC/PV/CSI events |

## 5. Deployments, stateful workloads and reliability

Deployments manage stateless rollout, ReplicaSets and pod replacement. Use readiness, liveness and startup probes appropriately; an aggressive liveness probe can cause restart storms. Use immutable image digests, resource requests, topology spread, PDBs and controlled rollout strategy. StatefulSets provide stable identities and ordered operations but **not database replication or backups**. For PostgreSQL/MongoDB/Kafka on Kubernetes, prefer an approved operator with tested backup/restore, fencing, storage topology, security and DBRE procedures. PVC reclaim policies and CSI snapshots must be reviewed; a disk snapshot alone may not be transaction-consistent.

HPA, VPA and cluster autoscaler solve different scaling problems. Coordinate HPA with connection pooling: \`replicas × per-pod max connections\` must stay under database headroom. For EKS/AKS/GKE, use workload identity rather than static cloud credentials in Secrets.

## 6. Helm and GitOps integration

Helm packages templated Kubernetes resources and tracks releases. Terraform's Helm provider can deploy a release, but upgrades and rollback semantics are not identical to Terraform state transitions. Separate platform Helm charts (CNI, CSI, ingress, cert-manager, monitoring) from app charts and CRDs. Prefer Argo CD/Flux for ongoing application reconciliation where the organization has GitOps operating standards. Avoid using Helm and Terraform to modify the same resource concurrently. Pin chart versions and image digests, review chart values, schema and hooks, and test uninstall behavior, especially for PVCs and CRDs.

## 7. Executable labs

Directory: \`infrastructure-as-code/labs/chapter-051/\`.

### Lab A — Offline namespace, RBAC, policy and operations contracts

~~~bash
cd infrastructure-as-code/labs/chapter-051
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter051.tfplan
terraform apply chapter051.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
~~~

Four \`terraform_data\` resources model cluster targeting, tenant isolation, workload reliability and operational approval. Production preconditions block wildcard cluster-admin, default service-account use, missing network policy, unpinned images, absent backup/DBRE controls and unapproved changes. This creates **no namespace or workload**.

### Lab B — Fail-closed declared-evidence policy

~~~bash
python3 kubernetes_gate.py fixtures/kubernetes-safe.json fixtures/plan-safe.json kubernetes-policy.json
python3 kubernetes_gate.py fixtures/kubernetes-unsafe.json fixtures/plan-destructive.json kubernetes-policy.json
python3 -m unittest -v test_kubernetes_gate.py
bash run-preflight.sh
~~~

Safe evidence must pass; unsafe and destructive plans must fail. The plan fixture is a **simplified action contract**, not a full \`terraform show -json\` parser. A passing fixture is not evidence of actual RBAC or NetworkPolicy enforcement.

### Lab C — Optional sandbox cluster

1. Obtain an explicitly approved context and confirm cluster name, API server endpoint, namespace and service identity.
2. Inspect \`examples/kubernetes-provider.tf.example\`; use it as a **separate root**, never blindly apply.
3. Validate provider version, credentials, RBAC and namespace/quotas in a disposable cluster.
4. Test deny-by-default networking, DNS/DB exceptions, pod security admission, image digest, PDB and rolling deployment.
5. Observe and document actual behavior, rollback and cleanup.

### Lab D — Drift and ownership tabletop

Simulate HPA changing replicas, an admission webhook adding labels, Argo CD restoring a Deployment, a missing CRD and a Terraform delete/replace plan. Decide who owns each field; test safe import/handoff and deny destructive operations. Record approved remediation and an incident timeline.

## 8. Production SRE/DBRE incidents

| Incident | Signals | Investigation | Recovery |
|---|---|---|---|
| Wrong kubeconfig context | changes in unexpected cluster | provider context, audit logs | stop pipeline, contain and restore |
| RBAC 403 | Terraform apply forbidden | effective roles, bindings | scoped role correction |
| CRD missing | manifest plan failure | CRD discovery and ordering | stage CRD installation |
| HPA/Terraform drift | perpetual replica diffs | field ownership, HPA | transfer ownership explicitly |
| NetworkPolicy outage | DNS/DB timeouts | CNI enforcement, policies, egress | restore minimal allowed flows |
| ResourceQuota exhaustion | Pending pods | quota, requests/limits | approve capacity change |
| Admission rejection | pods denied | PSA, policy webhooks | correct workload security |
| CrashLoopBackOff | restarts, 5xx | probes, OOM, config | rollback and tune |
| PVC zone mismatch | Pending StatefulSet | PV node affinity, CSI | safe reschedule/restore |
| DB connection storm | too many clients | replicas × pool size | throttle, pool and coordinate DBRE |
| Helm release stuck | pending upgrade | hooks, ownership, events | controlled rollback |
| Terraform delete plan | namespace/app deletion | state drift, provider diff | block and review |

## 9. Troubleshooting commands

~~~bash
kubectl config current-context
kubectl cluster-info
kubectl auth can-i get deployments -n NAMESPACE
kubectl get namespaces
kubectl get resourcequota,limitrange,networkpolicy -n NAMESPACE
kubectl get deploy,sts,ds,pods,pdb,hpa -n NAMESPACE
kubectl get pvc,pv -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe pod POD -n NAMESPACE
kubectl logs deploy/APP -n NAMESPACE --previous
helm list -A
terraform providers
terraform state list
terraform plan -var-file=environments/dev.tfvars
~~~

Use read-only access for initial diagnosis. Do not print Secret contents or token-bearing kubeconfig. Validate context before every mutating command.

## 10. Production runbooks

**Pre-change:** verify cluster identity, approved context, provider pinning, namespace ownership, RBAC, network policy, quotas, Pod Security, image digests, PDB, backup and DBRE sign-off. Reject unexpected destroy/replace.

**RBAC lockout:** preserve audit logs, verify impersonated effective permissions, use approved break-glass identity and restore least privilege.

**NetworkPolicy outage:** inspect CNI support, namespace labels, DNS and DB egress, test connectivity, restore narrowly scoped rules; do not leave broad allow-all in place.

**Stateful workload disruption:** stop unsafe rollout, assess PVC/CSI/zone and DB quorum, coordinate DBRE, restore from tested backup where required, validate writes.

**GitOps/Terraform conflict:** pause one controller under approval, identify source of truth, reconcile state and ownership, then resume safely.

**Cluster incident:** establish incident command, freeze changes, restore core DNS/CNI/CSI/identity, verify app health and data integrity, measure recovery and record postmortem.

## 11. Acceptance rubric (100 points)

| Domain | Points |
|---|---:|
| Kubernetes provider, state and bootstrap architecture | 20 |
| Namespace isolation, RBAC, policy and identity | 20 |
| Workload reliability, storage and DBRE controls | 20 |
| Terraform labs and automated negative policy tests | 15 |
| Production incidents, drift and recovery runbooks | 15 |
| Observability, FinOps, audit and approvals | 10 |

Pass **>=85/100 with zero critical failures**, including accidental production targeting, wildcard cluster-admin, missing default-deny where required, leaked Secrets, unapproved namespace deletion or untested stateful restore. Publication is **not** operational acceptance.

## 12. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
~~~

Destroy only the offline contract resources or an explicitly disposable cluster sandbox. Review: Why split cluster bootstrap from Kubernetes provider? What changes when HPA and Terraform both own replicas? Why is a StatefulSet not a backup? What is the difference between Kubernetes NetworkPolicy and cloud firewall? Why should Helm/GitOps ownership be explicit?

**Next proposed:** Chapter 052 — Kubernetes Namespaces, RBAC, Network Policies and Multitenancy with Terraform.
