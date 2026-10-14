# Chapter 062 — SOPS, Sealed Secrets and Encryption Key Lifecycle for GitOps

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 13:** Secrets, Policy and Workload Identity  
**Chapter:** 062 / 100  
**Audience:** Platform Engineers, SREs, Security Engineers, DevSecOps and Kubernetes Administrators

> **Safety:** All executable examples use disposable staging namespaces and synthetic credentials. Never use production key material in labs, commit unencrypted secret values, publish age private keys, or print decrypted Kubernetes Secret values into CI logs.

## 1. Learning objectives

After this chapter you will be able to:

1. Explain encrypted secrets in GitOps and their remaining risks.
2. Compare SOPS with age, SOPS with cloud KMS, Sealed Secrets and External Secrets Operator.
3. Configure SOPS encryption rules and safely edit encrypted manifests.
4. Implement Sealed Secrets with the correct namespace/name scope.
5. Design secure Argo CD secret decryption with a controlled plugin or rendering process.
6. Rotate encryption keys without losing the ability to decrypt historical revisions.
7. Back up and restore controller keys for disaster recovery.
8. Prevent plaintext exposure through GitLab, shell history, logs, artifacts and debugging.
9. Execute hands-on encryption, rotation, recovery and incident-response labs.

## 2. Threat model and encryption boundaries

~~~text
Developer workstation / approved CI
         |
      plaintext
         | encrypt before commit
         v
Git repository -> encrypted SOPS or SealedSecret YAML
         |
      Argo CD / GitOps renderer
         |
  decryption identity / Sealed Secrets controller
         |
         v
Kubernetes Secret -> application Pod
~~~

**Encryption in Git does not mean end-to-end secret protection.** Plaintext exists at creation/edit time, at the decryption boundary, inside Kubernetes Secrets and in application memory. Secure workstation handling, short-lived identities, RBAC, etcd encryption, log redaction and backup encryption remain necessary.

## 3. Comparison of approaches

| Approach | Stored in Git | Decryption boundary | Main dependency |
| --- | --- | --- | --- |
| SOPS + age | Encrypted YAML/JSON | Authorized renderer/editor | Protected age private identity |
| SOPS + cloud KMS | Encrypted YAML/JSON | Workload or CI identity using KMS | KMS IAM, key availability |
| Bitnami Sealed Secrets | SealedSecret custom resource | In-cluster controller | Controller private key |
| External Secrets Operator | References, not values | External provider -> Kubernetes Secret | Secret manager and workload identity |

SOPS is an encryption tool, not a Kubernetes controller. Argo CD does not automatically decrypt SOPS manifests without a supported rendering integration. Sealed Secrets controller decrypts SealedSecret resources in the cluster. ESO fetches secret values from an external provider; it does not require encrypted values in Git.

## 4. Enterprise selection criteria

Choose using blast radius, key custody, cloud dependencies, audit requirements, GitOps renderer hardening, rotation frequency, multi-cluster portability, backup requirements and operator expertise.

- Prefer ESO when a managed external secret store and workload identity are already available.
- Consider SOPS with cloud KMS when encrypted values must be versioned in Git with auditable cloud key usage.
- Consider SOPS with age for portable encryption where private-key custody can be rigorously controlled.
- Consider Sealed Secrets for cluster-bound encrypted Kubernetes Secret delivery, with tested controller-key backup/restore.

No method eliminates the need to protect the materialized Kubernetes Secret.

## 5. Prerequisites

Use a disposable staging namespace, approved pinned versions of sops, age, kubeseal, kubectl, Helm and Argo CD, and a synthetic credential such as a non-production demo password.

~~~bash
kubectl config current-context
kubectl get namespace demo-staging
sops --version
age --version
kubeseal --version
kubectl get crd sealedsecrets.bitnami.com
~~~

Commands that reference Sealed Secrets require a healthy controller and CRD. Do not install unreviewed binaries or Helm charts from unknown sources.

## 6. SOPS and age key generation

Generate a **lab-only** age identity locally. The private identity must remain outside Git and should be protected with restrictive file permissions and approved secret storage.

