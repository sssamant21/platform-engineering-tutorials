# Chapter 046 — Argo CD Enterprise RBAC, SSO, AppProject Security and Multi-Tenancy

**Part 10 — Argo CD Security, Multi-Tenancy and High Availability** | **Chapter 046 of 100**  
**Audience:** SREs, platform administrators, security engineers and Kubernetes operators  
**Prerequisites:** Chapters 036–045; working Argo CD installation, GitLab governance and approved Kubernetes access  
**Reference:** One Kubernetes cluster; \`argocd\` control plane; \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\` workload namespaces.

> **Safety:** Perform security configuration changes only in a disposable cluster or through an approved change window with a tested break-glass path. A malformed RBAC policy or SSO connector can lock out administrators; an overly broad role can expose production. Never paste passwords, client secrets, tokens or full Secret YAML into Git, logs or evidence.

## 1. Learning objectives

You will learn to:

1. Separate Argo CD RBAC, AppProject boundaries, Kubernetes RBAC and cloud IAM.
2. Integrate enterprise OIDC/SSO with group claims and least-privilege roles.
3. Build explicit read-only, developer, release-operator and platform-admin roles.
4. Limit access to specific Applications, Projects and environments.
5. Design Project source/destination/resource restrictions.
6. Evaluate multi-tenancy threats in a shared Kubernetes cluster.
7. Test allowed and denied actions before production rollout.
8. Secure GitLab repository access and application secrets.
9. Troubleshoot SSO group mapping, token claims and permission denials.
10. Recover safely from lockout or authorization drift.

## 2. Enterprise identity and authorization architecture

\`\`\`text
Enterprise Identity Provider (OIDC / SAML via supported broker)
             |
        SSO login + MFA
             |
       Argo CD API server
             |
      Argo CD RBAC (Casbin)
             |
         AppProject policy
             |
       Argo CD controllers
             |
       Kubernetes API RBAC
             |
         ONE cluster
  demo-dev | demo-test | demo-staging | demo-prod
             |
      Admission / NetworkPolicy / Quotas
\`\`\`

**Critical distinction:** Argo CD RBAC controls what a user can do through Argo CD. AppProjects constrain application sources, destinations and resource kinds. Kubernetes RBAC governs the privileges of Argo CD's Kubernetes identities. Cloud IAM/workload identity and admission controls enforce additional boundaries. None is a substitute for the others.

## 3. Shared-cluster multi-tenancy threat model

Four namespaces provide organizational boundaries, **not hard isolation**. Shared cluster control plane, nodes, CNI, DNS, storage, admission and controllers remain common failure/security domains.

| Threat | Example | Control |
| --- | --- | --- |
| Unauthorized prod sync | Dev operator deploys to \`demo-prod\` | Argo CD RBAC, approval gates |
| Cross-namespace deployment | App destination changed | AppProject + Kubernetes RBAC |
| Malicious manifest | Privileged Pod/hostPath | Admission and Pod Security |
| Repo compromise | Unauthorized GitOps change | GitLab protected branches, CODEOWNERS |
| Credential theft | Repo/registry token exposed | Scoped secrets, rotation, auditing |
| Project escape | Application selects broad Project | Project creation/update restrictions |
| Shared resource collision | Two Applications own one object | Ownership checks, shared-resource detection |
| Noisy neighbor | Workload exhausts nodes/API | Quotas, PriorityClasses, capacity |
| Lateral movement | Pod reaches another namespace | NetworkPolicy, identity, egress control |
| Control-plane outage | Repo-server/controller unavailable | HA, backups, monitoring |

For high-assurance production isolation, consider separate clusters/accounts even if this tutorial intentionally uses one cluster.

## 4. Role and permission design

Recommended conceptual roles:

| Role | Read Apps | Sync Dev/Test | Sync Staging | Sync Prod | Manage Projects/RBAC |
| --- | --- | --- | --- | --- | --- |
| Observer | Yes | No | No | No | No |
| Developer | Approved project | Dev only | No | No | No |
| Test operator | Approved project | Dev/Test | No | No | No |
| Release operator | Approved project | Approved | Approved | Approval-gated | No |
| Platform administrator | As authorized | As authorized | As authorized | Break-glass/approved | Yes |

Production approvals are **not** automatically enforced merely because a role has sync permission. Combine Argo CD RBAC with protected GitLab MRs, manual sync, change management and audited release workflows.

## 5. Understand Argo CD RBAC policy format

Argo CD uses policy rules resembling:

\`\`\`text
p, role:observer, applications, get, demo-platform/*, allow
g, platform-observers, role:observer
\`\`\`

- \`p\` defines a permission: subject, resource, action, object, effect.
- \`g\` maps a subject/group to a role.
- Application object scope commonly follows \`<project>/<application>\`.
- Deny policies and wildcard matching require careful review.
- ApplicationSets, repositories, clusters and projects have their own resource/action categories.

Verify the installed Argo CD version's RBAC syntax, glob matching and available actions before applying policies. Never assume Kubernetes namespace names are the Argo CD RBAC object identifier.

## 6. Example least-privilege RBAC

\`argocd-rbac-cm\` illustrative data:

\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  scopes: '[groups]'
  policy.csv: |
    p, role:demo-observer, applications, get, demo-platform/*, allow
    p, role:demo-dev-operator, applications, get, demo-platform/demo-app-dev, allow
    p, role:demo-dev-operator, applications, sync, demo-platform/demo-app-dev, allow
    p, role:demo-dev-operator, applications, action/*, demo-platform/demo-app-dev, deny
    p, role:demo-release-operator, applications, get, demo-platform/*, allow
    p, role:demo-release-operator, applications, sync, demo-platform/demo-app-staging, allow
    g, platform-demo-observers, role:demo-observer
    g, platform-demo-dev-operators, role:demo-dev-operator
    g, platform-demo-release-operators, role:demo-release-operator
\`\`\`

**Important:** This is a teaching example, not a production-ready RBAC baseline. \`policy.default: role:readonly\` can grant broad read visibility to authenticated users; for strict tenant isolation, create and validate a custom minimal default role rather than assuming the built-in read-only role is tenant-scoped. The explicit deny of \`action/*\` is only illustrative and may block desired operational actions; validate actual action syntax and intended behavior. Use dedicated group claims that your IdP actually emits.

Do not grant production sync in the initial example. Implement production release access only after authorization tests and approval policy are documented.

## 7. RBAC testing before rollout

Where the installed CLI supports it, inspect available RBAC commands:

\`\`\`bash
argocd admin settings rbac --help
argocd account can-i --help
\`\`\`

Example read-only capability check (syntax depends on CLI version and authenticated identity):

\`\`\`bash
argocd account can-i get applications 'demo-platform/demo-app-dev'
argocd account can-i sync applications 'demo-platform/demo-app-prod'
\`\`\`

Expected for a Dev-only operator: Dev \`get\` and \`sync\` allowed, Production \`sync\` denied. **Test using the actual identity/group token** rather than inferring access from policy text.

For an offline policy file, use the installed version's \`argocd admin settings rbac can\` or equivalent policy test facility after checking \`--help\`; avoid relying on unverified CLI flag syntax.

## 8. SSO/OIDC integration design

Use the organization's approved OIDC identity provider (for example, Microsoft Entra ID, Okta or another enterprise IdP).

Required design decisions:

1. HTTPS Argo CD external URL and redirect URI.
2. OIDC issuer, client ID and approved scopes.
3. Client secret managed outside Git (if confidential client).
4. Group claim mapping and group overage behavior.
5. MFA/conditional access enforcement at IdP.
6. Token expiration, refresh and session lifetime.
7. Account disablement/revocation propagation.
8. Emergency access and recovery ownership.
9. Certificate rotation and IdP outage response.
10. Audit trail linking Argo CD actions to user identity.

**Do not copy a generic OIDC client secret into \`argocd-cm\`.** Use Argo CD-supported secret references and a tested external secret delivery mechanism.

## 9. SSO configuration illustration

An OIDC configuration shape in \`argocd-cm\`:

\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  oidc.config: |
    name: EnterpriseSSO
    issuer: https://idp.example.com/oauth2/default
    clientID: demo-argocd-client
    clientSecret: $oidc.enterprise.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
\`\`\`

This is illustrative only. The \`clientSecret\` reference must correspond to a supported key in the Argo CD secret configuration, provisioned by an approved secret mechanism. Exact issuer, scopes, group claim format and IdP setup vary. Verify Argo CD version compatibility and use a staged rollout.

## 10. Lab A — Security inventory (read-only)

\`\`\`bash
kubectl config current-context
kubectl get pods,deployments -n argocd
kubectl get configmap argocd-rbac-cm -n argocd -o yaml
kubectl get configmap argocd-cm -n argocd -o yaml
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl get serviceaccounts,roles,rolebindings -n argocd
kubectl auth can-i get applications.argoproj.io -n argocd
\`\`\`

Avoid dumping \`argocd-secret\` or repository Secrets. Sanitized ConfigMaps may still contain internal URLs; restrict evidence sharing.

## 11. Lab B — AppProject isolation

Platform-owned Project:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.com/platform/demo-gitops.git
    - https://charts.example.com
    - https://gitlab.example.com/platform/demo-gitops-values.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: demo-dev
    - server: https://kubernetes.default.svc
      namespace: demo-test
    - server: https://kubernetes.default.svc
      namespace: demo-staging
    - server: https://kubernetes.default.svc
      namespace: demo-prod
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: rbac.authorization.k8s.io
      kind: Role
    - group: rbac.authorization.k8s.io
      kind: RoleBinding
\`\`\`

For stronger tenant isolation, use **separate AppProjects** per trust domain or environment rather than one shared Project allowing all four namespaces. This lab's single Project demonstrates policy syntax but is not sufficient by itself to stop a permitted Project operator from changing a Dev Application's destination to Prod.

A stronger design uses \`demo-dev-project\`, \`demo-test-project\`, \`demo-staging-project\` and \`demo-prod-project\`, each with only its approved destination. Couple that with role permissions scoped to those Projects.

## 12. Lab C — Validate denied destination

In a disposable environment, construct an Application that requests an unauthorized namespace, such as \`kube-system\`, while referencing the restricted \`demo-platform\` Project.

First validate offline:

\`\`\`bash
kubectl apply --dry-run=client -f unauthorized-destination.yaml
\`\`\`

After approval, inspect the resulting Argo CD comparison/sync authorization failure **without forcing deployment**. Restore the approved destination via reviewed GitOps change. Never use a real privileged namespace for destructive testing.

## 13. Lab D — Validate Kubernetes RBAC independently

Argo CD policy does not remove Kubernetes permissions from the controller.

Inspect authorized ServiceAccount access:

\`\`\`bash
kubectl get serviceaccounts -n argocd
kubectl get rolebindings,clusterrolebindings -A
kubectl auth can-i create deployments \
  --as=system:serviceaccount:argocd:argocd-application-controller \
  -n demo-dev
kubectl auth can-i create deployments \
  --as=system:serviceaccount:argocd:argocd-application-controller \
  -n kube-system
\`\`\`

The ServiceAccount name and workload identity vary by installation; verify before testing. Impersonation requires permission; a denied impersonation attempt does not establish the controller's actual privileges. If the controller can modify resources in forbidden namespaces, escalate the architecture risk and review namespace-scoped installation options or independent admission controls.

## 14. GitLab and repository authorization

Use GitLab protected branches, CODEOWNERS, required MR approvals and CI validation for:

- Application/AppProject/ApplicationSet definitions.
- Production Helm values.
- Chart source changes and version updates.
- Container image digest promotion.
- RBAC policy and SSO configuration.
- Cluster registration and destination changes.

Argo CD repository credentials should be read-only and scoped to approved repositories. Avoid giving Argo CD a GitLab write token or the GitLab runner a broad production kubeconfig.

## 15. Secrets and workload identity

Secrets must not be committed to GitOps values or ApplicationSet generator files. Use approved external secret management, such as AWS Secrets Manager, Azure Key Vault or Google Secret Manager, with cloud workload identity and narrowly scoped policies.

Workload identity grants cloud API access to Pods; it does **not** replace Argo CD user RBAC, AppProject restrictions or Kubernetes admission controls.

## 16. Multi-tenancy architecture choices

| Model | Advantages | Limitations |
| --- | --- | --- |
| One Argo CD, one shared Project | Simple | Weak environment isolation |
| One Argo CD, Project per environment | Better source/destination separation | Shared controller blast radius |
| One Argo CD, Project per tenant/team | Delegated governance | Complex RBAC and cluster privileges |
| Separate Argo CD installations | Stronger management separation | More operational overhead |
| Separate Kubernetes clusters | Stronger runtime isolation | More infrastructure and cost |

For the tutorial's one-cluster topology, favor Project-per-environment and GitLab approval gates for production. Strongly regulated workloads may require independent clusters despite the training architecture.

## 17. Incident: Developer can sync Production

**Scenario:** A developer unexpectedly receives permission to synchronize \`demo-app-prod\`.

1. Confirm identity, SSO group claims and current role mappings.
2. Capture sanitized \`argocd-rbac-cm\` and AppProject policy.
3. Check whether the permission comes from \`policy.default\`, group membership or wildcard grants.
4. Stop unapproved release activity and notify the security owner.
5. Revoke excess group/role permission through an approved change.
6. Test allowed Dev sync and denied Production sync with real test identities.
7. Check GitLab protected branch approvals and audit logs for unauthorized changes.
8. Record impact, detection, remediation and preventive RBAC tests.

Do not remove all administrator access before validating the break-glass path.

## 18. Incident: SSO login outage

**Scenario:** IdP certificate rotation or OIDC issuer changes prevent login.

1. Confirm Argo CD server and Kubernetes health separately.
2. Review SSO redirect URI, issuer, TLS chain, client configuration and group claims.
3. Inspect sanitized Argo CD server logs and IdP audit events.
4. Use only the documented, audited break-glass procedure if necessary.
5. Restore approved SSO configuration through change control.
6. Validate login, group mapping, MFA and permission tests.
7. Rotate any exposed credentials and close temporary access.
8. Record outage duration and add certificate/issuer expiry alerts.

Existing workloads may continue serving even if the Argo CD UI/SSO login is unavailable.

## 19. Troubleshooting matrix

| Symptom | Likely cause | First checks |
| --- | --- | --- |
| SSO login loop | Redirect URI or cookie/TLS mismatch | Argo CD URL, IdP redirect |
| User has no access | Missing group claim or role mapping | Token claims, \`policy.csv\` |
| User has too much access | Broad default role or wildcard | \`policy.default\`, inherited groups |
| Sync denied | Argo CD RBAC | Application object scope |
| Project destination denied | AppProject destination rules | \`destinations\` |
| Kubernetes forbidden | Controller ServiceAccount RBAC | RoleBindings/ClusterRoleBindings |
| Repo authentication fails | Scoped token expired | Repo credentials, GitLab logs |
| Privileged Pod blocked | Admission/Pod Security | Admission events |
| App can read another tenant's resources | Overbroad Project/default role | Project split and read permissions |
| Emergency access unavailable | Untested break-glass | Recovery owner and secret delivery |

## 20. Failure-injection and policy testing

Use an approved disposable environment and dedicated test identities:

| Test | Expected result | Recovery |
| --- | --- | --- |
| Observer tries Dev sync | Denied | No change required |
| Dev operator tries Dev sync | Allowed if approved | Validate audit event |
| Dev operator tries Prod sync | Denied | Correct role if not |
| Application targets \`kube-system\` | AppProject denies | Restore approved namespace |
| Application uses unapproved repo | AppProject denies | Restore source |
| Unauthorized RBAC resource in chart | Project/admission denies | Remove forbidden object |
| Missing IdP group claim (tabletop) | User lacks intended role | Fix IdP mapping |
| SSO outage (tabletop) | Break-glass recovery documented | Restore identity path |

Do not intentionally break the shared IdP or production SSO integration. Record whether each test was live or simulated.

## 21. Monitoring and audit

Track:

- SSO login failure rates and token/CA expiration.
- Argo CD RBAC denied actions and privileged role changes.
- AppProject source/destination denials.
- Application sync operations and initiator identity.
- GitLab MR approvals and protected branch modifications.
- Repository token rotation and authentication errors.
- Kubernetes RBAC denials and admission rejections.
- Cross-namespace network policy violations where telemetry exists.
- Argo CD API availability and controller reconciliation health.
- Production SLOs following authorized sync.

Retain audit evidence according to organizational policy and redact sensitive tokens.

## 22. EKS, AKS and GKE considerations

The Argo CD authorization model is the same across clouds, but identity and admission differ:

| Control | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Workload identity | EKS Pod Identity / IRSA | Entra Workload ID | Workload Identity Federation |
| Enterprise SSO | Approved OIDC IdP | Often Entra ID | Approved OIDC IdP |
| Secrets | AWS Secrets Manager | Azure Key Vault | Secret Manager |
| Network | VPC/CNI/NetworkPolicy | VNet/CNI/NetworkPolicy | VPC/CNI/NetworkPolicy |
| Cluster access | IAM + Kubernetes RBAC | Entra + Kubernetes RBAC | IAM + Kubernetes RBAC |

Do not confuse cloud IAM privileges with Argo CD RBAC. This chapter retains the one-cluster/four-namespace reference model on each provider.

## 23. Operational readiness checklist

- [ ] Argo CD RBAC, AppProjects and Kubernetes RBAC distinguished.
- [ ] SSO/OIDC issuer, redirect URI and MFA reviewed.
- [ ] Group claims mapped to least-privilege roles.
- [ ] Default role exposure assessed.
- [ ] Dev/Test/Staging/Prod sync permissions explicitly tested.
- [ ] Project-per-environment option evaluated.
- [ ] Repository source and destination allowlists enforced.
- [ ] No plaintext secrets in Git or evidence.
- [ ] GitLab protected branch and CODEOWNERS governance verified.
- [ ] Break-glass access tested under change control.
- [ ] Unauthorized destination and repo tests denied.
- [ ] Monitoring, audit and escalation owners documented.
- [ ] Multi-tenant blast radius and shared-cluster limits acknowledged.

## 24. Evidence worksheet

\`\`\`text
CHAPTER 046 — ENTERPRISE RBAC, SSO AND MULTI-TENANCY
Date:
Operator/reviewer:
Cluster/context:
Argo CD version:
SSO provider and issuer (sanitized):
MFA policy:
Redirect URI:
Group claim mapping:
Default RBAC role:
Role matrix:
Dev sync allow test:
Prod sync deny test:
AppProject source/destination test:
Kubernetes controller RBAC review:
GitLab CODEOWNERS/approval policy:
Repository credential scope:
External secret mechanism:
Break-glass test reference:
SSO outage tabletop:
Audit log location:
Open risks:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 25. Knowledge checks

1. How do Argo CD RBAC, AppProjects and Kubernetes RBAC differ?
2. Why is a shared Project across all four environments insufficient for strong separation?
3. Why can \`policy.default: role:readonly\` expose more than expected?
4. What happens when OIDC group claims are missing?
5. Why must Production sync permission be combined with GitLab approval gates?
6. What is the difference between cloud workload identity and Argo CD SSO?
7. Why is a tested break-glass path essential before SSO changes?
8. What threats remain when environments are separated only by namespaces?
9. How would you investigate a developer unexpectedly gaining Production sync access?
10. What evidence demonstrates least-privilege access in practice?

## 26. Completion

**Pass:** You can define least-privilege roles, validate SSO/group mapping, constrain sources and destinations, test allowed/denied operations and recover safely from authorization or login failures.

**Next: Chapter 047 — Argo CD Repository Credentials, Secrets Management, TLS and Supply-Chain Security.**
