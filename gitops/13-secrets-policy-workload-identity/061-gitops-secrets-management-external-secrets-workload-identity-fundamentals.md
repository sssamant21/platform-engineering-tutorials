# Chapter 061 — GitOps Secrets Management, External Secrets and Workload Identity Fundamentals

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 13:** Secrets, Policy and Workload Identity  
**Chapter:** 061 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Security Engineers and Kubernetes Administrators

> **Safety:** All examples use staging namespaces and placeholder names. Never commit plaintext production secrets, cloud access keys, kubeconfigs or unencrypted credential files to Git. Validate cloud IAM, Kubernetes RBAC and External Secrets Operator versions before using these manifests.

## 1. Learning objectives

By completing this chapter, you will:

1. Explain why GitOps desired state must not contain plaintext credentials.
2. Compare Kubernetes Secrets, External Secrets Operator, SOPS and Sealed Secrets.
3. Design secret delivery with external stores and least-privilege workload identity.
4. Configure SecretStore, ClusterSecretStore and ExternalSecret resources safely.
5. Separate application identity from the operator's provider identity.
6. Validate secret synchronization, refresh, rotation and failure modes.
7. Integrate secret management with GitLab, Argo CD and Kubernetes RBAC.
8. Troubleshoot provider permissions, missing secrets, stale values and accidental exposure.
9. Run incident-response and recovery exercises with auditable evidence.

## 2. Enterprise secret-delivery architecture

~~~text
GitLab source + GitOps repository
        |
        | Git stores only references/policies
        v
Argo CD reconciles ExternalSecret + SecretStore
        |
        v
External Secrets Operator controller
        |
        | workload identity / scoped provider credential
        v
Cloud secret store (AWS Secrets Manager / Azure Key Vault / GCP Secret Manager)
        |
        | fetch approved secret version
        v
Kubernetes Secret in target namespace
        |
        | Pod env or mounted volume
        v
Application workload
~~~

**Core principle:** Git describes *which secret* should exist and *how it is synchronized*, but the secret value remains in a controlled secret manager. Kubernetes Secret objects still hold the resulting values; base64 encoding is not encryption. Use Kubernetes encryption at rest, RBAC, admission policy, audit logging and etcd backup controls.

## 3. Secret management choices

| Pattern | Git contents | Advantages | Risks |
| --- | --- | --- | --- |
| Plain Kubernetes Secret manifest | Base64-encoded secret | Simple | Exposes credential in Git; avoid |
| SOPS-encrypted manifest | Encrypted values | Git-based change history | Key access/decryption integration |
| Sealed Secrets | Cluster-bound encrypted data | Git-friendly encrypted resource | Controller/key lifecycle complexity |
| External Secrets Operator (ESO) | External secret references | Centralized rotation and IAM | Provider/operator availability |
| Secrets Store CSI Driver | Mount-time provider integration | Volume-based consumption | Driver/provider and rotation behavior |

ESO and CSI Driver are different projects with different synchronization semantics. A Secret mounted through CSI is not necessarily a Kubernetes Secret unless configured for sync. Choose based on application consumption and security requirements.

## 4. Threat model

Protect against:

- Plaintext secrets in Git commits, CI logs, artifacts or merge requests.
- Overly broad cloud IAM access to secret prefixes.
- Cluster-wide SecretStore use without tenant isolation.
- Pods reading other namespaces' Secrets.
- ServiceAccount token theft and over-permissive Kubernetes RBAC.
- Secret exposure through debug endpoints, environment dumps or crash reports.
- Stale secret values after rotation.
- Compromised etcd backups or unencrypted cluster storage.
- Operator compromise with broad secret-manager permissions.

Secret management is a full lifecycle: creation, distribution, access, rotation, revocation, audit and recovery.

## 5. External Secrets Operator resources

| Resource | Purpose | Scope |
| --- | --- | --- |
| SecretStore | Provider connection configuration | Namespace |
| ClusterSecretStore | Shared provider configuration | Cluster |
| ExternalSecret | Maps provider secret into target Kubernetes Secret | Namespace |
| ClusterExternalSecret | Replicates ExternalSecret definitions to selected namespaces | Cluster |
| Kubernetes Secret | Materialized credential consumed by Pods | Namespace |

Use namespace-scoped SecretStore by default for tenant isolation. ClusterSecretStore and ClusterExternalSecret can amplify blast radius; restrict who may create or reference them.

## 6. Installation and preflight

Install ESO from an approved, pinned Helm chart/release using your organization’s GitOps bootstrap process. Confirm CRDs, webhook, controller, certificate management and leader election are healthy.

