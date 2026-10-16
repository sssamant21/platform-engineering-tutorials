# Chapter 049 — Jenkins on Azure AKS: Workload Identity, Node Pools and Operations

**Part 10 — Jenkins on Kubernetes, EKS and AKS**  
**Audience:** Jenkins SRE, Azure platform engineers, Kubernetes administrators, security and FinOps teams  
**Prerequisites:** Chapters 046–048; disposable AKS cluster; Azure CLI, kubectl, Helm; approved Entra ID and Azure RBAC access.

## Learning objectives

Operate Jenkins Kubernetes agents on Azure AKS with Microsoft Entra Workload ID, scoped Azure RBAC, secure ACR access, dedicated node pools, cluster autoscaler, observability, recovery and cost controls. Keep Kubernetes API permissions distinct from Azure resource permissions.

## 1. Architecture

```text
Git → Jenkins controller (AKS namespace, durable PVC)
           │
           ├─ Kubernetes plugin → AKS API
           │                       ↓
           │                 ephemeral agent Pods
           │                    ├─ untrusted CI (no Azure role)
           │                    ├─ artifact CI (scoped federated identity)
           │                    └─ release (separate trusted identity)
           │
           └─ metrics/logs → Azure Monitor / Prometheus / Grafana
                                   ↓
                        AKS system/user node pools
                        autoscaler / quotas / PDBs
```

Do not expose controller admin tokens or broad Azure subscription permissions to Jenkins build Pods. An AKS workload identity is for Azure APIs; Kubernetes RBAC governs Pod creation and namespace access.

## 2. Identity architecture

| Layer | Identity | Scope |
|---|---|---|
| Jenkins controller → Kubernetes API | Provisioner service account | Pod lifecycle in build namespace |
| Untrusted agent → Kubernetes API | Build service account | No Pod/Secret management |
| Trusted agent → Azure API | Entra federated identity | Exact Azure resource permissions |
| ACR pull | Kubelet identity or approved imagePullSecret | Repository/registry pull |
| ACR push | Dedicated trusted release identity | Repository push only |
| Cluster operator | Entra ID + Kubernetes/Azure RBAC | Audited administrative access |

**Microsoft Entra Workload ID** uses the AKS OIDC issuer and a federated identity credential binding issuer, audience and Kubernetes service-account subject. It is distinct from legacy Azure AD Pod Identity. Avoid legacy aad-pod-identity for new designs.

## 3. Prerequisites and AKS OIDC issuer

AKS must have OIDC issuer and workload identity enabled; enabling them can affect cluster behavior and must follow change controls.

```sh
az aks show --resource-group "$AKS_RG" --name "$AKS_NAME" \
  --query '{oidc:oidcIssuerProfile.issuerUrl,workload:securityProfile.workloadIdentity.enabled}' \
  -o json
```

Use a disposable cluster. If features are disabled, follow approved AKS upgrade/configuration guidance rather than modifying production interactively.

## 4. Federated identity design

A typical federated credential maps:

- Issuer: AKS `oidcIssuerProfile.issuerUrl`
- Subject: `system:serviceaccount:jenkins-build:jenkins-artifacts`
- Audience: `api://AzureADTokenExchange`
- Target: a user-assigned managed identity (or supported Entra app) with narrow Azure RBAC

Example with a **user-assigned managed identity** and federated credential:

```sh
set -eu
ISSUER="$(az aks show -g "$AKS_RG" -n "$AKS_NAME" \
  --query 'oidcIssuerProfile.issuerUrl' -o tsv)"
az identity federated-credential create \
  --resource-group "$IDENTITY_RG" \
  --identity-name "$IDENTITY_NAME" \
  --name jenkins-artifacts \
  --issuer "$ISSUER" \
  --subject system:serviceaccount:jenkins-build:jenkins-artifacts \
  --audiences api://AzureADTokenExchange
```

Prerequisites: user-assigned identity already created, approved access to configure federated credentials, and supported CLI extension/version. Use a unique credential name and confirm existing state before creating. Federated identity credentials can have propagation delay.

## 5. Kubernetes service account and Pod labels

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-artifacts
  namespace: jenkins-build
  annotations:
    azure.workload.identity/client-id: REPLACE_WITH_MANAGED_IDENTITY_CLIENT_ID
---
apiVersion: v1
kind: Pod
metadata:
  name: ch049-identity-test
  namespace: jenkins-build
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: jenkins-artifacts
  restartPolicy: Never
  containers:
    - name: az
      image: mcr.microsoft.com/azure-cli:azurelinux3.0
      command: ["/bin/sh", "-c", "sleep 600"]
