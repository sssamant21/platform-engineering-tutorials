# Chapter 002 — OpenShift CLI, Web Console, Kubeconfig and Access

**Audience:** OCP administrators, SREs and DBREs · **Duration:** 60 minutes · **Version baseline:** OCP 4.22 · **Status:** Draft, not runtime-tested

## Objectives and prerequisites

Install a version-matched `oc` client, authenticate safely, identify the exact cluster and namespace, inspect effective RBAC permissions, and navigate the console without changing cluster resources.

Prerequisites: approved account (prefer identity-provider SSO), API/console endpoints provided by your platform team, network access and a workstation with a secure user profile. The examples are **read-only after login**. The login itself writes local authentication state to kubeconfig. Do not use a shared workstation or a production cluster without authorization.

For generic Kubernetes kubeconfig concepts, see [Kubernetes Chapter 006](../../kubernetes/chapters/006-kubectl-installation-and-kubeconfig.md).

## 1. Obtain and install the OpenShift CLI

Use the **Command line tools** download link in your organization's OpenShift web console, or the approved Red Hat client distribution. Select the `oc` binary matching your cluster's OCP minor version and workstation OS/architecture; do not blindly download a generic or latest binary.

**Windows 11 PowerShell (illustrative; extracted binary must be approved):**

```powershell
# Extract the official Windows archive into a controlled tools directory.
# Add that directory to PATH through approved workstation management.
Get-Command oc
oc version --client
```

**Linux:**

```bash
command -v oc
oc version --client
```

A missing command means the client is not installed or is absent from PATH. An old client can lack newer OCP features. Avoid installation from untrusted mirrors. The CLI archive can also include `kubectl`, but `oc` supports OpenShift-specific resources and authentication.

## 2. Authenticate without exposing secrets

Prefer the organization's interactive SSO login. Use an API endpoint supplied by the platform team, not a guessed hostname:

```bash
oc login https://api.example.com:6443
```

If the CLI provides a browser-assisted authentication flow, follow the approved organizational procedure. **Do not put `--token` or `-p` values into shell history, screenshots, tickets, or Git.** Do not bypass TLS verification with `--insecure-skip-tls-verify` to work around certificate failures; escalate trust-chain issues.

Login may change the active context and write credentials to the local kubeconfig. Never run `oc config view --raw` in logs or share a kubeconfig; it can contain credentials.

## 3. Identify the active cluster before inspection

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc config get-contexts
oc project -q
oc version
```

`oc version` may fail to query the server when network access or authentication is unavailable; `oc version --client` checks the local binary only.

**Safety gate:** Confirm the API URL, active identity, project and environment classification against an independently maintained inventory. Never assume the current context is staging merely because its name contains 'staging'.

To inspect a different existing context, first confirm its mapping in the inventory; switching context is a local configuration change:

```bash
oc config use-context <approved-context-name>
oc whoami --show-server
```

Switching the default project with `oc project <approved-project>` also changes local context state. For an unambiguous read-only query, prefer `-n <namespace>` rather than relying on the default project.

## 4. Check RBAC without escalating privileges

```bash
oc auth can-i get pods -n <approved-project>
oc auth can-i list deployments -n <approved-project>
oc auth can-i get routes.route.openshift.io -n <approved-project>
oc auth can-i get nodes
oc auth can-i get clusteroperators.config.openshift.io
oc get pods -n <approved-project>
```

Expected `oc auth can-i` output is typically `yes` or `no`. A `no` is not an invitation to assume admin rights: request the minimum role needed from the RBAC owner. Cluster-scoped resources such as nodes and Cluster Operators commonly require broader permissions than namespace workloads. The effective permissions can depend on identity, group memberships and namespace.

Avoid `oc auth can-i --list` for blanket exports to external locations: permission inventories may reveal sensitive operational metadata.

## 5. Inspect the web console

After authenticating to the **approved** console URL, inspect the current project, Workloads → Pods, Networking → Routes, and (if authorized) Administration → Cluster Settings / Cluster Operators. Navigation labels can vary by OCP release and permissions; OCP 4.19+ uses a unified console perspective rather than the older default Administrator/Developer split.

If already logged in, this read-only command can reveal the console URL:

```bash
oc whoami --show-console
```

The console displays only what your account is allowed to view. Never use an emergency `kubeadmin` identity for ordinary exercises.

## 6. Common failures and triage

| Symptom | Likely causes | Safe next action |
| --- | --- | --- |
| `oc: command not found` / not recognized | Binary absent or PATH incorrect | Verify trusted installation and shell PATH |
| `Unauthorized` | Expired login or incorrect identity | Reauthenticate via approved SSO |
| `Forbidden` | RBAC does not allow resource/action | Run `oc auth can-i`, request least privilege |
| TLS x509 error | Untrusted CA, wrong endpoint, interception | Verify URL and CA chain with platform team; never disable verification |
| DNS/timeout | VPN, proxy, firewall, DNS or API outage | Validate network path and incident status |
| Unexpected cluster | Wrong kubeconfig/context | Stop; verify server, identity and inventory before further commands |

## 7. Lab and acceptance

Complete [Lab 002](../labs/002-oc-cli-context-and-rbac.md). Demonstrate an installed client, confirmed context and server, least-privilege RBAC checks and console navigation. Capture sanitized evidence only. No real cluster was accessed while drafting this chapter.

**Production change/rollback:** The lab makes no cluster resource changes. If login or context selection changed local kubeconfig, restore the previously documented context using `oc config use-context <prior-context>`. Do not delete or overwrite kubeconfig files as a generic rollback. For authentication compromise, follow organizational credential revocation procedures.

## Official references

- [OCP 4.22 CLI tools](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/cli_tools/openshift-cli-oc)
- [OCP 4.22 web console](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/web_console/index)
