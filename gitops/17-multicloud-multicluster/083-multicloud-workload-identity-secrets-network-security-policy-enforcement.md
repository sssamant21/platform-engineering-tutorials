# Chapter 083 — Multi-Cloud Workload Identity, Secrets, Network Security and Policy Enforcement

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 17:** Multi-Cloud and Multi-Cluster GitOps  
**Chapter:** 083 / 100  
**Audience:** SREs, Platform Engineers, Cloud Security Engineers, DevSecOps and Incident Commanders

> **Safety:** Use isolated EKS, AKS and GKE staging clusters, synthetic secrets, temporary identities and approved budgets. Do not revoke live identities, rotate production secrets, alter shared network routes or enable untested deny-all policies. Enforce controls only after positive and negative tests and a documented rollback path.

## 1. Learning objectives

1. Compare EKS Pod Identity/IRSA, Microsoft Entra Workload ID and Workload Identity Federation for GKE.
2. Configure scoped trust without long-lived cloud credentials.
3. Separate cloud IAM, Kubernetes RBAC, admission and network enforcement.
4. Integrate AWS Secrets Manager, Azure Key Vault and Google Secret Manager.
5. Design secret rotation, reload, audit and break-glass workflows.
6. Enforce Kubernetes NetworkPolicy with verified provider-specific dataplanes.
7. Apply Pod Security Admission, image trust and policy-as-code.
8. Secure GitLab OIDC federation and Argo CD AppProjects.
9. Audit identity and policy failures across providers.
10. Run safe multi-cloud security incident recovery.

## 2. Security architecture

~~~text
Protected GitLab MR / OIDC
            |
      signed artifact digest
            |
       Argo CD AppProjects
            |
   per-cluster RBAC + admission
       /        |        \
      EKS      AKS       GKE
       |        |         |
 Pod Identity  Entra    GKE WIF
    / IRSA   Workload ID
       |        |         |
 AWS Secrets Azure Key  Google Secret
  Manager     Vault       Manager
       \        |         /
         scoped workload APIs
                  |
      NetworkPolicy + ingress
                  |
        cloud audit + SRE alerts
~~~

The same security *intent* should apply to every provider, but IAM principals, network enforcement, CSI drivers, audit categories and controller annotations are provider-specific.

## 3. Trust boundaries

Define separate roles for human operators, GitLab CI, Argo CD controllers, node identities, Kubernetes ServiceAccounts and applications. A role that builds images should not automatically administer clusters or read production secrets.

Record who may create service accounts, bind cloud identities, edit admission policies, mutate cluster registrations, approve GitOps changes and invoke break-glass.

## 4. Provider identity comparison

| Provider | Recommended workload mechanism | Trust detail |
| --- | --- | --- |
| Amazon EKS | EKS Pod Identity or IRSA | IAM role association or OIDC trust for KSA |
| Azure AKS | Microsoft Entra Workload ID | Federated identity credential subject/audience |
| Google GKE | Workload Identity Federation for GKE | Workload principal or IAM service account impersonation |

Select the supported mechanism for each cluster version and operating model. Do not assume the same Kubernetes annotation or token audience works across providers.

## 5. EKS IRSA

IRSA maps a Kubernetes ServiceAccount to an IAM role using an OIDC trust policy. The role trust must match the cluster's OIDC issuer and exact namespace/service account subject.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/demo-staging-reader
~~~

The annotation alone does not grant access: configure the correct IAM OIDC provider, trust conditions and scoped permissions. Use an SDK credential chain that supports web identity.

## 6. EKS Pod Identity

EKS Pod Identity uses supported Pod Identity associations and agent components to deliver credentials for associated Pods. It has different prerequisites and trust configuration from IRSA.

~~~bash
aws eks list-pod-identity-associations \
  --cluster-name eks-staging --region AWS_REGION
aws eks describe-cluster \
  --name eks-staging --region AWS_REGION \
  --query 'cluster.identity'
