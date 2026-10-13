# Chapter 084 — AKS Identity, Security, Monitoring and Upgrades

**Track:** Kubernetes Administration · **Part 17 — Azure Kubernetes Service**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, AKS platform, Azure security and observability engineers  
**Prerequisites:** Chapters 061–070, 081–083; Azure CLI, kubectl, Windows PowerShell, kubelogin; approved AKS staging cluster and subscription

## 1. Production scenario and mission

An AKS platform is preparing a Kubernetes version upgrade while security audit findings remain open. Several workloads still use static service principal credentials, Azure RBAC and Kubernetes RBAC ownership is unclear, Key Vault secrets are not rotated consistently, and container monitoring misses node provisioning failures. A staging upgrade also reveals an outdated admission webhook and a node image rollout blocked by a PodDisruptionBudget.

**Mission:** audit identity and workload security, establish operational telemetry, and design a staged AKS upgrade with application acceptance, rollback boundaries and incident response procedures.

**Safety:** changing Entra group membership, Azure role assignments, managed identities, admission policies, logging, cluster versions or node images can disrupt access and services. All mutating labs are staging-only, require change approval and must preserve emergency administrator access.

### Learning outcomes

1. Separate Microsoft Entra authentication, Azure RBAC and Kubernetes RBAC.
2. Understand AKS-managed identities and federated workload identity.
3. Validate Key Vault, CSI secrets and rotation controls.
4. Assess Pod security, network policy and image provenance.
5. Configure audit/diagnostic log governance and Azure Monitor.
6. Build Prometheus/Grafana observability and actionable alerts.
7. Inventory AKS upgrade compatibility and version support.
8. Prepare node image, add-on and control-plane upgrade plans.
9. Troubleshoot identity and upgrade-related incidents.
10. Produce an operational security and reliability acceptance report.

## 2. Identity and observability architecture

```text
Human operator / CI
        |
Microsoft Entra ID / Conditional Access
        |
Azure Resource Manager RBAC
        |
AKS authentication (kubelogin)
        |
Azure RBAC for Kubernetes OR Kubernetes RBAC
        |
Kubernetes API / namespaces / workloads
        |
ServiceAccount + federated token
        |
AKS Workload Identity -> Managed Identity -> Key Vault / Storage

AKS control plane / node / Pod / application
        |
Azure Monitor / Log Analytics / managed Prometheus
        |
Grafana / alerts / incident response
```

**Authorization distinction:** Azure permissions to administer the AKS resource do not automatically imply permission to read Kubernetes Secrets. Kubernetes authorization depends on the cluster's selected authorization model and role bindings.

## 3. Lab 1 — Verify Azure identity, cluster and access mode

```powershell
$ErrorActionPreference = 'Stop'
$subscription = 'REPLACE_WITH_APPROVED_SUBSCRIPTION_ID'
$resourceGroup = 'REPLACE_WITH_STAGING_RESOURCE_GROUP'
$cluster = 'REPLACE_WITH_STAGING_AKS_CLUSTER'
az account set --subscription $subscription
az account show --query '{Name:name,Id:id,Tenant:tenantId}' --output json
az aks show --resource-group $resourceGroup --name $cluster --query '{Name:name,Version:kubernetesVersion,Aad:aadProfile,Identity:identity,Security:securityProfile,Oidc:oidcIssuerProfile}' --output json
kubectl config current-context
kubectl auth can-i get pods --all-namespaces
```

**Stop** if subscription or kubeconfig context is not the approved staging cluster. Verify which principal the kubeconfig exec plugin uses; Azure CLI login and kubeconfig identity can differ.

**Expected:** identify tenant, Entra integration, Azure RBAC mode, cluster identity and workload identity state.

## 4. Lab 2 — Audit Microsoft Entra and Azure RBAC

```powershell
$aksId = az aks show --resource-group $resourceGroup --name $cluster --query id --output tsv
az role assignment list --scope $aksId --output table
az aks show --resource-group $resourceGroup --name $cluster --query '{Aad:aadProfile,EnableRbac:enableRbac}' --output json
kubectl get clusterrolebindings
kubectl get rolebindings -A
```

### Access review

- Entra groups instead of long-lived individual grants.
- Separate AKS resource management from Kubernetes administration.
- Minimize cluster-admin privileges and review stale principals.
- Apply namespace-scoped roles for application teams.
- Audit elevated access, break-glass accounts and approvals.
- Confirm Conditional Access and credential rotation policies.
- Document cluster local-account settings and authorized recovery paths.

**Expected:** an access matrix listing principal, role, scope, business justification, owner and review date.

## 5. Lab 3 — Verify kubelogin and Kubernetes authorization

```powershell
kubelogin --version
kubectl config current-context
kubectl auth can-i list pods -n default
kubectl auth can-i get secrets -n default
kubectl auth can-i create deployments -n default
```

