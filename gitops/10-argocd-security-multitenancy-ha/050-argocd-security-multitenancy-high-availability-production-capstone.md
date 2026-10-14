# Chapter 050 — Argo CD Security, Multi-Tenancy and High Availability Production Capstone

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 10:** Argo CD Security, Multi-Tenancy and High Availability  
**Chapter:** 050 / 100 — Part 10 Capstone  
**Audience:** Platform Engineers, SREs, Kubernetes Administrators, DevSecOps and Security Teams

> **Safety:** All commands and fault injection are intended for isolated staging infrastructure. Use dummy applications and test identities. Never intentionally revoke production credentials, drain production nodes, disable production SSO or simulate failures against live customer workloads.

## 1. Mission and learning outcomes

Build, validate and operate an enterprise Argo CD GitOps platform that supports multiple teams and multiple Kubernetes clusters without sacrificing security, auditability or availability.

This capstone integrates:

- **Chapter 046:** Enterprise RBAC, SSO, AppProject isolation and tenant boundaries.
- **Chapter 047:** Argo CD high availability, capacity, scaling and resilience.
- **Chapter 048:** Security hardening, credential governance, audit evidence and incident response.
- **Chapter 049:** Remote cluster registration, cloud identity and secure fleet operations.

**Definition of done:** All critical security tests deny unauthorized operations, approved applications converge to the intended Git revision, controlled failures recover within documented objectives, and evidence is recorded without leaking secrets.

## 2. Reference architecture and trust boundaries

```text
                    Enterprise IdP / MFA
                           |
                 GitLab (MR + approvals)
                    |             |
                source repo    GitOps config
                    +------v------+
                           |
                 Argo CD HA control plane
             +-------------+--------------+
             | API servers | repo servers |
             | controllers | Redis HA     |
             +-------------+--------------+
                           |
             +-------------+--------------+
             |                            |
      Staging cluster A             Staging cluster B
       namespace team-a              namespace team-b
       scoped identity               scoped identity
             |                            |
          K8s audit                    K8s audit
             +-------------+--------------+
                           |
                  Metrics / logs / SIEM
```

The central control plane, Git provider, identity provider, Kubernetes API endpoints and secret-management system are independent failure domains. An Argo CD outage normally stops reconciliation rather than directly stopping healthy running workloads. A compromise of an overly privileged controller identity, however, can affect multiple clusters; use least-privilege registration and defense in depth.

## 3. Lab topology and prerequisites

| Item | Required staging baseline |
| --- | --- |
| GitLab | Test repository, protected branch, review approvals |
| Argo CD | Supported version-pinned HA deployment |
| Clusters | Two disposable Kubernetes clusters or isolated equivalents |
| Tenants | `team-a` and `team-b` |
| Namespaces | `team-a-dev`, `team-b-dev` |
| Identity | Enterprise test SSO identities and documented break-glass |
| Credentials | Approved secret manager or supported short-lived identity |
| Observability | Argo CD metrics, Kubernetes events/audit, centralized logs |
| Workloads | Harmless sample Deployment and Service per tenant |

Before changing anything:

```bash
kubectl config current-context
kubectl config get-contexts
kubectl -n argocd get deploy,sts,pods,pdb -o wide
kubectl -n argocd get appprojects,applications,applicationsets
argocd cluster list
argocd app list
helm -n argocd list
```

Capture timestamp, Argo CD/chart versions, desired and ready replicas, node/zone placement, application sync/health and cluster status. Do not export Secret values or kubeconfigs into lab evidence.

## 4. Suggested repository structure

```text
gitops-capstone/
├── README.md
├── bootstrap/
│   ├── argocd-values-staging.yaml
│   └── recovery-runbook.md
├── projects/
│   ├── team-a-project.yaml
│   └── team-b-project.yaml
├── applicationsets/
│   └── team-a-staging.yaml
├── apps/
│   └── demo-web/
│       ├── base/
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   └── kustomization.yaml
│       └── overlays/
│           └── staging/
│               └── kustomization.yaml
├── policies/
│   ├── rbac-test-cases.md
│   └── project-policy-tests.md
└── evidence/
    └── acceptance-template.md
```

The repository is an example layout; only store non-sensitive configuration and redacted evidence. Protect `bootstrap/`, `projects/` and `applicationsets/` using CODEOWNERS, branch protection and review requirements.

## 5. Phase 1 — Validate the HA foundation

