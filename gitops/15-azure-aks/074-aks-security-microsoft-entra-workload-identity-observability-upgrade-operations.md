# Chapter 074 — AKS Security, Microsoft Entra Workload Identity, Observability and Upgrade Operations

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 15:** Azure Kubernetes Service (AKS)  
**Chapter:** 074 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Kubernetes Administrators, Security Engineers

> **Safety:** Perform security failure injection, role changes, policy enforcement and upgrades only in an approved staging AKS cluster. Never remove production break-glass access, disable audit logging, force node drains or change shared Key Vault policies during exercises. Control-plane downgrade is not a routine AKS recovery option.

## 1. Learning objectives

After completing this chapter, you will:

1. Design least-privilege Microsoft Entra, Azure RBAC and Kubernetes authorization.
2. Implement AKS Microsoft Entra Workload ID with federated identity credentials.
3. Protect Azure Key Vault, ACR and managed identity access.
4. Enforce workload admission, Pod security and GitOps security boundaries.
5. Configure AKS diagnostic logs, Azure Activity Log and Azure Monitor.
6. Build Prometheus/Grafana operational dashboards and alerts.
7. Validate AKS Kubernetes, node-image and add-on upgrade compatibility.
8. Troubleshoot authorization, identity, monitoring and upgrade failures.
9. Execute incident recovery and document security acceptance evidence.

## 2. Security and operations architecture

~~~text
Microsoft Entra ID + MFA + PIM
             |
     Azure RBAC / AKS access
             |
      Private AKS API endpoint
             |
   Kubernetes authorization + admission
             |
      system and user node pools
             |
 ServiceAccount + OIDC federation
             |
    user-assigned managed identity
             |
     Key Vault / Storage / Azure APIs
             |
 GitLab protected MR -> Argo CD AppProject
             |
     verified workload deployment
             |
 Azure Activity Log + AKS diagnostic logs
             |
 Azure Monitor / Managed Prometheus / Grafana
             |
 SRE alerts, incident response and upgrades
~~~

**Security model:** Azure subscription permissions, AKS API authentication, Kubernetes authorization, Pod admission and Azure resource permissions are separate layers. A principal may authenticate successfully and still be correctly denied a Kubernetes or Azure operation.

## 3. Threat model

Review the following threats:

- Compromised developer or CI identity.
- Overbroad Azure Contributor or Owner assignments.
- Unauthorized Kubernetes cluster-admin privileges.
- Federated identity credential subject mismatch or overly broad trust.
- Pods using legacy static service principal secrets.
- Key Vault secret exposure through manifests, logs or permissive RBAC.
- Privileged containers and unsafe host access.
- Unauthorized Argo CD project destinations or repositories.
- Public AKS API exposure or insecure ingress.
- Missing audit evidence and monitoring gaps.
- Deprecated Kubernetes APIs or incompatible controllers during upgrades.
- Excessive node disruption and failed stateful recovery.

Apply preventive controls, detection, safe containment and documented recovery.

## 4. Microsoft Entra and Azure RBAC

Use Microsoft Entra groups for human access, privileged identity management where available, MFA and short-lived role elevation. Scope Azure role assignments to the resource group or resource instead of the entire subscription wherever possible.

~~~bash
az account show --output table
az aks show -g rg-aks-staging -n aks-staging \
  --query '{aad:aadProfile,identity:identity,api:apiServerAccessProfile}' -o json
az role assignment list --scope /subscriptions/SUBSCRIPTION_ID/resourceGroups/rg-aks-staging -o table
~~~

**Do not treat Azure RBAC and Kubernetes RBAC as interchangeable.** AKS can use Azure RBAC for Kubernetes authorization when enabled, but Kubernetes RBAC remains relevant for ServiceAccounts and controllers. Confirm the actual authorization mode.

## 5. AKS access via kubelogin

~~~bash
az login
az account set --subscription SUBSCRIPTION_ID
az aks get-credentials -g rg-aks-staging -n aks-staging --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
kubectl config current-context
kubectl auth can-i list pods -n demo-staging
kubectl auth can-i get secrets -n demo-staging
~~~

A private cluster requires approved network and DNS connectivity. Avoid distributing long-lived admin kubeconfigs; test and audit emergency access separately.

## 6. Kubernetes RBAC baseline

~~~yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-observer
  namespace: demo-staging
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-observer
  namespace: demo-staging
subjects:
  - kind: Group
    name: platform-staging-observers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: app-observer
  apiGroup: rbac.authorization.k8s.io
