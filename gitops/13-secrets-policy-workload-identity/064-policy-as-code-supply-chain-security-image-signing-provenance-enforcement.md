# Chapter 064 — Policy-as-Code Supply Chain Security, Image Signing and Provenance Enforcement

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 13:** Secrets, Policy and Workload Identity  
**Chapter:** 064 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Security Engineers, Kubernetes Administrators and Release Managers

> **Safety:** All exercises use disposable staging namespaces and synthetic workloads. Image signatures, provenance, SBOMs and admission policy must be verified together. A signed image is not automatically secure; a valid signature proves a trusted signer approved specific content under the configured policy.

## 1. Learning objectives

After this chapter, you can:

1. Model software supply-chain threats from source through production runtime.
2. Build and promote immutable OCI images by digest.
3. Generate and validate Software Bills of Materials (SBOMs).
4. Sign OCI artifacts with Cosign using approved identities.
5. Verify signatures, trusted issuer/subject and build provenance.
6. Enforce trusted artifacts through GitLab CI/CD and Kubernetes admission.
7. Integrate verification with Argo CD, Argo Rollouts and GitOps promotion.
8. Handle compromised signing identities, vulnerable dependencies and emergency releases.
9. Test negative security cases and complete operational recovery drills.

## 2. Supply-chain architecture

~~~text
Developer source commit
        |
GitLab protected MR and pipeline
        |
Build in trusted isolated runner
        |
Generate SBOM + vulnerability scan
        |
Create provenance attestation
        |
Sign immutable OCI digest
        |
Push image, SBOM, attestation and signature to registry
        |
GitOps MR pins approved digest
        |
Argo CD reconciles workload
        |
Admission verifies signer + digest + policy
        |
Kubernetes starts approved Pods
        |
Runtime observability and incident response
~~~

**Trust must span the chain.** A valid signature from an untrusted identity, a valid SBOM for the wrong digest or a successful vulnerability scan on a different image does not satisfy the release policy.

## 3. Threat model

| Attack | Typical control | Residual risk |
| --- | --- | --- |
| Compromised source branch | Protected MR and CODEOWNERS | Insider collusion |
| Malicious dependency | Lockfiles, SBOM and scanning | Zero-day/unreported issues |
| Compromised CI runner | Ephemeral hardened runner | Runner image/supply-chain compromise |
| Tag substitution | Digest pinning | Signed malicious digest |
| Stolen signing key | Keyless identity or protected KMS | Identity compromise |
| Forged provenance | Verified trusted builder identity | Compromised builder |
| Registry tampering | Signature/digest verification | Availability and rollback issues |
| Unapproved deployment | Admission verification and GitOps RBAC | Policy bypass or break-glass abuse |
| Stale vulnerable image | Continuous rescanning | Newly disclosed CVEs |

## 4. Core terminology

- **OCI digest:** content-addressed identifier such as sha256:...; unlike mutable tags it identifies exact artifact content.
- **SBOM:** inventory of software components and dependencies, often SPDX or CycloneDX.
- **Signature:** cryptographic binding of a digest to a signing identity/key.
- **Attestation:** signed statement about an artifact, such as build provenance or SBOM.
- **Provenance:** information about source, builder, materials and build process.
- **SLSA:** framework for assessing supply-chain security properties and provenance.
- **Sigstore:** ecosystem for signing and verifying artifacts, including Cosign and identity transparency mechanisms.
- **Admission policy:** runtime enforcement at Kubernetes API request time.

## 5. Immutable digest policy

A workload image should use:

~~~yaml
containers:
  - name: web
    image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_64_HEX_DIGEST
~~~

The placeholder is not deployable. In real releases, capture the registry-reported digest after push, verify the digest refers to the intended platform/manifest, and commit that exact digest to GitOps. Multi-architecture indexes and platform-specific manifests have distinct digests; understand which object your verification policy covers.

## 6. Security responsibility matrix

| Boundary | Owner | Mandatory evidence |
| --- | --- | --- |
| Source review | Engineering | Approved commit/MR |
| Runner trust | Platform security | Runner identity and isolation |
| Build | CI | Reproducible metadata and digest |
| SBOM | Security/CI | SBOM linked to digest |
| Signature | Release security | Trusted signer identity |
| Provenance | CI platform | Trusted builder and source |
| GitOps promotion | Release owner | Protected MR and digest |
| Admission | Platform security | Allow/deny decision |
| Runtime | SRE | Observed running digest and alerts |

## 7. Prerequisites

Use an approved pinned Cosign binary, OCI registry, Syft or equivalent SBOM tool, Grype/Trivy or approved vulnerability scanner, GitLab runner, Argo CD staging Application, Kubernetes admission engine and disposable namespace.