~~~bash
umask 077
mkdir -p "$HOME/.config/sops/age"
age-keygen -o "$HOME/.config/sops/age/keys.txt"
age-keygen -y "$HOME/.config/sops/age/keys.txt"
~~~

The second command prints only the public recipient. Record the public recipient in the repository's encryption policy. Never paste the private identity into issues, chat, CI variables with broad access or release evidence.

**Windows/PowerShell:** use an approved protected user directory and the native sops/age binaries; avoid assuming POSIX chmod or umask semantics. Ensure NTFS ACLs restrict the private key.

## 7. SOPS configuration

Example .sops.yaml:

~~~yaml
creation_rules:
  - path_regex: ^gitops/apps/demo-web/overlays/staging/.*secret.*\.yaml$
    encrypted_regex: '^(data|stringData)$'
    age: age1REPLACE_WITH_REAL_PUBLIC_RECIPIENT
~~~

The age recipient above is a placeholder. The path_regex must match the actual file path **relative to the SOPS working directory**, and encrypted_regex must match the intended YAML fields. Validate that only non-sensitive metadata remains plaintext.

A more conservative policy may encrypt entire YAML value trees except a documented set of metadata fields. Do not assume the regex above protects sensitive values placed in annotations or custom fields.

## 8. Create and encrypt a synthetic Kubernetes Secret

Create an example plaintext file **outside the Git repository**:

~~~yaml
apiVersion: v1
kind: Secret
metadata:
  name: demo-db-credentials
  namespace: demo-staging
type: Opaque
stringData:
  password: synthetic-not-a-real-password
~~~

Then encrypt with a real public recipient and a policy that matches the destination path:

~~~bash
sops encrypt --in-place gitops/apps/demo-web/overlays/staging/demo-secret.yaml
sops filestatus gitops/apps/demo-web/overlays/staging/demo-secret.yaml
~~~

For this lab, first create the file in the target path, verify it is excluded from staging until encryption is complete, then encrypt immediately. Never commit the temporary plaintext state. An even safer workflow encrypts from a protected temporary directory directly to the final encrypted file, with an explicit recipient and validated policy.

**Important:** sops filestatus reports encryption status; also inspect the file to ensure no secret values are visible.

## 9. Editing and inspecting encrypted manifests

~~~bash
sops edit gitops/apps/demo-web/overlays/staging/demo-secret.yaml
sops filestatus gitops/apps/demo-web/overlays/staging/demo-secret.yaml
git diff -- gitops/apps/demo-web/overlays/staging/demo-secret.yaml
~~~

SOPS edit decrypts into a temporary editor buffer; editor swap files, terminal scrollback and temporary files are part of the threat model. Use a hardened workstation/editor and never run verbose shell tracing during decryption.

Avoid sops decrypt piped to tee, grep, log capture or CI artifacts. If a lab needs to prove successful decryption, validate status and functional application behavior rather than printing the value.

## 10. SOPS with cloud KMS

SOPS supports cloud KMS backends such as AWS KMS, Azure Key Vault and Google Cloud KMS. Use workload identity or short-lived federated credentials instead of static cloud keys.

AWS example policy (replace identifiers):

~~~json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:us-east-1:111122223333:key/REPLACE-WITH-KEY-ID"
    }
  ]
}
~~~

Separate encryption/editor privileges from runtime decryption where feasible. The runtime decryption role may only need kms:Decrypt; exact permissions depend on SOPS operations and KMS key policy. Apply encryption context and resource restrictions where supported.

Cloud KMS key rotation of backing key material is different from changing the SOPS recipient/key ARN. Plan both separately.

## 11. Key lifecycle states

~~~text
Proposed -> Active -> Rotating -> Retired -> Disabled -> Destroyed
                  |          |
                  +---- backup/restore verification
~~~

For each key maintain an owner, environment, allowed decryptors, activation date, retirement date, backup/escrow policy, audit trail and destruction approval.

**Critical rule:** do not destroy an old decryption key until all required historical Git revisions, backups and disaster-recovery artifacts have been re-encrypted or have a tested recovery path.

## 12. Re-encrypt SOPS files after recipient changes