If needed for an approved Entra-integrated kubeconfig:

```powershell
kubelogin convert-kubeconfig -l azurecli
```

Conversion changes local kubeconfig behavior; back it up first. Do not use local admin credentials as a shortcut where local accounts are disabled or prohibited.

### RBAC test example

Save `ch084-rbac.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch084
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: readonly
  namespace: ch084
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: ch084
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader
  namespace: ch084
subjects:
  - kind: ServiceAccount
    name: readonly
    namespace: ch084
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply --dry-run=server -f .\ch084-rbac.yaml
kubectl apply -f .\ch084-rbac.yaml
kubectl auth can-i get pods -n ch084 --as=system:serviceaccount:ch084:readonly
kubectl auth can-i get secrets -n ch084 --as=system:serviceaccount:ch084:readonly
```

Impersonation tests require impersonation permission. If the caller cannot impersonate the service account, record the test as Not run rather than concluding the service account was denied.

**Expected:** Pod read allowed, Secret read denied for the service account.

## 6. Lab 4 — Audit managed identities and AKS Workload Identity

AKS Workload Identity uses Kubernetes projected service account tokens and Microsoft Entra federated identity credentials to obtain Azure access tokens without embedding static client secrets in Pods.

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{Identity:identity,Oidc:oidcIssuerProfile,WorkloadIdentity:securityProfile.workloadIdentity}' --output json
kubectl get serviceaccounts -A -o yaml | Select-String 'azure.workload.identity/client-id'
kubectl get pods -A --show-labels | Select-String 'azure.workload.identity/use'
```

### Required checks

1. OIDC issuer enabled and expected.
2. User-assigned managed identity exists with least privilege.
3. Federated credential subject matches namespace/service account.
4. Audience and issuer match expected token exchange.
5. Pod/service account labels and annotations are correct.
6. Azure role assignment scopes are minimal.
7. Token acquisition and negative authorization tests are documented.

**Expected:** workload-to-identity map with owner, permissions and credential lifecycle.

## 7. Lab 5 — Key Vault and CSI secrets design

Azure Key Vault can supply application secrets through approved SDK/workload identity patterns or Secrets Store CSI Driver integrations. Mounting a secret does not automatically make it safe: filesystem access, rotation, audit and application reload behavior matter.

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query 'addonProfiles.azureKeyvaultSecretsProvider' --output json
kubectl get csidrivers
kubectl get secretproviderclasses -A
kubectl get secretproviderclasspodstatuses -A
```

The CSI custom resources may not be installed. Record Not installed rather than treating the missing CRD as proof of cluster failure.

### Secrets acceptance

- Key Vault RBAC and managed identity scope reviewed.
- Secret material not logged or committed to Git.
- Rotation cadence and application reload strategy documented.
- CSI mount and network/private endpoint access validated.
- Recovery procedures for expired credentials and inaccessible vault.
- Audit logs retained and protected.

## 8. Lab 6 — Pod security, network policy and image controls

```powershell
kubectl get namespaces --show-labels
kubectl get networkpolicies -A
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get clusterrolebindings
az aks show --resource-group $resourceGroup --name $cluster --query '{Security:securityProfile,Network:networkProfile}' --output json
```

### Security baseline

- Pod Security Admission or approved policy engine.
- Run as non-root where supported.
- Drop Linux capabilities and restrict privilege escalation.
- Read-only root filesystem where practical.
- Image scanning, signed artifacts and trusted registries.
- NetworkPolicy enforcement confirmed for active CNI/dataplane.
- Admission webhook availability and certificate monitoring.
- No unapproved hostPath or privileged containers.

**Expected:** evidence-based security findings with remediation owners and severity.

## 9. Lab 7 — Audit Azure diagnostic logs and activity records

```powershell
az monitor diagnostic-settings list --resource $aksId --output json
az monitor activity-log list --resource-id $aksId --max-events 20 --output json
az aks show --resource-group $resourceGroup --name $cluster --query '{Monitoring:addonProfiles.omsagent}' --output json
```

Diagnostic categories, log destinations and retention depend on AKS and Azure Monitor configuration. Control-plane audit logs, Azure Activity Logs and application logs cover different events; none replaces the others.

### Audit acceptance

- AKS diagnostic settings route required categories.
- Log Analytics/workspace access is least privilege.
- Retention and regional compliance requirements met.
- Authentication and authorization events are queryable.
- Alerts exist for role assignment and identity changes.
- Cost and sensitive-data handling approved.

## 10. Lab 8 — Establish monitoring and SLO baselines

```powershell
kubectl get nodes
kubectl top nodes
kubectl top pods -A
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
az aks show --resource-group $resourceGroup --name $cluster --query '{Monitoring:addonProfiles.omsagent}' --output json
```

