# Chapter 079 — EKS Security, Identity, Monitoring and Upgrades

**Track:** Kubernetes Administration · **Part 16 — Managed Kubernetes on AWS and Azure**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes platform engineers, cloud security and observability teams  
**Prerequisites:** Chapters 061–070 and 076–078; AWS CLI v2, kubectl, PowerShell; approved EKS staging environment; read-only AWS IAM/EKS/CloudWatch access

## 1. Production scenario and mission

An EKS cluster hosts APIs and stateful services. A platform audit finds overly broad Kubernetes privileges, several applications sharing node IAM permissions, disabled control-plane audit logging, missing alerts for node health, and a Kubernetes version approaching the end of its standard support window. The team must strengthen identity and monitoring before scheduling a safe upgrade.

**Mission:** inventory and harden EKS security controls, establish reliable production observability, and prepare an upgrade plan with compatibility, validation and rollback gates.

**Safety boundary:** This chapter is staging-first. IAM policy changes, access entry updates, log configuration, add-on upgrades, node replacement and control-plane version upgrades require approved change windows. Never remove the only working cluster administrator or assume that an EKS control-plane version can be downgraded.

### Learning outcomes

1. Separate AWS IAM, EKS authentication, Kubernetes authorization and workload identity.
2. Audit EKS access entries, access policies and legacy `aws-auth` integration.
3. Design namespace-scoped RBAC and break-glass access.
4. Compare EKS Pod Identity and IAM Roles for Service Accounts (IRSA).
5. Apply workload security controls, secrets encryption and network isolation.
6. Enable and interpret EKS control-plane logs and AWS audit signals.
7. Establish CloudWatch, Prometheus and Grafana monitoring with actionable alerts.
8. Assess EKS version support, add-on compatibility and node lifecycle.
9. Build safe control-plane, node and add-on upgrade procedures.
10. Validate incident response, rollback constraints and operational acceptance.

## 2. Security and observability architecture

```text
Human operator / CI system
        |
AWS IAM Identity Center / STS / IAM
        |
EKS access entry or legacy auth mapping
        |
Kubernetes RBAC / EKS access policy
        |
Kubernetes API server --------> EKS control-plane logs
        |                                |
        v                                v
Namespace / workloads                CloudWatch Logs
        |                                |
Pod Identity / IRSA                 CloudWatch alarms
        |
AWS APIs / KMS / S3 / Secrets Manager

Nodes / Pods / kube-state-metrics / application metrics
        |
Prometheus / managed collector / Grafana / alerts
```

EKS authentication and Kubernetes authorization are related but distinct. An AWS IAM permission to call `eks:DescribeCluster` does not automatically grant permission to read Kubernetes Secrets. A workload IAM role authorizes AWS API calls; Kubernetes RBAC authorizes Kubernetes API operations.

## 3. Lab 1 — Verify identity, cluster and change boundary

```powershell
$ErrorActionPreference = 'Stop'
$profile = 'REPLACE_WITH_APPROVED_AWS_PROFILE'
$region = 'us-east-1'
$cluster = 'REPLACE_WITH_STAGING_EKS_CLUSTER'
aws sts get-caller-identity --profile $profile
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Name:name,Status:status,Version:version,Access:accessConfig,Logging:logging}' --output json
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
```

**Stop:** account, cluster or Kubernetes context mismatch. The AWS CLI profile and kubeconfig exec-auth profile may differ; verify both. Do not run mutating commands in production as part of this tutorial.

**Expected:** recorded AWS principal, cluster identity, version and current logging configuration.

## 4. Lab 2 — Inventory EKS access entries and authentication modes

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.accessConfig'
aws eks list-access-entries --cluster-name $cluster --region $region --profile $profile
kubectl -n kube-system get configmap aws-auth -o yaml
```

The legacy `aws-auth` ConfigMap may be absent or unused on access-entry-only clusters. Treat a NotFound response as a configuration fact, not proof of failed authentication.

### Authentication modes

- `CONFIG_MAP`: legacy authentication mapping.
- `API_AND_CONFIG_MAP`: both access entries and legacy mapping.
- `API`: EKS access-entry API authentication.

Migration to access entries is a separately approved change. Verify bootstrap creator access, access policies, node authentication, automation principals and break-glass roles before changing mode. Authentication-mode transitions have important one-way constraints; do not assume they can be reverted.

## 5. Lab 3 — Audit Kubernetes authorization and least privilege

```powershell
kubectl get clusterrolebindings
kubectl get rolebindings -A
kubectl get roles -A
kubectl get clusterroles
kubectl auth can-i get pods --all-namespaces
kubectl auth can-i get secrets -n default
```

### Review priorities

- Broad `cluster-admin` grants to routine users.
- Service accounts bound to cluster-wide privileges.
- Roles granting `secrets`, `pods/exec`, `impersonate` or workload mutation unnecessarily.
- Unused or stale access entries and IAM roles.
- Namespace isolation and privileged controller permissions.
- Break-glass credentials, audit trail and expiration process.

**Expected:** a least-privilege access matrix for human operators, deployment automation, controllers and application service accounts.

## 6. Lab 4 — Create namespace-scoped RBAC in staging

Save `ch079-rbac.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch079
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: readonly
  namespace: ch079
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: ch079
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader
  namespace: ch079
