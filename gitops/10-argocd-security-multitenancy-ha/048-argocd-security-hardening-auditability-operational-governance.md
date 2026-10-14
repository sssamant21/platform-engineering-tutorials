# Chapter 048 — Argo CD Security Hardening, Auditability and Operational Governance

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 10:** Argo CD Security, Multi-Tenancy and High Availability  
**Chapter:** 048 / 100  
**Audience:** Platform Engineers, SREs, Kubernetes Administrators, Security and Compliance Teams

> **Safety and scope:** Commands are educational and should first be run in a disposable or staging environment. Never export raw Secret values, authentication tokens, kubeconfigs or repository credentials into tickets, terminal transcripts or evidence archives. Review configuration against the exact installed Argo CD and Helm chart versions before applying.

## 1. Learning objectives

After completing this chapter, you will be able to:

1. Map Argo CD's trust boundaries and attack surfaces.
2. Harden authentication, API exposure, AppProjects, repositories, Kubernetes permissions and workloads.
3. Design layered audit trails across GitLab, Argo CD, Kubernetes and identity providers.
4. Rotate repository and cluster credentials without uncontrolled deployment interruption.
5. Detect privilege escalation, unauthorized application changes and risky project configuration.
6. Execute safe security validation labs and incident-response runbooks.
7. Define measurable governance acceptance criteria.

## 2. Enterprise reference architecture

```text
                         Enterprise identity provider
                              (MFA, groups, SSO)
                                      |
                                      v
Developer --> GitLab MR --> protected branch --> GitOps repo
               |                |                   |
         CODEOWNERS, scans   signed/reviewed        v
                                                Argo CD
                                      ingress/TLS -> API/RBAC
                                                     |
                         +---------------------------+------------------+
                         |                           |                  |
                      AppProjects                repo-server        controllers
                         |                           |                  |
                source/destination limits      trusted Git/Helm    scoped K8s API
                         |                           |                  |
                         +---------------------------+------------------+
                                                     |
                                               EKS / AKS / GKE
                                                     |
                                          audit logs + metrics + SIEM
```

**Trust boundary:** Git approval, Argo CD authorization and Kubernetes authorization are separate controls. A permitted Git change can still be dangerous if a Project accepts untrusted sources, an Application can target sensitive namespaces, or the Argo CD controller has overly broad Kubernetes privileges.

### Threat model

| Threat | Example | Defense |
| --- | --- | --- |
| Credential theft | Leaked repository deploy key or Argo CD token | Short-lived identity, vault-backed secrets, rotation and alerting |
| Privilege escalation | Tenant creates Application targeting another team's namespace | AppProject destinations plus Kubernetes RBAC and admission policy |
| Malicious Git change | Unreviewed privileged manifest | Protected branches, CODEOWNERS, scanning, admission enforcement |
| Untrusted manifest rendering | Malicious config-management plugin | Restricted plugin execution, trusted sources, isolated repo-server |
| Control-plane exposure | Public Argo CD API with weak authentication | Private access, TLS, SSO/MFA, rate limits and network controls |
| Audit gaps | Direct kubectl mutation bypasses Git | Kubernetes audit logs, drift alerts and correlated identity evidence |
| Supply-chain compromise | Mutable image tag or untrusted chart | Digest pinning, provenance, policy and reviewed artifact promotion |

## 3. Baseline inventory and version validation

Capture non-secret baseline information before making changes.

```bash
kubectl config current-context
kubectl -n argocd get deploy,sts,svc,ingress,pdb -o wide
kubectl -n argocd get cm argocd-cm argocd-rbac-cm -o yaml
kubectl -n argocd get sa,role,rolebinding,clusterrole,clusterrolebinding
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
helm -n argocd list
argocd version --client
```

**Evidence hygiene:** ConfigMaps can still include sensitive infrastructure details; redact before sharing. Never run `kubectl get secret -o yaml` as a general audit collection command.

Create a security inventory with component/version, ingress exposure, authentication mode, authorized teams, AppProjects, repository credential owners, cluster access scope, audit log destinations and retention requirements.

## 4. Authentication and session hardening