~~~bash
kubectl config current-context
kubectl get crd externalsecrets.external-secrets.io secretstores.external-secrets.io
kubectl -n external-secrets get deploy,pods,svc
kubectl -n demo-staging get serviceaccounts
kubectl auth can-i get secrets -n demo-staging
~~~

Do not grant application users broad list/watch permissions on Secrets. Confirm installed ESO API version and provider auth schema against its documentation; provider integration fields vary by release.

## 7. AWS Secrets Manager example using EKS Pod Identity or IRSA

There are two distinct AWS identity models:

- **IRSA:** Kubernetes ServiceAccount annotation links to an IAM role with an OIDC trust relationship.
- **EKS Pod Identity:** EKS Pod Identity association binds a ServiceAccount to an IAM role using the Pod Identity agent and service principal.

Do not assume an IRSA annotation is required for EKS Pod Identity. Choose one supported model and validate the role trust, cluster setup and permissions.

Example scoped AWS IAM policy (replace account/region/name):

~~~json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:111122223333:secret:staging/demo-web/db-password-*"
      ]
    }
  ]
}
~~~

If the secret uses a customer-managed KMS key, the role may also require narrowly scoped kms:Decrypt permissions. Deny broad wildcard resource access unless there is a documented exception.

## 8. ESO ServiceAccount and SecretStore

The following is an **IRSA-oriented** staging example. Create the actual IAM role trust and OIDC provider first. With EKS Pod Identity, use the corresponding association rather than relying on the annotation.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eso-demo-reader
  namespace: demo-staging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/staging-demo-eso-reader
---
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: demo-aws-secrets
  namespace: demo-staging
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: eso-demo-reader
~~~

**Version note:** This uses the ESO v1 API available in newer releases. If your installed CRDs support v1beta1 instead, adapt manifests to the installed version and verify provider-auth fields before applying. Namespace-scoped ServiceAccount identity for provider access differs from the application's own ServiceAccount.

## 9. ExternalSecret manifest

~~~yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: demo-db-credentials
  namespace: demo-staging
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: demo-aws-secrets
    kind: SecretStore
  target:
    name: demo-db-credentials
    creationPolicy: Owner
  data:
    - secretKey: password
      remoteRef:
        key: staging/demo-web/db-password
~~~

The remote secret must exist in the provider, and the ESO identity must have permission to read it. The resulting Kubernetes Secret is named demo-db-credentials with a password key.

**Refresh behavior:** refreshInterval controls periodic reconciliation, not a guaranteed end-to-end application rotation time. Applications reading Secrets through environment variables generally require a restart to consume changed values; projected Secret volumes update eventually, subject to kubelet and application reload behavior.

## 10. Application consumption and separation of identity

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-web
  namespace: demo-staging
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      serviceAccountName: demo-web
      automountServiceAccountToken: false
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_DIGEST
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: demo-db-credentials
                  key: password
          ports:
            - containerPort: 8080
~~~

This example assumes the application does not need Kubernetes API credentials, so automountServiceAccountToken is disabled. If it needs cloud workload identity, the identity setup may require a projected token or provider-specific injection; review that architecture separately.

**Caution:** environment variables can leak through debug dumps and process inspection. Prefer mounted files and runtime reload when supported, and avoid logging secret values.

## 11. Verify synchronization without printing secrets

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get secretstore demo-aws-secrets
kubectl --context STAGING_CONTEXT -n demo-staging describe secretstore demo-aws-secrets
kubectl --context STAGING_CONTEXT -n demo-staging get externalsecret demo-db-credentials
kubectl --context STAGING_CONTEXT -n demo-staging describe externalsecret demo-db-credentials
kubectl --context STAGING_CONTEXT -n demo-staging get secret demo-db-credentials
kubectl --context STAGING_CONTEXT -n demo-staging get events --sort-by=.lastTimestamp
~~~

Avoid kubectl get secret -o yaml/json and avoid base64 decoding in shared logs or screenshots. Validate presence, key names, status conditions and workload behavior without exposing the value.

## 12. Cloud workload identity comparison

| Platform | Typical identity integration | Key checks |
| --- | --- | --- |
| Amazon EKS | IRSA or EKS Pod Identity | Role trust, association/annotation, IAM scope |
| Azure AKS | Microsoft Entra Workload ID | Federated identity credential, issuer, audience, ServiceAccount annotation |
| Google GKE | Workload Identity Federation for GKE | KSA-to-IAM authorization and principal bindings |

