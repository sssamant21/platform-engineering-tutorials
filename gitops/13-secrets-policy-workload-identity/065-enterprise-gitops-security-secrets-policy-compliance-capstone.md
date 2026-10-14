# Chapter 065 — Enterprise GitOps Security, Secrets and Policy Compliance Capstone

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 13:** Secrets, Policy and Workload Identity  
**Chapter:** 065 / 100 — Part 13 Capstone  
**Audience:** Platform Engineers, SREs, DevSecOps, Security Engineers, DBREs and Release Managers

> **Safety:** Run every exercise in an isolated staging cluster with synthetic credentials and disposable applications. Do not print Secret data, export real signing keys, disable admission protections in production, or inject faults into shared system components. Security and availability controls must be tested together.

## 1. Mission

Design, implement, validate and recover a secure enterprise GitOps release pipeline integrating the capabilities from Chapters 061–064:

- **061:** External Secrets Operator (ESO), secret-manager integration and workload identity.
- **062:** SOPS, Sealed Secrets, encryption-key custody and disaster recovery.
- **063:** Kubernetes admission, OPA Gatekeeper, Kyverno and policy exceptions.
- **064:** Immutable image digests, SBOMs, signing and build provenance.

**Outcome:** demonstrate that only reviewed, verified workloads can be deployed; secrets remain protected; policy violations fail safely; and approved recovery restores the platform without weakening the security baseline.

## 2. Reference architecture

~~~text
Developer -> protected GitLab merge request
                |
           trusted CI runner
                |
         test -> build -> SBOM -> scan
                |
        sign digest + attest provenance
                |
         protected GitOps promotion MR
                |
              Argo CD
                |
       Kubernetes API admission
          /       |        \
     Native VAP Gatekeeper  Kyverno/signature verifier
          \       |        /
             allow or deny
                |
        Deployment by signed digest
                |
      application ServiceAccount
                |
       Kubernetes Secret (materialized)
                ^
                |
      External Secrets Operator
                |
        scoped workload identity
                |
        external secret manager

Parallel encrypted-Git path:
SOPS encrypted manifest -> hardened decrypt boundary -> Secret
or
SealedSecret -> Sealed Secrets controller -> Secret
~~~

**Design rule:** choose one authoritative owner per target Kubernetes Secret. Do not simultaneously manage the same Secret with ESO, SOPS-rendered manifests and Sealed Secrets.

## 3. Capstone objectives and boundaries

| Control | Expected result | Owner |
| --- | --- | --- |
| Git governance | Protected MR, required reviewers, immutable revision | Release engineering |
| Artifact security | Trusted digest, SBOM, signature, provenance | DevSecOps |
| Admission | Unauthorized image/config rejected | Platform security |
| Secret delivery | Least-privilege access, no plaintext in Git | Platform/DBRE |
| Encryption | Recoverable SOPS/Sealed Secrets key lifecycle | Security |
| Identity | Scoped cloud IAM and Kubernetes RBAC | IAM/platform |
| GitOps | Approved desired state reconciled | SRE |
| Recovery | Restore trusted service and preserve audit trail | Incident commander |

The capstone deliberately separates **CI verification**, **GitOps approval**, **Kubernetes admission**, and **runtime health**. Passing one boundary never implies the others passed.

## 4. Staging prerequisites

- Disposable cluster and namespace, such as demo-security-staging.
- Argo CD Application restricted by AppProject destination and source rules.
- GitLab project with protected main branch and protected GitOps overlays.
- Approved pinned build runner, OCI registry and artifact retention.
- Cosign and an approved trusted signing identity or KMS key.
- SBOM generator and vulnerability scanner.
- ESO controller and a scoped staging external secret-manager identity.
- A supported policy engine: native VAP, Gatekeeper and/or Kyverno.
- SOPS age or cloud KMS and optionally Sealed Secrets in a separate lab namespace.
- Synthetic test application with readiness and non-sensitive health metrics.
- Security-approved exception and emergency rollback process.

~~~bash
kubectl config current-context
kubectl get namespaces
kubectl get crd externalsecrets.external-secrets.io
kubectl get validatingadmissionpolicies
kubectl -n argocd get applications.argoproj.io
cosign version
sops --version
~~~