`kubectl top` requires Metrics Server. If unavailable, use the organization's configured Azure Monitor or Prometheus metrics source.

### SLI inventory

| Domain | Signal | Owner |
|---|---|---|
| API | Error rate, latency, throughput | Application/SRE |
| Nodes | Ready, pressure, CPU/memory | Platform |
| Scheduling | Pending duration, unschedulable Pods | Platform |
| Network | CNI IP pressure, CoreDNS, ingress | Network |
| Storage | PVC Pending, Azure Disk/Files errors | DBRE |
| Security | Auth failures, role changes | Security |
| Cost | VMSS, disks, logging and egress | FinOps |

**Expected:** baseline dashboards and alert thresholds tied to actual incident actions.

## 11. Lab 9 — Prometheus, Grafana and alert acceptance

### Example PromQL

```promql
sum by (namespace) (
  kube_pod_status_phase{phase="Pending"} == 1
)
```

```promql
sum by (namespace) (
  increase(kube_pod_container_status_restarts_total[15m])
)
```

```promql
sum by (node) (
  kube_node_status_condition{condition="Ready",status="true"} == 0
)
```

Exporter labels and scrape configuration differ across environments. Verify metric names and missing-series behavior before enabling production alerts.

### Alert acceptance

1. Critical customer SLO burn has a paging path.
2. Node/Pod failures have an actionable threshold.
3. Storage and network failures link to runbooks.
4. Security events are routed to security operations.
5. Alerts are tested without disrupting production.
6. Noise, suppression and maintenance handling are documented.