~~~bash
cosign version
syft version
kubectl config current-context
kubectl get validatingwebhookconfigurations
kubectl -n demo-staging get deploy,pods
~~~

Tool CLI syntax and signing flows can change between releases. Confirm installed versions, registry capabilities and organizational signing policy before using examples.

## 8. Generate an SBOM

After building and pushing a synthetic test image, use its **real digest**:

~~~bash
syft registry.example.internal/demo/web@sha256:REAL_DIGEST   -o cyclonedx-json=sbom.cdx.json
~~~

Do not substitute a mutable tag for release evidence. Review SBOM completeness, package ecosystem coverage, licensing, sensitive build-path leakage and image provenance. SBOMs may omit dynamically downloaded runtime dependencies or opaque binaries.

## 9. Scan dependencies and images

Example using a scanner compatible with Syft SBOM output:

~~~bash
grype sbom:sbom.cdx.json --fail-on high
~~~

A severity threshold is an example, not a universal production standard. Define exception ownership, exploitability review, compensating controls, expiry and re-scan cadence. Scanner findings may be incomplete or incorrect.

## 10. Cosign signing models

| Model | Identity source | Key custody |
| --- | --- | --- |
| Local key pair | Private signing key | Operator-managed; protect carefully |
| Cloud KMS | Cloud IAM identity | KMS-managed key |
| Keyless/OIDC | Short-lived identity certificate | Identity provider and Sigstore trust |
| Hardware-backed | HSM/PKCS11 or supported integration | Hardware/key-service managed |

Prefer short-lived workload identity and trusted CI issuer where practical. Do not store private signing keys as repository files or unprotected CI variables.

## 11. Cosign sign and verify by digest

**Illustrative keyless workflow:** requires an approved OIDC-capable environment and registry permissions.

~~~bash
cosign sign --yes registry.example.internal/demo/web@sha256:REAL_DIGEST
~~~

Verification must constrain the expected signer and OIDC issuer rather than merely checking that *someone* signed the image:

~~~bash
cosign verify   --certificate-identity "https://gitlab.example.internal/group/project//.gitlab-ci.yml@refs/heads/main"   --certificate-oidc-issuer "https://gitlab.example.internal"   registry.example.internal/demo/web@sha256:REAL_DIGEST
~~~

The identity and issuer above are **illustrative**, not a guarantee of the certificate identity format issued by your GitLab/Sigstore integration. Discover the actual trusted certificate subject/issuer, validate the integration and pin the exact approved identity pattern. Public Sigstore keyless signing depends on supported OIDC providers and current trust configuration; private GitLab installations may require a private Fulcio/Rekor or alternative KMS signing design.

## 12. KMS-backed signing

When using cloud KMS, ensure the signing principal can invoke only the required KMS signing operations on the approved key. Verifiers need the trusted public key or supported key reference.

~~~bash
cosign sign --key "awskms:///arn:aws:kms:us-east-1:111122223333:key/REPLACE_KEY_ID"   registry.example.internal/demo/web@sha256:REAL_DIGEST
~~~

This command is a provider URI example; validate the installed Cosign version and KMS URI syntax. Do not grant wildcard kms:Sign across an account. Use separation of duties between signers and production policy administrators.

## 13. Attest build provenance

A provenance statement should bind:

- Subject: exact OCI image digest.
- Source repository and commit.
- Trusted builder identity and build invocation.
- Build parameters and material dependencies.
- Timestamp and invocation metadata.
- Relevant isolation and integrity properties.

The format and generation method must align with your chosen SLSA/in-toto statement and tool versions. Do not manufacture a provenance document with an arbitrary source SHA and call it verified evidence.

## 14. Verify provenance policy

A production verifier should require:

1. Valid attestation signature.
2. Trusted builder identity and issuer.
3. Subject digest equals the workload image digest.
4. Source repository matches an approved path.
5. Source commit is an approved protected revision.
6. Builder provenance meets the organization's required trust level.
7. Attestation predicate type and schema are expected.
8. Timestamp and freshness satisfy release policy.

Do not trust arbitrary self-signed attestations solely because their JSON shape is correct.

## 15. SBOM association and storage

Attach SBOMs to the exact OCI digest using an approved OCI referrer/attestation workflow. Registry support and garbage collection behavior vary.

Maintain retention for the image, signature, SBOM and provenance as one release evidence set. If the registry deletes signatures or attestations, admission verification can fail even while the image digest remains available.

## 16. GitLab CI/CD example

This is a production-pattern skeleton, not a turnkey pipeline. Internal builder/signing scripts, approved pinned images and secure identities must be supplied.