~~~

The group must be mapped using the chosen authentication/authorization design. This example intentionally excludes Kubernetes Secrets.

## 7. Workload identity architecture

AKS Workload ID uses the cluster OIDC issuer and a federated identity credential to let a Kubernetes ServiceAccount exchange projected tokens for Microsoft Entra tokens. It avoids storing static service principal secrets in Pods.

Key controls:

- Enable OIDC issuer and workload identity on AKS.
- Create dedicated user-assigned managed identity per trust boundary.
- Use exact issuer, audience and subject for federation.
- Annotate the Kubernetes ServiceAccount with the managed identity client ID.
- Label Pods for Azure Workload Identity webhook injection.
- Scope Azure permissions to required resources and actions.
- Confirm token exchange and negative authorization tests.

## 8. Workload identity inventory

~~~bash
az aks show -g rg-aks-staging -n aks-staging \
  --query '{oidc:oidcIssuerProfile,workloadIdentity:securityProfile.workloadIdentity}' -o json

az identity list -g rg-aks-staging -o table
kubectl -n demo-staging get serviceaccounts
~~~

Use the actual OIDC issuer returned by the cluster. Do not guess issuer URL, tenant ID or identity client ID.

## 9. Federated credential creation

Illustrative Azure CLI workflow:

~~~bash
az identity federated-credential create \
  --name fic-demo-reader \
  --identity-name uami-demo-reader \
  --resource-group rg-aks-staging \
  --issuer "REPLACE_WITH_AKS_OIDC_ISSUER" \
  --subject "system:serviceaccount:demo-staging:demo-reader" \
  --audiences "api://AzureADTokenExchange"
~~~

Federated credentials are trust configuration, not Azure resource authorization. Separately grant the minimum role needed for the target Key Vault, Storage account or other Azure resource.

## 10. ServiceAccount and Pod example

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
  annotations:
    azure.workload.identity/client-id: REPLACE_WITH_UAMI_CLIENT_ID
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-reader
  namespace: demo-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-reader
  template:
    metadata:
      labels:
        app: demo-reader
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: demo-reader
      containers:
        - name: reader
          image: registry.example.internal/demo/reader@sha256:REPLACE_WITH_REAL_DIGEST
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities:
              drop: ["ALL"]
~~~

Replace placeholders before use and ensure the container image supports non-root execution. The Pod label is required for supported workload identity mutation behavior.

## 11. Azure Key Vault and secret delivery

Preferred approaches include Secrets Store CSI Driver with Azure Key Vault provider, or an approved External Secrets Operator deployment using workload identity.

Security requirements:

- No Key Vault secret values in Git, Terraform outputs or CI logs.
- Scoped Key Vault RBAC permissions.
- Rotation and application reload behavior tested.
- Kubernetes Secret synchronization enabled only when needed.
- Private endpoint and DNS connectivity validated.
- Audit and alert on unusual secret access.

**Important:** CSI-mounted secrets and synchronized Kubernetes Secrets have different exposure and lifecycle risks. Kubernetes Secret RBAC remains necessary when synchronization is enabled.

## 12. Key Vault CSI SecretProviderClass example

~~~yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: demo-kv
  namespace: demo-staging
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: REPLACE_WITH_UAMI_CLIENT_ID
    keyvaultName: REPLACE_WITH_KEY_VAULT_NAME
    tenantId: REPLACE_WITH_TENANT_ID
    objects: |
      array:
        - |
          objectName: demo-synthetic-secret
          objectType: secret
~~~

This requires compatible Secrets Store CSI Driver and Azure provider installation, configured federated identity and permitted Key Vault access. Do not assume the SecretProviderClass alone creates an Azure identity association.

## 13. Azure Container Registry security

Grant the AKS kubelet identity approved pull permissions under the ACR registry's authorization mode. Restrict push permissions to protected CI identity. Scan, sign and deploy immutable image digests.

Never use the ACR admin account for ordinary workloads. Review ACR private networking, DNS and image-pull troubleshooting separately from application workload identity.

## 14. Pod security and admission

Use Pod Security Admission, Azure Policy for AKS where supported, and approved policy-as-code controllers such as Gatekeeper or Kyverno.

~~~bash
kubectl label namespace demo-staging \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted \
  --overwrite
~~~

Start in warn/audit, then validate and selectively enforce. System controllers may require documented exceptions. Pod Security Admission is not an image signature verifier; configure an appropriate admission integration for image trust.