subjects:
  - kind: ServiceAccount
    name: readonly
    namespace: ch079
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply --dry-run=server -f .\ch079-rbac.yaml
kubectl apply -f .\ch079-rbac.yaml
kubectl auth can-i get pods -n ch079 --as=system:serviceaccount:ch079:readonly
kubectl auth can-i get secrets -n ch079 --as=system:serviceaccount:ch079:readonly
kubectl auth can-i delete deployments -n ch079 --as=system:serviceaccount:ch079:readonly
```

**Expected:** Pod read permitted; Secret read and Deployment delete denied. Impersonation checks require the caller to have permission to impersonate the test identity; failure to impersonate is not an RBAC test result.

## 7. Lab 5 — EKS Pod Identity versus IRSA

| Feature | EKS Pod Identity | IRSA |
|---|---|---|
| Trust model | EKS Pod Identity service principal and associations | Cluster OIDC issuer and service account subject |
| Association | EKS Pod Identity association API | IAM role annotation on service account |
| Credential delivery | Pod Identity Agent and credential endpoint | Web identity token and STS |
| Requirements | Supported cluster/platform, agent, IAM setup | IAM OIDC provider, role trust policy |
| Operational concern | Agent health and association lifecycle | OIDC issuer and trust policy correctness |

Both patterns avoid sharing broad node IAM permissions with applications. Do not attach administrator permissions to an application role.

```powershell
aws eks list-pod-identity-associations --cluster-name $cluster --region $region --profile $profile
kubectl -n kube-system get daemonset eks-pod-identity-agent
kubectl get serviceaccounts -A -o yaml | Select-String 'eks.amazonaws.com/role-arn'
```

If the Pod Identity Agent is absent, determine whether the cluster intentionally uses IRSA or another approved identity pattern. The agent is not required for IRSA.

### Workload identity acceptance

1. Each workload has a dedicated Kubernetes service account.
2. IAM trust policy restricts authorized principals.
3. IAM permissions are scoped to required AWS actions/resources.
4. CloudTrail confirms the intended role is used.
5. A negative test proves unauthorized AWS actions are denied.
6. Credential rotation and role removal have an owner.

## 8. Lab 6 — Audit Secrets, encryption and Pod security

```powershell
kubectl get namespaces --show-labels
kubectl get serviceaccounts -A
kubectl get networkpolicies -A
kubectl get priorityclasses
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.encryptionConfig'
```

### Controls to evaluate

- Kubernetes Secret access restricted through RBAC.
- AWS KMS key policies and recovery access reviewed.
- External Secrets/Secrets Manager integration controlled.
- Pod Security Admission labels or equivalent admission policies.
- Non-root containers, read-only root filesystem and dropped capabilities.
- Image provenance, signed artifacts and vulnerability scanning.
- NetworkPolicy enforcement verified against actual CNI configuration.
- Admission controllers and workload identity dependencies monitored.

EKS encryption defaults and supported configuration options vary by Kubernetes/platform version; inspect actual cluster configuration rather than assuming a specific historical encryption behavior.

**Expected:** a security baseline with evidence and remediation ownership, not just a checklist of enabled features.

## 9. Lab 7 — Inventory control-plane and AWS audit logging

EKS control-plane log types include `api`, `audit`, `authenticator`, `controllerManager` and `scheduler`.

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.logging'
aws logs describe-log-groups --log-group-name-prefix "/aws/eks/$cluster/" --region $region --profile $profile
aws cloudtrail describe-trails --region $region --profile $profile
```

Enabling additional control-plane logs can incur CloudWatch ingestion and retention charges. Review PII, sensitive audit data, retention, access controls and cost before a change.

### Logging acceptance

- Audit and authenticator events are available where required.
- Log retention and encryption align with policy.
- CloudTrail captures AWS-side IAM/EKS changes.
- Logs can be correlated with application incidents.
- Alerts exist for privilege changes and authentication anomalies.
- No assumption that CloudTrail replaces Kubernetes audit logging.

## 10. Lab 8 — Build the EKS monitoring inventory