**Stop** if cluster identity, tool compatibility or policy scope is uncertain. Use actual installed CRD API versions; the examples below assume modern ESO v1 and Kubernetes ValidatingAdmissionPolicy v1 support.

## 5. Repository layout

~~~text
gitops-security-capstone/
  app/
    src/
    tests/
    Dockerfile
  ci/
    build-and-push.sh
    generate-sbom.sh
    verify-artifact.sh
    propose-gitops-mr.sh
  .gitlab-ci.yml
  gitops/
    bootstrap/
      namespaces/
      controllers/
    applications/
      demo-security/
        base/
          deployment.yaml
          serviceaccount.yaml
        overlays/staging/
          kustomization.yaml
          externalsecret.yaml
    secrets/
      sops/
      sealed/
    policies/
      native/
      gatekeeper/
      kyverno/
      tests/
    argocd/
      application.yaml
    exceptions/
      exception-register.yaml
  runbooks/
    secret-sync-failure.md
    admission-denial.md
    signer-compromise.md
    key-disaster-recovery.md
  evidence/
    acceptance-template.md
~~~

The scripts are **interfaces to implement** using approved internal tools; they are not commands supplied by GitLab or Kubernetes.

## 6. Security acceptance contract

Each release must record:

~~~text
Release ID:
Source repository, SHA, MR and reviewers:
GitLab pipeline and trusted runner identity:
OCI image digest:
SBOM reference and scan findings:
Signature identity and issuer/KMS reference:
Provenance subject, builder and source:
GitOps MR, approvers and revision:
Argo CD Application, project and destination:
Admission policy version and decision:
SecretStore / ExternalSecret name and status:
Cloud workload identity and IAM review:
Observed Pod imageID and readiness:
Approved rollback digest and data compatibility:
Incident owner, evidence location and retention:
~~~

Never place plaintext secret values, decryption private keys, OIDC tokens or provider credentials in this record.

## 7. Secret ownership and identity model

For the primary application, choose **ESO** to materialize a synthetic database credential from a managed secret store. Use SOPS and Sealed Secrets only in separate comparison/recovery exercises.

~~~text
ExternalSecret demo-db-credentials
        |
SecretStore demo-cloud-store
        |
ESO-scoped cloud identity
        |
Cloud secret staging/demo-security/db-password
        |
Kubernetes Secret demo-db-credentials
        |
Application Pod reads key password
~~~

The application's Kubernetes ServiceAccount and ESO's provider-access identity must be independently reviewed. The application does not automatically need cloud secret-manager permissions simply because it consumes the materialized Kubernetes Secret.

## 8. Example ESO configuration

This is an AWS IRSA-oriented example. EKS Pod Identity, AKS Workload Identity and GKE Workload Identity Federation require different trust and provider configuration.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eso-capstone-reader
  namespace: demo-security-staging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/staging-eso-capstone-reader
---
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: demo-cloud-store
  namespace: demo-security-staging
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: eso-capstone-reader
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: demo-db-credentials
  namespace: demo-security-staging
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: demo-cloud-store
    kind: SecretStore
  target:
    name: demo-db-credentials
    creationPolicy: Owner
  data:
    - secretKey: password
      remoteRef:
        key: staging/demo-security/db-password
~~~

Prerequisites: create the synthetic provider secret and a correctly trusted IAM role with permission to read only that secret. Add narrowly scoped KMS decrypt permissions if the backing secret uses a customer-managed KMS key.

**Operational warning:** refreshInterval is not the application's end-to-end credential rotation time. Environment-variable consumers usually need a controlled restart after the target Secret changes.

## 9. Application ServiceAccount and workload

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-security-web
  namespace: demo-security-staging
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-security-web
  namespace: demo-security-staging
  labels:
    platform.example/owner: security-capstone
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-security-web
  template:
    metadata:
      labels:
        app: demo-security-web
    spec:
      serviceAccountName: demo-security-web
      automountServiceAccountToken: false
      containers:
        - name: web
          image: registry.example.internal/demo/security-web@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - containerPort: 8080
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: demo-db-credentials
                  key: password
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities:
              drop: ["ALL"]
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
~~~

The digest is a placeholder and must be replaced with an actual signed OCI digest. Confirm the image supports non-root execution. For environments enforcing restricted Pod Security Standards, add any required seccomp profile and ensure the image/runtime configuration meets the installed policy.

