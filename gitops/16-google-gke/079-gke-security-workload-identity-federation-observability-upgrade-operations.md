# Chapter 079 — GKE Security, Workload Identity Federation, Observability and Upgrade Operations

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 16:** Google Kubernetes Engine (GKE)  
**Chapter:** 079 / 100  
**Audience:** SREs, Platform Engineers, Security Engineers, DevSecOps and Kubernetes Administrators

> **Safety:** Use an approved, isolated GKE staging project with synthetic identities and data. Do not revoke production access, disable audit logging, enforce untested admission policies or upgrade live clusters without a change window, tested backups and a recovery plan. Google Cloud IAM changes may take time to propagate. GKE control-plane downgrade is not a routine recovery method.

## 1. Learning objectives

After completing this chapter, you can:

1. Design least-privilege Google Cloud IAM and Kubernetes RBAC.
2. Explain Google Cloud IAM versus Kubernetes API authorization.
3. Configure Workload Identity Federation for GKE without service account keys.
4. Integrate Secret Manager and approved CSI/secret delivery.
5. Secure Artifact Registry and verify software supply-chain controls.
6. Enforce Pod Security Admission and supported GKE policy controls.
7. Use Binary Authorization and signed artifact policy where supported.
8. Collect Cloud Audit Logs, GKE logs, metrics and traces.
9. Build Cloud Monitoring, Managed Service for Prometheus and SLO alerts.
10. Rehearse safe GKE release channel, node and control-plane upgrades.
11. Diagnose identity, security, telemetry and upgrade failures.
12. Execute documented production recovery runbooks.

## 2. Architecture

~~~text
Google Cloud Organization / Organization Policy
                      |
             Google Cloud IAM
                      |
          GKE control-plane access
                      |
          Kubernetes RBAC + admission
                      |
       Standard / Autopilot workloads
                      |
      Kubernetes ServiceAccount (KSA)
                      |
    Workload Identity Federation for GKE
                      |
      Google APIs / Secret Manager
                      |
      Artifact Registry + Binary Auth
                      |
 GitLab protected MR -> Argo CD reconciliation
                      |
 Cloud Audit Logs + GKE operational logs
                      |
 Cloud Monitoring + Managed Prometheus
                      |
        SRE alerts / upgrade gates
~~~

**Trust boundaries:** IAM project permissions, Kubernetes API authorization, admission, workload-to-Google-API identity, image pull permissions and GitOps repository privileges must be reviewed independently.

## 3. Security threat model

Review compromise or misconfiguration of human access, CI federation, cluster administration, Kubernetes ServiceAccounts, node service accounts, Artifact Registry, secret delivery, admission webhooks, audit pipelines and upgrades.

Controls should include prevention, detection, containment, recovery and independently reviewed evidence. Avoid shared wildcard permissions across production namespaces and projects.

## 4. IAM and Kubernetes RBAC

Google Cloud IAM controls access to Google Cloud resources and certain GKE operations. Kubernetes RBAC governs Kubernetes resource actions in the cluster. Permissions are not automatically equivalent.

~~~bash
gcloud config get-value project
gcloud projects get-iam-policy PROJECT_ID --format=json
gcloud container clusters describe gke-staging \
  --region REGION --project PROJECT_ID \
  --format="yaml(workloadIdentityConfig,releaseChannel,loggingConfig,monitoringConfig)"
kubectl auth can-i list pods -n demo-staging
kubectl auth can-i get secrets -n demo-staging
~~~

Use Google Groups for human access where configured, narrow roles and time-bound elevation. Never assume that a successful gcloud login grants Kubernetes cluster-admin.

## 5. Kubernetes Role example

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
    name: gke-staging-observers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: app-observer
  apiGroup: rbac.authorization.k8s.io
~~~

The group subject must correspond to an authenticated group identity supported by the configured GKE access integration. This Role deliberately excludes Secrets and writes.

## 6. Control-plane access

Select approved GKE control-plane endpoint configuration and authorized management connectivity. Private nodes do not necessarily imply a private control-plane endpoint. Review Cloud DNS, firewall, authorized networks and any proxy or Connect Gateway design.

Use the gke-gcloud-auth-plugin with approved identities and avoid sharing static admin kubeconfigs.

## 7. Workload Identity Federation for GKE