~~~

Check add-on/agent availability, node compatibility, AWS SDK support, IAM role association and network access to the relevant AWS endpoints.

## 7. AKS Microsoft Entra Workload ID

AKS Workload ID uses OIDC federation and a Microsoft Entra federated identity credential. The subject typically identifies the namespace and Kubernetes ServiceAccount.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
  annotations:
    azure.workload.identity/client-id: "REPLACE_WITH_CLIENT_ID"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-reader
  namespace: demo-staging
spec:
  replicas: 1
  selector:
    matchLabels: {app: demo-reader}
  template:
    metadata:
      labels:
        app: demo-reader
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: demo-reader
      containers:
        - name: app
          image: REGISTRY/demo@sha256:REPLACE_WITH_REAL_DIGEST
~~~

Validate OIDC issuer, subject, audience, workload identity webhook and Azure SDK support. A valid client ID does not substitute for Key Vault or resource-level RBAC.

## 8. GKE Workload Identity Federation

GKE workload principals can access supported Google Cloud resources directly through IAM, or impersonate a dedicated IAM service account using a scoped binding and KSA annotation.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-reader
  namespace: demo-staging
  annotations:
    iam.gke.io/gcp-service-account: demo-reader@PROJECT_ID.iam.gserviceaccount.com
~~~

This annotation is only for the IAM service account impersonation pattern; direct workload principal access does not require it. Verify node pool support in GKE Standard.

## 9. Identity contract

Every workload identity must declare:

~~~yaml
workload:
  name: demo-reader
  namespace: demo-staging
  cluster: eks-staging
  provider: aws
  cloudResource: synthetic-secret
  permissions: [read]
  rotationOwner: platform-security
  expiresReview: quarterly
~~~

This is governance metadata, not an API object. Validate cluster, namespace, service account, role, trust subject and approved cloud resources before provisioning.

## 10. Least-privilege Kubernetes RBAC

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
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-observer
  namespace: demo-staging
subjects:
  - kind: ServiceAccount
    name: demo-operator
    namespace: demo-staging
roleRef:
  kind: Role
  name: app-observer
  apiGroup: rbac.authorization.k8s.io
~~~

This does not permit reading Kubernetes Secrets. Cloud IAM permission and Kubernetes RBAC are separate controls.

## 11. Secret backends

| Provider | Service | Key consideration |
| --- | --- | --- |
| AWS | Secrets Manager | IAM resource policy, KMS and rotation |
| Azure | Key Vault | Azure RBAC/access model, network ACL and private endpoint |
| Google Cloud | Secret Manager | IAM resource scope, audit and rotation |

Choose approved CSI or external-secret integration and confirm driver/API versions. Secrets synced into Kubernetes Secrets inherit etcd, RBAC and backup risks.

## 12. CSI and External Secrets

Secrets Store CSI Driver, cloud-specific CSI providers and External Secrets Operator can solve different use cases. A mounted secret is not automatically reloaded by the application; a synced Kubernetes Secret is not automatically updated in every container process.

Document rotation latency, error handling, caching, filesystem permissions, Pod restart strategy and audit coverage.

## 13. Secret rotation contract

~~~text
Create new secret version
        |
Validate access for approved workload
        |
Stage workload reload
        |
Promote active version
        |
Verify positive/negative calls
        |
Revoke old version after grace period
        |
Audit and close change
~~~

Never delete an old version until dependent workloads and rollback requirements have been verified.

## 14. GitLab OIDC federation

Configure provider-specific federation from protected GitLab jobs with exact issuer, audience, subject and branch/environment conditions.

~~~text
GitLab protected pipeline
   |
short-lived OIDC token
   |
AWS / Azure / Google identity federation
   |
scoped registry or IaC permissions
~~~

Avoid cloud access keys, Azure client secrets and Google service account JSON keys in CI. Prevent untrusted merge requests from obtaining production identities.