## 10. Native admission baseline

A native ValidatingAdmissionPolicy can require owner labels on Deployments, reducing dependency on an external webhook for this basic validation.

~~~yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: capstone-require-owner
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: "has(object.metadata.labels) && 'platform.example/owner' in object.metadata.labels && object.metadata.labels['platform.example/owner'] != ''"
      message: "Deployment must include platform.example/owner"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: capstone-require-owner-staging
spec:
  policyName: capstone-require-owner
  validationActions: ["Audit", "Warn"]
  matchResources:
    namespaceSelector:
      matchLabels:
        platform.example/security-profile: capstone
~~~

Begin with Audit/Warn, test all fixtures, then change to Deny through approved GitOps review. Restrict who can edit namespace labels or policy bindings. This rule does not verify image signatures; use a cryptographic verifier for that.

## 11. Artifact verification and admission

Required controls:

1. Pin the image by digest.
2. Generate SBOM for the exact digest.
3. Scan the SBOM/image using the approved policy.
4. Sign the image using a trusted CI identity or KMS key.
5. Produce signed build provenance whose subject matches the digest.
6. Verify trusted signer identity, issuer and builder/source.
7. Reject unsigned/untrusted images in a scoped admission policy.
8. Confirm the running Pod imageID matches the approved digest.

Example verification commands using **real** artifact references:

~~~bash
cosign verify   --certificate-identity "APPROVED_CERTIFICATE_IDENTITY"   --certificate-oidc-issuer "APPROVED_OIDC_ISSUER"   registry.example.internal/demo/security-web@sha256:REAL_DIGEST

syft registry.example.internal/demo/security-web@sha256:REAL_DIGEST   -o cyclonedx-json=sbom.cdx.json

grype sbom:sbom.cdx.json --fail-on high
~~~

The certificate identity and issuer are policy inputs, not literal deployable defaults. Some installations require KMS/public-key verification instead of keyless verification. Pin tool versions and validate the actual certificate subject/issuer. A signed artifact can still be vulnerable or malicious; verify provenance and policy as separate controls.

## 12. GitLab CI/CD security pipeline

~~~yaml
stages: [test, build, scan, sign, promote]

test:
  stage: test
  image: registry.example.internal/ci/python:PINNED_DIGEST
  script:
    - python -m pip install -r requirements.txt
    - python -m pytest -q

build:
  stage: build
  image: registry.example.internal/ci/secure-builder:PINNED_DIGEST
  script:
    - ./ci/build-and-push.sh
  artifacts:
    reports:
      dotenv: release.env
    expire_in: 1 day

scan:
  stage: scan
  image: registry.example.internal/ci/security-tools:PINNED_DIGEST
  needs:
    - job: build
      artifacts: true
  script:
    - ./ci/generate-sbom.sh

sign:
  stage: sign
  image: registry.example.internal/ci/cosign-tools:PINNED_DIGEST
  needs:
    - job: build
      artifacts: true
    - scan
  script:
    - ./ci/sign-and-attest.sh
    - ./ci/verify-artifact.sh

promote:
  stage: promote
  image: registry.example.internal/ci/gitlab-client:PINNED_DIGEST
  needs:
    - job: build
      artifacts: true
    - sign
  resource_group: security-staging-promotion
  script:
    - ./ci/propose-gitops-mr.sh
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

All images and scripts above are placeholders for organization-approved implementations. Use short-lived CI identities and avoid storing signing keys in pipeline artifacts. Protected GitOps approval and runtime admission must be independently enforced.

## 13. Argo CD delivery sequence

~~~text
Bootstrap cluster security controllers and CRDs
        |
Configure namespace, IAM and SecretStore
        |
Create ExternalSecret and verify Ready
        |
Apply admission policies in audit mode
        |
Validate signed image and provenance
        |
Approve GitOps MR with digest
        |
Argo CD sync
        |
Admission verifies workload
        |
Pod starts after required Secret exists
        |
Monitor app readiness, digest and secret freshness
~~~

Argo CD sync waves can help order resources but do not guarantee external secret availability. Include startup retry behavior, readiness gates and clear failure handling.

## 14. Key custody and disaster recovery

