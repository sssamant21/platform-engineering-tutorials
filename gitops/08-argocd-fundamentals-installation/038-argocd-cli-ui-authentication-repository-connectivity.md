# Chapter 038 — Argo CD CLI, UI, Authentication and Repository Connectivity

**Part 08 — Argo CD Fundamentals and Installation** | **Chapter 038 of 100**  
**Audience:** SREs, Kubernetes administrators and platform/infrastructure engineers  
**Prerequisites:** Chapters 036–037; authorized read access to an existing Argo CD installation  
**Reference design:** One Kubernetes cluster, Argo CD in \`argocd\`, four application namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.

> **Safety:** Default exercises are read-only. Use a disposable environment for repository registration, token rotation, SSO changes or sync tests. Do not paste tokens, passwords, kubeconfigs, secret contents or sensitive logs into Git, CI artifacts or tickets. Commands referencing \`argocd.example.com\`, \`gitlab.example.com\` and \`demo-app-dev\` are illustrative; replace them only with authorized resources.

## 1. Objectives

After this chapter, you can:

1. Connect securely to Argo CD through its UI and CLI.
2. Explain Argo CD API access, SSO/OIDC, local accounts and token handling.
3. Inspect Applications, Projects, repositories, sync/health and revision history.
4. Diagnose CLI TLS, DNS, proxy, gRPC and RBAC errors.
5. Register and validate GitLab HTTPS/SSH repositories securely.
6. Apply least-privilege repository credentials and certificate trust.
7. Understand Argo CD repository Secrets and repository credential templates.
8. Verify chart source paths and Helm values without changing workloads.
9. Troubleshoot repo-server connectivity and manifest-generation failures.
10. Produce an operational runbook and evidence-backed acceptance result.

## 2. Where the CLI and UI fit

\`\`\`text
SRE browser / argocd CLI
          |
   HTTPS / gRPC(-web)
          |
      argocd-server
          |
   Authentication / RBAC
          |
     Argo CD API
          |
    Applications / Projects
          |
      repo-server ---------> GitLab GitOps repository
          |                    (HTTPS or SSH)
    manifest generation
          |
   application-controller
          |
     Kubernetes API
          |
   demo-dev / demo-test /
   demo-staging / demo-prod
\`\`\`

The CLI and UI are operational interfaces to Argo CD. They do **not** replace GitLab merge-request approval or the Kubernetes API's own RBAC/admission controls.

## 3. Connection and identity models

| Method | Appropriate use | Security concern |
| --- | --- | --- |
| SSO/OIDC interactive login | Human operators | Session and group-claim mapping |
| Local Argo CD account | Break-glass or restricted service use | Password/token lifecycle |
| Project-scoped role token | Narrow automation where supported | Token expiration and revocation |
| Kubernetes access to Application CRDs | Read-only cluster investigation | Kubeconfig and Kubernetes RBAC |
| Argo CD CLI with \`--core\` | Kubernetes API-based mode | Different auth and authorization path |

Prefer SSO for humans, least-privilege short-lived credentials for automation and an audited break-glass process. Do not use shared admin tokens for routine tasks.

## 4. Lab A — Verify prerequisites (read-only)

\`\`\`bash
kubectl config current-context
kubectl get pods,svc -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl get appprojects.argoproj.io -n argocd
argocd version --client
\`\`\`

If the Argo CD CLI is not installed, use the official versioned release for your workstation architecture, verify its publisher/integrity using your organization's approved process and confirm compatibility with the server. Avoid unverified package scripts.

**Windows PowerShell:**

\`\`\`powershell
kubectl config current-context
kubectl get pods,svc -n argocd
argocd version --client
\`\`\`

Record the CLI version and the server version once authenticated; mismatches may affect supported commands.

## 5. Lab B — Private UI access

If the Argo CD server is not exposed through an approved private gateway, use local port forwarding:

\`\`\`bash
kubectl port-forward -n argocd svc/argocd-server 8080:443
\`\`\`

Visit \`https://localhost:8080\` from the same workstation. Authenticate using approved SSO or a lab credential. A local certificate warning is not a reason to disable TLS verification for production access.

In the UI, inspect:

- Applications and their Sync/Health status.
- Application resource tree, history and diff.
- Projects and allowed source/destination policy.
- Repositories and connection status, if your role permits.
- User account and effective privileges.
- Operation details and error messages.

Avoid clicking **Sync**, **Prune**, **Delete**, **Terminate**, or changing repository credentials in a read-only exercise.

## 6. Lab C — CLI login and read-only inspection

For a private, trusted Argo CD endpoint:

\`\`\`bash
argocd login argocd.example.com --sso
argocd account get-user-info
argocd version
argocd app list
argocd proj list
argocd repo list
\`\`\`

The CLI's SSO browser flow requires an appropriate local callback/browser environment. If your organization uses a gateway that does not support native gRPC, \`--grpc-web\` may be necessary:

\`\`\`bash
argocd login argocd.example.com --sso --grpc-web
\`\`\`

When connecting through localhost port-forward, the endpoint, TLS certificate and login method depend on the deployment. Use your platform team's documented procedure; do not make \`--insecure\` a default. If your lab explicitly permits a temporary TLS bypass, record the exception and remove it afterward.

**Do not place passwords directly on the command line.** They may be exposed through process inspection or shell history.

## 7. Read-only Application operations

\`\`\`bash
argocd app get demo-app-dev
argocd app history demo-app-dev
argocd app manifests demo-app-dev
argocd app resources demo-app-dev
argocd app diff demo-app-dev
\`\`\`

Commands depend on your Argo CD version and privileges. The \`diff\` command compares desired and live state and is generally nonmutating, but may invoke manifest generation and should be used with awareness of custom plugins.

Compare:

- Git source URL and target revision.
- Chart path and Helm values files.
- Destination namespace.
- AppProject restrictions.
- Sync and health separately.
- Verified image digest in the rendered Deployment.
- Managed resource ownership and deletion candidates.

**Do not export full manifests into public CI logs**; rendered configuration may include sensitive information if upstream hygiene failed.

## 8. Lab D — Kubernetes-native inspection without Argo CD login

When Argo CD API authentication is unavailable but Kubernetes read access is authorized:

\`\`\`bash
kubectl get applications.argoproj.io -n argocd
kubectl get application demo-app-dev -n argocd \
  -o jsonpath='{.status.sync.status}{" "}{.status.health.status}{"\\n"}'
kubectl describe application demo-app-dev -n argocd
kubectl get deployment,pods,svc -n demo-dev
kubectl get endpointslices -n demo-dev
\`\`\`

PowerShell can use the same \`jsonpath\` expression in single quotes. Do not assume Kubernetes RBAC grants permission to modify Argo CD Applications.

## 9. Authentication and RBAC boundaries

Argo CD access is layered:

1. **Identity provider** authenticates a human or service principal.
2. **Argo CD RBAC** authorizes actions on Applications, Projects and repositories.
3. **AppProject** restricts allowed sources, destinations and resource kinds.
4. **Kubernetes RBAC** governs what the controller ServiceAccount can change.
5. **GitLab permissions** govern who can approve desired-state modifications.

An operator may be allowed to view an Application but not sync it. A GitLab maintainer may be able to merge configuration but not log in as Argo CD admin. These are intentional separation-of-duties controls.

## 10. Inspect RBAC configuration safely

With authorized read access:

\`\`\`bash
kubectl get configmap argocd-rbac-cm -n argocd -o yaml
kubectl get configmap argocd-cm -n argocd -o yaml
\`\`\`

These ConfigMaps may expose security-sensitive configuration details; redact before sharing. Verify \`policy.default\`, role mappings, SSO group claims and resource-scoped permissions. Avoid a broad default read role if confidential repository/application metadata must be restricted.

Where supported by your installed version, use the CLI RBAC validation commands in a controlled environment to confirm both allowed and denied actions. An RBAC policy that permits an action is not proof that the underlying Kubernetes service account can execute it.

## 11. GitLab repository connection architecture

\`\`\`text
argocd-repo-server
       |
   DNS / proxy / firewall / TLS
       |
GitLab repository
       |
HTTPS deploy token / SSH deploy key
       |
Git source + chart + values
\`\`\`

A repository may be publicly readable or private. For private GitLab projects, prefer a **read-only** deploy token or read-only deploy key, scoped to the specific repository or approved group.

**Security requirements:**

- Validate GitLab TLS certificates or SSH host keys.
- Use least-privilege repository credentials.
- Store tokens/keys only in approved Kubernetes Secret or external secret management.
- Rotate and audit credentials.
- Avoid embedding credentials in repository URLs.
- Restrict who can edit Argo CD repository configuration.

## 12. Lab E — Inspect repository connectivity (read-only)

\`\`\`bash
argocd repo list
argocd app get demo-app-dev
kubectl get pods -n argocd
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
\`\`\`

A healthy repo-server Pod does not prove every repository is reachable. A repository's connection status, credentials, URL and chart path must all be validated. Logs may contain sensitive metadata; sanitize before sharing.

For a GitLab HTTPS repository, inspect the **exact URL**:

\`\`\`text
https://gitlab.example.com/platform/demo-gitops.git
\`\`\`

A mismatch in scheme, host, path or redirect behavior can break repository credential matching.

## 13. Lab F — Add a public read-only repository (optional)

Only on an authorized disposable Argo CD instance:

\`\`\`bash
argocd repo add https://gitlab.example.com/platform/demo-gitops.git \
  --name demo-gitops
argocd repo list
\`\`\`

This command assumes the repository is publicly readable and the operator has repository-management permission. For private repositories, **do not** use personal credentials or inline \`--password\` flags as the default workflow. Instead, use a reviewed Kubernetes Secret or approved external secret controller.

## 14. Declarative private GitLab repository configuration

Argo CD commonly discovers repository credentials from labeled Kubernetes Secrets in its control-plane namespace.

Example **structure only**; values are intentionally omitted:

\`\`\`yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-demo-gitops
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://gitlab.example.com/platform/demo-gitops.git
  username: <INJECTED_BY_SECRET_MANAGER>
  password: <INJECTED_BY_SECRET_MANAGER>
\`\`\`

**Do not commit this manifest with real or placeholder credentials and assume it is safe.** Treat it as a schema example. In production, have an approved external secret controller create the Secret from an enterprise secret store, or use a controlled bootstrap procedure. Validate whether the Argo CD release supports your selected secret-discovery model.

Repository credential templates can reduce duplication for trusted URL prefixes, but scope them carefully: an overly broad prefix can cause credentials to be sent to unintended repositories.

## 15. HTTPS certificates and SSH host keys

When connecting to internal GitLab:

- Confirm DNS resolution and proxy configuration from the repo-server network.
- Trust the correct enterprise CA certificate for HTTPS.
- Verify certificate hostname, expiration and chain.
- For SSH, pin trusted GitLab host keys using approved host-key verification.
- Rotate trust material through controlled change management.
- Do not use \`--insecure-skip-server-verification\` as a routine workaround.
- Do not disable SSH host-key verification.

Certificate failures should trigger trust-chain investigation, not security bypass.

## 16. GitLab path, branch and Helm values validation

Example Application source:

\`\`\`yaml
source:
  repoURL: https://gitlab.example.com/platform/demo-gitops.git
  targetRevision: main
  path: charts/demo-app
  helm:
    valueFiles:
      - env/dev-values.yaml
\`\`\`

Confirm the GitLab repository actually contains:

\`\`\`text
charts/demo-app/Chart.yaml
charts/demo-app/values.yaml
charts/demo-app/env/dev-values.yaml
charts/demo-app/templates/
\`\`\`

For four environments, use separate Applications referencing:

| Application | Namespace | Values file |
| --- | --- | --- |
| \`demo-app-dev\` | \`demo-dev\` | \`env/dev-values.yaml\` |
| \`demo-app-test\` | \`demo-test\` | \`env/test-values.yaml\` |
| \`demo-app-staging\` | \`demo-staging\` | \`env/staging-values.yaml\` |
| \`demo-app-prod\` | \`demo-prod\` | \`env/prod-values.yaml\` |

The source path is relative to the Git repository root; Helm \`valueFiles\` paths are relative to the chart source. Multi-source external values are addressed in later chapters.

## 17. Validate the chart offline

In a trusted checkout:

\`\`\`bash
helm dependency build charts/demo-app
helm lint charts/demo-app
helm template demo-app charts/demo-app \
  --namespace demo-dev \
  -f charts/demo-app/env/dev-values.yaml > rendered-dev.yaml
\`\`\`

If this fails, fix the chart or values before investigating Kubernetes. If offline rendering passes but Argo CD fails, focus on repo-server environment, credentials, network access, dependency registry access, plugin/tool versions or Application configuration.

## 18. Safe diagnostic workflow

Use this sequence:

\`\`\`text
CLI/UI unavailable?
   -> DNS/TLS/SSO/API-server
   -> RBAC permission checks

CLI/UI works, repo unavailable?
   -> URL -> GitLab auth -> DNS/proxy/TLS
   -> repo-server logs

Repo reachable, manifest generation fails?
   -> revision/path -> Helm values/dependencies
   -> chart lint/template -> repo-server resources

Manifest generation works, sync fails?
   -> AppProject -> Kubernetes RBAC/admission
   -> namespace/resource ownership

Sync succeeds, app unhealthy?
   -> Pods -> events -> Service endpoints
   -> registry image digest -> probes -> SLOs
\`\`\`

Do not confuse **repository connectivity**, **manifest generation**, **sync**, **resource health** and **application SLOs**.

## 19. Failure injection lab

Use a disposable Application and approved repository:

| Test | Fault | Expected signal | Recovery |
| --- | --- | --- | --- |
| 1 | Invalid GitLab URL | Repository connection failure | Restore correct URL |
| 2 | Expired read-only token | Authentication denied | Rotate token |
| 3 | Invalid CA trust | TLS verification failure | Install approved CA |
| 4 | Wrong Helm path | Manifest generation failure | Correct source path |
| 5 | Missing values file | Helm rendering error | Restore chart-local file |
| 6 | Unauthorized Application read | RBAC denied | Validate group mapping |
| 7 | Unauthorized repository management | RBAC denied | Keep least privilege |
| 8 | Wrong image digest | Runtime image pull failure | Revert to verified digest |

Do not deliberately disable TLS, delete shared credentials or alter production Applications to create failures. Capture sanitized evidence of both the failure and the successful recovery.

## 20. Operational security checklist

- [ ] Human access uses SSO/OIDC and approved MFA.
- [ ] Argo CD API endpoint uses TLS and private access controls.
- [ ] CLI version and server version compatibility reviewed.
- [ ] No personal/shared admin tokens used for automation.
- [ ] RBAC allows only required Application/Project/repository operations.
- [ ] GitLab deploy tokens/keys are read-only and narrowly scoped.
- [ ] Repository credentials are delivered through approved secrets management.
- [ ] GitLab TLS/SSH trust is validated.
- [ ] GitOps repository changes use protected branches and approvals.
- [ ] Audit logs capture repository and permission changes.
- [ ] Emergency access and token rotation are documented.
- [ ] Production sync/prune permissions are restricted.

## 21. SRE incident runbook — GitLab repository unavailable

**Scenario:** Argo CD Applications report comparison errors after a GitLab token rotation.

1. Confirm the affected Applications and their source URLs.
2. Verify the repo-server is healthy; distinguish Git auth from network/TLS failure.
3. Check credential expiry, scope and repository URL-prefix matching.
4. Validate the replacement credential through an approved secret workflow.
5. Rotate the scoped credential without printing it in logs.
6. Verify repository connection status and manifest generation.
7. Confirm no unapproved sync or prune occurred during the incident.
8. Verify Applications recover to expected sync/health states.
9. Record impact, detection time, recovery duration and preventive rotation checks.

**Recovery principle:** Existing Kubernetes workloads may continue serving during GitLab or repo-server outages. Avoid unnecessary changes to healthy application resources.

## 22. Observability and SLOs

Monitor:

| Metric or signal | Why it matters |
| --- | --- |
| Argo CD API availability | Operators can inspect/manage Apps |
| Login/SSO errors | Identity outages or misconfiguration |
| Repository fetch failures | GitLab, token, TLS or network issues |
| Manifest generation duration/errors | Repo-server performance |
| Application comparison errors | Desired-state reconciliation failures |
| Sync failures and health degradation | Deployment issues |
| Unauthorized access attempts | Security and audit |
| Token/certificate expiration | Preventable outages |
| Application error rate and latency | User-facing impact |

Choose thresholds from real operational baselines; do not equate a successful login with deployment health.

## 23. EKS, AKS and GKE considerations

| Topic | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Workload identity | EKS Pod Identity/IRSA | Entra Workload ID | Workload Identity Federation |
| Private egress | VPC DNS/proxy/endpoints | VNet DNS/proxy | VPC DNS/proxy |
| Secret source | AWS Secrets Manager | Azure Key Vault | Secret Manager |
| Audit | CloudTrail/Kubernetes | Azure activity/Kubernetes | Cloud Audit Logs/Kubernetes |
| GitLab access | Private/public approved route | Private/public approved route | Private/public approved route |

Provider identity does not replace Argo CD RBAC or GitLab repository authorization.

## 24. Acceptance checklist

- [ ] CLI and UI access tested through approved private endpoint.
- [ ] SSO and effective role verified.
- [ ] Read-only and denied RBAC cases documented.
- [ ] Application, Project and repository status inspected.
- [ ] GitLab URL, TLS trust and authentication validated.
- [ ] Credentials are not embedded in Git or logs.
- [ ] Helm chart and values paths verified offline.
- [ ] Manifest-generation troubleshooting demonstrated.
- [ ] Four-environment source/namespace mapping documented.
- [ ] Failure injection performed only in approved disposable scope.
- [ ] Incident runbook and monitoring responsibilities recorded.

## 25. Evidence worksheet

\`\`\`text
CHAPTER 038 — ARGO CD CLI/UI/REPOSITORIES
Date:
Operator/reviewer:
Cluster/context:
Argo CD CLI/server versions:
UI/API endpoint:
TLS validation:
SSO identity/group mapping:
Effective RBAC:
Denied-action test:
AppProject:
Application:
GitLab repository URL:
Repository auth method (no credential values):
Token/certificate expiry owner:
Repo-server health:
Chart path/values:
Manifest-generation result:
Sync status:
Health status:
Failure tests and recovery:
SLO baseline:
Open risks:
Final decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 26. Knowledge checks

1. What is the difference between Argo CD API authentication and Kubernetes RBAC?
2. Why is \`--grpc-web\` sometimes required?
3. Why should repository credentials be read-only and URL-scoped?
4. How do you validate internal GitLab HTTPS certificates?
5. What is the security risk of disabling SSH host-key verification?
6. Why does a healthy repo-server Pod not guarantee repository connectivity?
7. How do Helm values paths differ from Application source paths?
8. Why can a repository outage leave existing application Pods running?
9. What separates manifest-generation errors from Kubernetes sync failures?
10. Why should GitOps promotion not require a shared Argo CD admin token?

## 27. Completion

**Pass:** You can securely use Argo CD CLI/UI, inspect Applications and Projects, validate trusted GitLab repository connectivity, diagnose authentication/TLS/Helm rendering failures, and produce an SRE incident and evidence record.

**Next: Chapter 039 — Argo CD Application Creation, Synchronization, Health and Drift Detection.**