## 15. Network isolation and private API

Keep the AKS API private where required, validate private DNS and approved operator connectivity, enforce supported NetworkPolicy, and restrict Azure egress through approved routes.

NetworkPolicy manifests do not provide enforcement unless the installed AKS network dataplane supports and enables it. Test both allowed and denied traffic.

## 16. Argo CD security boundaries

Separate platform and application AppProjects. Restrict repository sources, destinations, cluster-scoped resource types and privileged namespace access. Protect Argo CD credentials and require GitLab CODEOWNERS approval for security-sensitive manifests.

Do not let application teams modify admission policy, cluster-admin RBAC or shared workload identity associations through an unrestricted AppProject.

## 17. Azure Activity Log versus AKS audit logs

Azure Activity Log records Azure control-plane events, such as role assignments and resource changes. Kubernetes audit logs record Kubernetes API activity when configured through AKS diagnostics. They are complementary.

Capture logs to an approved Log Analytics workspace or central archive with encryption, retention, access controls and alert routing.

## 18. Diagnostic settings and log categories

~~~bash
az monitor diagnostic-settings list \
  --resource "$(az aks show -g rg-aks-staging -n aks-staging --query id -o tsv)" \
  -o json
~~~

AKS log categories and resource-specific table support vary. Inspect available categories and configure through approved Terraform or Azure Policy rather than assuming a fixed set. Avoid exposing tokens or sensitive request metadata in log exports.

## 19. Azure Monitor and managed Prometheus

~~~text
AKS diagnostics -> Log Analytics -> audit/security queries
Azure Activity Log -> central activity archive
Container Insights -> node/Pod/container telemetry
Managed Prometheus -> Kubernetes and controller metrics
Azure Managed Grafana -> SRE dashboards
Argo CD metrics -> GitOps reconciliation alerts
Application traces -> latency/error SLOs
~~~

Validate supported metrics and scrape configuration before deploying alerts. Configure collection cost budgets and cardinality controls.

## 20. Suggested SLOs and alerts

| Domain | Indicator | Alert condition |
| --- | --- | --- |
| AKS API | Reachability/auth failures | Sustained operational failure |
| Nodes | Ready capacity by pool/AZ | Critical pool below safe floor |
| Workload identity | Token exchange/authorization | Sustained AccessDenied |
| Key Vault | Secret fetch success/latency | Application credential unavailable |
| CoreDNS | DNS errors/latency | Sustained resolution failures |
| Ingress | Healthy endpoints/5xx | User-impacting failure |
| Storage | PVC mount/provisioning | Sustained attach or mount failure |
| Argo CD | Sync/health/reconciliation | Prolonged Degraded/OutOfSync |
| Upgrades | Version skew and node readiness | Failed node image rollout |

Set actual numeric objectives based on application service tier and measured baselines.

## 21. AKS upgrade strategy

1. Review supported Kubernetes target versions and maintenance policy.
2. Inventory deprecated APIs and installed CRDs/webhooks.
3. Validate Azure CNI, CoreDNS, CSI, ingress, Argo CD and policy controllers.
4. Verify backup and application restore.
5. Check node pool surge capacity and PodDisruptionBudgets.
6. Rehearse a staged upgrade in nonproduction.
7. Upgrade control plane and node pools using approved supported order.
8. Validate workload identity, DNS, storage and ingress.
9. Soak and measure SLOs before production promotion.
10. Record forward recovery; do not assume control-plane downgrade.

## 22. Version inventory

~~~bash
az aks show -g rg-aks-staging -n aks-staging \
  --query '{version:kubernetesVersion,provisioningState:provisioningState}' -o json
az aks get-upgrades -g rg-aks-staging -n aks-staging -o table
az aks nodepool list -g rg-aks-staging --cluster-name aks-staging -o table
kubectl version
kubectl get nodes -o wide
kubectl get apiservices
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
~~~

Do not rely on a static version compatibility table. Use the selected AKS region, Kubernetes release, Azure CLI version and supported controller matrix.

## 23. Node image and add-on upgrades

Node image upgrades are distinct from control-plane minor upgrades. Verify OS image, kernel, CNI, CSI and runtime compatibility. Drain safely with surge capacity, readiness checks, topology spread and PDBs.

PDBs limit voluntary eviction, not all node failures. A restrictive PDB can block planned upgrades. Never force-drain production Pods solely to make a change appear successful.

## 24. GitLab upgrade policy gates