Use enterprise OIDC or a supported SSO integration, enforced MFA at the identity provider, controlled group mapping, documented emergency access and regular access reviews.

Illustrative Argo CD configuration (adapt issuer, redirect URL and group claims to your identity provider):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.internal
  admin.enabled: "false"
  oidc.config: |
    name: EnterpriseOIDC
    issuer: https://idp.example.internal
    clientID: argocd
    clientSecret: $oidc.enterprise.clientSecret
    requestedScopes: ["openid", "profile", "email", "groups"]
```

The client secret reference must be backed by an appropriately protected Secret key using the supported Argo CD configuration mechanism. **Do not disable the local admin account until SSO, a second administrator and a tested break-glass procedure are verified.**

Validation:

```bash
kubectl -n argocd get cm argocd-cm -o jsonpath='{.data.url}{"\n"}'
argocd account get-user-info
argocd account list
```

Do not place long-lived API tokens in pipeline variables when a supported short-lived identity or workload federation flow is available. Protect any unavoidable token using a secret manager, minimal permissions, rotation and expiration.

## 5. RBAC least privilege and deny-by-default design

Argo CD RBAC controls Argo CD API actions. It does **not** replace Kubernetes RBAC or AppProject boundaries.

Example tenant role:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:authenticated
  policy.csv: |
    p, role:authenticated, applications, get, tenant-dev/*, allow
    p, role:team-dev, applications, get, tenant-dev/*, allow
    p, role:team-dev, applications, sync, tenant-dev/*, allow
    p, role:team-dev, applications, update, tenant-dev/*, allow
    g, platform-team-dev, role:team-dev
  scopes: '[groups]'
```

**Important:** `role:authenticated` is a custom role in this example, not a built-in policy; it receives only the explicit `applications,get` rule. Avoid a broad `role:readonly` default in multi-tenant deployments because it may expose other teams' applications. Review the exact object matching syntax, including applications-in-any-namespace behavior, for the deployed Argo CD version. Deny policies cannot be overridden by allows in Argo CD's RBAC model; test the effective policy rather than assuming order-based behavior.

Test with supported CLI capabilities for your installed version:

```bash
argocd admin settings rbac can team-dev get applications 'tenant-dev/demo-app'
argocd admin settings rbac can team-dev sync applications 'tenant-dev/demo-app'
argocd admin settings rbac can team-dev delete applications 'tenant-prod/payments'
```

CLI argument order and support vary by release: consult `argocd admin settings rbac can --help` before use. Record both expected allowed and denied outcomes. A failed authorization test must block promotion.

## 6. AppProject source, destination and resource controls

AppProjects limit allowed sources, destinations and Kubernetes resource kinds. Example staging tenant Project:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: tenant-dev
  namespace: argocd
