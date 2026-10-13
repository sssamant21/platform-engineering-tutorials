# Chapter 089 — GKE Security, Workload Identity Federation, IAM, Monitoring and Upgrades

**Track:** Kubernetes Administration · **Part 18 — Google Kubernetes Engine**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, GKE platform, cloud security and observability engineers  
**Prerequisites:** Chapters 061–070, 086–088; Google Cloud CLI, gke-gcloud-auth-plugin, kubectl, Windows PowerShell; approved staging project and GKE cluster

## 1. Production scenario and mission

A GKE application cannot read a Secret Manager secret after a deployment. Its Kubernetes service account is configured for Workload Identity Federation, but the IAM principal binding does not match the workload namespace. At the same time, a security audit identifies broad project-level roles, incomplete audit log ownership and an approaching GKE release-channel upgrade. An admission webhook and a PodDisruptionBudget could block node replacement.

**Mission:** audit human and workload identities, verify secrets access and Pod security, establish observability and audit controls, and design safe GKE upgrade and incident recovery procedures.

**Safety:** IAM grants, service account impersonation, security policy, cluster upgrades and node maintenance are sensitive changes. Use read-only discovery first; perform mutations only in an approved staging project with change approval, rollback planning and emergency access preserved.

### Learning outcomes

1. Distinguish Google Cloud IAM from Kubernetes RBAC.
2. Explain GKE authentication through gke-gcloud-auth-plugin.
3. Use Workload Identity Federation for GKE instead of long-lived service account keys.
4. Audit Secret Manager and CSI secret delivery patterns.
5. Review Pod Security Admission, network policies and image security.
6. Validate Cloud Audit Logs, Cloud Logging and Cloud Monitoring.
7. Establish Prometheus/managed metrics and actionable alerts.
8. Assess release channels, maintenance windows and upgrade compatibility.
9. Diagnose authorization, admission and upgrade failures.
10. Deliver a security and upgrade readiness acceptance report.

## 2. Security and observability architecture

```text
Human operator / CI
        |
 Google Cloud IAM / organization policy
        |
 gcloud + gke-gcloud-auth-plugin
        |
      GKE API
        |
 Kubernetes RBAC / admission
        |
 Pod + Kubernetes ServiceAccount
        |
 Workload Identity Federation for GKE
        |
 IAM principal -> Secret Manager / Cloud Storage

GKE control plane / nodes / workloads
        |
 Cloud Audit Logs / Cloud Logging
        |
 Cloud Monitoring / Managed Service for Prometheus
        |
 Dashboards / alerts / incident response
```

A Google Cloud IAM permission to manage GKE infrastructure does not automatically authorize every Kubernetes API action. Kubernetes RBAC and Google Cloud IAM both matter, and access should be tested using the actual cluster authorization model.

## 3. Lab 1 — Verify project, identity and cluster

```powershell
$ErrorActionPreference = 'Stop'
$project = 'REPLACE_WITH_APPROVED_STAGING_PROJECT'
$location = 'us-central1'
$cluster = 'REPLACE_WITH_APPROVED_GKE_CLUSTER'
gcloud config set project $project
gcloud auth list
gcloud config get-value project
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(name,location,currentMasterVersion,releaseChannel,workloadIdentityConfig,securityPostureConfig)'
kubectl config current-context
kubectl auth can-i list pods --all-namespaces
```

**Stop** if Google Cloud project, active principal or kubeconfig context is not the approved staging target.

**Expected:** identity, GKE version, release channel and Workload Identity Federation configuration recorded.

## 4. Lab 2 — Audit Google Cloud IAM and Kubernetes RBAC

```powershell
gcloud projects get-iam-policy $project --format=json
kubectl get clusterroles
kubectl get clusterrolebindings
kubectl get roles -A
kubectl get rolebindings -A
kubectl auth can-i get secrets -n default
```

### Access review

- Group-based access where possible.
- Least-privilege IAM roles and minimal project-level grants.
- Namespace-scoped Kubernetes roles for application teams.
- Controlled cluster-admin and break-glass access.
- Separate CI deploy permissions from human administration.
- Periodic review of dormant principals and service accounts.
- Cloud Audit Logs for elevated changes.

**Expected:** principal, role, scope, justification, owner and review date matrix.