~~~yaml
stages: [test, build, scan, attest, promote]

unit_tests:
  stage: test
  image: registry.example.internal/ci/python:PINNED_DIGEST
  script:
    - python -m pip install -r requirements.txt
    - python -m pytest -q

build_image:
  stage: build
  image: registry.example.internal/ci/secure-builder:PINNED_DIGEST
  script:
    - ./ci/build-and-push.sh
  artifacts:
    reports:
      dotenv: release.env
    expire_in: 1 day

scan_image:
  stage: scan
  image: registry.example.internal/ci/security-tools:PINNED_DIGEST
  needs:
    - job: build_image
      artifacts: true
  script:
    - ./ci/generate-and-scan-sbom.sh

sign_and_attest:
  stage: attest
  image: registry.example.internal/ci/cosign-tools:PINNED_DIGEST
  needs:
    - job: build_image
      artifacts: true
    - scan_image
  script:
    - ./ci/sign-and-attest.sh
    - ./ci/verify-release-evidence.sh

propose_gitops:
  stage: promote
  image: registry.example.internal/ci/gitlab-client:PINNED_DIGEST
  needs:
    - job: build_image
      artifacts: true
    - sign_and_attest
  resource_group: staging-gitops-promotion
  script:
    - ./ci/propose-gitops-mr.sh
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

**Critical:** placeholder image references and internal scripts must be implemented. The dotenv report may contain only non-secret metadata such as IMAGE_DIGEST; never include signing keys, OIDC tokens, registry passwords or kubeconfigs.

## 17. GitOps promotion security

Recommended sequence:

~~~text
1. Build from reviewed source commit.
2. Push and record immutable image digest.
3. Generate SBOM and vulnerability findings.
4. Sign image and trusted provenance attestation.
5. Verify all evidence against policy.
6. Open protected GitOps MR updating digest.
7. Approve and merge through controlled release boundary.
8. Argo CD reconciles desired image.
9. Admission verifies image and attestation policy.
10. Runtime checks confirm actual digest and health.
~~~

An approved GitOps MR is not proof that the image signature is valid. Admission verification provides an independent runtime control.

## 18. Kyverno verifyImages policy concept

Kyverno supports image verification, but verifyImages syntax and supported attestors/attestations vary by version. Configure a policy requiring an approved image registry, trusted signer identity, expected attestation predicate and immutable digest.

**Do not deploy an unverified generic example as production enforcement.** Use the pinned Kyverno version's verified examples and test against signed and unsigned synthetic images. For keyless verification, constrain certificate identity and issuer; for key-based verification, use an approved public key or KMS verifier.

## 19. Gatekeeper and native VAP roles

Gatekeeper or native ValidatingAdmissionPolicy can reject mutable tags, unapproved registries and insecure workload settings. Cryptographic signature verification requires a trustworthy verifier or integrated admission component; a CEL string match or Rego check on image name alone cannot prove a signature.

Design separate layers:

- Native VAP/Gatekeeper: schema, digest presence, registry allowlist.
- Signature-aware admission engine: cryptographic verification and provenance.
- GitLab CI: early evidence validation.
- Argo CD: desired-state reconciliation.
- SRE monitoring: running digest and security alerts.

## 20. Runtime and continuous reassessment

Admission checks occur when objects are admitted; newly disclosed CVEs or revoked signers may affect already-running workloads without a new admission request.

Schedule approved inventory scans and monitor:

- Running digest inventory.
- New vulnerability advisories affecting SBOM components.
- Signature/attestation availability.
- Revoked or compromised signer identities.
- Policy changes and admission bypasses.
- Drift between GitOps digest and observed Pods.
- Artifact retention and registry outages.

Use controlled rollout replacement to remediate running workloads; do not assume admission automatically evicts them.

## 21. Lab A — Immutable digest build and inventory

1. Build a synthetic application in a trusted staging runner.
2. Push it to a disposable registry repository.
3. Capture the registry-reported digest.
4. Deploy by digest, not tag.
5. Confirm running Pod imageID and approved GitOps digest.
6. Record source SHA, builder and release ID.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get pods   -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[*].image,IMAGEID:.status.containerStatuses[*].imageID
~~~

**Pass:** running workload content matches the approved immutable artifact.

## 22. Lab B — SBOM generation and vulnerability policy

1. Generate CycloneDX or SPDX SBOM for the exact digest.
2. Run the approved vulnerability scanner.
3. Identify direct and transitive dependencies.
4. Introduce a synthetic vulnerable test dependency.
5. Verify the policy gate rejects the release or requires an approved exception.
6. Archive the redacted SBOM and findings.

