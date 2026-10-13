# Chapter 006 — kubectl Installation and kubeconfig

**Track:** Kubernetes Administration · **Part:** 02 — Cluster Installation and Setup · **Level:** Beginner–Intermediate · **Status:** Draft — lab execution pending

## 1. Learning objectives

After this chapter, you should be able to:

1. Install and verify `kubectl` on Windows PowerShell and understand supported client/server version skew.
2. Explain kubeconfig clusters, users, contexts, namespaces, and authentication mechanisms.
3. Safely manage multiple clusters and switch contexts without modifying the wrong environment.
4. Inspect and merge kubeconfig files while preserving backups and minimizing credential exposure.
5. Use `kubectl` with a disposable kind cluster, explicitly target a context, and troubleshoot authentication, TLS, and network errors.
6. Understand the high-level EKS, AKS, and GKE kubeconfig workflows and operational security controls.

## 2. How kubectl communicates with Kubernetes

```text
Operator / PowerShell
       |
       v
kubectl
       |
       +--> kubeconfig: cluster API endpoint + CA trust
       |                 user authentication configuration
       |                 context = cluster + user + optional namespace
       v
Kubernetes API server
       |
       +--> Authentication --> Authorization (RBAC) --> Admission
       |
       v
Kubernetes API objects and status
```

`kubectl` is a Kubernetes API client. It does not talk directly to kubelet or etcd during normal administration. The client sends requests to the API server using the active context or an explicitly specified context.

### Version compatibility

Use a `kubectl` version within **one minor version** of the API server version, per Kubernetes' supported version-skew policy. For example, a v1.34 client is intended to work with v1.33–v1.35 API servers, subject to the policy in effect for that release. Prefer a client matching the server minor version when practical. Do not infer a server version from the local Docker or kind version.

## 3. Install kubectl on Windows

### Option A — Windows Package Manager (recommended when approved)

```powershell
winget search --id Kubernetes.kubectl --exact
winget install --id Kubernetes.kubectl --exact
```

Package availability, version, and install policy may vary. Restart PowerShell if the executable is not immediately on `PATH`.

### Option B — Chocolatey (if already approved and installed)

```powershell
choco install kubernetes-cli -y
```

Use your organization's managed package source where required. Do not run arbitrary internet scripts as Administrator to install tools.

### Verify the binary

```powershell
Get-Command kubectl
kubectl version --client
kubectl version --client -o yaml
kubectl help
```

**Expected:** PowerShell resolves `kubectl` and prints a client version. No cluster connection is needed for `--client`.

### Linux/macOS note

Use the official Kubernetes package-manager or binary installation instructions for the relevant OS/architecture. Verify downloaded binaries and checksums against the official release source. This tutorial's executable lab uses Windows PowerShell.

## 4. kubeconfig structure

A kubeconfig file commonly looks like this (illustrative placeholders only):

```yaml
apiVersion: v1
kind: Config
clusters:
  - name: demo-cluster
    cluster:
      server: https://127.0.0.1:6443
      certificate-authority-data: BASE64_CA_DATA
users:
  - name: demo-user
    user:
      exec:
        apiVersion: client.authentication.k8s.io/v1
        command: some-approved-login-helper
        interactiveMode: IfAvailable
contexts:
  - name: demo-context
    context:
      cluster: demo-cluster
      user: demo-user
      namespace: default
current-context: demo-context
```

The example is not runnable. Actual `exec` authentication helpers have provider-specific arguments, installation requirements, and output formats.

| Entry | Meaning | Security consideration |
|---|---|---|
| `clusters[].cluster.server` | Kubernetes API endpoint | Verify destination and TLS |
| `certificate-authority-data` | Trusted CA bundle | Do not bypass certificate verification |
| `users[].user` | Client credential, token, or exec plugin | May contain sensitive credential material |
| `contexts[].context` | Selected cluster + user + namespace | Context mistakes can affect production |
| `current-context` | Default context for requests | Never assume it points to a lab |
| `namespace` | Default namespace in that context | `-n` overrides it per command |

**Important:** Kubeconfig is sensitive. It may embed client keys/tokens or invoke an executable through an `exec` authentication plugin. Treat kubeconfig files from untrusted sources as potentially dangerous, and do not share them publicly.

## 5. kubeconfig precedence and context commands