Do not copy an AWS ServiceAccount annotation into AKS or GKE. Each cloud has different trust configuration, token audience and permission syntax.

## 13. Azure Key Vault example (conceptual)

An AKS implementation generally requires:

1. AKS OIDC issuer and workload identity enabled.
2. A Kubernetes ServiceAccount associated with an authorized Azure identity.
3. A federated identity credential matching issuer, subject and audience.
4. Scoped Key Vault secret read permission.
5. An ESO SecretStore using a supported Azure Key Vault authentication mode.
6. A test ExternalSecret and non-sensitive status verification.

Verify the exact ESO version and Azure provider fields before applying. Avoid service-principal client secrets where workload identity is available and approved.

## 14. GKE Secret Manager example (conceptual)

A GKE implementation generally requires:

1. Workload Identity Federation for GKE enabled.
2. Namespace/ServiceAccount identity selected.
3. Secret Manager IAM grant scoped to required secrets.
4. ESO SecretStore configured for the supported GCP provider auth mode.
5. ExternalSecret reconciliation tested.
6. Audit logs reviewed for access and denied requests.

Use cloud-native short-lived identity instead of static JSON service-account keys whenever possible.

## 15. GitOps and Argo CD security

Recommended order:

~~~text
1. Bootstrap ESO controller and CRDs.
2. Configure scoped cloud workload identity.
3. Create namespace and SecretStore.
4. Create ExternalSecret.
5. Wait for Ready condition and target Secret.
6. Deploy application that consumes the Secret.
7. Monitor refresh and rotation.
~~~

An Argo CD sync ordering mechanism can coordinate resources, but it does not by itself guarantee an external provider has populated the target Secret. Use health checks, application startup behavior and explicit readiness gates.

Prevent Argo CD from showing Secret values in logs, diffs or troubleshooting artifacts. Restrict Argo CD repository credentials and project destinations.

## 16. Kubernetes RBAC and namespace isolation

~~~yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: external-secret-observer
  namespace: demo-staging