Workload Identity Federation for GKE lets workloads use Kubernetes identity to obtain scoped Google Cloud credentials without distributing long-lived service account keys.

Two common patterns are:

- **Direct resource access:** Grant a supported Google Cloud resource role to the Kubernetes workload principal.
- **IAM service account impersonation:** Bind the workload principal to a dedicated IAM service account and annotate the KSA as required by that pattern.

Choose based on API support and governance. The GKE workload identity pool is associated with the cluster project; IAM principal syntax must match the actual project number, namespace and KSA.

## 8. Direct workload principal IAM example

~~~bash
gcloud projects describe PROJECT_ID --format="value(projectNumber)"

gcloud storage buckets add-iam-policy-binding gs://SYNTHETIC_BUCKET \
  --role=roles/storage.objectViewer \
  --member="principal://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/PROJECT_ID.svc.id.goog/subject/ns/demo-staging/sa/demo-reader"
~~~

This is a staging-only example. Replace placeholders and confirm that the target resource supports the principal and role. Grant at resource scope, not project scope, when practical.

## 9. ServiceAccount and Pod

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-reader
  namespace: demo-staging
spec:
  replicas: 2
  selector:
    matchLabels: {app: demo-reader}
  template:
    metadata:
      labels: {app: demo-reader}
    spec:
      serviceAccountName: demo-reader
      containers:
        - name: app
          image: REGION-docker.pkg.dev/PROJECT_ID/demo/app@sha256:REPLACE_WITH_REAL_DIGEST
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {memory: 256Mi}
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities:
              drop: ["ALL"]
~~~

For Standard clusters, verify Workload Identity Federation is enabled on the node pool and workload placement supports it. Autopilot enables workload identity behavior by design, subject to its supported constraints.

## 10. IAM service account impersonation

When direct access is unsupported or policy requires IAM service account identity, use a dedicated IAM service account with narrow resource roles, a precise workload identity binding and the KSA annotation:

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
  annotations:
    iam.gke.io/gcp-service-account: demo-reader@PROJECT_ID.iam.gserviceaccount.com
~~~

This annotation alone is insufficient: configure the correct IAM policy binding for the workload principal and verify token exchange. Never generate downloadable service account JSON keys for this pattern.

## 11. Secret Manager integration

Prefer Secret Manager API access using Workload Identity Federation or a supported Secret Manager CSI driver. Control access at the secret or project resource as appropriate, with least-privilege IAM, audit logging, rotation and reload tests.

Mounting secrets into Pods and synchronizing them into Kubernetes Secrets have different lifecycle and RBAC risks. Avoid committing secret values or exposing them in CI output.

## 12. Secret Manager CSI design

~~~text
KSA -> GKE Workload Identity Federation
         |
Secret Manager IAM permission
         |
Supported GKE Secret Manager CSI driver
         |
Pod volume mount
         |
Application reload/rotation strategy
~~~

Validate the exact installed driver, CRDs, API versions and rotation support for your GKE version. Do not assume the generic Secrets Store CSI driver and the GKE-managed Secret Manager CSI integration use identical manifests.

## 13. Artifact Registry access

Artifact Registry pull authorization normally depends on the node's image-pull identity and repository permissions, while application Google API calls depend on workload identity.

Grant push only to protected CI identities, pull only to approved node identities, and use immutable digests. Review private network egress and regional repository availability.

## 14. Binary Authorization

Binary Authorization can enforce deployment policies using attestations or approved image constraints, subject to supported GKE modes and policy configuration. Pair it with provenance generation, signature verification and restricted CI permissions.

**Important:** Image signing alone does not enforce admission. Validate a negative test that an untrusted synthetic image is denied in the intended enforcement scope.

## 15. Pod Security Admission

~~~bash
kubectl label namespace demo-staging \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted \
  --overwrite
~~~

Start in warn/audit and validate workload compatibility before enforcing. Admission policies may reject system components if scope and exceptions are poorly designed.

## 16. Workload securityContext

~~~yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    image: REGION-docker.pkg.dev/PROJECT_ID/demo/app@sha256:REPLACE_WITH_REAL_DIGEST
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
~~~

This is a PodSpec fragment. Validate application write paths, user IDs and filesystem needs; use writable ephemeral volumes for required temporary data.