`kubectl` generally uses `--kubeconfig` when explicitly supplied; otherwise it uses the `KUBECONFIG` environment variable if set; otherwise the default `$HOME/.kube/config`. On Windows, `KUBECONFIG` entries are separated with semicolons.

```powershell
$env:KUBECONFIG
kubectl config get-contexts
kubectl config current-context
kubectl config view --minify
kubectl config view --raw
```

**Do not paste the output of `kubectl config view --raw` into tickets or chat.** It can expose private keys, tokens, and other credentials. Use redacted views for sharing.

Useful commands:

```powershell
kubectl config get-clusters
kubectl config get-users
kubectl config use-context kind-k8s-admin-ch006
kubectl config set-context --current --namespace=ch006
kubectl --context kind-k8s-admin-ch006 -n ch006 get pods
```

The `--context` flag is safer for one-off operations because it does not mutate the globally active context.

## 6. Lab prerequisites and safety boundaries

Use Windows PowerShell, Docker Desktop, `kind`, and `kubectl`. A disposable local cluster is required for this chapter's hands-on exercise.

```powershell
docker version
kind version
kubectl version --client
```

If any tool is missing, install it from its official documentation or an approved package source. Ensure Docker Desktop is running.

**Do not use a production kubeconfig for this lab.** Back up any existing kubeconfig before changing global context or merging files.

## 7. Hands-on Lab A — Create and inspect a local kubeconfig

### Step A1 — Create a disposable cluster

```powershell
kind create cluster --name k8s-admin-ch006 --wait 120s
kind get clusters
kubectl config get-contexts
kubectl config current-context
kubectl get nodes -o wide
```

**Expected:** context `kind-k8s-admin-ch006`, a Ready kind control-plane node, and a functioning API connection.

**Safety gate:** Continue only if the current context is `kind-k8s-admin-ch006`.

### Step A2 — Inspect the active context

```powershell
kubectl config view --minify
kubectl config view --minify -o jsonpath='{.current-context}'
kubectl cluster-info
kubectl version
```

**Expected:** context points to the disposable kind cluster, the API server is reachable, and client/server version information appears. Credential material is usually redacted in normal `config view`, but still review output before sharing.

### Step A3 — Export an isolated lab kubeconfig

```powershell
New-Item -ItemType Directory -Force .\k8s-ch006 | Out-Null
$labConfig = (Join-Path (Resolve-Path .\k8s-ch006) 'kind-ch006.kubeconfig')
kind export kubeconfig --name k8s-admin-ch006 --kubeconfig $labConfig
kubectl --kubeconfig $labConfig config current-context
kubectl --kubeconfig $labConfig get nodes
```

**Expected:** the exported file works with the local cluster. **Treat the exported file as a credential**; do not commit it to Git, attach it to tickets, or leave it on a shared machine.

### Step A4 — Explicit context selection without switching defaults

```powershell
kubectl --context kind-k8s-admin-ch006 get namespaces
kubectl --kubeconfig $labConfig --context kind-k8s-admin-ch006 get nodes
```

**Expected:** both commands target the lab cluster. Explicit targeting reduces the risk of accidentally modifying an unrelated context.

## 8. Hands-on Lab B — Namespace and context operations

### Step B1 — Create a training namespace

```powershell
kubectl --context kind-k8s-admin-ch006 create namespace ch006
kubectl --context kind-k8s-admin-ch006 -n ch006 get pods
```

**Expected:** namespace exists; initially there may be no Pods.

### Step B2 — Set namespace on the isolated kubeconfig only

```powershell
kubectl --kubeconfig $labConfig config set-context kind-k8s-admin-ch006 --namespace=ch006
kubectl --kubeconfig $labConfig config view --minify -o jsonpath='{.contexts[0].context.namespace}'
kubectl --kubeconfig $labConfig get pods
```

**Expected:** namespace `ch006` appears; the isolated kubeconfig defaults to that namespace. This step avoids changing the namespace on your normal/global kubeconfig.

### Step B3 — Demonstrate explicit overrides

```powershell
kubectl --kubeconfig $labConfig -n kube-system get pods
kubectl --kubeconfig $labConfig -n ch006 get pods
```

**Expected:** `-n` overrides the context's default namespace for the specific command.

## 9. Hands-on Lab C — Authentication, authorization, and safe troubleshooting

### Step C1 — Inspect identity and permissions