## 15. Argo CD AppProject restrictions

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: staging-apps
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.com/platform/gitops.git
  destinations:
    - namespace: demo-staging
      name: eks-staging
    - namespace: demo-staging
      name: aks-staging
    - namespace: demo-staging
      name: gke-staging
  clusterResourceWhitelist: []
~~~

Verify registered destination names. Restrict who can edit AppProjects and cluster registration Secrets; AppProject alone is not a complete authorization boundary.

## 16. NetworkPolicy semantics

NetworkPolicy requires a capable, enabled network implementation. Standard Kubernetes NetworkPolicy defines Pod ingress/egress behavior but does not itself provide universal DNS FQDN rules or cloud firewall enforcement.

~~~yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: demo-staging
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: frontend}
      ports:
        - protocol: TCP
          port: 8080
~~~

Test both allowed and denied traffic. For egress default-deny, explicitly allow required DNS, identity, metrics and secret endpoints.

## 17. Provider dataplane considerations

EKS network policy depends on installed CNI/policy engine and supported configuration. AKS uses supported Azure/Cilium network policy modes depending on cluster setup. GKE Dataplane V2 has provider-specific behavior.

Never copy a provider-specific Cilium, Calico or cloud firewall policy blindly across clouds. Standardize security objectives and verify enforcement locally.

## 18. Cloud network boundaries

Design VPC/VNet subnets, private endpoints, NAT, firewall, ingress and DNS independently. Avoid broad public API exposure for GitOps convenience.

Secrets Manager, Key Vault and Secret Manager endpoints may need explicit private networking, DNS or egress allowance. Diagnose network failure separately from IAM denial.

## 19. Pod Security Admission

~~~bash
kubectl label namespace demo-staging \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted \
  --overwrite
~~~

Start with audit/warn and test workloads before enforcement. Validate compatibility with CSI, monitoring, sidecars and required Linux capabilities.

## 20. Image provenance and admission

Build once, generate SBOM, sign immutable digest and enforce policy with supported admission tooling. AWS, Azure and Google may offer different native enforcement capabilities; use tested controls and documented exceptions.

A signed image is not necessarily admitted unless policy checks the signature and approved issuer/identity.

## 21. Policy-as-code contract

Common policy requirements should include restricted privilege, trusted registries, signed digests, scoped ServiceAccounts, namespace quotas, network isolation, secret delivery rules and protected storage.

Use Kyverno, Gatekeeper/Policy Controller or approved alternatives according to installed platform. Test deny, audit and exceptions before enforcing.

## 22. Cross-cloud audit strategy

Collect AWS CloudTrail and EKS audit logs, Azure Activity/diagnostic logs and AKS audit logs, and Google Cloud Audit Logs and GKE audit logs. Distinguish cloud control-plane actions from Kubernetes API actions.

Normalize fields for cluster ID, provider, environment, principal, resource, action, result, timestamp and change ID. Respect residency and retention requirements.

## 23. Observability and alerts

Monitor identity token failures, 403/AccessDenied, secret CSI mount errors, secret rotation lag, policy denials, network drops, registry pull failures, Argo CD sync errors and unusual privilege grants.

Use synthetic authorized/unauthorized tests to validate alert coverage. Avoid logging credentials or secret values.

## 24. Incident response and break-glass

Emergency access must be time-limited, approved, audited and revoked after recovery. Separate IAM lockout, Kubernetes RBAC denial, network outage and admission rejection during triage.

Do not grant cluster-admin or broad cloud Owner roles as a default workaround.

## 25. Multi-cloud threat model

| Threat | Prevention | Detection | Recovery |
| --- | --- | --- | --- |
| Stolen static credential | Federation, no keys | IAM audit | Revoke trust |
| Namespace privilege escalation | RBAC, admission | Kubernetes audit | Remove binding |
| Secret exfiltration | Scoped IAM, private egress | Secret access audit | Rotate/revoke |
| Lateral movement | NetworkPolicy | Flow logs/policy events | Isolate workload |
| Untrusted image | Signature admission | Admission logs | Revert digest |
| GitOps privilege escalation | Protected MRs, AppProjects | Audit and diff | Restore policy |
| Cross-cloud blast radius | Per-cluster identities | Fleet telemetry | Revoke scoped access |

