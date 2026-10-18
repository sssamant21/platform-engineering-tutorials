# Chapter 052 — Kubernetes Namespaces, RBAC, Network Policies and Multitenancy with Terraform

**Part 11 — Kubernetes and Helm | Chapter 052/120**  
**Audience:** Platform engineers, Kubernetes administrators, SRE, DBRE and security engineers.  
**Prerequisites:** Chapters 051, Terraform >=1.7, Python >=3.9. Live exercises require an explicitly approved disposable Kubernetes cluster.

> **Evidence and safety:** The required Terraform lab uses only \`terraform_data\`, with no Kubernetes API or credentials. Optional \`*.tf.example\` manifests are review-only and must be validated separately. The policy gate checks declared evidence and a simplified plan fixture, **not actual Kubernetes admission, RBAC or network enforcement**. Never run the examples against production without approval.

## 1. Learning outcomes

Design tenant isolation using namespaces, Kubernetes RBAC, ServiceAccounts, NetworkPolicy, ResourceQuota, LimitRange and Pod Security Admission (PSA); implement Terraform ownership and safe dependency ordering; build negative automated policy tests; validate effective permissions and network flows in a sandbox; troubleshoot production SRE/DBRE incidents and execute an audited multitenancy runbook.

## 2. Enterprise reference architecture

~~~text
                    Platform CI / OIDC identity
                              |
                   Terraform state + policy
                              |
                    Approved cluster context
                              |
           Platform-owned namespace provisioning
             /               |                \
       team-a-prod        team-b-prod       shared-platform
         |                    |                 |
    quotas + limits      quotas + limits     DNS/ingress/CSI
    restricted PSA       restricted PSA      monitoring
    least-privilege RBAC + ServiceAccounts
    default-deny ingress and egress NetworkPolicies
         |                    |
      workloads             workloads
         |                    |
     explicit allow -> private database / message broker
         |
    audit logs + metrics + SLOs + cost allocation
~~~

**Threat model:** accidental cross-tenant reads, service-account privilege escalation, wildcard RBAC, namespace deletion, data exfiltration, unrestricted egress, DNS failures, noisy-neighbor resource exhaustion, insecure admission, leaked tokens and Terraform/GitOps ownership conflict. Namespaces alone do not isolate nodes, kernel or cluster-scoped resources. For strong adversarial tenant isolation, evaluate dedicated clusters or stronger runtime isolation.

## 3. Namespace and identity architecture

Use a stable naming convention \`<team>-<environment>\`, e.g. \`payments-prod\`. Label namespaces with owner, environment, cost center and PSA mode; do not let tenants alter platform governance labels. Apply resource quotas and LimitRanges before workloads. Namespace deletion can delete **all namespaced objects** and cause data loss; treat deletion/replacement as a destructive change requiring incident-command approval.

Create a dedicated ServiceAccount per workload. Set \`automount_service_account_token = false\` when Kubernetes API access is unnecessary. Avoid static service-account tokens, long-lived cloud keys and the default ServiceAccount. Use EKS Pod Identity/IRSA, AKS Workload Identity or GKE Workload Identity Federation as applicable. Restrict \`secrets\`, \`pods/exec\`, \`rolebindings\`, \`impersonate\`, \`escalate\` and \`bind\` verbs to reviewed operators.

## 4. RBAC policy design

RBAC grants permissions through Role/ClusterRole and RoleBinding/ClusterRoleBinding. A Role is namespaced; ClusterRole may describe namespaced permissions but ClusterRoleBinding can grant cluster-wide scope. Prefer RoleBinding scoped to a namespace, with precise API groups, resources and verbs. Kubernetes RBAC is additive: no explicit deny. The \`*"\` wildcard can unintentionally include future resource types and subresources; avoid it.

~~~yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-reader
  namespace: payments-prod
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-reader-binding
  namespace: payments-prod
subjects:
  - kind: ServiceAccount
    name: app-observer
    namespace: payments-prod
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: app-reader
~~~

Validate effective access using impersonation only when authorized:

~~~bash
kubectl auth can-i list deployments -n payments-prod --as=system:serviceaccount:payments-prod:app-observer
kubectl auth can-i get secrets -n payments-prod --as=system:serviceaccount:payments-prod:app-observer
kubectl auth can-i create rolebindings -n payments-prod --as=system:serviceaccount:payments-prod:app-observer
~~~

Expected: deployments read allowed, Secrets and RoleBinding creation denied. A RoleBinding to a ClusterRole does not automatically grant cluster-wide access; scope is determined by binding and resource.

## 5. NetworkPolicy and CNI enforcement

NetworkPolicy is implemented by a supporting CNI; simply creating policy objects is not evidence of enforcement. Standard Kubernetes NetworkPolicy rules are additive. A namespace's default-deny ingress and egress policies should be followed by narrowly scoped DNS, application ingress and private database egress allowances. Egress DNS may need both UDP and TCP port 53 and the correct CoreDNS namespace/pod labels. Consider kube-dns NodeLocal DNSCache, service mesh, Cilium/Calico features and cloud firewalls separately.

~~~yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: payments-prod
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
~~~

For private PostgreSQL, validate actual destination IP/port and CNI behavior. IPBlock policies may interact with service NAT, external gateways and pod IP ranges. Avoid broad \`0.0.0.0/0\` exceptions. NetworkPolicy does not replace Kubernetes RBAC, TLS, database authentication or cloud network controls.

## 6. Resource governance and Pod Security

ResourceQuota limits namespace aggregate requests, limits, object counts and PVC storage where configured. LimitRange sets defaults/min/max per container or PVC; quotas and LimitRanges can block scheduling/admission. Choose requests from observed p95/p99 usage and HPA behavior, not arbitrary maximums. Apply Pod Security Admission \`restricted\` where workloads are compatible; use \`warn\` and \`audit\` before enforcement during migrations. PSA does not replace image provenance, policy engines, kernel isolation or runtime detection.

## 7. Terraform patterns and ownership

Use separate platform roots for cluster/bootstrap, shared add-ons and tenant resources. Pin \`hashicorp/kubernetes\` provider and explicit context, isolate state by cluster and environment, and avoid mixing cluster creation and Kubernetes API resources in the same initial plan. Terraform resource types include \`kubernetes_namespace_v1\`, \`kubernetes_service_account_v1\`, \`kubernetes_role_v1\`, \`kubernetes_role_binding_v1\`, \`kubernetes_resource_quota_v1\`, \`kubernetes_limit_range_v1\`, and \`kubernetes_network_policy_v1\`.

Never allow Terraform and Helm/Argo CD/Flux to control the same resource without explicit handoff. Do not put Kubernetes Secret values in Terraform state. Plan deletes and replacements must be reviewed independently of \`prevent_destroy\`, which can be removed with configuration changes.

## 8. Executable hands-on labs

All paths relative to \`infrastructure-as-code/labs/chapter-052/\`.

### Lab 1 — Offline Terraform tenant contracts

~~~bash
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=dev.tfplan
terraform apply dev.tfplan
terraform output -json
terraform state list
terraform destroy -var-file=environments/dev.tfvars
~~~

Four \`terraform_data\` contracts represent namespace governance, RBAC, network isolation and operations. Production preconditions reject wildcard permissions, default ServiceAccounts, broad network egress, missing quotas/PSA, missing DBRE approval and unsafe tenant deletion. These are **assertions on declared inputs**, not live Kubernetes resources.

### Lab 2 — Python fail-closed evidence gate

~~~bash
python3 tenant_gate.py fixtures/tenant-safe.json fixtures/plan-safe.json tenant-policy.json
python3 tenant_gate.py fixtures/tenant-unsafe.json fixtures/plan-destructive.json tenant-policy.json
python3 -m unittest -v test_tenant_gate.py
bash run-preflight.sh
~~~

Safe evidence must pass; unsafe evidence must fail. The gate rejects delete/replace actions and unapproved resource types in its **simplified plan fixture**. For real Terraform plans, write and test a provider-aware parser of \`terraform show -json\` and validate the resulting plan against live cluster policy.

### Lab 3 — Optional sandbox integration

1. Confirm approved cluster context, API availability, provider version and scoped RBAC. Read \`examples/kubernetes-tenancy.tf.example\` as a **separate Terraform root**.
2. Provision a disposable namespace with labels, quotas, LimitRange, dedicated ServiceAccount, Role/RoleBinding and default-deny NetworkPolicy.
3. Use approved test pods to verify allowed namespace reads and denied Secrets reads; test DNS, ingress and PostgreSQL egress with CNI enforcement.
4. Apply PSA restricted policy and verify rejected privileged workload in sandbox. Verify resource quota rejection, HPA headroom and PDB behavior.
5. Record sanitized evidence and remove disposable resources after checking no PVC or database data will be deleted.

### Lab 4 — Red-team tenant isolation

Inject (a) wildcard RBAC, (b) cross-namespace RoleBinding, (c) default ServiceAccount token, (d) broad egress, (e) absent DNS allowance, (f) quota exhaustion and (g) a Terraform namespace deletion plan. Require the gate to fail, document the exact blast radius, and demonstrate safe recovery.

## 9. Production SRE/DBRE scenarios

| Scenario | Detection | Diagnosis | Recovery |
|---|---|---|---|
| Cross-tenant RBAC exposure | audit reads from wrong namespace | RoleBinding subjects and effective rights | revoke scoped grant, audit access |
| Cluster-admin wildcard | privilege escalation alert | ClusterRole/ClusterRoleBinding | revoke and rotate affected credentials |
| Default-deny breaks DNS | DNS timeouts, app 5xx | egress to CoreDNS UDP/TCP 53 | allow minimal DNS traffic |
| Database access blocked | connection timeouts | policy, service NAT, private CIDR, TLS | scoped DB egress and validation |
| Quota exhausted | Pending pods, FailedCreate | ResourceQuota, requests/limits | approve quota/capacity changes |
| Noisy neighbor | CPU throttling, p99 latency | requests, limits, node contention | rightsize, topology, capacity |
| PSA rejects deployment | forbidden admission | restricted profile violations | correct pod security context |
| Secret leaked into state | audit finding | Terraform state history | revoke secret, secure state, rotate |
| Namespace delete in plan | planned delete/replace | state drift, ownership | block, restore config, incident review |
| GitOps and Terraform conflict | perpetual drift | managed fields and controller logs | transfer ownership, reconcile |
| Stateful pod eviction | database unavailable | PDB, PV affinity, quorum | halt rollout, DBRE recovery |
| ServiceAccount token abuse | anomalous API calls | audit logs, bound roles | revoke, reduce token exposure |

## 10. Troubleshooting commands

~~~bash
kubectl config current-context
kubectl get ns --show-labels
kubectl get role,rolebinding,serviceaccount -n payments-prod
kubectl get clusterrolebinding
kubectl auth can-i --list -n payments-prod
kubectl get networkpolicy -n payments-prod -o yaml
kubectl get resourcequota,limitrange -n payments-prod
kubectl describe resourcequota -n payments-prod
kubectl get pods -n payments-prod -o wide
kubectl get events -n payments-prod --sort-by=.lastTimestamp
kubectl get pvc,pv -A
terraform providers
terraform state list
~~~

Avoid dumping Secrets, access tokens or production kubeconfig contents. Validate current context before any mutation.

## 11. Production runbooks

**Pre-change:** verify cluster and namespace, tenant owner, state location, service identity, RBAC diff, policy enforcement, quotas, PSA, network flow matrix, backups, change ticket and Security/DBRE approval. Block delete/replace.

**RBAC exposure:** freeze access changes, capture audit events, identify affected principals/resources, remove offending binding, revoke credentials, validate effective permissions and notify incident command.

**NetworkPolicy outage:** inspect CNI enforcement and DNS/DB allow rules, use approved connectivity probes, restore minimum flows and validate SLOs. Never leave an allow-all emergency policy untracked.

**Quota exhaustion:** assess namespace utilization and application requests, verify cluster capacity and fair-share policy, adjust only with owner approval, observe Pending pods and p95 latency.

**Stateful disruption:** check PDBs, PVC topology, database quorum, replication and backup. Coordinate DBRE before any eviction, PVC deletion or namespace cleanup.

**Drift and rollback:** identify Terraform/GitOps ownership, halt competing reconciler under approval, restore known-good state, run a reviewed plan, validate audit logs and tenant isolation.

## 12. 100-point operational assessment

| Area | Points | Evidence |
|---|---:|---|
| Tenant architecture and isolation design | 20 | diagrams and threat model |
| RBAC and service-account least privilege | 20 | effective permission tests |
| NetworkPolicy, DNS, DB connectivity and PSA | 20 | actual enforcement probes |
| Terraform contracts and automated negative tests | 15 | test output and reviewed plan |
| SRE/DBRE incident drills and recovery | 15 | timeline and runbooks |
| Monitoring, FinOps, audit and approvals | 10 | SLO/cost/sign-off |

**Pass:** >=85/100 with zero critical failures: no wildcard cluster-admin, exposed Secret, public/broad tenant access, unapproved namespace deletion or missing stateful recovery evidence. Authored tests alone do not count as executed evidence.

## 13. Cleanup and chapter review

Destroy **offline** \`terraform_data\` only unless the sandbox is explicitly disposable. Questions: Why is namespace isolation insufficient by itself? Why is Kubernetes RBAC additive? What breaks when default-deny egress omits DNS? How does quota exhaustion affect a rollout? Why does Terraform state need a separate security review?

**Next proposed:** Chapter 053 — Kubernetes Workloads, StatefulSets, Storage and Helm Releases with Terraform.