~~~yaml
stages: [validate, compatibility, report]

validate:
  stage: validate
  image: registry.example.internal/ci/kubernetes-tools:PINNED_DIGEST
  script:
    - ./ci/validate-kubernetes-manifests.sh
    - ./ci/check-deprecated-apis.sh

compatibility:
  stage: compatibility
  image: registry.example.internal/ci/azure-tools:PINNED_DIGEST
  script:
    - ./ci/check-aks-version-and-addon-compatibility.sh
    - ./ci/check-workload-identity-policy.sh

report:
  stage: report
  image: registry.example.internal/ci/report-tools:PINNED_DIGEST
  script:
    - ./ci/generate-upgrade-readiness-report.sh
~~~

Images and scripts are placeholders to be implemented and pinned. A passing pipeline does not authorize an unreviewed production control-plane upgrade.

## 25. Lab A — Identity and RBAC inventory

1. Verify tenant, subscription and AKS context.
2. Inventory Azure role assignments and AKS authorization mode.
3. Review Microsoft Entra groups and privileged role eligibility.
4. Inspect Kubernetes ClusterRoles and RoleBindings.
5. Identify access to Secrets and cluster-scoped resources.
6. Archive redacted baseline.

**Pass:** privileged access is scoped and documented.

## 26. Lab B — Read-only access and denial

1. Create approved staging observer identity.
2. Grant only required Azure/Kubernetes permissions.
3. Verify permitted Pod read.
4. Attempt unauthorized Secret read and workload mutation.
5. Confirm denial and audit record.
6. Revoke test access.

**Pass:** least privilege is proven.

## 27. Lab C — Workload identity federation

1. Create user-assigned managed identity.
2. Retrieve AKS OIDC issuer.
3. Configure exact ServiceAccount federated subject.
4. Deploy labeled synthetic workload.
5. Verify authorized Azure API read.
6. Test unrelated ServiceAccount denial.

**Pass:** no static Azure client secret is used.

## 28. Lab D — Federation failure injection

1. Record working identity baseline.
2. Change federated subject in disposable staging identity.
3. Observe token exchange failure.
4. Inspect issuer, audience, subject and client ID.
5. Restore exact trust.
6. Verify recovery.

**Pass:** trust errors are diagnosable without broadening permissions.

## 29. Lab E — Key Vault CSI access

1. Deploy approved CSI driver/provider.
2. Create synthetic Key Vault secret.
3. Grant scoped secret read to test identity.
4. Mount through SecretProviderClass.
5. Verify unauthorized Pod cannot retrieve secret.
6. Rotate synthetic value and test reload.

**Pass:** Key Vault access and rotation are controlled.

## 30. Lab F — ACR identity and signed image

1. Verify registry authorization mode.
2. Configure kubelet pull permission.
3. Push signed synthetic digest-pinned image.
4. Verify successful deployment.
5. Attempt unauthorized pull or unsigned image admission.
6. Restore approved artifact.

**Pass:** pull and admission controls operate independently.

## 31. Lab G — Pod security policy

1. Enable Pod Security Admission warn/audit.
2. Deploy compliant non-root synthetic Pod.
3. Test privileged Pod using dry-run.
4. Inspect warnings and policy audit.
5. Enforce in disposable namespace after compatibility check.
6. Record exception policy.

**Pass:** risky Pod settings are rejected in enforced scope.

## 32. Lab H — Argo CD security boundary

1. Create restricted staging AppProject.
2. Register approved GitOps repository.
3. Deploy permitted namespaced application.
4. Attempt unauthorized cluster-scoped resource.
5. Confirm Argo CD denial.
6. Restore reviewed policy.

**Pass:** application teams cannot bypass platform boundaries.

## 33. Lab I — AKS diagnostic logs

1. Enable approved AKS audit/diagnostic categories.
2. Generate authorized and denied Kubernetes API calls.
3. Locate events in Log Analytics.
4. Verify retention and access restrictions.
5. Measure ingestion delay.
6. Preserve redacted evidence.

**Pass:** Kubernetes API activity is auditable.

## 34. Lab J — Azure Activity Log anomaly

1. Perform approved staging Azure role assignment change.
2. Locate Activity Log record.
3. Trigger synthetic detection for unexpected role elevation.
4. Verify alert delivery.
5. Revert test assignment.
6. Document incident workflow.

**Pass:** privileged Azure changes are detectable.

## 35. Lab K — Managed Prometheus/Grafana