## 26. Lab A — Security baseline

1. Inventory EKS, AKS and GKE staging clusters.
2. Record identity mechanism and Kubernetes RBAC.
3. Inspect secret drivers, admission and network policy.
4. Review cloud audit coverage.
5. Verify no production context is active.
6. Archive redacted baseline.

**Pass:** security posture is documented.

## 27. Lab B — EKS IRSA

1. Create synthetic KSA and scoped IAM role.
2. Configure exact OIDC trust.
3. Deploy synthetic reader.
4. Verify allowed Secrets Manager read.
5. Verify denied write and wrong KSA.
6. Remove test role binding.

**Pass:** IRSA works without static AWS keys.

## 28. Lab C — EKS Pod Identity

1. Confirm supported cluster and agent.
2. Create scoped Pod Identity association.
3. Deploy supported SDK workload.
4. Verify allowed synthetic API read.
5. Verify unrelated KSA denial.
6. Remove association.

**Pass:** association trust is explicit.

## 29. Lab D — AKS Workload ID

1. Verify AKS OIDC issuer and workload identity support.
2. Create Entra federated identity credential.
3. Annotate KSA and label Pod.
4. Grant scoped Key Vault access.
5. Verify allowed read and denied write.
6. Revoke test federation.

**Pass:** AKS identity uses short-lived tokens.

## 30. Lab E — GKE WIF

1. Inspect GKE workload pool and node support.
2. Create synthetic KSA.
3. Grant exact workload principal resource read.
4. Verify authorized Google Secret Manager access.
5. Verify unauthorized KSA denial.
6. Remove IAM binding.

**Pass:** GKE workload trust is scoped.

## 31. Lab F — Secret CSI mounting

1. Verify supported driver and provider.
2. Create synthetic secret.
3. Mount in disposable Pod.
4. Verify filesystem permissions.
5. Deny unrelated workload access.
6. Remove disposable mount.

**Pass:** only intended workload sees secret.

## 32. Lab G — Secret rotation

1. Create synthetic secret version.
2. Read from approved workload.
3. Rotate to new version.
4. Measure reload latency.
5. Verify old version retirement safely.
6. Check audit logs for secret exposure.

**Pass:** rotation and rollback are documented.

## 33. Lab H — GitLab federation

1. Configure protected GitLab OIDC job.
2. Federate to scoped cloud role.
3. Perform permitted registry operation.
4. Attempt unprotected branch access.
5. Verify denial.
6. Remove test grants.

**Pass:** CI has no persistent cloud key.

## 34. Lab I — Kubernetes RBAC

1. Create namespace observer Role.
2. Bind synthetic operator KSA.
3. Verify Pod list allowed.
4. Verify Secret read denied.
5. Verify cluster-scoped mutation denied.
6. Revoke binding.

**Pass:** Kubernetes permissions are least-privileged.

## 35. Lab J — NetworkPolicy positive/negative

1. Verify provider network policy enforcement.
2. Deploy frontend, API and unauthorized client.
3. Apply ingress policy.
4. Verify frontend success.
5. Verify unauthorized client denial.
6. Restore baseline.

**Pass:** isolation is actually enforced.

## 36. Lab K — Egress and secret endpoint

1. Apply disposable default-deny egress policy.
2. Observe denied synthetic secret API call.
3. Add narrow required DNS/endpoint allowance.
4. Verify authorized access.
5. Verify unrelated egress remains denied.
6. Revert test policy.

**Pass:** identity access and network egress are independently controlled.

## 37. Lab L — Pod Security Admission

1. Enable restricted warn/audit labels.
2. Deploy compliant non-root Pod.
3. Dry-run privileged Pod.
4. Review admission warnings.
5. Enforce in disposable namespace.
6. Verify denial and restore baseline.