Confirm supported HA deployment settings from the **pinned** chart/release. Do not assume replica counts automatically imply controller workload sharding or Redis failover.

```bash
kubectl -n argocd get deploy,sts -o wide
kubectl -n argocd get pods -o wide
kubectl -n argocd get pdb
kubectl -n argocd top pods
kubectl -n argocd get events --sort-by=.lastTimestamp | tail -25
```

Review:
1. At least two ready API-server and repo-server replicas if supported by the chosen installation.
2. Controller HA/sharding behavior as documented for the deployed version.
3. Supported Redis HA topology and tested failover.
4. Pod placement across failure domains and enough spare node capacity.
5. Resource requests/limits, TLS ingress, backup and bootstrap recovery.

**Pass:** no critical single-node placement issue; expected replica readiness; versioned installation manifests and rollback plan available. Record exceptions with risk owner.

## 6. Phase 2 — Create tenant namespaces and scoped RBAC

Use explicit cluster contexts. Replace placeholders before execution.

```bash
kubectl --context CLUSTER_A create namespace team-a-dev \
  --dry-run=client -o yaml | kubectl --context CLUSTER_A apply -f -
kubectl --context CLUSTER_B create namespace team-b-dev \
  --dry-run=client -o yaml | kubectl --context CLUSTER_B apply -f -
```

Apply a separate namespace-scoped ServiceAccount/Role/RoleBinding for each tenant. Example for team A, saved as `team-a-rbac.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitops-team-a
  namespace: team-a-dev
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: gitops-team-a
  namespace: team-a-dev
rules:
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["services", "configmaps"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gitops-team-a
  namespace: team-a-dev
subjects:
  - kind: ServiceAccount
    name: gitops-team-a
    namespace: team-a-dev
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: gitops-team-a
```

```bash
kubectl --context CLUSTER_A apply -f team-a-rbac.yaml
kubectl --context CLUSTER_A auth can-i create deployments \
  --as=system:serviceaccount:team-a-dev:gitops-team-a -n team-a-dev
kubectl --context CLUSTER_A auth can-i create deployments \
  --as=system:serviceaccount:team-a-dev:gitops-team-a -n kube-system
kubectl --context CLUSTER_A auth can-i create clusterroles \
  --as=system:serviceaccount:team-a-dev:gitops-team-a
```

Expected: allowed, denied, denied. Impersonation checks require appropriate impersonation rights. Argo CD may require additional narrowly scoped discovery/resource permissions depending on the rendered workload; review actual failures before extending access.

## 7. Phase 3 — Configure AppProjects and RBAC

Create a restrictive Project for each tenant. Example:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.internal/platform/team-a-gitops.git
  destinations:
    - name: cluster-a-staging
      namespace: team-a-dev
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
    - group: ""
      kind: LimitRange
```

Create an equivalent `team-b` Project for `cluster-b-staging` and `team-b-dev`. Protect the Project definitions against unauthorized changes. Namespace-resource restrictions and cluster-resource allowlists are not replacements for Kubernetes RBAC/admission policy.

Recommended Argo CD RBAC principles:
- Use a narrowly scoped default role, not broadly readable access to every tenant.
- Map SSO groups to per-tenant roles.
- Permit approved `get` and `sync` actions only for the intended Project.
- Deny cross-tenant Application operations and changes to AppProjects/cluster credentials.
- Verify effective permissions using actual low-privilege test identities.

**Pass:** team A cannot view, sync, update or delete team B Applications. Record allowed and denied tests with actor, time and result.

## 8. Phase 4 — Secure cluster registration

Register the staging clusters using an approved scoped identity or supported workload identity mechanism. Review the Argo CD version's registration options before using `argocd cluster add`, which can create broad permissions depending on flags and configuration.

```bash
argocd cluster list
kubectl -n argocd get secrets \
  -l argocd.argoproj.io/secret-type=cluster \
  -o custom-columns=NAME:.metadata.name,CREATED:.metadata.creationTimestamp
```

Never disable TLS verification or store bearer tokens in Git. Validate cluster CA trust, private endpoint DNS, identity expiration and remote Kubernetes audit logging.

**Pass:** each staging cluster is registered, accessible, labeled with an approved owner/environment and backed by a scoped identity. Confirm unauthorized cross-namespace writes are denied by the Kubernetes API.

## 9. Phase 5 — Build a sample application

`apps/demo-web/base/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      containers:
        - name: web
          image: nginx:1.27.5
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 2
            periodSeconds: 5
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 250m
              memory: 128Mi