When adding or replacing recipients, update the SOPS creation rules, then use the supported updatekeys workflow and verify decryptability with the intended identity:

~~~bash
sops updatekeys gitops/apps/demo-web/overlays/staging/demo-secret.yaml
sops filestatus gitops/apps/demo-web/overlays/staging/demo-secret.yaml
~~~

Check the exact SOPS version and updatekeys behavior before applying across many files. Updating recipients changes who can unwrap the data key; it is not necessarily a full data-key rotation. Where the threat model requires new data keys, use the supported rotate workflow and verify all recipients and historical recovery requirements.

Do not remove the previous identity until the new one has been tested in the actual GitOps decryption environment.

## 13. Sealed Secrets architecture

~~~text
kubeseal client -> controller public certificate
          |
          v
SealedSecret YAML in Git
          |
          v
Sealed Secrets controller with private key
          |
          v
Kubernetes Secret in target namespace
          |
          v
Application
~~~

The controller private key is a high-value asset. A new controller installed in a replacement cluster cannot automatically decrypt existing SealedSecrets unless the original private key is restored or resources are resealed for the new key.

## 14. Install and verify Sealed Secrets

Install a pinned, approved Sealed Secrets controller through a reviewed GitOps bootstrap process. Validate the release's actual controller name and namespace:

~~~bash
kubectl get crd sealedsecrets.bitnami.com
kubectl -n kube-system get deploy,pods | grep sealed
kubeseal --fetch-cert   --controller-name sealed-secrets   --controller-namespace kube-system > staging-sealed-secrets-public.pem
~~~

The controller name/namespace above are examples; adjust to the actual installation. The fetched certificate is public but must still be authenticated against the intended cluster/controller to prevent encryption to an attacker-controlled key.

## 15. Seal a synthetic Secret safely

Prepare a synthetic Secret manifest in a protected temporary location, not in the Git repository. Encrypt to a SealedSecret using the verified controller certificate:

~~~bash
kubeseal --format yaml   --cert staging-sealed-secrets-public.pem   --scope strict   < demo-secret-plaintext.yaml   > gitops/apps/demo-web/overlays/staging/demo-sealedsecret.yaml
~~~

Strict scope binds ciphertext to the Secret name and namespace. Renaming or moving it generally requires resealing. Namespace-wide or cluster-wide scope weakens that binding and must be explicitly approved.

Delete the temporary plaintext file using your organization's secure-handling procedure after validating the sealed output. Do not claim normal filesystem deletion guarantees forensic erasure.

## 16. SealedSecret manifest shape

~~~yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: demo-db-credentials
  namespace: demo-staging
spec:
  encryptedData:
    password: REPLACE_WITH_REAL_KUBESEAL_CIPHERTEXT
  template:
    metadata:
      name: demo-db-credentials
      namespace: demo-staging
    type: Opaque
~~~

This is a **schema illustration** and will not decrypt with placeholder ciphertext. Generate the real resource with kubeseal and verify it using the installed CRD.

## 17. Sealed Secrets controller key rotation

Sealed Secrets may renew sealing certificates while retaining old private keys to decrypt historical ciphertext. Rotation of the sealing certificate is **not the same** as eliminating compromised historical private keys.

A safe rotation plan:

1. Back up controller private keys using approved encrypted, access-controlled procedures.
2. Validate restoration in an isolated recovery cluster.
3. Obtain the new authenticated public certificate.
4. Reseal current manifests using the new certificate and commit changes.
5. Confirm all target namespaces reconcile successfully.
6. Preserve historical-key recovery for required Git revisions.
7. Retire compromised keys only after re-encryption and recovery risk assessment.

If the controller private key is compromised, treat all SealedSecrets encrypted to it as potentially exposed and rotate the underlying application credentials as well.

## 18. Argo CD integration patterns

### Sealed Secrets

Argo CD can reconcile SealedSecret custom resources after the controller and CRD exist. The Sealed Secrets controller materializes the Kubernetes Secret.

### SOPS

Argo CD does **not** natively decrypt arbitrary SOPS manifests by default. Use an approved, pinned integration such as a carefully hardened Config Management Plugin or a supported rendering/decryption workflow. Do not embed age private keys in Git or broad-access Argo CD configuration.