**Pass:** SBOM and scan evidence refer to the same image digest.

## 23. Lab C — Sign and verify trusted image

1. Sign a synthetic image with approved staging identity.
2. Verify cryptographic signature.
3. Constrain expected issuer and identity.
4. Attempt verification with an incorrect signer identity.
5. Confirm rejection.
6. Record digest, signer and verification outcome.

**Pass:** trusted signature succeeds; untrusted identity fails.

## 24. Lab D — Provenance attestation verification

1. Generate a trusted build attestation for the synthetic image.
2. Verify its signature and subject digest.
3. Validate source repository, commit and builder identity.
4. Attempt to verify an attestation for a different digest.
5. Confirm rejection.
6. Record provenance predicate and verification policy version.

**Pass:** subject and trusted builder identity are enforced.

## 25. Lab E — GitLab pipeline security gates

1. Trigger a clean staging pipeline.
2. Confirm tests, SBOM, scanning, signing and attestation complete.
3. Confirm only the verified digest is proposed to GitOps.
4. Simulate a failed vulnerability threshold.
5. Verify promotion is blocked.
6. Check logs and artifacts for secret leakage.

**Pass:** no unverified digest reaches the GitOps promotion MR.

## 26. Lab F — Admission rejects unsigned image

1. Deploy a signature-verifying policy in Audit mode.
2. Test a signed staging image.
3. Test an unsigned synthetic image.
4. Verify audit results and false-positive behavior.
5. Switch a disposable namespace to Enforce after approval.
6. Confirm unsigned image is denied.

**Pass:** cryptographic verification is enforced at the actual admission boundary.

## 27. Lab G — Registry/tag substitution attack

1. Build two different synthetic images.
2. Assign the same mutable tag sequentially.
3. Observe tag resolution changing over time.
4. Pin the approved digest in GitOps.
5. Verify signature and runtime digest remain tied to the approved content.
6. Document why mutable tags are insufficient for release identity.

**Pass:** tag changes do not alter the pinned deployed artifact.

## 28. Lab H — Signing identity compromise tabletop

1. Simulate unauthorized access to a staging signing identity.
2. Freeze promotions from the affected signer.
3. Revoke/rotate signing credentials or identity trust.
4. Identify affected images and attestations.
5. Update admission trusted-identity policy.
6. Rebuild/resign clean artifacts and redeploy if needed.
7. Verify historical audit and incident evidence.

**Pass:** trust revocation is enforced and potentially compromised releases are reviewed.

## 29. Lab I — Registry and attestation outage

1. Verify a healthy signed staging release.
2. Simulate signature/attestation retrieval failure in a disposable environment.
3. Observe admission failure or configured fallback.
4. Confirm production policy would not silently accept unsigned content.
5. Restore registry/referrer availability.
6. Revalidate the same digest and signature.

**Pass:** outage behavior is documented, measurable and security-approved.

## 30. Lab J — Full GitOps release and rollback

1. Promote a signed, attested digest through protected GitOps MR.
2. Reconcile Argo CD and confirm admission acceptance.
3. Verify observed Pod digest and application SLO.
4. Simulate a post-release application regression.
5. Revert GitOps to a previously approved signed digest.
6. Verify signature, provenance and compatibility of rollback target.
7. Measure recovery time and preserve evidence.

**Pass:** rollback restores a trusted, approved artifact, not merely an older mutable tag.

## 31. Troubleshooting — fourteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Cosign verification fails | Wrong signer/issuer | Inspect trusted identity policy |
| 2 | Signature missing | Registry referrer/retention issue | Restore verified evidence |
| 3 | Image digest mismatch | Wrong manifest/index or tag | Reconcile exact digest |
| 4 | SBOM scan finds nothing | Unsupported ecosystem/empty SBOM | Validate coverage |
| 5 | Vulnerability gate fails | High-risk dependency | Patch or approve scoped exception |
| 6 | Keyless signing fails | OIDC trust/integration issue | Verify supported issuer and token |
| 7 | KMS signing denied | IAM/key policy | Restore least-privilege access |
| 8 | Attestation rejected | Wrong predicate/subject | Rebuild trusted provenance |
| 9 | CI passes, admission denies | Different verifier policy | Align policy revisions |
| 10 | Argo CD repeatedly fails sync | Unsigned digest in GitOps | Revert MR or sign approved artifact |
| 11 | Rollback image denied | Old signer revoked | Rebuild approved recovery artifact |
| 12 | Runtime image vulnerable | New CVE after deployment | Rescan and remediate |
| 13 | Signing identity compromised | Trust boundary breached | Revoke and review affected releases |
| 14 | Policy bypass during outage | Fail-open webhook | Restore enforcement and audit |

