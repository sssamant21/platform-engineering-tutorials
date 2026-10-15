# Chapter 069 — EKS Security, Workload Identity, Observability and Upgrade Operations

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 14:** Amazon EKS  
**Chapter:** 069 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Cloud Security, Kubernetes Administrators and Incident Commanders

> **Safety:** All labs use a disposable staging cluster and synthetic credentials. Do not modify production access entries, delete system DaemonSets, rotate live credentials, disable admission enforcement or upgrade production clusters without approved change control. EKS control-plane minor-version downgrades are generally unsupported; design forward recovery before upgrades.

## 1. Learning objectives

By completing this chapter you will:

1. Apply defense in depth to AWS IAM, EKS authentication and Kubernetes RBAC.
2. Compare EKS access entries, IRSA and EKS Pod Identity.
3. Enforce Pod security, image verification, secrets protection and network boundaries.
4. Configure EKS control-plane logging, CloudTrail and workload observability.
5. Define SLOs and alerts for EKS API, nodes, add-ons and Argo CD.
6. Inventory Kubernetes API deprecations and add-on compatibility.
7. Execute controlled staging upgrade rehearsals and node rotation.
8. Investigate IAM failures, audit anomalies, telemetry gaps and failed upgrades.
9. Produce security and operational acceptance evidence.

## 2. Reference architecture

~~~text
AWS IAM Identity Center / federated roles
               |
         EKS access entries
               |
       Kubernetes RBAC + admission
               |
      Amazon EKS managed API
         /       |         \
   system Pods  app Pods   GitOps controllers
      |           |              |
 EKS add-ons  workload IAM     Argo CD
      |           |              |
 VPC CNI     IRSA/Pod Identity  approved Git MR
      |           |              |
 CloudWatch / Prometheus / CloudTrail
               |
     alerts, dashboards and SRE runbooks
               |
 staged EKS control-plane + add-on + node upgrades
~~~

AWS CloudTrail records relevant AWS API operations; Kubernetes audit logs provide Kubernetes API activity when EKS control-plane audit logging is enabled. They are complementary, not interchangeable.

## 3. Shared responsibility

| Layer | AWS responsibility | Platform responsibility |
| --- | --- | --- |
| EKS control plane | Managed API availability/infrastructure | Access, logging, versions, configuration |
| IAM | IAM service | Role trust, least privilege, lifecycle |
| Nodes | Managed node group orchestration | AMIs, workloads, security, rollout |
| Add-ons | Distribution/managed options | Compatibility, configuration, permissions |
| Network | VPC services | Routing, subnet IPs, SGs, network policy |
| Workloads | — | Image security, RBAC, secrets, observability |
| GitOps | — | AppProjects, credentials, review and rollback |

## 4. Security threat model

Evaluate:

- Compromised AWS SSO session or CI identity.
- Overprivileged cluster-admin access.
- Workload privilege escalation through Pod permissions.
- Misconfigured IRSA trust or Pod Identity association.
- Exposed instance metadata credentials.
- Unverified container images and vulnerable dependencies.
- Secrets in Git, CI logs or Kubernetes audit output.
- Unauthorized Argo CD AppProject changes.
- Insecure API endpoint exposure.
- Missing audit logs during a security incident.
- Upgrade failures caused by deprecated APIs or incompatible controllers.

Controls should be preventive, detective and recoverable.

## 5. EKS access entries and authentication

EKS access entries associate IAM principals with EKS cluster access. EKS access policies and Kubernetes RBAC are distinct authorization mechanisms.

~~~bash
aws sts get-caller-identity
aws eks describe-cluster --name demo-eks-staging --region us-east-1   --query 'cluster.accessConfig'
aws eks list-access-entries   --cluster-name demo-eks-staging --region us-east-1
~~~

Choose supported authentication mode deliberately. Migrating from legacy aws-auth ConfigMap must preserve node access and tested emergency administrator recovery. Access entries do not automatically grant all permissions; inspect associated access policies or Kubernetes groups.