## 17. NetworkPolicy and admission governance

Enforce network isolation with a supported GKE dataplane and policy mode. Use approved admission policy tooling (such as Policy Controller/Gatekeeper or equivalent) for organization-specific constraints.

Do not rely on YAML NetworkPolicy alone without verifying actual enforcement. Keep platform exceptions explicit and audited.

## 18. GitLab federation to Google Cloud

Use supported GitLab OIDC federation to Google Cloud Workload Identity Federation for CI workloads, with exact audience, issuer, attribute conditions and protected branch/environment restrictions.

~~~text
Protected GitLab pipeline
        |
short-lived OIDC token
        |
Google Cloud Workload Identity Pool/Provider
        |
scoped CI service account or resource principal
        |
Artifact Registry / Terraform plan / GitOps MR
~~~

Do not use long-lived service account keys. A GitLab runner that builds images should not automatically possess cluster-admin privileges.

## 19. Argo CD boundaries

Restrict Argo CD AppProjects by repository, namespace, destination cluster and cluster-scoped resource kinds. Protect Argo CD SSO, admin break-glass, repository credentials and signing configuration.

GitLab CODEOWNERS approval should be required for IAM-adjacent manifests, RBAC, policies and shared platform controllers. Record Git commit SHA and Argo CD sync revision for incident correlation.

## 20. Cloud Audit Logs

Google Cloud Audit Logs include Admin Activity, System Event, Policy Denied and Data Access categories with differing default availability, retention and cost behavior. Review which Data Access logs must be explicitly enabled.

GKE Kubernetes audit logs and Google Cloud IAM activity are related but not interchangeable. Confirm where required Kubernetes API audit events are delivered and how they are retained.

## 21. Cloud Logging queries

Illustrative Logs Explorer filter:

~~~text
resource.type="k8s_cluster"
resource.labels.cluster_name="gke-staging"
severity>=WARNING
~~~

For Kubernetes API audit events, inspect actual GKE audit log resource types and log names in the target project rather than assuming the generic cluster filter captures every security event.

Avoid exporting credentials, secret payloads or full authorization tokens to logging sinks.

## 22. Cloud Monitoring and Managed Prometheus

Use Cloud Monitoring for cluster, node, Pod, load balancer and Google Cloud service metrics. Managed Service for Prometheus supports Prometheus-style workload metrics with managed collection and querying.

Monitor:

- Control-plane/API access failures.
- Node Ready and available capacity by zone.
- Pod Pending, restarts, OOM and CPU throttling.
- CoreDNS, ingress/Gateway and load balancer errors.
- Persistent Disk/Filestore latency and CSI failures.
- Workload identity/Secret Manager errors.
- Argo CD reconciliation drift.
- Upgrade progress and SLO regression.

## 23. SLO and alert design

| Service | Signal | Alert condition |
| --- | --- | --- |
| Application | Request success and latency | Error-budget burn |
| Node pool | Ready capacity | Below required headroom |
| DNS | Resolution errors | Sustained failures |
| Ingress | 5xx and unhealthy backends | User impact |
| Identity | Google API permission errors | Sustained auth failures |
| Secrets | Secret Manager access | Credential unavailable |
| GitOps | Degraded/OutOfSync | Prolonged drift |
| Storage | CSI attach/mount failures | Persistent workload impact |
| Upgrades | Node unavailable duration | Exceeds change threshold |

Set numeric objectives from application criticality and measured baseline. Avoid paging for every transient Pod restart.

## 24. GKE release channels and upgrades

Choose a supported release channel and maintenance policy based on compatibility and operational needs. Review target Kubernetes versions, version skew, deprecated APIs, admission webhooks, CNI/CSI, Argo CD and workload identity.

For Standard node pools, evaluate surge/blue-green upgrade support, PodDisruptionBudgets, quota, reservations, zone headroom and persistent volume topology. Autopilot upgrade operations follow its managed lifecycle and constraints.

## 25. Upgrade readiness commands

~~~bash
gcloud container clusters describe gke-staging \
  --region REGION --project PROJECT_ID \
  --format="yaml(currentMasterVersion,releaseChannel,maintenancePolicy)"
gcloud container get-server-config \
  --region REGION --project PROJECT_ID