```

**Important:** The Pod label `azure.workload.identity/use: "true"` is required for the workload identity webhook mutation. The image tag above is illustrative and should be replaced with an approved, tested digest. The projected service account token is injected by the workload identity webhook; inspect actual Pod spec and environment before relying on it. For agents that need no Azure APIs, do not apply the label or identity annotation, and disable token automount where possible.

## 6. Verify identity inside the Pod

After Pod starts:

```sh
kubectl exec -n jenkins-build ch049-identity-test -- sh -c '
  test -n "$AZURE_CLIENT_ID"
  test -n "$AZURE_TENANT_ID"
  test -n "$AZURE_FEDERATED_TOKEN_FILE"
  test -r "$AZURE_FEDERATED_TOKEN_FILE"
  az login --service-principal \
    --username "$AZURE_CLIENT_ID" \
    --tenant "$AZURE_TENANT_ID" \
    --federated-token "$(cat "$AZURE_FEDERATED_TOKEN_FILE")" \
    --output none
  az account show --query "{tenant:tenantId,subscription:id,user:user.name}" -o json
'
```

Never print the federated token or client secret. An identity login proves token exchange, not that Azure RBAC is least privilege. Test a permitted operation and a deliberately denied operation against disposable Azure resources.

## 7. Jenkins Kubernetes Pod template

The Kubernetes plugin injects its remoting container. In a trusted Jenkins job, specify the workload identity label and the exact service account:

```groovy
pipeline {
    agent {
        kubernetes {
            defaultContainer 'az'
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: jenkins-artifacts
  restartPolicy: Never
  containers:
    - name: az
      image: mcr.microsoft.com/azure-cli:azurelinux3.0
      command: ["sleep"]
      args: ["99d"]
      tty: true
      resources:
        requests: {cpu: "250m", memory: "512Mi"}
        limits: {cpu: "1", memory: "1Gi"}
'''
        }
    }
    options { timestamps(); timeout(time: 20, unit: 'MINUTES') }
    stages {
        stage('Federated identity') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    test -r "$AZURE_FEDERATED_TOKEN_FILE"
                    az login --service-principal \
                      --username "$AZURE_CLIENT_ID" \
                      --tenant "$AZURE_TENANT_ID" \
                      --federated-token "$(cat "$AZURE_FEDERATED_TOKEN_FILE")" \
                      --output none
                    az account show --query '{tenant:tenantId,subscription:id}' -o json
                '''
            }
        }
    }
}
```

This example is for a disposable trusted agent; pin the Azure CLI image digest and validate nonroot, seccomp, capabilities, injected `jnlp` compatibility and token isolation before production. Avoid exposing workload identity to untrusted PR jobs.

## 8. Azure RBAC and ACR

For ACR pull by AKS kubelet identity, configure supported ACR integration/role assignments. For trusted Jenkins push, grant a dedicated identity only the needed registry/repository permissions (e.g. `AcrPush` where supported, or repository-scoped ABAC roles in ABAC-enabled registries). Registry role semantics differ by ACR permission mode; verify current configuration. Do not grant `Owner` or broad subscription `Contributor` to a Jenkins release identity.

For token-based ACR login, `az acr login` requires Docker unless using an approved token-exposure workflow; do not print access tokens in logs.

## 9. AKS node pools and autoscaling

| Pool | Typical purpose | SRE guidance |
|---|---|---|
| System node pool | Kubernetes system components | Stable on-demand baseline |
| Controller pool | Jenkins controller | Durable storage and controlled upgrades |
| General CI user pool | Retryable builds | Cluster autoscaler and quotas |
| Trusted release pool | Protected release jobs | Restrict placement and credentials |
| Spot user pool | Interruptible test jobs | Idempotent retries only |

Avoid putting controller and high-churn untrusted builds on the same unconstrained nodes. AKS node pools can use taints, labels, min/max autoscaling settings and zone topology; verify supported VM sizes, availability and max-pods constraints. Cluster autoscaler acts on unschedulable Pods, not Jenkins queue directly.

Example discovery:

```sh
az aks nodepool list -g "$AKS_RG" --cluster-name "$AKS_NAME" \
  --query '[].{name:name,mode:mode,count:count,autoscale:enableAutoScaling,min:minCount,max:maxCount}' -o table