### External Secrets

Argo CD reconciles SecretStore/ExternalSecret references. ESO obtains the secret from its provider and creates the Kubernetes Secret.

**Important:** sync order is not the same as readiness. Applications may start before a Secret is available; use health checks, dependency readiness and safe startup behavior.

## 19. Decryption boundary and Argo CD hardening

If using a Config Management Plugin:

- Restrict which repositories and Applications can invoke the plugin.
- Mount decryption identity only into the dedicated, isolated renderer.
- Use least-privilege KMS identity or tightly protected age key material.
- Avoid printing decrypted manifests in logs or errors.
- Keep temporary plaintext in an appropriate protected ephemeral filesystem.
- Pin plugin versions and validate supply-chain provenance.
- Review multi-tenant repo-server isolation and cache behavior.
- Rotate renderer credentials and audit every decrypt path.

An untrusted repository that can trigger privileged decryption or execute arbitrary plugin commands can become a serious cross-tenant secret exposure path.

## 20. GitLab CI/CD secret-scanning and policy checks

Example CI skeleton:

~~~yaml
stages: [validate, scan]

validate_encrypted_manifests:
  stage: validate
  image: registry.example.internal/ci/sops-tools:PINNED_VERSION
  script:
    - ./ci/check-encrypted-files.sh
    - ./ci/validate-gitops-manifests.sh

secret_scan:
  stage: scan
  image: registry.example.internal/ci/secret-scanner:PINNED_VERSION
  script:
    - ./ci/scan-secrets.sh
~~~

These scripts/images are organization-provided interfaces, not built-in commands. A scanner can miss secrets and produce false positives. Combine scanning with code review, branch protection and a policy prohibiting plaintext Secret data. Never pass decrypted values into CI artifacts, dotenv reports or verbose logs.

## 21. Backup and disaster-recovery design

| Asset | Backup requirement | Recovery test |
| --- | --- | --- |
| SOPS age private identity | Encrypted, access-controlled escrow | Decrypt synthetic historical file |
| KMS key and policy | Provider lifecycle and DR design | Authorized decrypt in recovery region/account |
| Sealed Secrets private keys | Encrypted controller-key backup | Restore and unseal historical resource |
| GitOps repository | Protected version history | Reconcile approved revision |
| Kubernetes etcd | Encrypted backup and restore | Restore target Secret/RBAC |
| Application credentials | Provider backup/version policy | Rotate/revoke safely after restore |

A Git backup containing encrypted files alone is insufficient if all corresponding decryption keys are lost.

## 22. Lab A — SOPS age encryption

1. Generate a staging-only age identity.
2. Configure .sops.yaml with a real public recipient.
3. Create a synthetic Secret outside Git.
4. Encrypt into the target GitOps path.
5. Verify encryption metadata and absence of visible plaintext.
6. Commit only the encrypted manifest.

**Pass:** authorized editor can decrypt; Git history contains no plaintext.

## 23. Lab B — Wrong key and denied decryption

1. Encrypt with a known staging recipient.
2. Attempt decryption with a different lab identity.
3. Confirm decryption fails.
4. Restore the approved identity and verify authorized access.
5. Record only status, not secret values.

**Pass:** access controls deny unauthorized decryptors.

## 24. Lab C — SOPS recipient rotation

1. Add a second approved staging recipient.
2. Run sops updatekeys on a synthetic file.
3. Verify new recipient can decrypt.
4. Assess whether old recipient remains authorized.
5. Perform full rotation where required by policy.
6. Preserve historical recovery before retiring old identity.

**Pass:** new identity works, and retirement is supported by tested recovery evidence.

## 25. Lab D — Sealed Secrets strict scope

1. Verify controller certificate authenticity.
2. Seal a synthetic Secret using strict scope.
3. Apply it to the intended namespace.
4. Confirm the materialized Secret exists without printing data.
5. Try changing name/namespace in a disposable copy.
6. Confirm decryption does not succeed with the altered strict-scope identity.

**Pass:** strict scope prevents unintended relocation.