```

For production, replace the example tag with a reviewed immutable image digest and enforce image-signature/provenance policy where appropriate.

`apps/demo-web/base/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-web
spec:
  selector:
    app: demo-web
  ports:
    - port: 80
      targetPort: 80
```

`apps/demo-web/base/kustomization.yaml`:

```yaml
resources:
  - deployment.yaml
  - service.yaml
```

`apps/demo-web/overlays/staging/kustomization.yaml`:

```yaml
resources:
  - ../../base
```

Validate before committing:

```bash
kubectl kustomize apps/demo-web/overlays/staging
kubectl --context CLUSTER_A -n team-a-dev apply \
  --dry-run=server -k apps/demo-web/overlays/staging
```

## 10. Phase 6 — Deploy through Argo CD

Example `team-a-demo.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: team-a-demo
  namespace: argocd
spec:
  project: team-a
  source:
    repoURL: https://gitlab.example.internal/platform/team-a-gitops.git
    targetRevision: main
    path: apps/demo-web/overlays/staging
  destination:
    name: cluster-a-staging
    namespace: team-a-dev
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
```

The Project and registered cluster name must match the actual staging configuration. The example intentionally uses manual sync to require review before deployment.

```bash
kubectl -n argocd apply --dry-run=server -f team-a-demo.yaml
kubectl -n argocd apply -f team-a-demo.yaml
argocd app get team-a-demo
argocd app diff team-a-demo
# After change approval:
argocd app sync team-a-demo
argocd app wait team-a-demo --sync --health --timeout 300
kubectl --context CLUSTER_A -n team-a-dev rollout status deploy/demo-web
```

**Pass:** the Application is Synced and Healthy at the expected Git revision, and Kubernetes reports both replicas Ready.

## 11. Phase 7 — Controlled fault-injection exercises

Perform these one at a time. Establish baseline health and a recovery owner before each test.

| Test | Controlled staging fault | Expected behavior | Recovery evidence |
| --- | --- | --- | --- |
| F1 | Delete one Argo CD API server pod with redundant replicas | UI/API available or recovers within objective | Pod readiness and API checks |
| F2 | Delete one repo-server pod with redundant replicas | Manifest generation continues or recovers | Repo-server logs, canary refresh |
| F3 | Drain a node when PDB/capacity permit | Replicas reschedule safely | PDB status, pod placement |
| F4 | Temporarily block one remote API endpoint | Only affected cluster reconciliation fails | Per-cluster status and recovery time |
| F5 | Temporarily block test Git endpoint | Refresh/generation errors, no unexpected deletion | Reconciliation after restoration |
| F6 | Remove one staging user's tenant group | Access denied after session/claim refresh | SSO and RBAC audit evidence |
| F7 | Rotate a dedicated staging cluster credential | New identity succeeds; old identity rejected | Redacted credential audit |
| F8 | Apply a harmless direct annotation change | Drift detected or self-healed | Kubernetes audit + Argo CD status |

**Do not** use forced PDB bypass, Redis data deletion, production credential revocation or uncontrolled namespace deletion. If a failure blocks recovery, stop the exercise and invoke the staging incident procedure.

### Example F1

```bash
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-server -o wide
# Only after confirming two or more healthy staging replicas:
kubectl -n argocd delete pod VERIFIED_STAGING_SERVER_POD
kubectl -n argocd rollout status deploy/argocd-server --timeout=5m
argocd app list
```

### Example F3

```bash
kubectl -n argocd get pdb
kubectl get nodes
# Only after verifying this is a disposable staging node:
kubectl drain STAGING_NODE --ignore-daemonsets --delete-emptydir-data --timeout=10m
kubectl -n argocd get pods -o wide
kubectl uncordon STAGING_NODE
```

### Example F8

```bash
kubectl --context CLUSTER_A -n team-a-dev annotate deployment demo-web \
  training.example/drift=capstone --overwrite