```powershell
kubectl get nodes
kubectl top nodes
kubectl top pods -A
kubectl -n kube-system get deployments,daemonsets
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

`kubectl top` requires Metrics Server. A missing Metrics Server is a monitoring gap, not necessarily a cluster failure.

### Observability layers

| Layer | Signals | Typical source |
|---|---|---|
| Control plane | API errors, audit, scheduler/controller activity | EKS control-plane logs |
| Nodes | CPU, memory, filesystem, Ready, pressure | kubelet, node exporter, CloudWatch |
| Workloads | Restarts, OOM, pending, readiness | kube-state-metrics, Prometheus |
| Network | Pod IP pressure, CoreDNS, ingress target health | VPC CNI, DNS, ALB/NLB |
| Storage | PVC status, EBS/EFS latency and errors | CSI, CloudWatch |
| Applications | Error rate, latency, throughput, saturation | OpenTelemetry/APM |
| Security | IAM changes, denied access, anomalous behavior | CloudTrail, audit logs |

**Expected:** an owner, dashboard, alert threshold and response runbook for each critical signal.

## 11. Lab 9 — Design actionable alerts and dashboards

### Example PromQL queries

```promql
sum by (cluster, namespace) (
  kube_pod_status_phase{phase="Pending"} == 1
)
```

```promql
sum by (cluster, namespace) (
  increase(kube_pod_container_status_restarts_total[15m])
)
```

```promql
sum by (node) (
  kube_node_status_condition{condition="Ready",status="true"} == 0
)
```

Metric labels vary by exporter and scrape configuration. Verify metric availability and labels before installing alerts. The node expression is illustrative and must be tested against missing-series behavior.

### Alert acceptance

- High severity: customer SLO burn, cluster API unavailable, sustained node unavailability.
- Medium severity: pending capacity, CoreDNS errors, CNI IP pressure, EBS CSI failures.
- Security: unauthorized IAM/EKS access changes and unusual audit events.
- Informational: planned upgrades, capacity trends and cost anomalies.

Each alert must include impact, threshold, owner, runbook link, dashboard, and an action that an on-call engineer can take.

## 12. Lab 10 — Assess Kubernetes and add-on upgrade compatibility

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Version:version,Platform:platformVersion,Status:status}'
aws eks list-addons --cluster-name $cluster --region $region --profile $profile
aws eks list-nodegroups --cluster-name $cluster --region $region --profile $profile
kubectl version
kubectl get apiservices
kubectl get pdb -A
kubectl get crds
```

### Compatibility worksheet

```text
Current Kubernetes version:
Target Kubernetes version:
EKS support window and upgrade deadline:
API deprecations and removed versions:
Add-on compatibility:
VPC CNI / CoreDNS / kube-proxy versions:
EBS/EFS CSI compatibility:
AWS Load Balancer Controller version:
Karpenter compatibility:
Managed node group AMI/version:
Fargate and custom node considerations:
Webhook/CRD/operator compatibility:
kubectl/client version skew:
Application and database validation owners:
```

Verify AWS's current supported-version matrix and version-skew rules before any upgrade. EKS control-plane version upgrades are performed in supported increments; do not assume direct multi-minor jumps are permitted.

## 13. Lab 11 — Prepare a staged EKS upgrade runbook

### Phase A — Preflight

1. Approve target version and maintenance window.
2. Inventory API deprecations, CRDs and admission webhooks.
3. Confirm etcd/control-plane responsibility and application-level backup coverage.
4. Verify Kubernetes objects, PV data and database backups independently.
5. Validate subnet free IPs, EC2 quotas and node capacity.
6. Check PDBs, topology spread and graceful termination.
7. Review add-on, Karpenter and managed node group compatibility.
8. Capture SLIs, alerts and rollback options.

### Phase B — Controlled rollout

1. Upgrade nonproduction cluster first.
2. Validate control-plane API and authentication.
3. Update compatible add-ons in a documented order.
4. Update managed node groups or Karpenter nodes using approved disruption budgets.
5. Validate CSI, ingress, DNS, workload identity and Pod scheduling.
6. Run application and database synthetic tests.
7. Monitor error budget, latency, node health and costs.

### Phase C — Rollback decision

**Important:** EKS control-plane version downgrades are not supported. A rollback plan must therefore focus on workload/configuration reversions, compatible node/add-on rollback where supported, or recovery into a separate previously validated environment. Do not promise a simple control-plane downgrade.

### Read-only upgrade status commands