## 26. Lab E — Controller key backup and restore

1. Back up staging controller key material through an approved encrypted process.
2. Build an isolated recovery cluster with a compatible controller.
3. Restore the original controller key using the documented supported method.
4. Reconcile a previously sealed synthetic resource.
5. Verify the target Secret materializes.
6. Destroy recovery environment and record evidence.

**Pass:** disaster recovery succeeds without exporting private keys into logs or Git.

## 27. Lab F — Compromised Sealed Secrets key tabletop

1. Simulate disclosure of the staging controller private key.
2. Identify SealedSecrets encrypted under that key.
3. Rotate underlying application credentials.
4. Establish a replacement controller key and reseal current manifests.
5. Validate recovery and historical-data retention obligations.
6. Revoke old access and document the incident.

**Pass:** underlying credentials are rotated; certificate rotation alone is not accepted as remediation.

## 28. Lab G — Argo CD integration and sync ordering

1. Deploy the approved decryption integration or Sealed Secrets controller.
2. Reconcile a staging Application containing encrypted secret resources.
3. Verify the materialized Secret is ready before application readiness.
4. Simulate a missing decryption identity or controller outage.
5. Confirm deployment fails safely and does not leak plaintext.
6. Restore the dependency and verify convergence.

**Pass:** GitOps delivery works without broad plaintext exposure.

## 29. Lab H — GitLab leakage prevention

1. Add a synthetic secret string to an untracked test file.
2. Run repository secret scanning and policy checks.
3. Confirm plaintext Secret manifests are rejected.
4. Verify CI logs and artifacts contain no decrypted value.
5. Remove the test file and ensure it was never committed.

**Pass:** prevention and detection controls both operate.

## 30. Lab I — KMS permission denial and recovery

1. Encrypt a synthetic file with a staging cloud KMS key.
2. Confirm an authorized short-lived identity can decrypt.
3. Remove decrypt permission.
4. Confirm access fails and audit events are recorded.
5. Restore the least-privilege grant.
6. Verify recovery without granting broad wildcard permissions.

**Pass:** KMS IAM enforcement and audit are demonstrated.

## 31. Lab J — Full recovery acceptance

1. Select a historical encrypted staging revision.
2. Restore GitOps files and required keys in an isolated environment.
3. Decrypt/reconcile the resource using authorized identities.
4. Verify the application consumes the recovered synthetic secret.
5. Rotate the synthetic credential after recovery.
6. Record recovery time and key provenance.

**Pass:** the historical revision is recoverable within the defined RTO, and no private keys are exposed.

## 32. Troubleshooting — fourteen scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | SOPS cannot decrypt | Wrong/missing age identity | Verify recipient and key custody |
| 2 | KMS AccessDenied | IAM/key policy mismatch | Restore scoped decrypt grant |
| 3 | SOPS file partially plaintext | Incorrect encrypted_regex | Repair policy and rotate exposed values |
| 4 | SOPS updatekeys ineffective | Wrong config path/recipient | Verify policy and SOPS version |
| 5 | Argo CD shows encrypted YAML as Secret | No SOPS rendering integration | Configure supported decryption boundary |
| 6 | SealedSecret not unsealed | Wrong controller certificate/key | Verify controller identity and logs |
| 7 | Strict-scope ciphertext fails | Namespace/name changed | Reseal for intended scope |
| 8 | New cluster cannot decrypt | Controller private key missing | Restore tested encrypted backup |
| 9 | Rotation breaks old revisions | Old keys retired too soon | Restore escrow or re-encrypt history |
| 10 | Secret leaks in CI logs | Verbose decrypt/debug | Revoke, redact and fix pipeline |
| 11 | Repo-server cross-tenant exposure | Overly privileged plugin | Isolate renderer and identities |
| 12 | App starts without Secret | Readiness/sync ordering | Gate startup and retry safely |
| 13 | Sealed Secrets cert rotated, exposure persists | Old private key compromised | Rotate application credentials |
| 14 | Backup exists but recovery fails | Untested key restore | Execute recovery drill and repair |

## 33. Production runbook — SOPS key rotation