argocd app get team-a-demo --refresh
argocd app diff team-a-demo
# Restore through the approved Argo CD sync workflow.
```

Record actual detection time, error rate, recovery time, observed application impact and whether the stated objective was met. Do not claim zero downtime without measurements.

## 12. Phase 8 — Security and compliance validation

Execute positive and negative tests using distinct identities.

| Test ID | Scenario | Required outcome |
| --- | --- | --- |
| S01 | Team A reads own Application | Allowed |
| S02 | Team A syncs own approved Application | Allowed |
| S03 | Team A reads team B Application | Denied |
| S04 | Team A syncs team B Application | Denied |
| S05 | Team A modifies AppProject policy | Denied |
| S06 | Team A creates cluster-scoped RBAC | Denied |
| S07 | Application references unapproved repository | Rejected by Project/policy |
| S08 | Application targets unapproved namespace | Rejected by Project and Kubernetes controls |
| S09 | Unreviewed wildcard AppProject proposed | CI/admission policy rejects |
| S10 | Direct kubectl drift occurs | Audit actor and drift signal recorded |
| S11 | Test credential rotated | New credential works; old is revoked |
| S12 | Production sync without required approval | Blocked by governance workflow |

An Argo CD RBAC denial alone is not sufficient evidence for S06/S08: verify the Kubernetes API and admission controls enforce their own boundaries.

## 13. Phase 9 — Observability and SLO design

Measure at least:

- Argo CD API availability and latency.
- Controller reconciliation duration, errors and backlog.
- Repo-server manifest generation latency and error rate.
- Application sync/health status at expected revisions.
- Per-cluster connection health, Kubernetes API throttling and TLS/auth failures.
- Redis availability and failover events.
- Unauthorized access attempts, Project changes and credential rotation events.
- Pod readiness, OOMKills, restarts and node/zone placement.

Suggested **example** objectives, to be approved based on actual business requirements:

| Service indicator | Illustrative objective |
| --- | --- |
| Argo CD API availability | 99.9% monthly |
| Approved staging deployment convergence | 95% within 10 minutes |
| Single API-server pod failure recovery | Within 5 minutes |
| Remote API outage detection | Within 5 minutes |
| Credential-expiry warning | At least 14 days before expiry |

These are design targets, not observed results. Define measurement sources, exclusions, burn-rate alerts and escalation paths before adopting them.

## 14. Incident response drill — unauthorized production sync

**Scenario:** A simulated audit alert indicates an Application was synced without the required change approval.

1. Declare a staging security incident and assign incident commander.
2. Identify actor, source IP where available, target Application, Git revision and time.
3. Preserve GitLab MR/commit, Argo CD operation and Kubernetes audit references.
4. Determine whether the change affected a running workload.
5. Contain the affected credential or promotion path using approved controls.
6. Restore a reviewed known-good revision if needed.
7. Verify workload readiness, Git revision, authorization policy and audit forwarding.
8. Document root cause, missed control, owner and deadline.

Do not destroy evidence, disable logging or assume a reverted Git commit automatically rolls back deployed workloads.

## 15. Production runbook — central Argo CD outage

**Trigger:** widespread UI/API failure or reconciliation failures across multiple clusters.

```bash
kubectl -n argocd get pods -o wide
kubectl -n argocd get deploy,sts,pdb
kubectl -n argocd get events --sort-by=.lastTimestamp | tail -40
kubectl -n argocd top pods
kubectl -n argocd logs deploy/argocd-server --since=20m --tail=200
kubectl -n argocd logs deploy/argocd-repo-server --since=20m --tail=200
```

**Triage:** distinguish ingress/API, SSO, Redis, repo-server, controller, Git provider and Kubernetes API faults. Identify whether existing application-serving workloads are impacted.

**Contain:** pause nonessential promotions; preserve healthy workloads and audit data.

**Recover:** restore the failing dependency, capacity or last known-good configuration through the authoritative installation method. If Argo CD manages itself and is unavailable, follow the independently documented bootstrap procedure.

**Validate:** API connectivity, ready replicas, controller backlog, per-cluster status, a canary sync and expected revision/health. Close only after the agreed monitoring window.

## 16. Troubleshooting — ten capstone failure patterns

| # | Symptom | Diagnostic focus | Remediation |
| --- | --- | --- | --- |
| 1 | UI unavailable, workloads healthy | Ingress/server/SSO | Restore API path without touching apps |
| 2 | All apps Unknown | Controller/API/Redis | Restore control-plane dependency |
| 3 | One cluster disconnected | TLS, network, cloud identity | Restore scoped access |
| 4 | Team A sees team B | Default RBAC/group mapping | Remove broad access and retest |
| 5 | Repo-server OOMKilled | Large renders, plugin resources | Right-size and optimize manifests |
| 6 | Sync blocked | Hooks, admission, Project, RBAC | Identify exact denial/failure |
| 7 | ApplicationSet targets wrong cluster | Generator labels/template | Correct selector before sync |
| 8 | Node drain stalls | PDB and capacity | Add capacity; never force bypass |
| 9 | Credential rotation breaks reconciliation | Secret reference, token expiry | Restore valid scoped identity |
| 10 | Missing incident evidence | Audit collection/retention | Repair forwarding and correlation |

## 17. Rollback and cleanup

Use Git revert or a reviewed prior revision to roll back Application and Project changes. Review prune and ApplicationSet deletion behavior before modifying generators or removing cluster registrations. For a failed Argo CD Helm upgrade, inspect `helm history` and apply only a version-compatible, approved rollback; CRD migrations may not be reversible.

Lab cleanup order:
1. Stop test fault injection and restore network access.
2. Restore test credentials and remove temporary access grants.
3. Confirm Applications are at intended revisions and Healthy.
4. Remove only capstone-owned Applications and namespaces after confirming finalizers and prune impact.
5. Revoke capstone-only identities and retire test cluster registrations.
6. Archive redacted evidence and remove temporary local rendered manifests.

Never delete shared `argocd` resources or remote production namespaces as part of training cleanup.

## 18. Acceptance evidence template

```text
Capstone ID:
Date/time (UTC):
Environment and cluster IDs (non-sensitive):
Argo CD version/chart version:
Change ticket / approval:
Test ID:
Expected result:
Actual result:
Start time:
Detection time:
Recovery time:
Customer/workload impact:
Git revision / artifact digest:
Evidence link (redacted):
Pass / Fail / Waiver:
Reviewer:
Follow-up owner and due date:
```

## 19. Scoring and sign-off

| Domain | Weight | Minimum required evidence |
| --- | ---: | --- |
| Tenant isolation and authorization | 25 | S01–S09 positive/negative tests |
| High availability and recovery | 20 | F1–F3 measurements |
| Multi-cluster operations | 20 | Scoped access, F4, cluster canary |
| Credential and supply-chain security | 15 | F6–F7, source and policy controls |
| Observability and incident response | 15 | Alerts, F8, incident drill |
| Documentation and rollback | 5 | Runbooks, evidence and sign-off |
| **Total** | **100** | |

**Pass threshold:** at least 85/100 **and** every critical isolation, credential protection and unauthorized production deployment control passes. Any failed critical control blocks production approval regardless of aggregate score. Document waivers only for non-critical gaps with explicit owner, expiry and compensating control.

## 20. Final production readiness checklist

- [ ] HA control plane, placement, PDBs and failover verified.
- [ ] Controller and repo-server capacity baselines established.
- [ ] Tenant RBAC and AppProject negative tests pass.
- [ ] Kubernetes RBAC/admission independently enforce isolation.
- [ ] Remote clusters use scoped identities and verified TLS.
- [ ] EKS/AKS/GKE authentication integrations validated where used.
- [ ] ApplicationSet labels and templates are review protected.
- [ ] SSO/MFA and emergency access are tested.
- [ ] GitLab branch protection, CODEOWNERS and approvals enforced.
- [ ] Credential expiry, rotation and revocation tested.
- [ ] Audit logs correlate identity, Git, Argo CD and Kubernetes.
- [ ] Failure injection outcomes recorded with actual recovery timings.
- [ ] Recovery/bootstrap and rollback runbooks exercised.
- [ ] Security and platform reviewers sign off on critical controls.

## 21. Knowledge check

1. Which independent controls prevent a tenant from deploying to another namespace?
2. What happens to running workloads when Argo CD loses connectivity to Git?
3. Why is controller replica count insufficient to prove HA or throughput?
4. How do you verify a rotated cluster credential is both effective and least privileged?
5. What audit records are needed to attribute a direct Kubernetes mutation?
6. Why must ApplicationSet cluster labels be treated as sensitive deployment controls?
7. Which faults should stop the capstone even if the numeric score remains high?
8. How can you restore Argo CD when its own GitOps reconciliation is unavailable?

## 22. References

- [Argo CD Operator Manual](https://argo-cd.readthedocs.io/en/stable/operator-manual/)
- [Argo CD RBAC](https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/)
- [Argo CD Projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [Argo CD High Availability](https://argo-cd.readthedocs.io/en/stable/operator-manual/high_availability/)
- [Argo CD ApplicationSet Cluster Generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Cluster/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

---

**Chapter 050 complete — Part 10 complete (Chapters 046–050).**

**Next:** Chapter 051 — Environment Promotion Architecture and Release Governance, beginning Part 11: Environment Promotion and Release Governance.
