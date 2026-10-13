# Chapter 093 — Multi-Tenancy and Namespace Governance

**Track:** Kubernetes Administration · **Part 19 — GitOps and Platform Automation**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, platform engineers, security engineers  
**Prerequisites:** Chapters 021–045, 091–092; kubectl, Git, PowerShell, a disposable cluster with a CNI that enforces NetworkPolicy, and authorization to administer a test cluster.

## Learning outcomes

Design tenant boundaries; apply least-privilege RBAC; enforce resource budgets and Pod Security Admission; isolate network traffic; govern service accounts and admission policies; implement GitOps ownership; detect and recover from policy failures; and demonstrate measurable isolation with negative and positive tests.

## 1. Multi-tenancy architecture

A **tenant** is an independently governed team, application, business unit or customer. Kubernetes namespaces provide naming and administrative boundaries, **not** a complete security boundary. Namespaces do not isolate nodes, the kernel, cluster-scoped APIs, shared storage, the control plane or the network by themselves.

Common patterns:

| Model | Isolation | Tradeoff |
|---|---|---|
| Shared cluster, namespace per team | Logical and policy-based | Efficient but shared failure domains |
| Shared cluster, dedicated node pools | Stronger scheduling separation | Nodes and control plane still shared |
| Dedicated cluster per tenant | Stronger operational boundary | Higher cost and fleet complexity |
| Virtual clusters | Tenant-specific API abstraction | Extra controllers and security assumptions |

For untrusted tenants or strict regulatory boundaries, evaluate dedicated clusters rather than relying on namespaces alone. Define a threat model, trust level, compliance requirements, shared infrastructure, and blast radius before choosing.

**Reference design:** platform administrators own cluster-scoped policy, ingress, CNI, DNS, storage classes and observability. Tenant teams own approved namespaced workloads. Admission, RBAC, network policy and quotas enforce the contract.

## 2. Governance contract

Every tenant should have an owner, cost center, environment, support channel, approved namespaces, namespace administrator group, service account inventory, resource budget, network egress requirements, data classification, escalation contact and deletion/retention procedure.

Recommended labels: `platform.example.com/team`, `platform.example.com/environment`, `platform.example.com/cost-center`, and `platform.example.com/managed-by`. Avoid placing secrets or personal information in labels. Document which actor may create namespaces and which changes require platform approval.

## 3. Lab prerequisites and safety (Lab 01)

Use a **disposable** cluster. Confirm the current context and authorization before applying anything:

```powershell
kubectl config current-context
kubectl cluster-info
kubectl auth can-i create namespaces
kubectl get nodes -o wide
kubectl get networkpolicy -A
```

Create two tenants and a shared test namespace:

```powershell
kubectl create namespace tenant-alpha
kubectl create namespace tenant-beta
kubectl create namespace shared-services
kubectl label namespace tenant-alpha platform.example.com/team=alpha platform.example.com/environment=lab
kubectl label namespace tenant-beta platform.example.com/team=beta platform.example.com/environment=lab
kubectl label namespace shared-services platform.example.com/team=platform platform.example.com/environment=lab
kubectl get namespaces --show-labels
```

**Acceptance:** namespace labels are visible and the context is confirmed. Do not use production namespaces for experiments.

## 4. RBAC: least-privilege namespace access (Lab 02)

Roles and RoleBindings scope access to namespaced resources. A RoleBinding may reference a ClusterRole, but still grants permissions only within the RoleBinding namespace for namespaced resources. RBAC is additive: no explicit deny rule. Be especially careful with permission to create Pods, read Secrets, impersonate identities, or modify Roles/RoleBindings.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alpha-deployer
  namespace: tenant-alpha
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: workload-editor
  namespace: tenant-alpha
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alpha-deployer-binding
  namespace: tenant-alpha
subjects:
- kind: ServiceAccount
  name: alpha-deployer
  namespace: tenant-alpha
roleRef:
  kind: Role
  name: workload-editor
  apiGroup: rbac.authorization.k8s.io
```

Save as `alpha-rbac.yaml` and apply:

```powershell
kubectl apply -f .\alpha-rbac.yaml
kubectl auth can-i create deployments -n tenant-alpha --as=system:serviceaccount:tenant-alpha:alpha-deployer
kubectl auth can-i create deployments -n tenant-beta --as=system:serviceaccount:tenant-alpha:alpha-deployer
kubectl auth can-i get secrets -n tenant-alpha --as=system:serviceaccount:tenant-alpha:alpha-deployer
```

Expected: **yes**, **no**, **no**, assuming no broader bindings exist. `--as` requires impersonation permission and is a useful administrative test, not proof of effective credentials. Inspect existing ClusterRoleBindings if results differ.

## 5. Human access and escalation (Lab 03)

Bind an IdP-managed group to a narrow namespace Role; do not bind all developers to `cluster-admin`. Keep platform-admin and break-glass paths separate, audited and time-limited.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alpha-viewers
  namespace: tenant-alpha
subjects:
- kind: Group
  name: k8s-alpha-viewers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: view
  apiGroup: rbac.authorization.k8s.io
```