1. Configure approved collection.
2. Verify node, Pod, CoreDNS and Argo CD targets.
3. Create capacity and reconciliation dashboards.
4. Generate synthetic Pod failure.
5. Confirm alert routing.
6. Review retention and cost.

**Pass:** operational failures are visible.

## 36. Lab L — Deprecated API scan

1. Inventory Kubernetes manifests and CRDs.
2. Select a supported target AKS version.
3. Run deprecation scanner.
4. Introduce synthetic deprecated API fixture.
5. Confirm GitLab validation fails.
6. Migrate fixture to supported API.

**Pass:** compatibility blockers are caught before upgrade.

## 37. Lab M — Node image rotation

1. Check system/user node pool health.
2. Verify PDBs and surge capacity.
3. Initiate approved staging node image upgrade.
4. Observe cordon, drain and replacement.
5. Validate storage mounts and workload SLO.
6. Record rollback/forward repair.

**Pass:** node image rotation preserves required availability.

## 38. Lab N — AKS control-plane upgrade rehearsal

1. Review available target version and compatibility.
2. Validate backups, add-ons, webhooks and node pools.
3. Approve staging upgrade.
4. Observe Azure upgrade status.
5. Update compatible node pools/add-ons as planned.
6. Test identity, DNS, ingress, storage and GitOps.

**Pass:** staging upgrade is operationally verified.

## 39. Lab O — Security incident recovery capstone

1. Simulate wrong workload identity federation.
2. Simulate a separate Argo CD admission denial.
3. Correlate AKS audit, Azure Activity Log and app logs.
4. Restore reviewed IAM and GitOps configuration.
5. Verify authorized/denied access and application health.
6. Measure detection and recovery time.

**Pass:** security recovery is traceable and least-privileged.

## 40. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | kubectl authentication fails | Tenant/kubelogin/token | Verify Entra identity |
| 2 | kubectl Forbidden | Azure/Kubernetes RBAC | Correct scoped access |
| 3 | Azure role assignment ineffective | Wrong scope/propagation | Verify principal and scope |
| 4 | Workload token exchange fails | OIDC subject/audience | Repair federation |
| 5 | Workload Azure API AccessDenied | Missing resource role | Grant minimum permission |
| 6 | Key Vault CSI mount fails | Identity/DNS/provider | Inspect CSI and Key Vault |
| 7 | Key Vault rotation not reflected | Rotation/reload behavior | Repair refresh path |
| 8 | ACR ImagePullBackOff | Kubelet identity/ACR mode | Restore pull permission |
| 9 | Privileged Pod admitted | Policy enforcement gap | Fix admission scope |
| 10 | Argo CD sync denied | AppProject/admission | Correct reviewed manifest |
| 11 | AKS audit logs missing | Diagnostics/export | Restore logging |
| 12 | Azure role change not alerted | Activity Log rule | Repair detection |
| 13 | Prometheus targets missing | Scrape configuration | Restore metrics |
| 14 | Alert noise | Threshold/cardinality | Tune alerts |
| 15 | Upgrade blocked | Deprecated APIs/webhooks | Migrate compatibility |
| 16 | Node rotation stalls | PDB/surge capacity | Restore headroom |
| 17 | CSI/ingress fails post-upgrade | Add-on incompatibility | Restore supported version |
| 18 | Workload degraded post-upgrade | Runtime/API behavior | Forward repair or replacement |

## 41. Runbook — AKS authorization incident

1. Identify affected identity, tenant and cluster.
2. Check Microsoft Entra authentication and kubelogin.
3. Review Azure role scope and AKS authorization mode.
4. Inspect Kubernetes RBAC and audit logs.
5. Restore only required access through approved IaC.
6. Verify denied excessive permissions.
7. Record incident evidence and owner.

## 42. Runbook — workload identity and Key Vault failure

1. Identify ServiceAccount, managed identity and Key Vault.
2. Verify OIDC issuer, audience, subject and Pod label.
3. Inspect CSI provider and token exchange errors.
4. Check Azure resource role assignments and private DNS.
5. Restore scoped trust/permissions.
6. Verify secret retrieval and rotation.
7. Preserve audit trail.

## 43. Runbook — audit or monitoring outage

1. Identify missing AKS diagnostics, Activity Log or metrics.
2. Inspect diagnostic settings and collection health.
3. Verify workspace permissions, routing and ingestion.
4. Restore logging without exposing secret values.
5. Generate synthetic event.
6. Confirm alert delivery and retention.
7. Document coverage gap and corrective action.