## 5. Lab 3 — Namespace-scoped RBAC test

Save `ch089-rbac.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch089
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pod-reader
  namespace: ch089
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: ch089
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader
  namespace: ch089
subjects:
  - kind: ServiceAccount
    name: pod-reader
    namespace: ch089
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply --dry-run=server -f .\ch089-rbac.yaml
kubectl apply -f .\ch089-rbac.yaml
kubectl auth can-i get pods -n ch089 --as=system:serviceaccount:ch089:pod-reader
kubectl auth can-i get secrets -n ch089 --as=system:serviceaccount:ch089:pod-reader
```

The impersonation check requires impersonation permission. If denied, record Not run rather than assuming the service account itself lacks the requested permission.

**Expected:** Pod read allowed, Secret read denied.

## 6. Lab 4 — Workload Identity Federation for GKE

Workload Identity Federation for GKE enables Kubernetes workloads to access supported Google Cloud APIs using short-lived credentials. In a direct principal binding pattern, IAM grants target a Kubernetes service account identity from the workload identity pool. In a service account impersonation pattern, the Kubernetes principal is permitted to impersonate a Google Cloud service account.

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(workloadIdentityConfig)'
kubectl get serviceaccounts -A -o yaml | Select-String 'iam.gke.io/gcp-service-account'
kubectl get pods -A -o wide
```

### Review gates

1. Cluster workload identity pool is correct.
2. Namespace and Kubernetes service account are stable and owned.
3. IAM binding principal matches namespace and service account.
4. Resource access is scoped to the minimum required secret or bucket.
5. No JSON service account key is embedded in Pods.
6. Audit events and token access errors can be investigated.
7. Network egress to required Google APIs is supported.

**Expected:** workload-to-principal-to-resource map and explicit negative access tests.

## 7. Lab 5 — Secret Manager and secrets delivery

```powershell
gcloud secrets list --project $project
kubectl get secrets -A
kubectl get csidrivers
kubectl get secretproviderclasses -A
```

**Do not print secret values** in terminal output, CI logs or the tutorial evidence package. SecretProviderClass CRDs may not be installed; record Not installed if absent.

### Secrets acceptance

- Secret Manager IAM is resource-scoped.
- Rotation owner and interval documented.
- Application reload/restart behavior defined.
- Workload Identity Federation access verified.
- Secret values excluded from Git, logs and tickets.
- Audit and recovery procedures documented.
- Private networking and Google API access tested.

## 8. Lab 6 — Pod security and admission governance

```powershell
kubectl get namespaces --show-labels
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get networkpolicies -A
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(securityPostureConfig,networkPolicy,datapathProvider)'
```

### Pod security review

1. Pod Security Admission or approved policy engine.
2. Run-as-non-root and restricted Linux capabilities.
3. No unnecessary privileged or hostPath access.
4. Seccomp and filesystem restrictions where supported.
5. Trusted images and vulnerability scanning.
6. NetworkPolicy enforced by active GKE dataplane.
7. Admission webhook health and certificate expiry monitored.
8. Autopilot-specific workload restrictions accounted for.

**Expected:** prioritized security findings with remediation owners and dates.

## 9. Lab 7 — Cloud Audit Logs and security events

```powershell
gcloud logging logs list --project $project
gcloud logging read 'resource.type="k8s_cluster"' --project $project --limit 20 --format=json
gcloud logging read 'logName:"cloudaudit.googleapis.com"' --project $project --limit 20 --format=json
```

Log availability depends on permissions, enabled categories, exclusions, retention and organization policies. Do not treat a query returning no entries as proof that logging is disabled.

### Audit acceptance

- Admin Activity and required Data Access audit coverage.
- Kubernetes API activity and GKE control-plane events as configured.
- IAM policy change visibility and alert routing.
- Retention, access controls and export destinations.
- Sensitive-data minimization and cost governance.
- Security incident response ownership.

## 10. Lab 8 — Cloud Monitoring and SLO baselines

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(loggingConfig,monitoringConfig)'
kubectl get nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
```

`kubectl top` requires a metrics pipeline. If unavailable, inspect Cloud Monitoring or the approved Prometheus source.

### SLI baseline