| Key material | Normal storage | Recovery requirement |
| --- | --- | --- |
| SOPS age identity | Protected vault/escrow | Historical encrypted Git revision decrypts |
| SOPS KMS key | Cloud KMS | Authorized decrypt under DR conditions |
| Sealed Secrets controller private key | Encrypted controlled backup | Restore old sealed resource in recovery cluster |
| Signing KMS key or CI identity | KMS/identity provider | Verify trusted replacement signer and revocation |
| ESO provider identity | Workload identity | Recreate trust and scoped permissions |

A repository backup alone does not restore encrypted secrets without corresponding key access. Rotating a Sealed Secrets certificate alone does not remediate a compromised controller private key; underlying application credentials must also be rotated.

## 15. Exception and emergency change governance

~~~yaml
exceptionId: SEC-CAPSTONE-001
environment: staging
policy: signed-image-required
namespace: demo-security-staging
resource: demo-security-web
reason: temporary compatibility investigation
owner: platform-security
approver: independent-security-reviewer
expiresAt: "2026-11-01T00:00:00Z"
ticket: CHANGE-EXAMPLE-001
compensatingControls:
  - synthetic data only
  - no external ingress
~~~

This is a **documentation record**, not a Kubernetes policy resource. Actual exceptions must be implemented through supported, scoped engine-specific mechanisms. Deny wildcard exceptions and require independent approval and automatic expiry review.

## 16. Observability and alerting

Monitor:

- ESO SecretStore/ExternalSecret Ready conditions and last successful refresh.
- Cloud secret-manager access denials and abnormal reads.
- Admission allow/deny counts, webhook health and latency.
- Signature verification failures and policy changes.
- GitLab pipeline and protected-branch approval outcomes.
- Argo CD OutOfSync, Degraded and sync failures.
- Running image digests versus approved GitOps revisions.
- Secret rotation propagation and application restarts.
- Key age, backup freshness, exception age and audit completeness.

Metrics names vary by controller and version. Discover the actual exported series before creating alerts. Never label telemetry with secret values or personal identifiers.

## 17. Lab A — Secure platform bootstrap

1. Confirm disposable cluster context and namespace.
2. Install approved pinned ESO and policy controllers.
3. Verify CRDs, webhook health and controller readiness.
4. Validate namespace labels and Argo CD AppProject restrictions.
5. Record versions and security owners.

**Pass:** bootstrap components are healthy and scope is explicitly limited.

## 18. Lab B — Least-privilege external secret delivery

1. Create a synthetic secret in the approved cloud store.
2. Grant ESO only the required read permission.
3. Configure workload identity and SecretStore.
4. Apply ExternalSecret and wait for Ready.
5. Confirm the target Kubernetes Secret exists without reading its value.
6. Attempt unauthorized secret access and verify denial.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-security-staging get secretstore
kubectl --context STAGING_CONTEXT -n demo-security-staging get externalsecret
kubectl --context STAGING_CONTEXT -n demo-security-staging get secret demo-db-credentials
~~~

**Pass:** authorized reconciliation succeeds and unrelated secret paths remain denied.

## 19. Lab C — SOPS encryption and recipient rotation

1. Generate a staging-only age identity.
2. Encrypt a synthetic Secret before committing.
3. Verify Git contains no plaintext.
4. Add a second approved recipient and update encryption metadata.
5. Test decryption using the new identity.
6. Confirm historical recovery before retiring the old identity.

**Pass:** encryption, authorized decryption and recipient transition are demonstrated without leaking keys.

## 20. Lab D — Sealed Secrets disaster recovery

1. Seal a synthetic Secret using authenticated controller public certificate and strict scope.
2. Reconcile it in the intended namespace.
3. Back up controller private key through approved encrypted custody.
4. Restore in an isolated recovery cluster.
5. Reconcile a historical sealed resource.
6. Record recovery time and cleanup.

**Pass:** recovery succeeds without private keys appearing in Git, logs or evidence.

## 21. Lab E — Policy-as-code audit to enforcement

1. Deploy owner-label and security-context policies in audit/warn mode.
2. Test compliant and noncompliant synthetic Deployments.
3. Review false positives and scope.
4. Switch the scoped policy to Deny/Enforce through GitOps.
5. Verify compliant workload passes and noncompliant workload fails.
6. Confirm system namespaces remain unaffected.