1. Identify affected files, environments, decryptors and historical retention requirements.
2. Create approved replacement identity or KMS key.
3. Update recipient policy through a protected GitOps MR.
4. Rewrap or rotate encrypted files with the supported SOPS workflow.
5. Validate authorized decrypt in staging and production rendering environments.
6. Confirm no plaintext enters logs, diffs or artifacts.
7. Test historical revision recovery.
8. Retire old access only after independent security approval.

## 34. Production runbook — Sealed Secrets controller recovery

1. Declare incident and stop unsafe reconciliation changes.
2. Inspect controller health and determine whether key material is missing.
3. Retrieve the approved encrypted controller-key backup.
4. Restore keys using the supported controller procedure.
5. Reconcile a non-production synthetic SealedSecret first.
6. Verify affected applications recover without exposing values.
7. Review blast radius, key rotation and historical recovery.
8. Preserve redacted evidence.

## 35. Production runbook — secret exposure

1. Treat plaintext disclosure or private-key compromise as a security incident.
2. Revoke/rotate underlying credentials immediately.
3. Contain access to Git history, CI logs, artifacts and decryption identities.
4. Audit access to provider secrets, workloads and decrypted values.
5. Re-encrypt/reseal current resources with approved keys.
6. Validate recovery and safe credential consumption.
7. Complete security review and preventive controls.

Deleting a Git commit or rotating a public sealing certificate alone does not undo exposure.

## 36. Evidence template

~~~text
Change / incident ID:
Environment and namespace:
Encryption approach and tool version:
GitOps repository revision:
SOPS recipients or KMS key reference:
Sealed Secrets controller identity:
Key owner and rotation approval:
Affected encrypted file paths:
Historical recovery requirements:
Decryption authorization test:
Unauthorized access denial test:
Controller key backup location (reference only):
Restore test result and duration:
Credential revocation/rotation evidence:
Argo CD sync and application health:
Security reviewer and archive reference:
~~~

Never include private keys, plaintext secret values or decrypted manifests in evidence.

## 37. Acceptance checklist

- [ ] Encryption pattern selected with a documented threat model.
- [ ] SOPS age or KMS encryption validated.
- [ ] Plaintext never committed to Git or CI artifacts.
- [ ] Decryption identities have least privilege.
- [ ] Sealed Secrets scope and controller identity verified.
- [ ] Argo CD rendering/decryption boundary is hardened.
- [ ] Key rotation preserves required historical recovery.
- [ ] Controller private-key backup and restore are tested.
- [ ] Compromised keys trigger underlying credential rotation.
- [ ] Kubernetes Secret RBAC and etcd encryption are reviewed.
- [ ] Missing keys and provider outages fail safely.
- [ ] Ten labs have evidence and owners.
- [ ] Production runbooks and security approvals are complete.

## 38. Knowledge check

1. Why does encryption in Git not protect Kubernetes Secret values after decryption?
2. How does SOPS differ from Sealed Secrets and ESO?
3. Why is a public age recipient safe to store in Git but the private identity is not?
4. What does SOPS updatekeys change, and when is full rotation needed?
5. Why must historical Git revisions be considered before key retirement?
6. Why does a replacement Sealed Secrets controller need the old private key?
7. What does strict Sealed Secrets scope protect?
8. Why is Argo CD repo-server decryption a security boundary?
9. Why does rotating a Sealed Secrets certificate not remediate a stolen private key?
10. What must be verified before declaring key-disaster recovery complete?

## 39. References

- [SOPS Project](https://github.com/getsops/sops)
- [age Encryption](https://age-encryption.org/)
- [Sealed Secrets Project](https://github.com/bitnami-labs/sealed-secrets)
- [External Secrets Operator](https://external-secrets.io/latest/)
- [Argo CD Config Management Plugins](https://argo-cd.readthedocs.io/en/stable/operator-manual/config-management-plugins/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes Encryption at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
- [AWS KMS Key Rotation](https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html)

---

**Chapter 062 complete.** Next: **Chapter 063 — Kubernetes Admission Policies, OPA Gatekeeper and Kyverno for GitOps Security**.