```powershell
aws eks list-updates --name $cluster --region $region --profile $profile
aws eks describe-update --name $cluster --update-id REPLACE_WITH_UPDATE_ID --region $region --profile $profile
kubectl get nodes -o wide
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

No control-plane upgrade command is executed in this lab.

## 14. Lab 12 — Security incident and failed-upgrade tabletop

**Scenario:** after a staging control-plane upgrade, the ingress controller cannot authenticate to AWS APIs, an older admission webhook rejects Deployments, and audit logs show an unexpected cluster-admin access policy association.

### Investigation

1. Freeze further upgrade and access changes.
2. Verify AWS identity, EKS access entries and CloudTrail activity.
3. Inspect admission webhook configuration and certificate validity.
4. Confirm Pod Identity/IRSA trust policy and controller service account.
5. Review controller logs and AWS authorization failures.
6. Validate API versions and deprecated resource usage.
7. Confirm application SLO impact and data integrity.
8. Apply only reviewed, reversible fixes where possible.
9. Document whether a separate-cluster recovery path is required.
10. Produce a blameless RCA with preventive controls.

**Expected:** a defensible incident timeline and recovery decision without attempting an unsupported EKS control-plane downgrade.

## 15. Operational runbooks

### A. Kubernetes API access denied

1. Verify `aws sts get-caller-identity`.
2. Check kubeconfig exec profile and target cluster.
3. Confirm endpoint network reachability.
4. Inspect EKS access entries/authentication mode.
5. Check EKS access policies and Kubernetes RBAC.
6. Review authenticator/audit logs.
7. Use break-glass access only through documented approval.

### B. Application cannot access S3/Secrets Manager

1. Identify the Pod's service account.
2. Check Pod Identity association or IRSA annotation.
3. Verify IAM trust policy and resource permissions.
4. Check Pod Identity Agent where applicable.
5. Inspect STS/CloudTrail errors.
6. Validate private networking/VPC endpoint connectivity.
7. Test least-privilege access and restore service.

### C. EKS upgrade causes service degradation

1. Pause further node/add-on rollouts.
2. Review Kubernetes Events and component health.
3. Compare pre/post-upgrade SLIs.
4. Check add-on versions and admission webhooks.
5. Confirm Pod IPs, CSI, DNS and ingress.
6. Revert workload changes where supported.
7. Escalate control-plane incompatibilities; plan recovery instead of downgrade.

## 16. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| kubectl Unauthorized | IAM/authentication/token | STS, kubeconfig, access entries |
| kubectl Forbidden | RBAC/access policy | `kubectl auth can-i` |
| Pod cannot access AWS API | Pod Identity/IRSA trust/permissions | Association, agent, CloudTrail |
| Secret decryption fails | KMS permissions or key state | KMS policy, audit |
| Audit logs missing | EKS log configuration/retention | Cluster logging, CloudWatch |
| Prometheus series absent | Scrape config/exporter | Targets and labels |
| Upgrade blocked | API deprecations, cluster health | EKS insights, webhooks, events |
| Nodes NotReady after upgrade | AMI, bootstrap, CNI | Node conditions and logs |
| CSI mount failures | Add-on/IAM/version mismatch | CSI logs, PVC Events |
| Ingress failures | Controller identity, webhook, API | Controller logs and target health |
| Upgrade rollback requested | Control-plane downgrade unsupported | Recovery/change plan |

## 17. Cost and governance considerations

```text
CloudWatch control-plane log ingestion and retention:
Container Insights / metrics ingestion:
Managed Prometheus/Grafana pricing:
CloudTrail trails and data events:
KMS key and API request charges:
Security scanning / vulnerability tooling:
Upgrade test cluster runtime:
Temporary duplicate node capacity:
Backup and cross-region recovery storage:
Owner / budget / alert threshold:
```

Production security and observability must be budgeted as operating requirements rather than treated as optional extras. Avoid hard-coded pricing because AWS rates and service configurations change.

## 18. Cleanup and evidence retention

For the isolated RBAC lab only:

```powershell
kubectl config current-context
kubectl -n ch079 get roles,rolebindings,serviceaccounts
kubectl delete namespace ch079
```

Do not delete production access entries, IAM roles, KMS keys, audit log groups, monitoring infrastructure or shared cluster resources as tutorial cleanup. Preserve audit evidence according to organizational retention policy.

## 19. Chapter acceptance checklist

- [ ] AWS account, cluster and kubeconfig identity verified.
- [ ] EKS authentication mode and access entries inventoried.
- [ ] Least-privilege Kubernetes RBAC reviewed.
- [ ] Namespace-scoped RBAC test performed or marked Not run.
- [ ] EKS Pod Identity and IRSA patterns compared.
- [ ] Secret, KMS, Pod security and network policy controls assessed.
- [ ] Control-plane and CloudTrail logging inventory completed.
- [ ] Cluster, node, workload, network and storage monitoring mapped.
- [ ] Actionable alerts and runbook ownership defined.
- [ ] Kubernetes version and add-on compatibility matrix created.
- [ ] Staged upgrade and rollback constraints documented.
- [ ] Security/upgrade incident tabletop completed.
- [ ] Cost and evidence retention controls reviewed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Amazon EKS Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Pod Identities](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Control Plane Logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [EKS Update Cluster](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS Kubernetes Versions](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS Best Practices — Security](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Kubernetes Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)

**Next:** Chapter 080 — EKS Production Operations Project (Part 16 final capstone).