Validate the identity provider's actual group claims. The built-in `view` role deliberately excludes Secrets, but other bindings may grant more access. Document onboarding, offboarding and emergency access review.

## 6. ResourceQuota: tenant budgets (Lab 04)

Quotas prevent tenants from monopolizing namespaced compute and object counts. They do **not** reserve node capacity, guarantee performance or cap cluster-wide usage by themselves.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: alpha-budget
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    pods: "10"
    services: "5"
    persistentvolumeclaims: "4"
```

```powershell
kubectl apply -f .\alpha-quota.yaml
kubectl describe resourcequota alpha-budget -n tenant-alpha
kubectl get resourcequota -n tenant-alpha -o yaml
```

Test a Pod whose requests exceed the budget and capture the admission rejection. Some quotas require each applicable Pod/container to declare requests and limits; pair quotas with LimitRanges and validate both.

## 7. LimitRange: defaults and boundaries (Lab 05)

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: alpha-container-limits
  namespace: tenant-alpha
spec:
  limits:
  - type: Container
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    default:
      cpu: 500m
      memory: 512Mi
    min:
      cpu: 25m
      memory: 32Mi
    max:
      cpu: "2"
      memory: 2Gi
```

```powershell
kubectl apply -f .\alpha-limitrange.yaml
kubectl describe limitrange -n tenant-alpha
```

Defaulting happens at admission; changing a LimitRange does not retroactively change existing Pods. Check that defaults are compatible with ResourceQuota and workload behavior. CPU throttling and memory OOM kills are runtime effects, not proof of admission failure.

## 8. Pod Security Admission (Lab 06)

Pod Security Admission uses namespace labels for `privileged`, `baseline` and `restricted` profiles with `enforce`, `audit` and `warn` modes. Start with warnings/audit, remediate, then enforce. Profile versions should be pinned to the supported Kubernetes minor version during controlled rollouts.

```powershell
kubectl label namespace tenant-alpha pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace tenant-alpha pod-security.kubernetes.io/audit=restricted --overwrite
kubectl get namespace tenant-alpha --show-labels
```

Review a noncompliant Pod in staging, then enforce after remediation:

```powershell
kubectl label namespace tenant-alpha pod-security.kubernetes.io/enforce=restricted --overwrite
```

A compatible example container security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

This snippet belongs under a **container**; Pod-level security context has a different field set. Check Linux/Windows and workload-specific requirements before reuse. Namespace exemptions and privileged platform workloads require explicit security review.

## 9. NetworkPolicy: deny by default (Lab 07)

**Critical prerequisite:** your CNI must implement Kubernetes NetworkPolicy; otherwise policies can be accepted but have no traffic effect. Standard NetworkPolicy governs supported L3/L4 traffic, not arbitrary HTTP identities or DNS domain names.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
```

```powershell
kubectl apply -f .\alpha-default-deny.yaml
kubectl describe networkpolicy default-deny -n tenant-alpha
```

New and existing tenant-alpha Pods selected by this policy become isolated for both directions, **if enforced by the CNI**. NetworkPolicy rules are additive: another policy can allow traffic. Default-deny may break DNS, metrics, image-related application calls and dependencies; prepare explicit allow rules and a rollback path before production enforcement.

## 10. Controlled DNS and intra-tenant access (Lab 08)

Example DNS egress policy; adjust CoreDNS labels and namespace for your distribution:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

Before applying, verify the actual DNS Pods' labels with `kubectl get pods -n kube-system --show-labels`. For intra-tenant services, add narrow ingress and egress rules using tenant labels and named workload selectors. Avoid blanket cross-namespace allowances.

## 11. Verify isolation with real traffic (Lab 09)

Deploy small HTTP server and test-client Pods to each tenant using approved images from your environment. Validate four scenarios: alpha-to-alpha explicitly allowed; beta-to-alpha denied; alpha-to-beta denied; alpha-to-approved-DNS allowed. Record commands, destination IP/service, protocol, policy YAML, CNI version and observed timeout/success.

Useful diagnostics:

```powershell
kubectl get networkpolicy -A
kubectl describe networkpolicy -n tenant-alpha
kubectl get pods -A -o wide
kubectl get endpointslice -A
kubectl get events -n tenant-alpha --sort-by=.lastTimestamp
```

A blocked connection is not enough by itself to prove policy enforcement: also demonstrate the positive control, service health and DNS resolution. Note that host-network traffic and node-level paths have implementation-specific considerations.

## 12. Service accounts and workload identity (Lab 10)

Create one service account per workload trust boundary. Disable automatic token mounting when the application does not call the Kubernetes API:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alpha-api
  namespace: tenant-alpha
automountServiceAccountToken: false
```