spec:
  description: Restricted development team project
  sourceRepos:
    - https://gitlab.example.internal/platform/team-dev-gitops.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: demo-dev
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
    - group: ""
      kind: LimitRange
  roles:
    - name: developer
      description: Development app access
      policies:
        - p, proj:tenant-dev:developer, applications, get, tenant-dev/*, allow
        - p, proj:tenant-dev:developer, applications, sync, tenant-dev/*, allow
```

An empty `clusterResourceWhitelist` restricts cluster-scoped resources under the Project's allowlist semantics. Namespaced resources not explicitly blacklisted can still be deployed; use Kubernetes admission policy and namespace RBAC for stronger enforcement. A Project's namespace restriction alone is insufficient if the Argo CD controller has cluster-admin and other application or credential paths remain unrestricted.

Production guardrails:

- No wildcard source repositories or destination namespaces for untrusted tenants.
- Separate production Projects, approval workflows and credentials from development.
- Protect `AppProject`, `Application`, `ApplicationSet`, and Argo CD configuration changes with CODEOWNERS and admission controls.
- Audit ApplicationSet generators and template values to prevent unexpected Application creation.
- Restrict cluster-scoped and privileged Kubernetes resources independently using admission policy.
- Prefer dedicated production clusters for high-risk isolation requirements.

## 7. Kubernetes authorization, network and pod security

Inspect service-account bindings without changing them:

```bash
kubectl -n argocd get sa
kubectl get clusterrolebinding -o wide | grep -i argocd || true
kubectl auth can-i create deployments \
  --as=system:serviceaccount:argocd:argocd-application-controller \
  -n demo-dev
kubectl auth can-i create clusterroles \
  --as=system:serviceaccount:argocd:argocd-application-controller
```

The `kubectl auth can-i --as` examples require impersonation permission. A successful check reflects Kubernetes authorization for the impersonated identity, not proof that every other guardrail is enforced.

Network hardening should limit Argo CD component ingress and egress to required Git, DNS, Kubernetes API, Redis, identity provider and metrics endpoints. Do not apply a blanket deny policy without first mapping these dependencies. Pod security settings should use non-root execution, restricted capabilities, seccomp and read-only filesystems where supported by the actual component image and workload.

## 8. Repository, Helm and plugin supply-chain security

Use reviewed, protected Git branches and immutable revisions for promotion. Prefer immutable image digests and trusted OCI/chart repositories. Prevent untrusted users from changing repository credentials, custom config-management plugins, Helm values paths or Application sources.

```bash
argocd repo list
argocd app get demo-staging
argocd app history demo-staging
argocd app manifests demo-staging > /tmp/demo-staging-rendered.yaml
```

Rendered manifests can contain sensitive values; restrict permissions on local output and delete it after review. For compliance evidence, store redacted diffs or hashes rather than unredacted manifests.

**Plugin warning:** Config-management plugins may execute arbitrary tooling during rendering. Review and isolate plugin containers, disable unnecessary capabilities, limit resources and restrict access to credentials.

## 9. Audit architecture and evidence correlation

Argo CD events alone are not a complete audit trail. Combine:

1. **GitLab:** merge requests, approvals, protected-branch events, commit identity, pipeline outcomes.
2. **Argo CD:** application sync history, operations, API/server logs and relevant Kubernetes events.
3. **Kubernetes API:** audit records for writes to Application/AppProject resources and target workloads.
4. **Identity provider:** authentication, MFA, group membership and access changes.
5. **Cloud/platform:** cluster access, secret-manager reads, IAM changes and network access.
6. **SIEM:** correlation, retention, access restrictions and incident evidence.

Minimum audit record:

| Field | Example |
| --- | --- |
| Event time | UTC ISO-8601 |
| Actor | Human/service identity |
| Source | GitLab, Argo CD, Kubernetes, IdP |
| Change reference | MR, commit SHA, release ID |
| Target | Project, Application, namespace, cluster |
| Action/outcome | Sync succeeded, denied access, policy changed |
| Correlation | Request ID, revision, incident/change ticket |
| Evidence | Redacted log location and retention policy |

**Retention:** define periods with security/compliance stakeholders; do not assume one universal retention period. Ensure logs are shipped off-cluster and access controlled.

## 10. Hands-on lab A — Audit a tenant boundary

**Goal:** confirm an unprivileged tenant cannot administer another team's production Application.

Prerequisites: two staging Projects (`tenant-dev` and `tenant-prod`), a test user mapped only to the development group and a harmless test Application in each Project.

1. Record the test identity's effective groups.
2. Confirm the development Application can be viewed.
3. Attempt a read and sync authorization check for the production Application.
4. Confirm access is denied and an appropriate audit event is generated.
5. Check Kubernetes API audit events for any unexpected write attempts.

```bash
argocd account get-user-info
argocd app get tenant-dev-demo
# Use a separate low-privilege test session for the negative test:
argocd app get tenant-prod-demo
```

**Pass:** the development user can perform approved actions only; production access is denied; evidence identifies the actor, time, attempted action and outcome. Do not use an administrator token to simulate tenant permissions.

## 11. Hands-on lab B — Detect unsafe AppProject configuration

Create a deliberately insecure Project **as a local file only**. Do not apply it.

```yaml
# insecure-project.yaml — NEVER APPLY
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: insecure-example
  namespace: argocd
spec:
  sourceRepos: ["*"]
  destinations:
    - server: "*"
      namespace: "*"
  clusterResourceWhitelist:
    - group: "*"
      kind: "*"
```

Review the file for wildcard sources, destinations and cluster-resource access. Use a CI policy check (for example, Conftest/OPA or a Kubernetes admission policy) to fail a merge request that introduces this configuration.

```bash
grep -nE 'sourceRepos|destinations|clusterResourceWhitelist|\*' insecure-project.yaml
# Add a version-controlled policy test and verify the CI job rejects the file.
```

**Pass:** the insecure Project is rejected before merge/deployment. Remove the local file after the lab.

## 12. Hands-on lab C — Credential rotation tabletop

Perform a tabletop or staging-only rotation; never revoke shared production credentials during a lab.

1. Inventory repository or cluster credential owners, scopes, expiration and dependencies.
2. Provision a replacement credential in the approved secret manager.
3. Update the supported External Secrets/secret reference path.
4. Verify Argo CD repository connectivity and a canary manifest generation.
5. Revoke the old credential only after validation and an approved overlap window.
6. Verify the revoked credential cannot authenticate.
7. Capture redacted audit evidence and record next rotation date.

```bash
argocd repo list
argocd app get demo-staging --refresh
argocd app diff demo-staging
kubectl -n argocd get externalsecret 2>/dev/null || true
```

An ExternalSecret object is optional and depends on the installed secrets solution. Do not print token values or copy Kubernetes Secret contents into evidence.

**Pass:** canary reconciliation succeeds with the new credential; old credential is revoked; logs contain no secrets; a rollback/recovery owner is assigned.

## 13. Hands-on lab D — Unauthorized drift and evidence collection

In a disposable staging namespace, modify a non-sensitive annotation on a test Deployment through `kubectl`, then observe drift. Ensure the Application's reconciliation settings are known before the test.

```bash
kubectl -n demo-dev annotate deploy demo-web \
  training.example/drift-test=chapter048 --overwrite
argocd app get demo-staging --refresh
argocd app diff demo-staging
```

If automated self-heal is enabled, Argo CD may revert the annotation quickly. If not, restore desired state using the approved sync workflow. Confirm Kubernetes audit logs capture the direct API write and Argo CD records the reconciliation. Do not create drift in production workloads.

**Pass:** unauthorized drift is detected or remediated, with actor and change evidence traceable through audit sources.

## 14. Security monitoring and alerting

| Detection | Signal | Response |
| --- | --- | --- |
| Repeated login failures | IdP and API logs | Check account abuse, SSO outage, clock skew |
| Unexpected RBAC change | GitLab diff plus Kubernetes audit | Freeze promotion, validate approval, revert if unauthorized |
| Wildcard AppProject introduced | CI policy and cluster admission | Block change, inspect other Projects |
| Unapproved production sync | Argo CD operation + MR linkage | Preserve evidence, evaluate workload impact |
| Repository credentials rejected | Repo-server errors and secret-manager audit | Validate rotation and access scope |
| Application source changes | Git review and Application resource audit | Confirm authorized repository/revision |
| Drift after direct kubectl write | Kubernetes audit + Argo CD OutOfSync | Identify actor and restore desired state |

Tune alert thresholds using baseline activity; distinguish failed access attempts from confirmed compromise. Route high-confidence production policy changes to security on-call.

## 15. Troubleshooting matrix — ten security scenarios

| # | Symptom | Investigation | Safe response |
| --- | --- | --- | --- |
| 1 | SSO login denied | IdP claims, redirect URI, time skew | Repair group mapping/IdP configuration |
| 2 | User sees other tenant apps | Default RBAC, group claims, Project roles | Remove broad access, retest negative cases |
| 3 | User can sync but not view app | Action-specific RBAC rules | Align approved get/sync policy |
| 4 | Production Application created from dev repo | AppProject source/destination and ApplicationSet | Restrict sources and review generators |
| 5 | Unauthorized cluster-scoped object | Controller RBAC, Project whitelist, admission | Block kind, investigate actor |
| 6 | Repository authentication fails after rotation | Credential reference, scope, expiry | Restore valid credential using secret manager |
| 7 | Missing sync audit evidence | Argo CD logs, retention, cluster audit | Repair forwarding and correlation |
| 8 | Direct kubectl change not attributed | API audit policy and identity propagation | Enable suitable audit records, investigate access |
| 9 | Repo-server plugin accesses sensitive resources | Plugin permissions and mounted secrets | Isolate plugin and rotate exposed credentials |
| 10 | Emergency admin access unavailable | SSO outage, break-glass custody | Follow approved emergency-access procedure |

## 16. Production runbook — suspected unauthorized GitOps deployment

**Trigger:** unapproved production sync, unknown actor, suspicious Application/AppProject mutation, or a policy bypass alert.

**First 15 minutes**

```bash
kubectl -n argocd get applications,appprojects
argocd app get AFFECTED_APP
argocd app history AFFECTED_APP
kubectl -n argocd get events --sort-by=.lastTimestamp | tail -40
```

1. Declare the incident and notify the security/platform incident commander.
2. Preserve GitLab MR, commit, pipeline, Argo CD and Kubernetes audit references.
3. Determine whether customer-serving workloads changed and assess immediate impact.
4. Suspend **only the affected promotion path** using the approved workflow; avoid globally disabling reconciliation without an impact assessment.
5. Revoke confirmed compromised credentials through the identity/secret-management owners.
6. Restore a reviewed known-good Git revision and reconcile using the approved deployment mechanism.
7. Validate the deployed image digest, manifest state, access controls and workload health.
8. Document root cause, detection gap, remediation owner and follow-up deadline.

**Do not:** delete audit logs, rotate all secrets indiscriminately, expose token values, or assume that Git history alone proves the deployed state.

## 17. Rollback, cleanup and recovery

For a failed RBAC or SSO change, prefer reverting the reviewed Git commit or Helm values change. Maintain a tested, narrowly scoped break-glass method outside the normal SSO dependency and audit every use. If an AppProject policy change breaks legitimate reconciliation, restore the previous approved policy rather than temporarily enabling `*` sources or destinations.

Lab cleanup:

```bash
# Confirm staging context and exact resources first.
kubectl config current-context
kubectl -n demo-dev get deploy demo-web
# Reconcile demo-staging through the approved Argo CD workflow.
argocd app get demo-staging --refresh
```

Do not automatically delete the shared namespace, Argo CD installation or production Application resources as part of lab cleanup.

## 18. Production acceptance criteria

- [ ] SSO/MFA, group mapping and break-glass access tested.
- [ ] Default Argo CD RBAC does not disclose cross-tenant applications.
- [ ] Tenant allow/deny authorization tests are automated.
- [ ] AppProjects restrict Git sources, destinations and cluster resources.
- [ ] Kubernetes RBAC and admission policies enforce independent boundaries.
- [ ] GitLab protected branches, CODEOWNERS and approvals protect configuration.
- [ ] Repository and cluster credentials have documented owners and rotation paths.
- [ ] Secret values are excluded from audit evidence and logs.
- [ ] Argo CD, Kubernetes, GitLab and IdP audit records are correlated.
- [ ] Audit retention, integrity and SIEM forwarding are tested.
- [ ] Unauthorized drift and policy changes trigger actionable alerts.
- [ ] Incident response, rollback and credential recovery are rehearsed.
- [ ] Security sign-off and change ticket evidence are recorded.

## 19. Knowledge check

1. Why does an AppProject restriction not replace Kubernetes RBAC?
2. Why can `policy.default: role:readonly` be risky for tenant isolation?
3. Which audit sources are needed to attribute a direct Kubernetes write?
4. What is the correct order for rotating a repository credential?
5. How would you distinguish an IdP outage from an RBAC denial?
6. Why must a break-glass procedure work independently of the usual SSO path?
7. Which CI and admission controls help block a wildcard AppProject?
8. Why is a Git commit SHA insufficient as the sole evidence of production deployment?

## 20. References

- [Argo CD RBAC](https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/)
- [Argo CD Projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [Argo CD Security Considerations](https://argo-cd.readthedocs.io/en/stable/operator-manual/security/)
- [Argo CD User Management](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/)
- [Kubernetes Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

---

**Chapter 048 complete.** Next: **Chapter 049 — Argo CD Multi-Cluster Access, Credential Management and Secure Fleet Operations** (proposed).