```powershell
kubectl --kubeconfig $labConfig auth whoami
kubectl --kubeconfig $labConfig auth can-i get pods -n ch006
kubectl --kubeconfig $labConfig auth can-i create deployments -n ch006
```

**Expected:** identity details and yes/no permission results. `auth whoami` requires server support for SelfSubjectReview; if unsupported, use `auth can-i` and note the limitation.

### Step C2 — Inspect API health

```powershell
kubectl --kubeconfig $labConfig cluster-info
kubectl --kubeconfig $labConfig get --raw /readyz
kubectl --kubeconfig $labConfig get nodes
```

**Expected:** reachable API endpoint, `ok` readiness response, and Ready node.

### Step C3 — Safe failure simulation with a nonexistent context

```powershell
kubectl --kubeconfig $labConfig --context does-not-exist get pods
```

**Expected:** an error indicating the context does not exist. This is a **client configuration failure**, not a Kubernetes control-plane outage.

Recover by explicitly selecting the valid context:

```powershell
kubectl --kubeconfig $labConfig --context kind-k8s-admin-ch006 get pods -n ch006
```

**Expected:** command succeeds.

### Step C4 — Inspect a nonexistent namespace

```powershell
kubectl --kubeconfig $labConfig -n missing-ch006 get pods
```

**Expected:** a `NotFound` error for the namespace, or a corresponding API response. Distinguish an API resource error from a credential or network failure.

## 10. kubeconfig backup, merge, and credential hygiene

### Safe backup before changing an existing kubeconfig

```powershell
$defaultConfig = Join-Path $HOME '.kube\config'
if (Test-Path $defaultConfig) {
    Copy-Item $defaultConfig "$defaultConfig.backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
}
```

Store backups in a secure location and restrict access. Avoid storing backups in repositories or shared folders.

### Merge concept

On Windows, multiple kubeconfig files can be selected using semicolon-separated `KUBECONFIG` values. Merge resolution depends on the order of files, and duplicate cluster/user/context names can cause surprising results. Do not merge untrusted configs or overwrite an existing file without inspecting conflicts.

**Illustrative example (not needed for the lab):**

```powershell
# Review and adjust paths before use:
$env:KUBECONFIG = "$HOME\.kube\config;$labConfig"
kubectl config get-contexts
```

This sets `KUBECONFIG` only for the current PowerShell process and its children. Restore your prior environment value afterward if you change it:

```powershell
Remove-Item Env:KUBECONFIG -ErrorAction SilentlyContinue
```

**Caution:** Removing `KUBECONFIG` is appropriate only if it was originally unset. If it had an existing value, restore that exact original value instead. Prefer using `--kubeconfig $labConfig` throughout this lab to avoid altering environment state.

### Credential safeguards

- Restrict kubeconfig access to authorized operators.
- Avoid static long-lived admin credentials where federated or short-lived identity is supported.
- Validate executable auth plugins before running a kubeconfig from another person.
- Never use `insecure-skip-tls-verify: true` as a routine fix for certificate errors.
- Keep distinct contexts and clearly recognizable names for prod/staging/dev.
- Prefer explicit `--context`, `--namespace`, and read-only preflight commands before changes.

## 11. EKS, AKS, and GKE kubeconfig workflows

These commands are **examples for authorized environments** and are not required for the local lab.

### Amazon EKS

```powershell
aws sts get-caller-identity --profile my-approved-profile
aws eks update-kubeconfig --region us-east-1 --name my-cluster --profile my-approved-profile --alias my-eks-context
kubectl --context my-eks-context get nodes
```

AWS CLI generates or updates kubeconfig with an exec authentication flow. Access also depends on IAM and cluster access configuration. `update-kubeconfig` can modify the default kubeconfig and current context, so review its target and use a dedicated `--kubeconfig` path when appropriate.

### Azure AKS

```powershell
az account show
az aks get-credentials --resource-group my-resource-group --name my-aks-cluster
kubectl config get-contexts
```

Microsoft Entra-integrated clusters may require `kubelogin` and a supported login mode. Do not assume local administrator credentials are enabled; many organizations disable them. `get-credentials` modifies kubeconfig, so verify the active context afterward.

### Google GKE

```powershell
gcloud auth list
gcloud container clusters get-credentials my-gke-cluster --region us-central1 --project my-project
kubectl config get-contexts
```

GKE authentication commonly uses the `gke-gcloud-auth-plugin`. The cluster may be zonal rather than regional; choose the correct `--zone` or `--region`. The command modifies kubeconfig and may switch the active context.