## 6. Least-privilege Kubernetes RBAC

~~~yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: staging-observer
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
  name: staging-observer
  namespace: demo-staging
subjects:
  - kind: Group
    name: platform-staging-observers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: staging-observer
  apiGroup: rbac.authorization.k8s.io
~~~

The IAM-to-Kubernetes group mapping must be configured explicitly using the chosen EKS authentication mechanism. Avoid granting secrets read access to general observers.

~~~bash
kubectl auth can-i list pods -n demo-staging
kubectl auth can-i get secrets -n demo-staging
kubectl auth can-i --list -n demo-staging
~~~

## 7. IRSA architecture

IRSA uses an IAM OIDC provider and a Kubernetes ServiceAccount subject to authorize AWS role assumption via web identity. Review the trust policy's audience and exact namespace/ServiceAccount subject.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-s3-reader
  namespace: demo-staging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/demo-eks-staging-s3-reader
~~~

The ARN is illustrative. Restrict IAM to the required S3 bucket/prefix or API actions, and confirm the trust policy cannot be used by unrelated namespaces.

## 8. EKS Pod Identity architecture

EKS Pod Identity uses a cluster association among ServiceAccount, IAM role and the EKS Pod Identity agent. It is distinct from IRSA and uses a different IAM role trust relationship.

~~~bash
aws eks list-pod-identity-associations   --cluster-name demo-eks-staging   --region us-east-1
~~~

Review the Pod Identity agent health, association status, IAM trust and service availability. Not every controller supports every identity mode or EKS deployment configuration; verify the supported mechanism for the installed add-on.

## 9. Workload identity decision table

| Question | IRSA | EKS Pod Identity |
| --- | --- | --- |
| Requires cluster IAM OIDC provider | Yes | Not in the same IRSA model |
| Role binding | ServiceAccount annotation | EKS association |
| Trust policy | Federated OIDC subject | Pod Identity service principal |
| Agent dependency | No Pod Identity agent | Requires agent |
| Migration | Explicit identity redesign | Explicit association redesign |
| Recommended action | Verify installed controller support | Verify installed controller support |

Do not assume an IRSA annotation creates an EKS Pod Identity association. Both require scoped IAM policies and independent authorization tests.

## 10. IMDS and credential isolation

Reduce risk of Pods reaching EC2 instance-profile credentials. Review IMDSv2, hop limit, hostNetwork Pods, node role scope, CNI behavior and workload identity controls. A Kubernetes ServiceAccount token setting alone does not guarantee Pods cannot access instance metadata.

## 11. Pod security and admission

Use Pod Security Admission restricted/baseline policies where compatible, and apply native ValidatingAdmissionPolicy, Gatekeeper or Kyverno for organization-specific rules.

~~~bash
kubectl label namespace demo-staging   pod-security.kubernetes.io/warn=restricted   pod-security.kubernetes.io/audit=restricted   --overwrite
~~~

Start in warn/audit; validate system add-ons and workloads before enforcement. Require non-root, least capabilities, privilege-escalation restrictions, signed digest-pinned images and safe host access as appropriate.

## 12. Secrets and encryption

Use AWS Secrets Manager or SSM Parameter Store with scoped ESO workload identity, or approved encrypted Git workflows (SOPS/Sealed Secrets). Enable EKS Kubernetes Secret envelope encryption where supported/configured and EBS/EFS encryption at rest.

Encryption at rest does not replace Kubernetes RBAC, secret rotation or avoidance of plaintext in logs.

## 13. GitOps security boundaries

Use separate Argo CD AppProjects for privileged platform add-ons and application namespaces. Restrict source repositories, destination clusters/namespaces, permitted resource kinds and repository credentials.

Protect GitLab branches, enforce CODEOWNERS review and require signed/digest-pinned images. CI should open reviewed GitOps MRs rather than receiving cluster-admin kubeconfig.