rules:
  - apiGroups: ["external-secrets.io"]
    resources: ["externalsecrets", "secretstores"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: external-secret-observer
  namespace: demo-staging
subjects:
  - kind: ServiceAccount
    name: release-observer
    namespace: demo-staging
roleRef:
  kind: Role
  name: external-secret-observer
  apiGroup: rbac.authorization.k8s.io
~~~

Create the release-observer ServiceAccount before applying this binding. Do not grant get/list/watch on Kubernetes Secrets merely to inspect ESO status. Restrict SecretStore creation because a malicious store may redirect credentials or provider access.

## 17. Rotation design

Rotation has multiple clocks:

~~~text
Cloud secret rotation
       |
ESO reconciliation interval
       |
Kubernetes Secret update
       |
Pod volume projection or restart
       |
Application credential reload
       |
Old credential revocation
~~~

A safe dual-credential rotation may require overlap while clients reconnect. Coordinate database users, connection pools, TLS certificates and application restarts. A changed Kubernetes Secret does not guarantee running processes have adopted the new value.

For incident-driven revocation, shorten exposure with emergency controls and measure actual propagation rather than assuming refreshInterval is sufficient.

## 18. Lab A — Controller and CRD readiness

1. Select a disposable staging context.
2. Verify ESO controller, webhook, CRDs and leader health.
3. Confirm namespace isolation.
4. Record controller and CRD versions.
5. Inspect logs for permission errors without exposing values.

**Pass:** ESO is healthy and the target namespace is correctly scoped.

## 19. Lab B — Least-privilege AWS secret access

1. Create a synthetic secret in staging AWS Secrets Manager.
2. Configure an IAM role scoped to that secret only.
3. Bind ESO provider identity through approved IRSA or Pod Identity.
4. Create the SecretStore.
5. Verify SecretStore Ready condition.
6. Attempt access to a second unauthorized synthetic secret and confirm denial.

**Pass:** allowed secret succeeds; unrelated secret access is denied.

## 20. Lab C — ExternalSecret reconciliation

1. Apply the ExternalSecret referencing the synthetic remote key.
2. Wait for Ready status.
3. Confirm the target Kubernetes Secret exists and has the expected key name.
4. Deploy a staging workload consuming the Secret.
5. Validate application connectivity without printing the credential.
6. Record sync time and events.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get externalsecret demo-db-credentials -w
kubectl --context STAGING_CONTEXT -n demo-staging get secret demo-db-credentials
~~~

**Pass:** the application consumes the materialized secret and no secret value appears in logs.

## 21. Lab D — Rotation and application reload

1. Rotate the synthetic provider secret to a new test value.
2. Observe ESO refresh and target Secret metadata changes.
3. Confirm whether the application uses env vars or projected volume.
4. Trigger an approved rollout restart if the application requires it.
5. Verify connectivity with the new credential.
6. Revoke the old credential after the overlap window.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging rollout restart deploy/demo-web
kubectl --context STAGING_CONTEXT -n demo-staging rollout status deploy/demo-web
~~~

**Pass:** new credentials are adopted within the measured objective, and old credentials are revoked safely.

## 22. Lab E — Missing provider secret

1. Reference a nonexistent synthetic remote key.
2. Observe ExternalSecret status and events.
3. Confirm the application fails safely rather than using a leaked fallback.
4. Repair the remote key reference.
5. Verify reconciliation and recovery.

**Pass:** missing secret is visible, actionable and does not expose credentials.

## 23. Lab F — Cloud IAM denial

1. Remove staging read permission from the scoped ESO identity.
2. Trigger reconciliation or wait for the normal refresh.
3. Inspect SecretStore/ExternalSecret conditions and operator logs.
4. Restore the minimal required permission.
5. Verify recovery without broadening IAM scope.

**Pass:** IAM denial is detected and recovery is scoped and auditable.

## 24. Lab G — Namespace isolation

1. Create two disposable namespaces with different synthetic secrets.
2. Scope each SecretStore to its intended namespace.
3. Verify applications cannot read the other namespace's Secret.
4. Test Kubernetes RBAC with impersonation where permitted.
5. Verify cloud IAM denies cross-environment secret paths.

~~~bash
kubectl auth can-i get secrets -n other-staging   --as=system:serviceaccount:demo-staging:demo-web
~~~

**Pass:** both Kubernetes and cloud-provider boundaries prevent cross-tenant access.

## 25. Lab H — ESO controller outage

1. Confirm application health and last successful synchronization.
2. Scale down ESO only in a disposable environment.
3. Rotate the synthetic remote secret.
4. Observe that existing Kubernetes Secrets remain but may become stale.
5. Restore the controller.
6. Verify eventual reconciliation and application reload.

**Pass:** operators understand that existing Secrets can remain usable while refresh is unavailable, and can measure stale-credential exposure.

## 26. Lab I — Accidental secret exposure tabletop

Scenario: a developer accidentally commits a plaintext credential to a Git branch.

1. Treat the value as compromised even if the commit is later deleted.
2. Revoke or rotate the exposed credential immediately.
3. Audit provider and application access during the exposure window.
4. Restrict logs, artifacts and repository history access.
5. Follow approved history-rewrite and notification procedures.
6. Add prevention controls and verify the replacement secret works.

**Pass:** the response prioritizes revocation and containment over merely deleting a commit.

## 27. Lab J — GitOps recovery and evidence

1. Break an ExternalSecret reference in a staging GitOps MR.
2. Observe Argo CD desired state and ESO Ready status.
3. Revert the GitOps reference through an approved change.
4. Verify target Secret reconciliation and application health.
5. Archive non-sensitive audit evidence.

**Pass:** recovery restores approved desired state without exposing values.

## 28. Troubleshooting — fourteen scenarios

| # | Symptom | Likely cause | Safe action |
| --- | --- | --- | --- |
| 1 | SecretStore not Ready | Provider auth/network | Check conditions and identity |
| 2 | ExternalSecret not Ready | Missing key or denied access | Verify remote key and scoped IAM |
| 3 | ESO CRD unknown | Controller/CRD not installed | Install approved pinned release |
| 4 | Kubernetes Secret absent | Reconciliation failure | Inspect events and target policy |
| 5 | Secret exists, app still fails | Wrong key/env reference | Validate key names and restart need |
| 6 | Rotated secret not used | Env var loaded at startup | Restart safely or implement reload |
| 7 | AWS AccessDenied | Role trust/IAM/KMS | Correct least-privilege permissions |
| 8 | IRSA works, Pod Identity fails | Missing association/agent | Check selected identity model |
| 9 | AKS federated auth fails | Issuer/subject/audience mismatch | Correct federation and annotations |
| 10 | GKE auth denied | KSA/IAM binding mismatch | Verify Workload Identity grants |
| 11 | Cross-namespace secret exposure | Broad ClusterSecretStore/RBAC | Restrict namespace and provider scope |
| 12 | Argo CD reports Healthy, app fails | Secret readiness not gated | Add workload startup/readiness checks |
| 13 | Secret printed in CI logs | Unsafe debug output | Revoke, redact, audit and prevent |
| 14 | ESO outage causes stale values | Controller unavailable | Restore controller and verify refresh |

## 29. Production runbook — new secret onboarding

**Preflight:** confirm owner, classification, cloud store path, IAM scope, namespace, application consumption method, rotation policy and expiry.

**Configure:** create provider secret through approved workflow, establish workload identity, create SecretStore and ExternalSecret in GitOps.

**Verify:** confirm ESO Ready conditions, target Secret presence and application functionality without revealing secret values.

**Close:** record version, identity binding, audit trail, rotation owner and rollback plan.

## 30. Production runbook — failed secret synchronization

1. Declare impact and identify affected namespace/application.
2. Inspect ExternalSecret and SecretStore status, events and ESO controller health.
3. Check cloud provider auth, secret existence, version and network reachability.
4. Determine whether a previously materialized Secret is still valid.
5. Restore least-privilege access or correct GitOps references.
6. Restart applications only if required for updated credential consumption.
7. Validate application health and audit the recovery.
8. Preserve redacted evidence; do not print secret values.

## 31. Production runbook — credential compromise

1. Contain exposure and notify security incident owner.
2. Revoke or rotate affected provider credential immediately.
3. Audit secret-manager access, CI logs, repository and workload activity.
4. Identify dependent applications and execute controlled reloads.
5. Remove exposed copies from accessible artifacts using approved procedures.
6. Verify old credential rejection and new credential functionality.
7. Document timeline, blast radius, root cause and preventive controls.

**Never assume deleting a Git commit eliminates an exposed credential.**

## 32. Production runbook — ESO controller outage

1. Assess application availability and freshness of materialized Secrets.
2. Inspect ESO controller, webhook, leader election, events and permissions.
3. Restore from the approved pinned deployment version.
4. Validate one non-production SecretStore and ExternalSecret first.
5. Confirm reconciliation resumes and rotation lag is acceptable.
6. Monitor downstream application credential reload.
7. Document RTO, stale-secret exposure and remediation.

## 33. Evidence template

~~~text
Change / incident ID:
Cluster and namespace:
SecretStore / ExternalSecret names:
External provider and non-sensitive secret path:
Workload identity model and role:
IAM permission review:
GitOps MR, commit and approvers:
ESO controller/CRD version:
Last successful sync:
Rotation start and completion:
Application reload/restart:
Observed application health:
Unauthorized access test:
Credential revocation evidence:
Incident and recovery duration:
Evidence archive location:
Owner and next rotation date:
~~~

Do not archive plaintext credentials, Secret YAML with data, tokens, or unredacted provider responses.

## 34. Acceptance criteria

- [ ] No plaintext credentials committed to Git.
- [ ] Kubernetes Secret base64 encoding is not treated as encryption.
- [ ] ESO controller and CRDs are version-validated.
- [ ] Namespace-scoped SecretStore and ExternalSecret work.
- [ ] Cloud workload identity uses least privilege.
- [ ] Cross-namespace/provider secret access is denied.
- [ ] Application identity and ESO provider identity are separated.
- [ ] Secret synchronization and refresh are observable.
- [ ] Rotation and application reload are measured.
- [ ] Missing secret and IAM denial fail safely.
- [ ] Controller outage and stale-secret behavior are tested.
- [ ] Compromised credential response includes immediate revocation.
- [ ] Ten labs have documented pass/fail evidence.
- [ ] Production runbooks and owners are approved.

## 35. Knowledge check

1. Why is base64-encoded Kubernetes Secret data not secure for Git?
2. How does ESO differ from Secrets Store CSI Driver?
3. When should a SecretStore be preferred over a ClusterSecretStore?
4. What distinguishes IRSA from EKS Pod Identity?
5. Why might an application continue using an old secret after ESO refresh?
6. What happens to materialized Secrets when ESO is unavailable?
7. Why must provider IAM and Kubernetes RBAC both be reviewed?
8. What is the first action after accidental credential disclosure?
9. Why is a healthy Argo CD Application insufficient proof of secret readiness?
10. How should secret rotation be audited without exposing values?

## 36. References

- [External Secrets Operator Documentation](https://external-secrets.io/latest/)
- [External Secrets Operator API](https://external-secrets.io/latest/api/externalsecret/)
- [AWS EKS IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [AWS EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Microsoft Entra Workload ID for AKS](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Argo CD Sync Phases and Waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)

---

**Chapter 061 complete.** Next: **Chapter 062 — SOPS, Sealed Secrets and Encryption Key Lifecycle for GitOps**.