gcloud container node-pools list \
  --cluster gke-staging --region REGION --project PROJECT_ID
kubectl get nodes -o wide
kubectl get pdb -A
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
~~~

Never assume a failed GKE control-plane upgrade can be rolled back by downgrading. Prepare supported forward repair, backup restoration or replacement-cluster migration.

## 26. Lab A — Security inventory

1. Verify project, region, cluster and GKE mode.
2. Review IAM bindings, Organization Policy and access paths.
3. Inventory Kubernetes ClusterRoleBindings.
4. Inspect node and workload service accounts.
5. Record Binary Authorization and admission posture.
6. Archive redacted evidence.

**Pass:** privilege boundaries are documented.

## 27. Lab B — Least-privilege Kubernetes RBAC

1. Create synthetic staging observer group/principal.
2. Grant namespace read-only permissions.
3. Verify allowed Pod list.
4. Verify denied Secret read and Deployment mutation.
5. Inspect Kubernetes audit evidence.
6. Revoke temporary test access.

**Pass:** least privilege is proven.

## 28. Lab C — Direct Workload Identity Federation

1. Create KSA in disposable namespace.
2. Retrieve project number and workload pool.
3. Grant exact workload principal read access to synthetic bucket.
4. Deploy supported workload on WIF-enabled nodes.
5. Verify allowed read.
6. Verify denied write and unrelated KSA.

**Pass:** no JSON service account key is used.

## 29. Lab D — IAM service account impersonation

1. Create dedicated IAM service account.
2. Bind exact workload principal for impersonation.
3. Annotate synthetic KSA.
4. Verify token exchange and allowed API call.
5. Test wrong KSA denial.
6. Remove test binding.

**Pass:** trust is scoped to intended workload.

## 30. Lab E — Secret Manager access

1. Create synthetic Secret Manager secret.
2. Grant scoped access to workload principal.
3. Retrieve through supported API/CSI mechanism.
4. Verify unauthorized KSA denial.
5. Rotate secret and validate reload.
6. Confirm no secret value appears in logs.

**Pass:** secret lifecycle and access are controlled.

## 31. Lab F — Artifact Registry pull and CI push

1. Inspect repository permissions.
2. Configure scoped CI writer.
3. Configure approved node pull identity.
4. Push signed digest-pinned synthetic image.
5. Verify deployment.
6. Test unauthorized pull denial.

**Pass:** build and runtime permissions are separate.

## 32. Lab G — Binary Authorization enforcement

1. Review current policy in staging.
2. Sign/attest approved synthetic image.
3. Deploy approved digest.
4. Attempt untrusted synthetic digest.
5. Confirm denial in enforced scope.
6. Restore reviewed policy.

**Pass:** admission verifies trusted artifacts.

## 33. Lab H — Pod Security Admission

1. Label disposable namespace warn/audit restricted.
2. Deploy compliant non-root Pod.
3. Dry-run privileged Pod.
4. Inspect warnings/audit.
5. Enable enforcement after compatibility review.
6. Verify privileged Pod denial.

**Pass:** restricted policy works without breaking platform add-ons.

## 34. Lab I — GitLab OIDC federation

1. Configure approved Google Cloud workload identity provider.
2. Restrict issuer/audience and protected branch claims.
3. Run short-lived CI authentication.
4. Verify permitted Artifact Registry action.
5. Test unprotected branch denial.
6. Remove test grants.

**Pass:** CI does not store static Google service account keys.

## 35. Lab J — Argo CD AppProject restrictions

1. Create restricted staging AppProject.
2. Register approved repository and namespace.
3. Sync permitted application.
4. Attempt unauthorized cluster-scoped resource.
5. Confirm denial.
6. Restore approved GitOps revision.

**Pass:** GitOps cannot bypass platform boundaries.

## 36. Lab K — Cloud Audit Logs

1. Review Admin Activity, Data Access and Policy Denied configuration.
2. Generate approved IAM change in staging.
3. Generate denied Google API access.
4. Locate both events in Logs Explorer.
5. Validate retention and alert routing.
6. Revert IAM change.

**Pass:** privileged and denied operations are auditable.

## 37. Lab L — Managed Prometheus

1. Configure approved managed collection.
2. Verify node/Pod/controller metrics.
3. Create workload SLO dashboard.
4. Trigger synthetic Pod unavailability.
5. Confirm alert routing.
6. Review metrics cardinality and cost.