## 14. EKS control-plane logging

EKS can export control-plane log types such as api, audit, authenticator, controllerManager and scheduler to CloudWatch Logs.

~~~bash
aws eks describe-cluster --name demo-eks-staging --region us-east-1   --query 'cluster.logging.clusterLogging'

aws logs describe-log-groups   --log-group-name-prefix /aws/eks/demo-eks-staging
~~~

Enable appropriate log categories using approved Terraform or AWS configuration. Configure retention, access control, encryption and cost budgets. Audit logs may contain sensitive metadata and must not be made public.

## 15. CloudTrail and AWS API audit

CloudTrail provides evidence for EKS, IAM, EC2, KMS and other AWS API activity. Correlate AWS API calls with Kubernetes audit logs, Argo CD revisions and GitLab change records.

Investigate suspicious events such as new EKS access entries, changes to IAM role trust, security group exposure, KMS key policy modifications and unapproved node provisioning.

## 16. Metrics and logs architecture

~~~text
EKS control-plane logs -> CloudWatch Logs -> security/SRE analytics
AWS API activity -> CloudTrail -> central audit archive
kube-state-metrics -> Prometheus -> Grafana/alerts
node exporter/kubelet -> Prometheus -> capacity dashboards
VPC CNI/CoreDNS/CSI -> logs + metrics -> platform dashboards
Argo CD -> metrics/events -> deployment health alerts
Applications -> OpenTelemetry/logs -> service SLO dashboards
~~~

Metrics names and availability vary by add-on versions. Discover real series before deploying alert rules.

## 17. Suggested EKS SLOs

| Service | Indicator | Example objective |
| --- | --- | --- |
| Kubernetes API | Successful authorized requests | Define from critical client probes |
| Pod scheduling | Time Pending to scheduled | Target by workload tier |
| CoreDNS | DNS success and latency | Alert on sustained errors |
| CNI | Pod IP allocation success | No sustained allocation failures |
| Nodes | Ready capacity | Maintain N+1 capacity |
| Argo CD | Reconciliation freshness | Detect stale/failed sync |
| Workload identity | Authorized token/role use | No unexplained AccessDenied |
| Storage | PVC provision/attach latency | Alert on abnormal tail latency |

Avoid claiming universal numerical SLOs; derive targets from application availability and recovery requirements.

## 18. Alerting and dashboards

At minimum alert on:

- EKS API access or audit log ingestion failure.
- Node NotReady and critical system Pod unavailable.
- CoreDNS saturation and sustained SERVFAIL.
- VPC CNI IP exhaustion and network allocation failures.
- EBS CSI provisioning/attach errors.
- AWS Load Balancer Controller reconciliation failures.
- Argo CD Application Degraded/OutOfSync beyond grace period.
- Unusual IAM AccessDenied and role assumption anomalies.
- Expiring certificates, secrets and key rotation deadlines.
- Kubernetes deprecated API usage before planned upgrade.

Route alerts by ownership, severity and runbook. Avoid paging on every transient Pod restart.

## 19. Upgrade strategy

EKS upgrade planning includes:

1. Review AWS-supported Kubernetes versions and support windows.
2. Inventory deprecated APIs and admission webhooks.
3. Check compatibility of VPC CNI, CoreDNS, kube-proxy, EBS CSI, ALB Controller, Karpenter and Argo CD.
4. Validate workload manifests, CRDs and Helm charts.
5. Confirm backups and tested restore.
6. Upgrade staging control plane one supported minor version at a time.
7. Update managed add-ons in a compatible order.
8. Rotate managed node groups or Karpenter AMIs.
9. Run application and platform smoke tests.
10. Approve production rollout after staging evidence.

**Critical:** Kubernetes control-plane minor-version downgrade is not generally supported in EKS. A failed upgrade needs forward remediation or a separately planned replacement-cluster migration.