**Pass:** Pod security is enforced without platform disruption.

## 38. Lab M — Image trust policy

1. Build synthetic image and sign digest.
2. Configure supported admission policy.
3. Deploy trusted digest.
4. Attempt unsigned synthetic digest.
5. Verify denial.
6. Record policy and attestation evidence.

**Pass:** trust policy prevents unauthorized deployment.

## 39. Lab N — Cross-cloud audit and alerts

1. Generate approved IAM access event in each provider.
2. Generate denied secret access event.
3. Locate cloud and Kubernetes audit records.
4. Normalize cluster/provider/principal metadata.
5. Trigger synthetic security alert.
6. Verify incident routing.

**Pass:** security events are attributable.

## 40. Lab O — Security incident capstone

1. Simulate wrong workload identity binding in one staging cluster.
2. Simulate separate network policy denial.
3. Correlate IAM, audit, Kubernetes events and Argo CD.
4. Restore scoped trust and reviewed policy.
5. Verify positive and negative tests.
6. Produce incident RCA and prevention actions.

**Pass:** recovery does not widen privileges.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | EKS IRSA AccessDenied | Wrong OIDC subject/trust | Repair exact trust |
| 2 | EKS Pod Identity unavailable | Agent/association | Inspect prerequisites |
| 3 | AKS token exchange fails | Issuer/audience/subject | Correct federation |
| 4 | AKS Key Vault 403 | Azure RBAC/network | Restore scoped access |
| 5 | GKE WIF denied | Principal/pool/IAM | Repair binding |
| 6 | GKE impersonation denied | Missing KSA binding | Correct trust |
| 7 | CSI secret mount fails | Driver/permissions | Inspect CSI |
| 8 | Secret rotation stale | App reload/cache | Repair refresh |
| 9 | GitLab OIDC denied | Claim restriction | Verify protected job |
| 10 | Kubernetes API Forbidden | RBAC | Correct scoped Role |
| 11 | NetworkPolicy ignored | Enforcement unavailable | Verify dataplane |
| 12 | DNS fails after default-deny | Missing egress rule | Allow DNS narrowly |
| 13 | Secret API timeout | Private endpoint/egress | Repair network |
| 14 | Pod rejected | Pod Security Admission | Make workload compliant |
| 15 | Signed image rejected | Signature/policy mismatch | Verify attestation |
| 16 | Argo CD sync denied | AppProject/admission | Review scope |
| 17 | Missing audit events | Log configuration | Restore collection |
| 18 | Unauthorized access persists | Stale trust/credential | Revoke and verify |

## 42. Runbook — cloud workload identity failure

1. Identify cluster, namespace, KSA and cloud resource.
2. Determine IRSA/Pod Identity, Entra Workload ID or GKE WIF.
3. Inspect exact trust subject, issuer and audience.
4. Verify scoped IAM permission and SDK support.
5. Restore correct binding without static keys.
6. Test allowed and denied calls.
7. Preserve audit evidence.

## 43. Runbook — secret delivery outage

1. Identify provider secret, version and consuming workload.
2. Inspect CSI/external-secret controller and events.
3. Separate IAM denial from private network failure.
4. Restore access or previous valid secret version.
5. Validate application reload and data safety.
6. Check audit logs for leakage.
7. Document rotation corrective actions.

## 44. Runbook — network isolation incident

1. Identify affected Pods and namespaces.
2. Confirm active dataplane and policy enforcement.
3. Inspect ingress/egress rules and DNS allowances.
4. Test allowed and denied paths.
5. Restore reviewed policy, not broad allow-all.
6. Validate application SLO.
7. Record RCA.

## 45. Runbook — admission or image trust failure

1. Identify image digest, policy and rejection reason.
2. Verify signature, issuer and artifact provenance.
3. Review Pod security and admission webhook status.
4. Restore approved compliant artifact or policy.
5. Confirm untrusted image remains denied.
6. Verify application health.
7. Archive evidence.