**Shared responsibility:** Obtaining kubeconfig does not automatically grant RBAC permissions. Cloud IAM, cluster authorization, networking, and private API endpoints may all affect access.

## 12. Troubleshooting runbook

| Symptom | Evidence | Investigation |
|---|---|---|
| `kubectl` not recognized | `Get-Command kubectl` | Install or fix PATH |
| `current-context is not set` | `kubectl config get-contexts` | Select an existing context |
| `context does not exist` | `kubectl config view` | Correct context name or config file |
| Connection refused / timeout | API server address, VPN, DNS, routing | Check endpoint and network reachability |
| x509 certificate error | TLS chain, endpoint name, CA | Fix trust or endpoint; do not disable verification |
| Unauthorized (401) | Auth plugin, token, session expiration | Reauthenticate or repair credential helper |
| Forbidden (403) | `kubectl auth can-i` | Check RBAC and cloud authorization |
| Exec plugin missing | kubeconfig `exec.command` | Install approved AWS/Azure/GKE auth helper |
| Wrong namespace | `config view --minify`, `-n` | Specify intended namespace |
| Wrong cluster | `current-context`, `cluster-info` | Stop and explicitly select the correct context |

### Read-only incident triage

```powershell
kubectl config current-context
kubectl config view --minify
kubectl cluster-info
kubectl auth can-i get pods --all-namespaces
kubectl get nodes
```

Do not post raw kubeconfig credentials or tokens in incident channels. Capture error timestamps and redact server addresses where policy requires it.

## 13. Production SRE operating procedure

1. Verify identity, cloud account/subscription/project, cluster, namespace, and current context.
2. Confirm the target environment is authorized for the planned change.
3. Prefer read-only checks first and capture current state.
4. Use least-privilege short-lived authentication and centrally governed RBAC.
5. Use explicit contexts for potentially disruptive operations.
6. Review rollout, rollback, maintenance windows, and incident escalation before applying changes.
7. Record audit-relevant commands and outcomes without logging credentials.
8. Rotate or revoke credentials if a kubeconfig is exposed.

**Anti-pattern:** Copying an admin kubeconfig between machines to fix access errors. Instead, repair the intended authentication and authorization workflow.

## 14. Cleanup

Verify the target context before deletion:

```powershell
kubectl config current-context
```

Proceed **only** if the output is `kind-k8s-admin-ch006`:

```powershell
kubectl --context kind-k8s-admin-ch006 delete namespace ch006
kind delete cluster --name k8s-admin-ch006
kind get clusters
```

Remove the exported kubeconfig file **only after** confirming you no longer need it:

```powershell
Remove-Item $labConfig
```

**Warning:** `kind delete cluster` permanently removes the local cluster and its contents. If you altered `KUBECONFIG`, restore its prior value.

## 15. Acceptance checklist

- [ ] Installed/verified `kubectl` and client version.
- [ ] Explained clusters, users, contexts, and namespaces.
- [ ] Created disposable kind cluster and verified context.
- [ ] Exported a dedicated lab kubeconfig.
- [ ] Used `--kubeconfig`, `--context`, and `-n` correctly.
- [ ] Verified identity/authorization where supported.
- [ ] Diagnosed a nonexistent context without modifying the cluster.
- [ ] Distinguished authorization, TLS, connectivity, and namespace errors.
- [ ] Understood credential-handling and backup safeguards.
- [ ] Cleaned up the lab cluster and sensitive temporary kubeconfig.

## 16. Knowledge check

1. What is the difference between a cluster, user, and context in kubeconfig?
2. How do `--kubeconfig`, `KUBECONFIG`, and the default path interact?
3. Why is an exec authentication plugin a security-sensitive part of kubeconfig?
4. How would you distinguish a 401 from a 403 API response?
5. Why should operators prefer explicit context selection for production changes?
6. What changes when using `kubectl config set-context --current --namespace=...`?
7. Why is `kubectl config view --raw` dangerous to paste into a ticket?
8. Which tools typically provide EKS, AKS, and GKE kubeconfig authentication?

## 17. Chapter status and next chapter

**Draft written; hands-on execution has not been independently verified.** Mark **Lab Validated** only after completing the acceptance checklist and **Complete** after review.

**Next:** Chapter 007 — Kubernetes Local Lab with kind and Minikube.