~~~bash
kubectl --context STAGING_CONTEXT apply --dry-run=server -f compliant-deployment.yaml
kubectl --context STAGING_CONTEXT apply --dry-run=server -f missing-owner-deployment.yaml
~~~

**Pass:** enforcement matches policy intent and produces actionable denial messages.

## 22. Lab F — Signed artifact and provenance

1. Build a synthetic application in a trusted staging runner.
2. Capture the real OCI digest.
3. Generate SBOM and scan findings for that digest.
4. Sign image and generate trusted provenance.
5. Verify signature identity, issuer, builder and subject.
6. Confirm a mismatched digest or signer fails verification.

**Pass:** artifact evidence is cryptographically tied to the approved digest and trusted identity.

## 23. Lab G — Admission rejects unsigned workload

1. Configure a signature-aware admission policy in audit mode.
2. Test signed approved image and unsigned synthetic image.
3. Validate actual cryptographic verification, not merely registry string matching.
4. Switch the disposable namespace to enforce mode.
5. Confirm unsigned workload is denied.
6. Restore approved signed image and verify healthy deployment.

**Pass:** unsigned image cannot be admitted in enforced scope.

## 24. Lab H — GitLab-to-Argo CD secure promotion

1. Run source tests, build, SBOM, scan, signing and attestation.
2. Open protected GitOps MR with exact digest.
3. Verify independent review and policy checks.
4. Merge and reconcile Argo CD.
5. Confirm admission success, Secret readiness and running Pod imageID.
6. Archive redacted evidence.

**Pass:** every boundary is independently verifiable.

## 25. Lab I — Secret rotation and stale consumer

1. Rotate a synthetic provider credential.
2. Observe ESO refresh and target Secret metadata.
3. Verify whether the application reloads mounted Secret or uses environment variables.
4. Restart workload safely if required.
5. Revoke old credential after successful adoption.
6. Measure total propagation time.

**Pass:** application uses the new credential within the documented objective.

## 26. Lab J — Provider IAM denial

1. Remove the ESO identity's staging read permission.
2. Observe SecretStore/ExternalSecret conditions and events.
3. Confirm no secret values appear in logs.
4. Restore only the required permission.
5. Verify synchronization and application health.
6. Record recovery duration.

**Pass:** access denial is visible and recovery does not broaden IAM scope.

## 27. Lab K — Admission controller outage

1. Record webhook failurePolicy and current health.
2. Simulate outage in a disposable policy-controller installation.
3. Attempt safe server-side dry-run requests.
4. Observe fail-open/fail-closed behavior.
5. Restore webhook, certificates and endpoints.
6. Verify normal admission and Argo CD reconciliation.

**Pass:** outage behavior and approved recovery path are documented.

## 28. Lab L — Compromised signer incident

1. Simulate compromise of a staging signing identity.
2. Freeze promotions from the affected signer.
3. Remove signer trust or revoke the credential.
4. Inventory impacted images and running digests.
5. Rebuild/resign approved artifact under replacement identity.
6. Reconcile GitOps and verify admission.
7. Archive incident evidence.

**Pass:** compromised trust is revoked and workloads are restored with a verified signer.

## 29. Lab M — GitOps policy regression and rollback

1. Introduce an overly strict policy in staging.
2. Confirm the expected workload is denied.
3. Capture policy revision and admission message.
4. Revert policy via approved GitOps emergency change.
5. Reconcile Argo CD and verify workload recovery.
6. Confirm unrelated security policies remain active.

**Pass:** recovery restores service without a broad permanent bypass.

## 30. Lab N — Integrated disaster recovery

1. Restore a protected GitOps revision in an isolated recovery cluster.
2. Recreate scoped cloud workload identity and ESO configuration.
3. Restore approved SOPS/Sealed Secrets decryption capability.
4. Restore signature verification trust and admission policy.
5. Deploy previously approved signed digest.
6. Verify Secret readiness, admission acceptance and application health.
7. Measure RTO and confirm no credential leakage.

**Pass:** the entire secure delivery chain can be reconstructed from protected sources and tested key custody.

## 31. Lab O — Audit and compliance assessment