## 12. Lab 10 — Assess AKS upgrade compatibility

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{Version:kubernetesVersion,Provisioning:provisioningState,AutoUpgrade:autoUpgradeProfile}' --output json
az aks get-upgrades --resource-group $resourceGroup --name $cluster --output table
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --output table
kubectl version
kubectl get apiservices
kubectl get crds
kubectl get pdb -A
```

### Compatibility worksheet

```text
Current AKS Kubernetes version:
Target supported version:
Current support window and deadline:
Deprecated/removed Kubernetes APIs:
Admission webhook/CRD compatibility:
CNI/dataplane and network policy:
Azure Disk/Files CSI:
Ingress controller:
Metrics and logging agents:
Node OS and image versions:
System/user pool upgrade order:
Max surge / subnet IP headroom:
PDBs and stateful workload constraints:
Database/application acceptance owners:
```

**Expected:** documented compatibility matrix and upgrade blockers before any control-plane change.

## 13. Lab 11 — Prepare a controlled AKS upgrade runbook

### Phase A — Preflight

1. Confirm supported version, regional availability and maintenance window.
2. Audit deprecated APIs and admission webhook compatibility.
3. Verify backups, application recovery and DR readiness.
4. Review max surge, VM quotas and subnet capacity.
5. Check PDBs, zone placement and stateful storage.
6. Capture baseline SLIs and alert routing.
7. Validate upgrade plan in staging before production.

### Phase B — Staged execution

1. Obtain approval and announce maintenance.
2. Validate API endpoint, identity and monitoring.
3. Upgrade control plane and node pools using supported AKS procedures.
4. Monitor system add-ons, CoreDNS, CNI, CSI and ingress.
5. Validate application synthetic tests and database integrity.
6. Record node replacement timing and cost impact.
7. Complete acceptance checks before closing change.

### Phase C — Recovery constraints

A Kubernetes control-plane downgrade is not a routine supported AKS recovery operation. Plan workload/configuration rollback where possible, compatible node-level remediation and separately tested recovery into another environment when required. Never promise an automatic rollback to a previous control-plane version.

**No upgrade command is executed in this chapter.**

## 14. Lab 12 — Identity and upgrade incident tabletop

**Scenario:** following a staging AKS upgrade, a workload can no longer read Key Vault, an admission webhook rejects new Pods, and node image rollout is blocked by a restrictive PDB.

### Response

1. Freeze further changes and establish incident command.
2. Verify Azure subscription and Kubernetes context.
3. Inspect workload identity federation and Key Vault authorization.
4. Review webhook health, TLS certificates and API compatibility.
5. Inspect PDB disruptionsAllowed and node pool upgrade status.
6. Check Kubernetes Events, Azure Activity Log and diagnostics.
7. Prefer scoped reversible changes with owner approval.
8. Validate application SLOs and secret access after remediation.
9. Record whether separate-cluster recovery is necessary.
10. Publish blameless RCA and preventive controls.

**Expected:** a decision log showing identity, admission and disruption problems were isolated correctly.

## 15. Lab 13 — Security and upgrade operational acceptance

### Evidence package

```text
Subscription, tenant and cluster:
Authentication and authorization model:
Entra groups and Azure RBAC assignments:
Kubernetes RBAC access matrix:
Managed identity / workload federation inventory:
Key Vault integration and rotation owner:
Pod security / network policy findings:
Diagnostic log destinations and retention:
Dashboards and actionable alerts:
AKS and node pool version matrix:
PDB / surge / quota readiness:
Application and database test owners:
Rollback/recovery constraints:
Cost owner and change window:
Open risks and remediation dates:
Independent technical reviewer:
Overall outcome: Pass / Fail / Not run
```

## 16. Production incident runbooks

### A. kubectl access denied

1. Confirm `az account show` identity and tenant.
2. Verify kubeconfig context and kubelogin token acquisition.
3. Check Azure RBAC and Kubernetes authorization model.
4. Inspect Entra group membership and role assignment scope.
5. Review audit logs and Conditional Access errors.
6. Use approved break-glass access only when necessary.

### B. Pod cannot read Key Vault

1. Identify service account and Pod identity labels.
2. Validate OIDC issuer and federated credential subject.
3. Check managed identity and Key Vault role assignments.
4. Confirm private endpoint, DNS and outbound network.
5. Inspect CSI/provider logs if CSI is used.
6. Test least-privilege access and application recovery.

### C. AKS upgrade stalled

1. Inspect upgrade state and node pool health.
2. Check PDBs, quotas and subnet IP headroom.
3. Review CNI/CSI/ingress and admission webhooks.
4. Verify application and database SLIs.
5. Pause further rollout under change control.
6. Escalate incompatible control-plane issues; use approved recovery path.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| kubectl Unauthorized | Entra/kubelogin token | az account, kubeconfig |
| kubectl Forbidden | Azure RBAC/Kubernetes RBAC | Role scope, auth can-i |
| Key Vault access denied | Workload identity/permissions | Federation, role assignments |
| CSI secrets mount fails | Identity/network/provider | CSI logs, private DNS |
| Pod admission fails | Webhook/cert/policy | Webhook logs and API |
| Audit logs absent | Diagnostics configuration | Diagnostic settings |
| Metrics missing | Agent/exporter/scrape | Azure Monitor/Prometheus |
| Upgrade blocked | API/webhook compatibility | AKS upgrade checks |
| Node image rollout stuck | PDB, quota, surge | Node pool status |
| Application degraded after upgrade | CNI/CSI/ingress/add-ons | Events and SLIs |

## 18. Cost and governance

```text
Azure Monitor / Log Analytics ingestion:
Managed Prometheus/Grafana:
Key Vault operations and private endpoints:
Defender for Containers or scanning tools:
Temporary upgrade surge VM capacity:
AKS staging test cluster:
Backup/DR retention:
Log retention and data transfer:
Owner and budget threshold:
```

Review current Azure pricing and retention requirements rather than hard-coding rates.

## 19. Cleanup and acceptance checklist

For the isolated RBAC namespace only:

```powershell
kubectl config current-context
kubectl -n ch084 get roles,rolebindings,serviceaccounts
kubectl delete namespace ch084
```

Do not delete shared Azure role assignments, managed identities, Key Vault resources, diagnostic settings, monitoring infrastructure or production access.

### Acceptance

- [ ] Azure identity, subscription and AKS context verified.
- [ ] Entra, Azure RBAC and Kubernetes RBAC model documented.
- [ ] Least-privilege RBAC lab completed or marked Not run.
- [ ] Managed identities and workload federation reviewed.
- [ ] Key Vault/CSI secret access and rotation assessed.
- [ ] Pod security, network policy and image controls reviewed.
- [ ] Diagnostic logs and audit retention validated.
- [ ] Monitoring, SLOs and alert ownership established.
- [ ] AKS upgrade compatibility matrix completed.
- [ ] Staged upgrade runbook and recovery constraints documented.
- [ ] Identity/upgrade incident tabletop completed.
- [ ] Cost and security governance owners identified.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [AKS Microsoft Entra Authentication](https://learn.microsoft.com/en-us/azure/aks/enable-authentication-microsoft-entra-id)
- [Azure RBAC for Kubernetes Authorization](https://learn.microsoft.com/en-us/azure/aks/manage-azure-rbac)
- [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [AKS Managed Identities](https://learn.microsoft.com/en-us/azure/aks/use-managed-identity)
- [AKS Key Vault Secrets Store CSI](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver)
- [AKS Monitoring](https://learn.microsoft.com/en-us/azure/aks/monitor-aks)
- [AKS Upgrade Cluster](https://learn.microsoft.com/en-us/azure/aks/upgrade-aks-cluster)
- [AKS Node Image Upgrade](https://learn.microsoft.com/en-us/azure/aks/node-image-upgrade)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Kubernetes Version Skew](https://kubernetes.io/releases/version-skew-policy/)

**Next:** Chapter 085 — AKS Production Operations Project (Part 17 final capstone).