## 46. Runbook — cross-cloud credential compromise

1. Declare security incident and identify impacted principals.
2. Suspend affected GitLab jobs and Argo CD promotions.
3. Revoke exact compromised trust and tokens.
4. Rotate affected secrets/credentials using approved procedure.
5. Audit AWS, Azure and Google access independently.
6. Restore scoped access with positive/negative tests.
7. Document blast radius and containment timeline.

## 47. Evidence template

~~~text
Incident/change ID:
Provider, cluster, namespace and KSA:
Cloud identity mechanism and exact trust:
Cloud resource and scoped permission:
Secret backend, version and rotation owner:
CSI/external-secret driver and status:
Kubernetes RBAC and AppProject:
NetworkPolicy engine and test results:
Pod security and image trust policy:
GitLab OIDC job and protected ref:
AWS/Azure/Google audit event IDs:
Positive/negative tests and SLO:
Approval, rollback and RCA:
~~~

Never record secret values, identity tokens, private keys or privileged kubeconfigs.

## 48. Scored security readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| Workload identity across providers | 25 | Allowed/denied API tests |
| Secret management and rotation | 20 | CSI, IAM and reload |
| Kubernetes RBAC and GitOps | 15 | Scoped destination and verbs |
| Network isolation | 15 | Positive/negative traffic |
| Admission and artifact trust | 15 | Signed/unsigned tests |
| Audit and incident recovery | 10 | Events and runbooks |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: persistent cloud keys in Pods/CI, wildcard production IAM, unauthorized secret read, unenforced required isolation, bypassable image trust or missing incident containment path.

## 49. Final acceptance checklist

- [ ] EKS IRSA/Pod Identity prerequisites validated.
- [ ] AKS Microsoft Entra Workload ID validated.
- [ ] GKE Workload Identity Federation validated.
- [ ] All identity trust scoped by workload and resource.
- [ ] No static cloud service account keys.
- [ ] Secret Manager/Key Vault/Secrets Manager permissions tested.
- [ ] Secret rotation and application reload verified.
- [ ] GitLab OIDC federation protected.
- [ ] Kubernetes RBAC and AppProject restrictions tested.
- [ ] NetworkPolicy enforcement verified on each dataplane.
- [ ] DNS and private endpoint egress tested.
- [ ] Pod Security Admission validated.
- [ ] Signed image admission enforced.
- [ ] Cloud and Kubernetes audit records collected.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five SRE runbooks validated.
- [ ] 100-point security readiness signed off.

## 50. Knowledge check

1. How does EKS Pod Identity differ from IRSA?
2. What issuer, subject and audience must AKS federation validate?
3. What are the direct principal and IAM service account impersonation patterns in GKE?
4. Why does cloud IAM not replace Kubernetes RBAC?
5. What are the tradeoffs between CSI-mounted and synced Kubernetes Secrets?
6. Why can secret rotation succeed at the provider but fail at the application?
7. Why must NetworkPolicy enforcement be tested on every provider?
8. What is the difference between Pod Security Admission and image signature enforcement?
9. How do GitLab OIDC conditions prevent untrusted branch privilege escalation?
10. What evidence proves a compromised identity was fully revoked?

## 51. References

- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [AKS Workload ID](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [GKE Workload Identity Federation](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Azure Key Vault](https://learn.microsoft.com/azure/key-vault/general/)
- [Google Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Secrets Store CSI Driver](https://secrets-store-csi-driver.sigs.k8s.io/)
- [External Secrets Operator](https://external-secrets.io/latest/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Argo CD AppProjects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [GitLab CI/CD OIDC](https://docs.gitlab.com/ci/secrets/id_token_authentication/)

---

**Chapter 083 complete.** Next: **Chapter 084 — Multi-Cluster Observability, SLOs, Incident Response and Cross-Cloud Disaster Recovery**.