## 20. Version and add-on inventory

~~~bash
aws eks describe-cluster --name demo-eks-staging --region us-east-1   --query 'cluster.version'
aws eks list-addons --cluster-name demo-eks-staging --region us-east-1
aws eks list-nodegroups --cluster-name demo-eks-staging --region us-east-1
kubectl version
kubectl get nodes -o custom-columns=NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion
kubectl get apiservices
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
~~~

Use AWS EKS upgrade insights where supported to identify deprecated API use and upgrade blockers. Review current AWS compatibility documentation rather than hard-coding a version matrix in a long-lived tutorial.

## 21. Managed node group upgrade

Use a controlled node rotation strategy with PodDisruptionBudgets, topology spread, capacity headroom, readiness probes and validated workload rollback. Managed node group upgrades may drain nodes and can fail when Pods cannot be evicted.

Karpenter node replacement uses NodePool/EC2NodeClass drift and disruption controls. Do not assume the same update process applies to both managed groups and Karpenter-managed nodes.

## 22. Add-on upgrade order and dependencies

Upgrade sequencing is compatibility-dependent. Ensure VPC CNI and kube-proxy/CoreDNS versions remain supported for the target Kubernetes release, and validate storage/ingress controllers before updating workloads that depend on them.

Avoid simultaneous cluster, CNI, CSI, Karpenter and Argo CD upgrades. Isolate changes so rollback or forward repair remains diagnosable.

## 23. Terraform and GitOps ownership

Terraform should own EKS infrastructure, IAM, core networking and selected managed add-ons. Argo CD should own approved Kubernetes add-ons and applications. If ownership is delegated, document a handoff to prevent Terraform and Argo CD from repeatedly overwriting the same resource.

Use protected MRs for both infrastructure and GitOps changes; require a plan diff and security review for IAM or network modifications.

## 24. GitLab upgrade validation pipeline

~~~yaml
stages: [validate, compatibility, approval]

validate:
  stage: validate
  image: registry.example.internal/ci/kubernetes-tools:PINNED_DIGEST
  script:
    - ./ci/validate-kubernetes-manifests.sh
    - ./ci/check-deprecated-apis.sh

compatibility:
  stage: compatibility
  image: registry.example.internal/ci/aws-tools:PINNED_DIGEST
  script:
    - ./ci/check-eks-addon-compatibility.sh
    - ./ci/check-karpenter-argocd-compatibility.sh

approval_report:
  stage: approval
  image: registry.example.internal/ci/report-tools:PINNED_DIGEST
  script:
    - ./ci/generate-upgrade-readiness-report.sh
~~~

All images/scripts are placeholders requiring approved implementation. This pipeline validates readiness; it does not authorize a production control-plane upgrade without independent change approval.

## 25. Lab A — EKS security inventory

1. Verify AWS account, cluster, region and endpoint mode.
2. Inventory EKS access entries and cluster authentication mode.
3. Review API public access CIDRs and private connectivity.
4. Inventory node IAM roles and system ServiceAccounts.
5. Record admission policies and audit logging.
6. Identify least-privilege gaps.

**Pass:** security boundaries and privileged identities are documented.

## 26. Lab B — Access entry and RBAC denial

1. Create a staging read-only IAM principal through approved IaC.
2. Map it using an EKS access entry or supported Kubernetes group.
3. Confirm permitted Pod read access.
4. Attempt unauthorized Secret read or namespace modification.
5. Verify denial and audit event.
6. Revoke test access.

**Pass:** authorization is limited to intended operations.

## 27. Lab C — IRSA workload identity

1. Create a staging IAM role with scoped read-only AWS permissions.
2. Configure OIDC trust for exact ServiceAccount subject.
3. Annotate synthetic test ServiceAccount.
4. Verify authorized AWS read.
5. Attempt unauthorized action and verify AccessDenied.
6. Inspect CloudTrail evidence.