## 44. Runbook — failed AKS upgrade

1. Freeze concurrent platform changes.
2. Inspect AKS operation status and version compatibility.
3. Check deprecated APIs, admission webhooks and node pools.
4. Restore compatible CSI/CNI/ingress/controller components.
5. Validate workloads, storage and GitOps.
6. Plan supported forward remediation or replacement cluster.
7. Do not assume control-plane downgrade.
8. Record RCA and preventive tests.

## 45. Runbook — compromised managed identity

1. Contain affected workload and federated trust.
2. Review Azure Activity Log, Key Vault audit and AKS audit.
3. Remove unauthorized role assignments or credentials.
4. Rotate affected secrets and restore approved identity.
5. Redeploy signed artifact through protected GitOps MR.
6. Validate authorization boundaries and application SLO.
7. Document blast radius and long-term remediation.

## 46. Evidence template

~~~text
Change/incident ID:
Azure tenant, subscription and AKS cluster:
Microsoft Entra access and PIM evidence:
Azure/Kubernetes RBAC authorization tests:
OIDC issuer and federated credential subject:
Managed identity client ID (nonsecret):
Key Vault access/rotation evidence:
ACR pull and image verification:
Admission and Argo CD AppProject revision:
AKS diagnostic/Activity Log evidence:
Prometheus/Grafana targets and alerts:
AKS, node image and add-on versions:
Deprecated API scan:
Upgrade duration and application SLO:
Recovery time and approver:
~~~

## 47. Scored operational assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| Entra authentication and least-privilege RBAC | 20 | Allowed/denied tests |
| Workload identity and Key Vault | 20 | Federation and rotation |
| Admission, ACR and GitOps security | 20 | Policy and artifact verification |
| Audit logs, monitoring and alerting | 20 | Synthetic event evidence |
| Upgrade compatibility and recovery | 15 | Rehearsal and node rotation |
| Documentation and ownership | 5 | Evidence packet |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: unscoped admin, exposed static credentials, unauthorized Key Vault read, missing security audit coverage, or unsupported upgrade without recovery planning.

## 48. Final acceptance checklist

- [ ] Microsoft Entra and Azure RBAC reviewed.
- [ ] Kubernetes RBAC and break-glass procedures tested.
- [ ] Workload identity federation scoped to exact ServiceAccount.
- [ ] Key Vault access and rotation validated.
- [ ] ACR pull and signed digest enforcement verified.
- [ ] Pod security and admission controls tested.
- [ ] Argo CD AppProject restrictions enforced.
- [ ] AKS diagnostic and Azure Activity logs functioning.
- [ ] Managed Prometheus/Grafana alerts validated.
- [ ] Deprecated API scan and add-on compatibility approved.
- [ ] Node image and control-plane upgrade rehearsed.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks validated.
- [ ] Evidence, owners and recovery procedures approved.

## 49. Knowledge check

1. How do Microsoft Entra authentication, Azure RBAC and Kubernetes RBAC differ?
2. Why must federated credentials match the ServiceAccount subject?
3. Why is workload identity safer than static service principal secrets?
4. What is the difference between Key Vault CSI mounting and Kubernetes Secret synchronization?
5. Why does an ACR pull identity differ from application workload identity?
6. Why is Pod Security Admission not image signature verification?
7. How do Azure Activity Logs differ from Kubernetes audit logs?
8. Which components need compatibility review before AKS upgrades?
9. Why can PDBs stall node rotation?
10. What evidence demonstrates a safe AKS security and upgrade posture?

## 50. References

- [AKS Microsoft Entra integration](https://learn.microsoft.com/azure/aks/enable-authentication-microsoft-entra-id)
- [AKS Azure RBAC](https://learn.microsoft.com/azure/aks/manage-azure-rbac)
- [AKS Workload Identity](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [Azure Key Vault CSI integration](https://learn.microsoft.com/azure/aks/csi-secrets-store-driver)
- [AKS security concepts](https://learn.microsoft.com/azure/aks/concepts-security)
- [AKS monitoring](https://learn.microsoft.com/azure/aks/monitor-aks)
- [AKS cluster upgrades](https://learn.microsoft.com/azure/aks/upgrade-aks-cluster)
- [AKS node image upgrades](https://learn.microsoft.com/azure/aks/node-image-upgrade)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 074 complete.** Next: **Chapter 075 — AKS Enterprise GitOps Production Operations and Disaster Recovery Capstone**, completing Part 15.