1. Collect GitLab MR and pipeline evidence.
2. Correlate image digest, signature, provenance and SBOM.
3. Collect admission decisions and policy versions.
4. Record ESO status, workload identity and IAM denial tests.
5. Record key rotation and disaster recovery results.
6. Confirm exceptions have independent approval and expiry.
7. Produce a redacted final audit packet.

**Pass:** an independent reviewer can reconstruct release authorization and security outcomes without accessing plaintext secrets.

## 32. Troubleshooting — sixteen scenarios

| # | Symptom | Investigation | Safe recovery |
| --- | --- | --- | --- |
| 1 | ExternalSecret not Ready | Provider IAM, remote key, ESO logs | Repair scoped identity/reference |
| 2 | Secret exists but app fails | Wrong key, stale env var | Fix reference and reload |
| 3 | AWS AccessDenied | IRSA/Pod Identity, IAM, KMS | Restore least privilege |
| 4 | SOPS cannot decrypt | Wrong age/KMS recipient | Recover approved identity |
| 5 | Historical SOPS revision fails | Key retired too early | Restore escrow/re-encrypt |
| 6 | SealedSecret cannot unseal | Wrong namespace/cert/private key | Reseal or restore key |
| 7 | New cluster cannot restore Secret | Missing controller-key backup | Use tested DR key custody |
| 8 | VAP denies compliant resource | CEL expression or selector | Test and correct policy |
| 9 | Gatekeeper template not ready | CRD generation delay | Wait for established CRD |
| 10 | Kyverno report missing | Engine version/background scope | Check policy and reports |
| 11 | Admission webhook timeout | Controller, TLS, endpoints | Restore healthy webhook |
| 12 | Unsigned image denied | Missing signature | Sign trusted digest or revert |
| 13 | Signature verifies wrong identity | Trust policy too broad | Constrain issuer/subject |
| 14 | Provenance subject mismatch | Attestation wrong digest | Rebuild trusted attestation |
| 15 | Argo CD reintroduces bad config | Git desired state unchanged | Revert GitOps commit |
| 16 | Secret printed in CI logs | Unsafe debug output | Revoke credential and contain |

## 33. Production runbook — secure release authorization

1. Confirm protected source revision and trusted CI runner.
2. Validate test results, SBOM, vulnerability findings and exceptions.
3. Verify exact OCI digest, signature identity and build provenance.
4. Confirm SecretStore/ExternalSecret Ready and least-privilege IAM.
5. Confirm admission policies and webhook health.
6. Merge approved GitOps MR and reconcile Argo CD.
7. Verify actual Pod imageID, application readiness and SLOs.
8. Archive redacted evidence and release-owner sign-off.

## 34. Production runbook — secret synchronization incident

1. Declare impact and affected applications.
2. Inspect ESO Ready conditions, provider errors and controller health.
3. Verify secret-manager availability, IAM trust and remote key existence.
4. Determine whether the existing Kubernetes Secret is valid or stale.
5. Restore scoped access or correct GitOps references.
6. Restart affected applications only when required for new credential adoption.
7. Validate health and revoke old credentials where applicable.
8. Document incident and rotation lag without exposing values.

## 35. Production runbook — admission enforcement outage

1. Identify affected policy, webhook and failurePolicy.
2. Inspect controller Pods, Service endpoints, certificates and events.
3. Capture GitOps revision and denied API operations.
4. Restore the approved pinned policy-controller deployment.
5. Test admission on synthetic compliant and noncompliant resources.
6. Use a narrowly scoped emergency exception only with security approval.
7. Reconcile affected Argo CD Applications.
8. Record availability impact and enforcement gap.

## 36. Production runbook — compromised encryption or signing key

1. Declare security incident and freeze affected promotions/decryptions.
2. Determine whether signing, SOPS, Sealed Secrets or cloud IAM identity is compromised.
3. Revoke affected access and rotate underlying application credentials where exposed.
4. Inventory affected Git revisions, OCI artifacts and running workloads.
5. Re-encrypt/reseal or rebuild/resign under approved replacement identities.
6. Validate historical recovery obligations before retiring old keys.
7. Update admission and decryption trust configuration.
8. Audit access, confirm recovery and document root cause.

## 37. Production runbook — secure GitOps disaster recovery