**Pass:** no static AWS credentials and trust is namespace-specific.

## 28. Lab D — EKS Pod Identity

1. Verify Pod Identity agent availability.
2. Create a staging-only IAM role and association.
3. Run a synthetic workload using the associated ServiceAccount.
4. Test authorized AWS API operation.
5. Verify unrelated ServiceAccount cannot use role.
6. Remove association after lab.

**Pass:** association and least privilege are enforced.

## 29. Lab E — Pod security and admission

1. Enable restricted Pod Security Admission warnings in staging.
2. Test compliant non-root Pod.
3. Test privileged or hostNetwork Pod using dry-run.
4. Review admission warnings.
5. Add policy-as-code tests.
6. Enforce only in approved disposable namespace.

**Pass:** risky Pod settings are detected without impacting system components.

## 30. Lab F — Secret exposure prevention

1. Configure synthetic ExternalSecret or encrypted Git secret.
2. Verify only intended workload can consume it.
3. Confirm GitLab logs and Argo CD manifests do not print plaintext.
4. Test unauthorized Kubernetes Secret read.
5. Rotate synthetic credential.
6. Verify application reload behavior.

**Pass:** secrets remain scoped and rotation is observable.

## 31. Lab G — Control-plane audit logs

1. Enable EKS audit/authenticator logs in staging.
2. Generate a synthetic permitted and denied Kubernetes API request.
3. Locate corresponding CloudWatch log events.
4. Verify retention and access controls.
5. Correlate timestamps with GitLab and Argo CD.
6. Record evidence without exposing tokens.

**Pass:** API access decisions can be reconstructed.

## 32. Lab H — CloudTrail IAM anomaly

1. Perform a scoped staging IAM operation.
2. Locate its CloudTrail record.
3. Test alert detection for unauthorized role/trust changes in a safe simulation.
4. Validate event delivery latency.
5. Confirm incident owner receives alert.
6. Record audit trail.

**Pass:** sensitive AWS IAM changes are detectable.

## 33. Lab I — Prometheus/Grafana platform dashboards

1. Deploy approved metrics collectors.
2. Verify kube-state-metrics, node and controller targets.
3. Build node readiness, Pod Pending and Argo CD dashboards.
4. Generate a synthetic failure.
5. Confirm alert and dashboard correlation.
6. Review label cardinality and retention.

**Pass:** failure is visible through monitoring without manual kubectl polling.

## 34. Lab J — Workload identity failure injection

1. Temporarily remove one staging-only IAM permission.
2. Run an authorized-operation test that now fails.
3. Inspect workload logs, IAM trust and CloudTrail.
4. Restore only the required permission.
5. Verify recovery.
6. Document failure signatures.

**Pass:** IAM AccessDenied is resolved without granting administrator permissions.

## 35. Lab K — Deprecated API detection

1. Inventory workload manifests and installed CRDs.
2. Run schema/deprecation scanners for the target EKS version.
3. Inspect EKS upgrade insights where available.
4. Introduce a synthetic deprecated API manifest fixture.
5. Verify CI rejects it.
6. Replace with supported API and rerun.

**Pass:** deprecated API usage is caught before cluster upgrade.

## 36. Lab L — Managed add-on compatibility

1. Inventory VPC CNI, CoreDNS, kube-proxy, EBS CSI and ALB Controller.
2. Check target Kubernetes compatibility.
3. Pin tested add-on versions.
4. Upgrade one disposable staging add-on at a time.
5. Validate DNS, networking, storage and ingress.
6. Record rollback/forward-repair plan.

**Pass:** no incompatible add-on remains after upgrade.

## 37. Lab M — Managed node group rolling upgrade

1. Verify application replicas, PDBs and capacity headroom.
2. Create approved node group update.
3. Observe cordon/drain and replacement nodes.
4. Validate new kubelet/AMI versions.
5. Confirm service health and storage mounts.
6. Record upgrade duration and disruption.

