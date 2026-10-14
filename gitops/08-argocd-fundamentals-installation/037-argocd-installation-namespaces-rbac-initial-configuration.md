# Chapter 037 — Argo CD Installation, Namespaces, RBAC and Initial Configuration

**Part 08 — Argo CD Fundamentals and Installation** | **Chapter 037 / 100**  
**Audience:** Kubernetes administrators, platform engineers and SREs  
**Reference architecture:** One cluster with four application namespaces (\`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`) and the Argo CD control-plane namespace (\`argocd\`).  
**Prerequisite:** Chapter 036 and authorization to inspect or change a disposable Kubernetes cluster.

> **Safety:** Installing Argo CD typically creates cluster-scoped CRDs and RBAC. Use a pinned, reviewed release on an approved cluster only. Never install a second Argo CD instance over an existing deployment, use unpinned \`latest\` manifests, expose an admin UI publicly, or commit Git/SSO credentials. The default lab can be performed read-only.

## 1. Learning objectives

- Plan a supported, secure Argo CD installation.
- Identify control-plane components, CRDs and Kubernetes permissions.
- Understand cluster-scoped versus namespace-scoped installation boundaries.
- Validate API/UI access, SSO, Argo CD RBAC and Kubernetes RBAC.
- Define a restricted AppProject and connect an approved GitLab repository.
- Prepare four namespace-specific Applications with manual synchronization.
- Troubleshoot install, auth, repository and manifest-generation failures.
- Produce installation, monitoring, backup and rollback evidence.

## 2. Architecture

\`\`\`text
GitLab CI -> build/test/scan/sign -> OCI image@sha256:<digest>
                  |
         Reviewed GitOps repo
                  |
             Argo CD
       namespace: argocd
   argocd-server / repo-server
   application-controller / Redis
   ApplicationSet controller
                  |
           Kubernetes API
                  |
           ONE cluster
   demo-dev | demo-test | demo-staging | demo-prod
\`\`\`

Argo CD is the authoritative deployment reconciler for the four applications. GitLab CI does not need broad production kubeconfig permissions merely to update GitOps desired state. The Argo CD control plane itself can be installed with reviewed manifests or managed through a separate Helm release, but do not mix those installation methods.

## 3. Installation choices

| Method | Benefits | SRE caveats |
| --- | --- | --- |
| Pinned official release manifests | Explicit review of all objects | Own upgrade/patch process |
| Pinned official Helm chart | Repeatable configuration and upgrades | Bootstrap release ownership |
| Approved platform distribution | Vendor lifecycle support | Check compatibility and governance |

Use a **specific, approved Argo CD release tag**, matched to the Kubernetes version and security policy. The release tag is deliberately a placeholder here; do not guess what is approved.

## 4. Preflight and change control

Run:

\`\`\`bash
kubectl config current-context
kubectl cluster-info
kubectl version
kubectl get namespaces
kubectl get crd
kubectl get deployments,statefulsets -A
kubectl auth can-i create namespaces
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
\`\`\`

Check for existing \`applications.argoproj.io\`, \`appprojects.argoproj.io\`, \`applicationsets.argoproj.io\`, and an existing Argo CD control plane. If present, **stop and inspect** rather than reinstall.

Record the cluster, owner, change ID, approved release, manifest checksum, installation method, maintenance window, access model and backup/rollback procedure.

## 5. Namespace plan

\`\`\`text
argocd          Argo CD control plane
demo-dev        Development workload
demo-test       Test workload
demo-staging    Staging workload
demo-prod       Production workload
\`\`\`

In an approved lab only:

\`\`\`bash
kubectl create namespace argocd
kubectl create namespace demo-dev
kubectl create namespace demo-test
kubectl create namespace demo-staging
kubectl create namespace demo-prod
\`\`\`

Skip creation for namespaces that already exist. Namespace separation does not equal independent clusters or strong security isolation. Production-critical workloads may require separate clusters.

## 6. Download and verify a pinned installation manifest

Use a real, reviewed release tag in the official versioned path:

\`\`\`text
https://raw.githubusercontent.com/argoproj/argo-cd/<APPROVED_VERSION>/manifests/install.yaml
\`\`\`

**Bash:**

\`\`\`bash
ARGOCD_VERSION='<APPROVED_VERSION>'
curl --fail --location --output argocd-install.yaml \
  "https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml"
sha256sum argocd-install.yaml
kubectl apply --dry-run=client -n argocd -f argocd-install.yaml
\`\`\`

**PowerShell:**

\`\`\`powershell
$ArgoCDVersion = '<APPROVED_VERSION>'
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/argoproj/argo-cd/$ArgoCDVersion/manifests/install.yaml" -OutFile argocd-install.yaml
Get-FileHash .\argocd-install.yaml -Algorithm SHA256
kubectl apply --dry-run=client -n argocd -f .\argocd-install.yaml
\`\`\`

Compare the downloaded artifact against a trusted release checksum/signature or internal approved mirror. A checksum calculated after downloading is useful for recording integrity but **does not by itself authenticate the publisher**. Review CRDs, ClusterRoles, ClusterRoleBindings, ServiceAccounts and Secrets before applying. Client-side dry run does not prove API admission or full RBAC compatibility.

## 7. Install in an authorized disposable cluster

After approval:

\`\`\`bash
kubectl apply -n argocd -f argocd-install.yaml
kubectl get crd
kubectl get deployments,statefulsets,services -n argocd
kubectl get pods -n argocd -o wide
\`\`\`

Inspect actual workload kinds before waiting. Common deployments include:

\`\`\`bash
kubectl rollout status deployment/argocd-server -n argocd --timeout=5m
kubectl rollout status deployment/argocd-repo-server -n argocd --timeout=5m
\`\`\`

The application controller can be a StatefulSet or Deployment depending on installation topology. Use the live inventory to determine its kind. Validate the repo-server, controller, API server, cache and ApplicationSet controller, where installed. API server readiness alone does not establish a healthy GitOps system.

## 8. Helm-based installation alternative

If your organization uses the official Argo Helm chart, pin and verify the **chart version** separately from the Argo CD application version:

\`\`\`bash
helm show chart <APPROVED_CHART_REFERENCE> --version <APPROVED_CHART_VERSION>
helm template argocd <APPROVED_CHART_REFERENCE> \
  --version <APPROVED_CHART_VERSION> \
  --namespace argocd -f argocd-platform-values.yaml > rendered-argocd.yaml
\`\`\`

These are placeholders, not commands to run literally. Review the rendered cluster-scoped resources and CRD lifecycle. Do not apply upstream install manifests and install the Helm chart over the same resources.

**Ownership distinction:** A Helm-managed Argo CD **control plane** can manage Argo CD-rendered Helm **applications**; application rollbacks should still use reviewed GitOps desired state.

## 9. Audit Kubernetes RBAC and CRDs

\`\`\`bash
kubectl get crd applications.argoproj.io
kubectl get crd appprojects.argoproj.io
kubectl get crd applicationsets.argoproj.io
kubectl get serviceaccounts,roles,rolebindings -n argocd
kubectl get clusterroles,clusterrolebindings
\`\`\`

Review which Argo CD ServiceAccounts have cluster-wide permissions. AppProject policy restricts Argo CD's sync decisions, but does **not** reduce underlying Kubernetes credentials. Use restricted control-plane access, admission policies and namespace-scoped installation patterns where appropriate.

## 10. Private API/UI access and bootstrap identity

For an authorized lab, keep the UI private:

\`\`\`bash
kubectl port-forward -n argocd svc/argocd-server 8080:443
\`\`\`

Open \`https://localhost:8080\` in your browser. Handle bootstrap admin credentials only through the approved secret-access process. Never paste them into Git, chat, CI output or incident tickets. Configure SSO/OIDC, verify least-privilege access and a break-glass account, then disable routine use of local admin credentials.

Do not add a public LoadBalancer or ingress as part of this introductory lab.

## 11. Argo CD RBAC example

Example **conceptual** \`argocd-rbac-cm\` policy:

\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    p, role:dev-operator, applications, get, demo-platform/*, allow
    p, role:dev-operator, applications, sync, demo-platform/demo-app-dev, allow
    p, role:release-approver, applications, get, demo-platform/*, allow
    p, role:release-approver, applications, sync, demo-platform/demo-app-prod, allow
    g, platform-dev-operators, role:dev-operator
    g, platform-release-approvers, role:release-approver
\`\`\`

Do not apply this policy blindly. Verify the installed version's policy syntax and identity-provider group claims. \`role:readonly\` can expose broad metadata; use a more restrictive default where confidentiality requires it. Argo CD RBAC, GitLab approvals and Kubernetes RBAC are independent layers.

## 12. Restricted AppProject

\`demo-platform-project.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  description: Approved demo workloads in one training cluster
  sourceRepos:
    - https://gitlab.example.com/platform/demo-gitops.git
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

Review source URLs, namespaces and required resource kinds before creating:

\`\`\`bash
kubectl apply --dry-run=client -f demo-platform-project.yaml
kubectl apply -f demo-platform-project.yaml
kubectl get appproject demo-platform -n argocd -o yaml
\`\`\`

Restrict Project mutation permissions; otherwise users could modify the policy boundary itself.

## 13. GitLab repository connectivity

Use an approved repository URL and **read-only** access for the repo-server wherever possible. For private repositories, use narrowly scoped deploy tokens or approved short-lived credentials from the enterprise secret store. Avoid embedding tokens in URLs, Helm values or Application manifests.

Check repository authentication, TLS trust, DNS, proxy/egress and the actual source path when manifest generation fails. GitLab CI should promote through reviewed GitOps MRs, not through Argo CD admin credentials.

## 14. First manual-sync Application

The repository must contain the chart and \`charts/demo-app/env/dev-values.yaml\`. This chart-local values layout avoids ambiguous paths outside the Helm chart source.

\`demo-app-dev.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app-dev
  namespace: argocd
spec:
  project: demo-platform
  source:
    repoURL: https://gitlab.example.com/platform/demo-gitops.git
    targetRevision: main
    path: charts/demo-app
    helm:
      releaseName: demo-app
      valueFiles:
        - env/dev-values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-dev
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
\`\`\`

Only after repository and Project approval:

\`\`\`bash
kubectl apply --dry-run=client -f demo-app-dev.yaml
kubectl apply -f demo-app-dev.yaml
kubectl get application demo-app-dev -n argocd -o yaml
\`\`\`

This defines an Application but does not enable automated sync, self-heal or prune. Perform a separately authorized manual sync only after reviewing the diff and verifying the image digest.

Repeat the design with separate Applications and \`env/test-values.yaml\`, \`env/staging-values.yaml\`, and \`env/prod-values.yaml\` for the corresponding namespaces. Keep the image digest identical across a single promotion wave.

## 15. Initial sync policy and deletion safeguards

Start with manual synchronization:

\`\`\`yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=false
\`\`\`

Before enabling automated sync, document who can approve GitOps changes, how drift is handled, which resources can be pruned, what happens when desired state becomes empty, and who authorizes emergency rollback. Review finalizers, PVC retention and cluster-scoped objects.

Do not turn on prune or self-heal just to make a lab appear automatic.

## 16. Read-only validation

\`\`\`bash
kubectl get deployments,statefulsets,pods,services -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl get appprojects.argoproj.io -n argocd
kubectl get events -n argocd --sort-by=.lastTimestamp
kubectl describe application demo-app-dev -n argocd
\`\`\`

Record sync status and health **separately**. An Application can be Synced but Degraded. Check actual Deployment availability, Service EndpointSlices and application error/latency SLIs.

## 17. Failure injection and troubleshooting

Use disposable Applications only:

| Scenario | Expected symptom | First check | Recovery |
| --- | --- | --- | --- |
| Invalid GitLab URL | Repository fetch error | Repo-server logs and DNS | Restore approved URL |
| Expired deploy token | Authentication error | Credential expiry/scopes | Rotate token |
| Wrong Helm values path | Manifest generation error | Chart source layout | Fix chart-local path |
| Wrong destination namespace | AppProject denies sync | Project destinations | Restore approved namespace |
| Missing CRD | API resource unavailable | Installed CRD inventory | Correct approved installation |
| RBAC denied | Kubernetes forbidden | ServiceAccount bindings | Review scoped permission |
| SSO group mismatch | Unauthorized UI/API | Group claims and policy | Fix approved mapping |
| ImagePullBackOff | Application Degraded | Pod events and digest | Restore verified image |
| Repo-server resource pressure | Slow renders/timeouts | CPU/memory and logs | Rightsize/scale safely |
| Controller backlog | Delayed reconciliation | Controller metrics and API throttling | Capacity review |

Never simulate controller outages by deleting shared Argo CD Pods.

## 18. SRE incident runbook

**Scenario:** Argo CD is installed, but the Dev Application cannot generate manifests.

1. Confirm cluster context, Application, Project, source URL and target revision.
2. Check repo-server readiness, network/DNS, TLS trust and GitLab authentication.
3. Verify chart path, Helm values path and locked dependencies.
4. Reproduce offline with \`helm dependency build\`, \`helm lint\` and \`helm template\`.
5. Inspect Application conditions and sanitized repo-server logs.
6. Correct the reviewed GitOps source or credential configuration.
7. Reconcile only after approval; verify sync, health, Pods and Service endpoints.
8. Record root cause, timeline, recovery and preventive CI checks.

For a production control-plane incident, preserve existing workload availability and avoid uncontrolled resource pruning.

## 19. HA, backup, monitoring and upgrade readiness

Before production adoption, assign owners for:
- Backups of declarative Applications, AppProjects, RBAC, SSO and repository configuration.
- Secure recovery of credentials through the enterprise secret store.
- CRD compatibility and supported Argo CD/Kubernetes upgrade order.
- HA design for server, controller, repo-server and cache.
- Controller reconciliation latency, queue depth, manifest generation failures and component saturation.
- API/SSO availability and audit logs.
- Restore drills that do not accidentally prune application resources.

Do not assume downgrading the Argo CD binary also safely downgrades CRDs.

## 20. EKS, AKS and GKE operational considerations

| Concern | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Workload identity | EKS Pod Identity / IRSA | Microsoft Entra Workload ID | Workload Identity Federation |
| Approved OCI registry | ECR | ACR | Artifact Registry |
| Secret source | AWS Secrets Manager | Azure Key Vault | Google Secret Manager |
| Private networking | VPC endpoints, DNS, egress | VNet, DNS, egress | VPC, DNS, egress |
| Audit/monitoring | CloudWatch / managed Prometheus | Azure Monitor / managed Prometheus | Cloud Monitoring / managed Prometheus |

Cloud identity grants must be scoped to actual Argo CD needs; avoid broad cloud-admin roles.

## 21. Acceptance checklist

- [ ] Cluster context and change approval recorded.
- [ ] Existing Argo CD deployment checked before installation.
- [ ] Approved version and artifact integrity documented.
- [ ] CRDs and cluster-scoped RBAC reviewed.
- [ ] Control-plane components healthy.
- [ ] UI/API access private and TLS protected.
- [ ] SSO, least privilege and break-glass documented.
- [ ] GitLab repository access uses scoped credentials.
- [ ] AppProject restricts repositories and destinations.
- [ ] Dev Application uses a real chart-local values path.
- [ ] Four namespace-specific Application design reviewed.
- [ ] Manual sync policy and deletion safeguards documented.
- [ ] Read-only validation and failure tests captured.
- [ ] Monitoring, backup and upgrade owners assigned.

## 22. Evidence worksheet

\`\`\`text
CHAPTER 037 — ARGO CD INSTALLATION
Date:
Operator/reviewer:
Cluster/context:
Kubernetes version:
Approved Argo CD version:
Installation method:
Manifest/chart integrity evidence:
Change ID:
Namespace inventory:
CRD inventory:
RBAC and ClusterRoleBinding review:
Component readiness:
SSO group mapping:
Unauthorized-access test:
GitLab repository authentication:
AppProject policy:
Dev Application sync/health:
Image digest:
Prune/self-heal policy:
Monitoring and backup owner:
Failure tests:
Recovery evidence:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 23. Knowledge checks

1. Why can an Argo CD installation affect cluster-scoped resources?
2. What is the difference between Argo CD RBAC and Kubernetes RBAC?
3. Why is a pinned release preferable to a \`latest\` manifest?
4. Why should bootstrap access use a private route?
5. What does an AppProject restrict?
6. Why is a read-only GitLab token preferred for repository fetching?
7. Why does defining an Application not necessarily deploy it?
8. Why start with manual sync and pruning disabled?
9. How would you diagnose a manifest-generation error?
10. What must be backed up before an Argo CD upgrade?

## 24. Completion

**Pass:** The operator can inspect or safely install an approved pinned Argo CD release, audit RBAC/CRDs, define a restricted AppProject, connect a trusted GitLab source, and prepare a manual-sync Dev Application with evidence and recovery procedures.

**Next: Chapter 038 — Argo CD CLI, UI, Authentication and Repository Connectivity.**