For cloud API access, use the provider's workload identity mechanism (EKS Pod Identity/IRSA, AKS Workload Identity or GKE Workload Identity Federation) with narrowly scoped IAM. Kubernetes RBAC and cloud IAM are separate authorization systems. Avoid long-lived service-account token Secrets and do not store credentials in Git.

## 13. Namespace lifecycle through GitOps (Lab 11)

Example repository structure:

```text
platform/
  tenants/
    alpha/
      namespace.yaml
      rbac.yaml
      quota.yaml
      limitrange.yaml
      networkpolicy.yaml
      serviceaccounts.yaml
    beta/
      ...
  policies/
    admission/
  environments/
    staging/
    production/
```

Platform owns namespace creation and cluster-scoped controls; tenants may propose approved namespaced workload changes. Configure Argo CD AppProjects or Flux reconciliation permissions so a tenant cannot deploy cluster-scoped resources or write into another tenant's namespace. Protect main branches; require code owners, automated schema/policy tests, staging promotion and documented rollback. **Git repository ownership alone is not a Kubernetes security boundary.**

## 14. Admission policy and exception governance (Lab 12)

Integrate Chapter 092 Kyverno/Gatekeeper policies to require ownership labels, disallow privileged containers, enforce approved registries and validate workload resources. Use audit before enforce and avoid contradictory controls. Explicitly document exception scope, reason, owner, expiration, approver and monitoring. Never use a broad exemption for all tenant namespaces to resolve one application issue.

## 15. Troubleshooting and incident recovery (Lab 13)

| Symptom | Likely control | Investigation | Safe response |
|---|---|---|---|
| `Forbidden` API response | RBAC | `kubectl auth can-i`, bindings, identity | Correct least-privilege binding |
| `exceeded quota` | ResourceQuota | `kubectl describe quota` | Right-size request or approved budget |
| Pod rejected by PSA | Pod Security Admission | Events, namespace labels, Pod spec | Fix security context, not broad exemption |
| Service unreachable | NetworkPolicy/CNI/DNS | Positive/negative tests, CNI logs | Restore narrow necessary flow |
| GitOps sync failure | Ownership/admission | Controller events, policy errors | Revert bad Git revision |
| Pods Pending | Scheduling/capacity | Events, requests, nodes, taints | Adjust capacity or requests |

**Exercise:** in staging, intentionally apply a deny-all egress policy to a healthy test workload. Record impact, identify policy selectors, apply a narrowly scoped DNS/application allow policy, retest positive and negative paths, and document time to restore. Reverting Git state is necessary for GitOps-managed objects; a manual `kubectl delete` may be immediately reconciled back. Maintain a tested break-glass procedure.

## 16. Operational acceptance (Lab 14)

- [ ] Tenant ownership, inventory, lifecycle and cost center documented.
- [ ] Alpha workload identity can manage only approved alpha resources.
- [ ] Cross-tenant authorization and Secret access negative tests denied.
- [ ] ResourceQuota and LimitRange defaults/denials demonstrated.
- [ ] Pod Security warn/audit and enforce behavior verified.
- [ ] CNI NetworkPolicy enforcement demonstrated with positive and negative traffic controls.
- [ ] Required DNS, observability and service flows remain functional.
- [ ] Workload identities have least-privilege Kubernetes and cloud permissions.
- [ ] GitOps scope, approvals, policy exceptions and rollback tested.
- [ ] Alerting, incident evidence, escalation and deletion procedures reviewed.
- [ ] Lab execution evidence and independent technical review recorded before marking Complete.

## Cleanup and rollback

Remove only resources created for this exercise, after checking GitOps ownership and whether any workloads depend on them:

```powershell
kubectl delete namespace tenant-alpha tenant-beta shared-services --ignore-not-found
```

Namespace deletion is destructive and can remove PVC objects and workloads. **Never run this cleanup against production or shared namespaces.** For a shared cluster, use a dedicated disposable test cluster or a reviewed manifest-by-manifest rollback instead.

## Production takeaways

Namespaces organize tenancy; security comes from layered authorization, admission, workload identity, quotas, scheduling controls and enforced network isolation. Test both what is **allowed** and what is **denied**, document the shared-cluster failure domains, and make governance changes auditable and reversible.

**Draft status:** examples are provided for review and lab execution; they have **not** been runtime-validated in this publication workflow.

**Next:** Chapter 094 — Kubernetes Cost Management and FinOps.