**Pass:** workload SLO remains within staging target.

## 38. Lab N — EKS control-plane upgrade rehearsal

1. Confirm supported target version and upgrade insights.
2. Verify backups, admission webhooks and add-on compatibility.
3. Approve staging control-plane upgrade.
4. Monitor AWS EKS update status.
5. Upgrade compatible add-ons/nodes as planned.
6. Validate GitOps, DNS, CNI, storage, ingress and application health.
7. Record forward-recovery procedures.

**Pass:** staging upgrade completes without unresolved blockers.

## 39. Lab O — Security incident and recovery capstone

1. Simulate a staging IAM trust misconfiguration.
2. Confirm workload identity failures and audit alerting.
3. Simulate a separate Argo CD policy denial.
4. Correlate AWS and Kubernetes evidence.
5. Restore IAM and reviewed GitOps policy.
6. Verify workload readiness and security controls.
7. Measure detection/recovery time.

**Pass:** the incident is diagnosable, recoverable and auditable.

## 40. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | kubectl Unauthorized | Wrong IAM identity/access entry | Verify caller and mapping |
| 2 | kubectl Forbidden | Kubernetes RBAC | Correct scoped RoleBinding |
| 3 | EKS access entry missing | IaC drift/auth mode | Restore approved entry |
| 4 | IRSA AccessDenied | OIDC trust/audience/subject | Correct exact trust |
| 5 | Pod Identity credentials unavailable | Agent/association/trust | Inspect agent and association |
| 6 | Pod reaches node IAM role | IMDS exposure | Restrict node/Pod access |
| 7 | Privileged Pod accepted | PSA/policy scope gap | Fix enforcement and test |
| 8 | Argo CD sync denied | Admission policy | Correct GitOps manifest |
| 9 | EKS audit logs missing | Log type disabled/permissions | Restore logging pipeline |
| 10 | CloudTrail event not found | Wrong account/region/delay | Check trail and event source |
| 11 | Prometheus target down | Service discovery/network | Restore scrape reachability |
| 12 | Alert storm | Noisy threshold/cardinality | Tune rules and ownership |
| 13 | Upgrade blocked | Deprecated APIs | Migrate APIs before retry |
| 14 | Add-on crash after upgrade | Version/config mismatch | Restore compatible release |
| 15 | Managed node upgrade stalls | PDB or capacity | Restore headroom/evictions |
| 16 | Karpenter nodes churn | AMI drift/disruption | Review NodePool budgets |
| 17 | EBS fails after upgrade | CSI mismatch/IAM | Repair driver and topology |
| 18 | Workload degraded after upgrade | Runtime/API incompatibility | Forward repair or migrate |

## 41. Production runbook — IAM and access incident

1. Identify affected IAM principal, EKS access entry and Kubernetes namespace.
2. Confirm caller identity, authentication mode and role trust.
3. Inspect EKS access policy associations and Kubernetes RBAC.
4. Correlate CloudTrail and Kubernetes audit events.
5. Restore least-privilege access through approved IaC.
6. Validate authorized operations and denied excessive permissions.
7. Record access impact and incident evidence.

## 42. Production runbook — workload identity failure

1. Identify affected ServiceAccount, namespace and AWS API.
2. Determine whether IRSA or Pod Identity is in use.
3. Validate OIDC trust or Pod Identity association and agent.
4. Check IAM policy, KMS permissions and STS connectivity.
5. Restore only required permission or trust.
6. Validate workload functionality and CloudTrail.
7. Record blast radius and preventive tests.

## 43. Production runbook — missing audit/telemetry

1. Determine which log stream or metric source is missing.
2. Check EKS control-plane log configuration, collector health and IAM.
3. Verify CloudWatch ingestion, retention and encryption.
4. Check Prometheus scrape targets and alert evaluation.
5. Restore pipeline without exposing sensitive data.
6. Test a synthetic event and measure delivery delay.
7. Document any audit coverage gap.