| Domain | Signal | Owner |
|---|---|---|
| Application | 5xx rate, latency, availability | Application/SRE |
| Nodes | Ready, pressure, CPU/memory | Platform |
| Scheduling | Pending Pods and unschedulable duration | Platform |
| Network | DNS, ingress/backend health | Network |
| Storage | PVC Pending, CSI errors | DBRE |
| Security | IAM changes, auth failures | Security |
| Cost | Nodes, disks, logging and egress | FinOps |

**Expected:** monitoring coverage and alert owner for every critical failure domain.

## 11. Lab 9 — Managed Service for Prometheus and alert acceptance

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

These queries require appropriate kube-state-metrics or equivalent exporters. Verify metric availability, labels and missing-series handling before enabling alerts.

### Alert quality criteria

- Every page links to an actionable runbook.
- Customer-impacting SLO burn is prioritized.
- Maintenance windows suppress known expected noise.
- IAM and policy change alerts reach security owners.
- Synthetic checks validate external client experience.
- Alert tests are documented and non-disruptive.

## 12. Lab 10 — GKE release channels and upgrade compatibility

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(currentMasterVersion,releaseChannel,maintenancePolicy,autopilot)'
gcloud container clusters get-upgrade-info $cluster --location $location --project $project
gcloud container node-pools list --cluster $cluster --location $location --project $project
kubectl get apiservices
kubectl get crds
kubectl get pdb -A
```

If the installed gcloud version does not support `get-upgrade-info`, consult the supported upgrade command/reference and record the tool limitation. Autopilot does not expose node pools for customer administration in the same way as Standard.

### Upgrade readiness worksheet

```text
Current and target GKE version:
Release channel:
Maintenance exclusions/window:
Deprecated Kubernetes APIs:
Admission webhook/CRD compatibility:
Dataplane and NetworkPolicy:
Persistent Disk/Filestore CSI:
Ingress/Gateway controller:
Observability agents:
PDB and node surge/blue-green capacity:
Quotas and Pod IP headroom:
Application/database validation owners:
Backup and recovery readiness:
```

**Expected:** documented blockers before any version change.

## 13. Lab 11 — Standard and Autopilot upgrade planning

### Standard

- Review control-plane and node pool upgrade paths.
- Confirm node auto-upgrade policy and release channel.
- Validate surge/blue-green capacity where supported.
- Inspect PDBs, StatefulSets and disk topology.
- Verify node image, admission and CNI/CSI compatibility.
- Run staged application acceptance tests.

### Autopilot

- Understand platform-managed node lifecycle.
- Verify workload admission and resource compatibility.
- Review maintenance exclusions and release channel.
- Test application behavior during voluntary disruptions.
- Preserve SLO monitoring and data protection.

**No upgrade is executed.** Kubernetes control-plane downgrades are not a routine GKE rollback method; use approved recovery strategies and application-level reversibility.

## 14. Lab 12 — Identity and admission incident tabletop

**Scenario:** a deployment loses Secret Manager access after namespace renaming. An admission webhook then rejects replacement Pods, while a GKE node upgrade waits for a restrictive PDB.

### Response

1. Freeze further changes and declare incident ownership.
2. Verify Google Cloud project and kubeconfig identity.
3. Inspect Workload Identity Federation principal bindings.
4. Confirm Secret Manager IAM scope and API connectivity.
5. Review webhook health, TLS and API compatibility.
6. Check PDB `disruptionsAllowed` and Ready replicas.
7. Capture Cloud Audit Logs and Kubernetes Events.
8. Apply only approved reversible remediations.
9. Validate application SLIs and secret access.
10. Record RCA, contributing factors and preventive actions.

**Expected:** fault isolation across IAM, admission and disruption constraints.

## 15. Lab 13 — Security, monitoring and upgrade acceptance

### Evidence package

```text
Project, region/zone and cluster:
Standard or Autopilot:
Google Cloud IAM principal matrix:
Kubernetes RBAC ownership:
Workload identity pool and bindings:
Secret Manager rotation and access:
Pod security and network policy findings:
Audit log destinations/retention:
Cloud Monitoring dashboards and SLOs:
Alert routing and runbook links:
Current/target Kubernetes version:
Release channel and maintenance policy:
Deprecated API and webhook assessment:
PDB/surge/quota/IP capacity:
Application and DB validation owners:
Recovery and rollback limitations:
Security/platform reviewer:
Overall outcome: Pass / Fail / Not run
```

## 16. Production troubleshooting runbooks

### A. kubectl authentication or authorization denied

1. Confirm `gcloud auth list` and active project.
2. Check gke-gcloud-auth-plugin and kubeconfig context.
3. Separate Unauthorized from Forbidden.
4. Inspect IAM permissions and Kubernetes RBAC.
5. Review audit logs and organization policy.
6. Use approved emergency access only when necessary.

### B. Workload cannot access Secret Manager

1. Identify Kubernetes service account and namespace.
2. Check workload identity pool and principal binding.
3. Confirm secret-level IAM permissions.
4. Verify Google API connectivity and DNS.
5. Inspect application SDK and token errors.
6. Validate restored access without exposing secret values.

### C. Upgrade stalled

1. Inspect GKE operations and version state.
2. Review PDBs, admission webhooks and deprecated APIs.
3. Check node quota, IP capacity and zone placement.
4. Inspect CNI/CSI/ingress compatibility.
5. Pause additional changes and escalate under change control.
6. Validate application and data integrity after remediation.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| kubectl Unauthorized | Auth plugin/token | gcloud and kubeconfig |
| kubectl Forbidden | IAM/RBAC | Role bindings |
| Secret Manager denied | Workload federation/IAM | Principal binding |
| Secret mount failure | CSI/API/network | Provider logs |
| Pod rejected | Admission policy/webhook | Webhook status |
| Audit logs missing | Routing/exclusions/permissions | Cloud Logging |
| Metrics missing | Exporter/collection | Monitoring config |
| Upgrade blocked | PDB/API compatibility | GKE operations |
| Node replacement slow | Quota/surge/topology | Node pool status |
| Cost spike | Logs/nodes/metrics | Billing reports |

## 18. Cost and governance

```text
Cloud Logging ingestion and retention:
Cloud Monitoring and Prometheus metrics:
Secret Manager operations:
Security scanning and posture:
Node upgrade surge capacity:
GKE staging environment:
Backup and DR:
Network egress and private access:
Budget owner and alert:
```

Review current Google Cloud pricing and organization retention policies rather than hard-coding rates.

## 19. Cleanup and acceptance checklist

Only delete the isolated RBAC test namespace after context verification:

```powershell
kubectl config current-context
kubectl -n ch089 get serviceaccounts,roles,rolebindings
kubectl delete namespace ch089
```

Do not delete shared IAM bindings, service accounts, Secret Manager secrets, monitoring, audit logs or production resources.

### Acceptance

- [ ] Project, principal, cluster and context verified.
- [ ] Google Cloud IAM and Kubernetes RBAC matrix documented.
- [ ] Namespace RBAC test completed or marked Not run.
- [ ] Workload Identity Federation reviewed.
- [ ] Secret Manager access and rotation controls assessed.
- [ ] Pod security, admission and network policy reviewed.
- [ ] Cloud Audit Logs and retention verified.
- [ ] Cloud Monitoring, Prometheus and SLO alerts assessed.
- [ ] Release channel and upgrade compatibility documented.
- [ ] Standard/Autopilot maintenance responsibilities understood.
- [ ] Identity/admission incident tabletop completed.
- [ ] Cost, security and on-call ownership recorded.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [GKE Authentication](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)
- [GKE Workload Identity Federation](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [GKE Security Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/security-overview)
- [GKE Security Posture](https://cloud.google.com/kubernetes-engine/docs/concepts/about-security-posture-dashboard)
- [Secret Manager](https://cloud.google.com/secret-manager/docs/overview)
- [Cloud Audit Logs](https://cloud.google.com/logging/docs/audit)
- [GKE Logging](https://cloud.google.com/kubernetes-engine/docs/concepts/about-logs)
- [GKE Monitoring](https://cloud.google.com/kubernetes-engine/docs/concepts/monitoring-overview)
- [Managed Service for Prometheus](https://cloud.google.com/stackdriver/docs/managed-prometheus)
- [GKE Release Channels](https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels)
- [GKE Upgrades](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-upgrades)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

**Next:** Chapter 090 — GKE Production Administration, Troubleshooting and Recovery Project (Part 18 final capstone).