**Pass:** monitoring detects service degradation.

## 38. Lab M — Deprecated API and add-on scan

1. Select supported target GKE version.
2. Inventory manifests, CRDs and admission webhooks.
3. Run approved deprecation scanner.
4. Add synthetic deprecated fixture.
5. Verify GitLab validation fails.
6. Migrate fixture to supported API.

**Pass:** compatibility blockers are caught before upgrade.

## 39. Lab N — Node upgrade rehearsal

1. Inspect node pool upgrade strategy and maintenance window.
2. Verify surge capacity, PDB and zone placement.
3. Approve staging node image/version update.
4. Observe drain and replacement.
5. Verify CSI, ingress, identity and SLO.
6. Document recovery strategy.

**Pass:** node maintenance preserves required availability.

## 40. Lab O — Security and upgrade incident capstone

1. Simulate a wrong workload principal binding.
2. Simulate separate admission denial.
3. Correlate Cloud Audit Logs, GKE events and Argo CD revision.
4. Restore reviewed IAM/GitOps state.
5. Verify positive/negative access and workload SLO.
6. Produce incident timeline and corrective actions.

**Pass:** recovery restores service without excessive permissions.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | kubectl authentication fails | Auth plugin/identity | Repair client auth |
| 2 | kubectl Forbidden | Kubernetes RBAC | Correct scoped binding |
| 3 | Google API AccessDenied | IAM role/scope | Grant minimum permission |
| 4 | WIF token exchange fails | Wrong KSA/workload pool | Correct trust |
| 5 | IAM impersonation denied | Missing binding/annotation | Repair exact principal |
| 6 | Secret Manager access denied | IAM/resource path | Restore scoped access |
| 7 | Secret CSI mount fails | Driver/permissions/network | Inspect CSI |
| 8 | Secret rotation stale | Reload/refresh | Repair rotation |
| 9 | Artifact Registry pull fails | Node IAM/egress | Restore pull access |
| 10 | Binary Authorization rejects image | Missing attestation/policy | Verify artifact |
| 11 | Privileged Pod admitted | Admission not enforced | Correct policy scope |
| 12 | Argo CD sync denied | AppProject/admission | Fix reviewed manifest |
| 13 | Cloud Audit Logs missing | Category/sink configuration | Restore logging |
| 14 | Managed Prometheus no metrics | Collector/target | Repair scrape |
| 15 | Alert noise or high cost | Threshold/cardinality | Tune collection |
| 16 | Upgrade blocked | Deprecated APIs/webhooks | Migrate blockers |
| 17 | Node upgrade stalls | PDB/quota/surge | Restore capacity |
| 18 | Workload degrades post-upgrade | Add-on/runtime mismatch | Supported forward repair |

## 42. Runbook — GKE IAM/RBAC lockout

1. Identify affected principal, project and cluster.
2. Verify gcloud identity and auth plugin.
3. Inspect Google Cloud IAM and Kubernetes RBAC separately.
4. Use approved break-glass access if necessary.
5. Restore only required permissions.
6. Test allowed and denied actions.
7. Preserve audit evidence and revoke emergency elevation.

## 43. Runbook — Workload Identity Federation failure

1. Identify KSA, namespace, workload pool and target Google API.
2. Inspect node WIF support and workload placement.
3. Review exact IAM principal and optional impersonation binding.
4. Verify Secret Manager/resource permissions and network.
5. Restore scoped trust.
6. Validate authorized/denied calls.
7. Record RCA.

## 44. Runbook — supply-chain or admission incident

1. Identify image digest, signature/attestation and admission policy.
2. Stop unsafe promotions.
3. Verify trusted CI build provenance and Artifact Registry permissions.
4. Restore reviewed policy or approved signed image.
5. Validate denial of untrusted artifacts.
6. Confirm application SLO.
7. Record evidence and preventive controls.

## 45. Runbook — logging or monitoring outage

1. Determine whether Cloud Audit Logs, GKE logs or metrics are missing.
2. Inspect collection configuration, sinks and IAM.
3. Check Managed Prometheus target health and cardinality.
4. Restore collection without exposing secrets.
5. Generate synthetic audit event and application alert.
6. Verify routing, retention and budget.
7. Document coverage gap.