## 44. Production runbook — failed EKS upgrade

1. Freeze concurrent platform and workload changes.
2. Identify EKS update phase and failed component.
3. Inspect AWS update status, control-plane health and compatibility.
4. Restore add-on/controller compatibility and node capacity.
5. Address deprecated API and admission webhook blockers.
6. Validate critical workloads and Argo CD reconciliation.
7. Plan forward remediation or blue/green replacement cluster if needed.
8. Record impact, evidence and follow-up; do not assume control-plane downgrade.

## 45. Production runbook — node rollout disruption

1. Identify impacted node group, AZs, Pods and PDBs.
2. Check available capacity and pending replacement nodes.
3. Inspect drain events and application readiness.
4. Pause further approved node rollout if SLO is threatened.
5. Restore capacity or correct PDB/topology constraints.
6. Validate stateful volume attachments and application consistency.
7. Resume rollout only after stability checks.

## 46. Evidence template

~~~text
Change / incident ID:
AWS account, region and EKS cluster:
Control-plane and node versions:
EKS access entries and IAM principal:
IRSA/Pod Identity association:
RBAC and admission policy revision:
EKS control-plane log categories:
CloudTrail event references:
Prometheus targets and alerts:
Add-on version compatibility:
Deprecated API scan result:
GitLab/Argo CD revision:
Upgrade and node rotation duration:
Observed application SLO:
Recovery path and owner:
Audit archive:
~~~

## 47. Scored operational assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| EKS access, IAM and RBAC | 20 | Scoped access and denial tests |
| Workload identity and secret security | 20 | IRSA/Pod Identity, rotation |
| Pod security and GitOps controls | 15 | Admission and reviewed MR |
| Logging, monitoring and incident response | 20 | Audit events and alerts |
| Upgrade compatibility and recovery | 20 | Rehearsal and node rotation |
| Evidence and ownership | 5 | Complete audit packet |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: uncontrolled cluster-admin, unauthorized secret access, absent incident audit trail, unsigned image admission in enforced scope, or unsupported upgrade without a recovery plan.

## 48. Final acceptance checklist

- [ ] EKS access entries and Kubernetes RBAC reviewed.
- [ ] Break-glass access is tested and audited.
- [ ] IRSA/Pod Identity roles follow least privilege.
- [ ] Pod IMDS exposure and node IAM scope reviewed.
- [ ] Pod Security Admission and policy enforcement tested.
- [ ] Secret encryption, access and rotation verified.
- [ ] EKS control-plane logs and CloudTrail operational.
- [ ] Prometheus/Grafana and alerts cover critical services.
- [ ] Deprecated API scan and compatibility matrix approved.
- [ ] EKS control-plane staging upgrade rehearsed.
- [ ] Managed node and Karpenter rotation plans validated.
- [ ] GitOps security and change governance enforced.
- [ ] Fifteen hands-on labs have evidence.
- [ ] Five production runbooks reviewed.

## 49. Knowledge check

1. How do EKS access entries and Kubernetes RBAC differ?
2. Why is IRSA trust scoped to a namespace and ServiceAccount?
3. What additional component does EKS Pod Identity use?
4. Why can a Pod still access node IAM credentials if IMDS is exposed?
5. What is the difference between CloudTrail and Kubernetes audit logs?
6. Why must NetworkPolicy and admission controls be tested?
7. Which EKS components need compatibility checks before upgrade?
8. Why is control-plane downgrade not a standard EKS recovery method?
9. How can PDBs block a managed node group upgrade?
10. What evidence demonstrates successful security and upgrade readiness?

## 50. References

- [Amazon EKS Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS Control Plane Logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [EKS Kubernetes Version Upgrades](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS Add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 069 complete.** Next: **Chapter 070 — EKS Enterprise GitOps Production Operations and Disaster Recovery Capstone**, completing Part 14.