kubectl get nodes -L agentpool,kubernetes.azure.com/mode
kubectl get pods -n jenkins-build -o wide
```

## 10. Storage, networking and security

Controller JENKINS_HOME requires durable storage and tested backups; do not scale multiple controllers against the same writable home. For Azure Disk CSI, consider zone constraints and ReadWriteOnce/ReadWriteOncePod support. Azure Files can serve some shared storage cases but does not automatically make multi-controller JENKINS_HOME safe. Agent workspaces should be ephemeral or isolated PVCs.

Use private AKS/API endpoints where required, network policies, controlled egress, TLS, ACR private endpoints, Azure Key Vault/CSI or supported secret integration, Pod Security admission and dedicated service accounts. Do not put long-lived service principal secrets in Jenkinsfiles.

## 11. Observability and FinOps

Measure queue p95, Pod provisioning latency, autoscaler node-ready time, OOM/eviction rate, Azure identity token-exchange failures, ACR pull/push errors, Azure Monitor/Container Insights cost, Log Analytics ingestion/retention, managed disk/PVC usage, NAT/egress, Spot interruption and node idle time. Right-size agent templates using actual CPU/memory telemetry.

## 12. Troubleshooting matrix

| Symptom | Diagnostic | Recovery |
|---|---|---|
| No federated env vars | Missing Pod label/webhook | Correct mutation |
| Token file missing | Projected volume/webhook | Verify service account and webhook |
| AADSTS federated mismatch | Issuer/subject/audience | Correct exact binding |
| Azure RBAC 403 | Role assignment/scope | Apply least privilege |
| Wrong Azure identity | Client ID / credential chain | Remove conflicting credentials |
| ACR pull 401/403 | Kubelet role/private endpoint | Fix pull permissions |
| ACR push denied | Release role/ACR mode | Correct repo permissions |
| Pod Pending | Quota/taint/node pool | Repair scheduling |
| Node autoscaler stalled | MaxCount/VM quota | Expand approved capacity |
| Spot eviction | Node events | Retry idempotent job |
| Controller PVC pending | Disk CSI/zone | Fix storage |
| Agent disconnect | Remoting/network | Restore route |
| Private AKS API unreachable | DNS/VNet/firewall | Repair private connectivity |
| Azure throttling | ARM API metrics | Backoff and rate-limit |
| High logging cost | Ingestion/retention | Tune telemetry policy |
| Unexpected token mount | Pod label/SA | Review trust boundary |

## 13. Production runbooks

### A. AKS onboarding
1. Confirm cluster OIDC/workload identity status and approved namespaces.
2. Configure provisioner Kubernetes RBAC and low-privilege build identities.
3. Create exact federated credential and narrowly scoped Azure RBAC.
4. Launch synthetic Jenkins Pod, verify token exchange and denied action.
5. Test ACR access, node autoscaling and cleanup.
6. Record recovery, backup and security sign-off.

### B. Federated identity outage
1. Capture Pod label, service account annotation, issuer and AADSTS error.
2. Verify token file, audience and client ID without logging token contents.
3. Check federated credential propagation and Entra service health.
4. Correct exact binding and rerun new Pod.
5. Validate permitted and denied Azure API actions.

### C. Node pool capacity incident
1. Record queue, Pending events, node pool autoscaler limits and VM quota.
2. Inspect taints, topology, resource requests and Spot availability.
3. Restore capacity or adjust approved templates.
4. Measure Pod startup and queue recovery.
5. Document cost impact and root cause.

### D. ACR access failure
1. Distinguish kubelet pull versus Jenkins push identity.
2. Capture registry mode, role assignments, network/DNS and HTTP status.
3. Correct least-privilege role or private endpoint routing.
4. Retest pull/push on disposable image.
5. Audit unauthorized access and credential exposure.

### E. Controller disaster recovery
1. Preserve Jenkins controller logs, PVC status and backup inventory.
2. Prevent concurrent writable mounts by multiple controllers.
3. Restore supported backup to controlled controller instance.
4. Verify credentials references, Kubernetes cloud and agent remoting.
5. Run smoke Pipeline and record measured RTO/RPO.

## 14. Acceptance criteria

- [ ] AKS OIDC/workload identity prerequisites verified.
- [ ] Federated identity bound to exact namespace/service account.
- [ ] Build identity cannot manage Kubernetes Pods or Secrets.
- [ ] Azure RBAC grants only required test resource access.
- [ ] ACR pull/push identities separated.
- [ ] Autoscaling and Spot behavior understood.
- [ ] Identity, ACR and scheduling incidents rehearsed.
- [ ] Controller storage/backup and FinOps baseline documented.

**Companion:** [Chapter 049 hands-on lab](labs/049-jenkins-azure-aks-workload-identity-node-pools-operations-check.md).  
**Next:** Chapter 050 — Jenkins on Kubernetes, EKS and AKS Production Operations Capstone.