1. Establish clean recovery cluster and validated access boundaries.
2. Restore GitOps revision and approved controller versions.
3. Recreate workload identity and scoped secret-manager permissions.
4. Restore decryption keys from encrypted, tested escrow where required.
5. Restore admission verification policy and trusted signer identity.
6. Deploy an approved signed digest.
7. Confirm Secret reconciliation, policy enforcement and runtime health.
8. Measure recovery time, validate evidence and rotate temporary credentials.

**Do not disable policy enforcement permanently to make a recovery cluster appear healthy.**

## 38. Audit evidence template

~~~text
Capstone / change ID:
Staging cluster and namespace:
Source commit and GitLab MR:
Pipeline ID and trusted runner:
OCI digest and imageID:
SBOM, scan and exception references:
Signature identity and provenance:
GitOps MR and Argo CD revision:
Policy engine, policy revision and admission result:
ESO SecretStore and ExternalSecret status:
Workload identity and IAM scope:
SOPS/Sealed Secrets key custody and restore test:
Rotation and revocation evidence:
Negative security tests and outcomes:
Recovery exercise RTO and service health:
Security reviewer, owner and archive:
~~~

No plaintext credentials, private keys, tokens or decoded Secret objects belong in evidence.

## 39. Scored enterprise readiness assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| GitLab source, CI and GitOps governance | 15 | Protected reviews and release revision |
| Secrets, workload identity and rotation | 20 | ESO Ready, scoped IAM, rotation drill |
| Encryption key custody and DR | 15 | SOPS/Sealed Secrets recovery |
| Admission and policy exceptions | 20 | Allow/deny tests, narrow exceptions |
| Signing, SBOM and provenance | 20 | Digest-linked verified evidence |
| Observability, incident runbooks and audit | 10 | Recovery timing and audit packet |
| **Total** | **100** | |

**Pass:** at least **85/100**, with every critical control passing: no plaintext credential exposure, no unauthorized secret access, no unsigned workload admission in enforced scope, no unauthorized policy exception, and a demonstrated secure recovery. A high score cannot compensate for failure of a critical control.

## 40. Final acceptance checklist

- [ ] Source and GitOps branches require independent review.
- [ ] Immutable OCI digests are used and verified.
- [ ] SBOM, scan, signature and provenance match the deployed digest.
- [ ] Untrusted or unsigned images are rejected by admission.
- [ ] ESO uses scoped workload identity and least-privilege provider access.
- [ ] Applications consume secrets without printing values.
- [ ] Secret rotation and application reload are measured.
- [ ] SOPS recipient and Sealed Secrets key recovery are tested.
- [ ] Historical encrypted revisions remain recoverable as required.
- [ ] Native VAP/Gatekeeper/Kyverno policies are tested before enforcement.
- [ ] Admission controller failure behavior is documented.
- [ ] Policy exceptions are approved, narrow and time-bound.
- [ ] GitOps rollback restores approved desired state.
- [ ] Signing and decryption compromise runbooks are tested.
- [ ] Fifteen integrated labs have pass/fail evidence.
- [ ] Independent security and SRE reviewers approve the audit packet.

## 41. Knowledge check

1. Why should one controller own each Kubernetes Secret?
2. What is the difference between ESO provider identity and application identity?
3. Why does SOPS key retirement require historical revision testing?
4. Why does a replacement Sealed Secrets controller need old key material?
5. Why is a signature insufficient without signer identity and provenance verification?
6. How do CI policy checks differ from admission enforcement?
7. Why can an Argo CD sync fail after CI and GitOps approval succeed?
8. Why might a rotated Kubernetes Secret not update a running process?
9. How should a compromised signing identity affect existing workloads?
10. What evidence proves the recovered cluster is both available and secure?

## 42. References

- [External Secrets Operator](https://external-secrets.io/latest/)
- [SOPS](https://github.com/getsops/sops)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/)
- [Kyverno](https://kyverno.io/docs/)
- [Sigstore Cosign](https://docs.sigstore.dev/cosign/)
- [SLSA](https://slsa.dev/spec/)
- [Argo CD](https://argo-cd.readthedocs.io/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 065 complete — Part 13 complete (Chapters 061–065).**

**Next:** Chapter 066 — Amazon EKS GitOps Architecture, Cluster Bootstrap and Platform Foundations, beginning Part 14: Amazon EKS.