## 32. Production runbook — secure release

**Preflight:** verify reviewed source, runner trust, dependency locks, artifact digest, SBOM, vulnerability findings, signature identity, provenance predicate and GitOps approval.

**Build:** produce and push the immutable image; generate SBOM, scan and attest in a trusted pipeline.

**Verify:** validate digest, signature, trusted issuer/subject, provenance builder/source and policy version.

**Promote:** merge approved GitOps digest update and reconcile Argo CD.

**Enforce:** confirm admission accepted the artifact and actual Pods run the approved digest.

**Close:** record SLOs, evidence retention, signer identity and rollback target.

## 33. Production runbook — admission signature failure

1. Freeze affected promotions.
2. Capture admission denial, digest, signer and policy revision.
3. Check registry, signature/referrer availability and verifier trust.
4. Determine whether the image is unsigned, untrusted or evidence is unavailable.
5. Restore trusted evidence or revert to a previously approved signed digest.
6. Avoid blanket bypass of signature enforcement.
7. Confirm workload health and audit the recovery.

## 34. Production runbook — compromised signer

1. Declare security incident and stop promotions from affected identity.
2. Revoke signing credentials or remove compromised issuer/subject from trusted policy.
3. Inventory signed images, attestations and running workloads.
4. Assess whether source, runner or builder was also compromised.
5. Rebuild and re-sign clean artifacts under a new trusted identity.
6. Update admission policy and GitOps revisions.
7. Validate production running digests and preserve evidence.
8. Conduct post-incident review and improve signer isolation.

## 35. Production runbook — vulnerable production artifact

1. Correlate advisory/CVE to running image digests and SBOM components.
2. Evaluate exploitability and business exposure.
3. Prioritize emergency patch, mitigation or approved rollback.
4. Build and verify a new signed artifact.
5. Promote via emergency change controls.
6. Verify runtime digest and application SLOs.
7. Document exception expiry and remediation completion.

## 36. Evidence template

~~~text
Release / incident ID:
Source repository, commit and MR:
GitLab pipeline and runner identity:
OCI image digest and architecture:
SBOM format and reference:
Vulnerability scan report and exception:
Signature identity / KMS key reference:
Signature verification result:
Provenance predicate and trusted builder:
GitOps MR, approvers and commit:
Admission policy version and decision:
Argo CD Application and sync revision:
Observed running Pod imageID:
Rollback target and compatibility:
Recovery duration:
Evidence archive and owner:
~~~

Never include private keys, OIDC tokens, cloud credentials or raw secrets in release evidence.

## 37. Acceptance checklist

- [ ] Release artifacts are immutable and referenced by digest.
- [ ] SBOMs are generated and associated with the correct digest.
- [ ] Vulnerability policies and exceptions are documented.
- [ ] Trusted signing identity and issuer are verified.
- [ ] Provenance attestation subject and builder are validated.
- [ ] GitLab blocks unverified release promotion.
- [ ] Argo CD deploys only approved GitOps digests.
- [ ] Admission rejects unsigned/untrusted images in enforced scope.
- [ ] Runtime observed digest matches the approved artifact.
- [ ] Compromised signer and registry outage procedures are tested.
- [ ] Rollback targets remain trusted and compatible.
- [ ] Ten hands-on labs have evidence and owners.
- [ ] Production runbooks and security approvals are complete.

## 38. Knowledge check

1. Why is an image digest stronger than a mutable tag?
2. Why is a signed image not necessarily safe?
3. What is the difference between SBOM, signature and provenance?
4. Why must verification constrain the trusted signer identity?
5. Why should attestations bind to the exact image digest?
6. How does a protected GitOps MR differ from admission verification?
7. Why can newly disclosed CVEs affect already-admitted Pods?
8. What happens when registry signatures are garbage-collected?
9. Why might an old rollback image be rejected after signer revocation?
10. What steps are required after signing identity compromise?

## 39. References

- [Sigstore Cosign](https://docs.sigstore.dev/cosign/)
- [Sigstore Overview](https://docs.sigstore.dev/)
- [SLSA Specification](https://slsa.dev/spec/)
- [in-toto Attestations](https://in-toto.io/)
- [Syft](https://github.com/anchore/syft)
- [Grype](https://github.com/anchore/grype)
- [Kyverno Image Verification](https://kyverno.io/docs/writing-policies/verify-images/)
- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)

---

**Chapter 064 complete.** Next: **Chapter 065 — Enterprise GitOps Security, Secrets and Policy Compliance Capstone**, completing Part 13.