## 46. Runbook — GKE upgrade stalled

1. Freeze concurrent platform changes.
2. Inspect GKE operation, release channel and target version.
3. Review PDB, surge capacity, quota and node health.
4. Check CRDs, admission webhooks and deprecated APIs.
5. Restore supported add-on compatibility and capacity.
6. Plan supported forward remediation or replacement cluster.
7. Validate identity, ingress, storage and SLO.
8. Record incident and approval.

## 47. Evidence template

~~~text
Change/incident ID:
GCP organization, project, region, cluster:
GKE mode, release channel and Kubernetes version:
Human IAM and Kubernetes RBAC:
Workload pool, KSA and IAM principal:
Secret Manager permission and rotation:
Artifact Registry digest and signature:
Binary Authorization policy and negative test:
Pod Security Admission / policy controller:
GitLab OIDC and Argo CD revision:
Cloud Audit Logs and GKE logs:
Managed Prometheus metrics and alerts:
Deprecated API scan and upgrade strategy:
Node upgrade result and measured SLO:
Approvers, owner and recovery evidence:
~~~

Do not archive access tokens, secret payloads, private keys or privileged kubeconfigs.

## 48. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| IAM and Kubernetes authorization | 20 | Positive/negative access |
| Workload Identity Federation and secrets | 20 | Scoped identity and rotation |
| Artifact trust and admission | 20 | Signed image and denial |
| Cloud Audit Logs and observability | 20 | Synthetic event and alert |
| Upgrade safety and recovery | 15 | Rehearsal and compatibility |
| Documentation and ownership | 5 | Evidence packet |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: static service account keys in workloads, unscoped cluster-admin, unauthorized secret access, unenforced required artifact admission, missing security audit evidence or unsupported upgrade without recovery plan.

## 49. Final acceptance checklist

- [ ] Google Cloud IAM and Kubernetes RBAC reviewed.
- [ ] Human authentication and break-glass access tested.
- [ ] Workload Identity Federation positive/negative tests passed.
- [ ] Secret Manager delivery and rotation verified.
- [ ] Artifact Registry access separated by identity.
- [ ] Binary Authorization or approved image trust enforced.
- [ ] Pod Security Admission and policy scope validated.
- [ ] GitLab OIDC federation and protected MRs reviewed.
- [ ] Argo CD AppProject restrictions verified.
- [ ] Cloud Audit Logs and GKE logging operational.
- [ ] Managed Prometheus and SLO alerts tested.
- [ ] Deprecated APIs and add-ons scanned.
- [ ] Node upgrade rehearsed with recovery plan.
- [ ] Fifteen labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five SRE runbooks validated.

## 50. Knowledge check

1. Why does Google Cloud IAM not replace Kubernetes RBAC?
2. What are the two common GKE Workload Identity Federation patterns?
3. Why is a KSA annotation alone insufficient for IAM impersonation?
4. How do Artifact Registry pull permissions differ from application API access?
5. Why does image signing not automatically enforce trusted deployments?
6. How do Pod Security Admission and Binary Authorization differ?
7. Which Cloud Audit Log categories may require additional configuration?
8. Why is Managed Prometheus cardinality a cost concern?
9. What must be validated before a GKE minor version upgrade?
10. Why is replacement-cluster recovery sometimes safer than attempting downgrade?

## 51. References

- [GKE security overview](https://cloud.google.com/kubernetes-engine/docs/concepts/security-overview)
- [GKE IAM access control](https://cloud.google.com/kubernetes-engine/docs/concepts/access-control)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [Configure Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Secret Manager with GKE](https://cloud.google.com/secret-manager/docs/secret-manager-managed-csi-component)
- [Binary Authorization](https://cloud.google.com/binary-authorization/docs)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Cloud Audit Logs](https://cloud.google.com/logging/docs/audit)
- [GKE observability](https://cloud.google.com/kubernetes-engine/docs/concepts/observability)
- [Managed Service for Prometheus](https://cloud.google.com/stackdriver/docs/managed-prometheus)
- [GKE release channels](https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels)
- [GKE cluster upgrades](https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 079 complete.** Next: **Chapter 080 — GKE Enterprise GitOps Production Operations and Disaster Recovery Capstone**, completing Part 16.