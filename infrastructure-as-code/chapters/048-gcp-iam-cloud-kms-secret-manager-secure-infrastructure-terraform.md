# Chapter 048 — GCP IAM, Cloud KMS, Secret Manager and Secure Infrastructure with Terraform

**Part 10 — GCP Infrastructure as Code | Chapter 048/120**  
**Audience:** SRE, DBRE, security engineering, platform engineering and incident commanders  
**Prerequisites:** Chapters 046–047, Terraform >=1.7, Python >=3.9; approved GCP sandbox for optional integration.

> **Safety and evidence boundary:** Mandatory labs use Terraform built-in \`terraform_data\` only, with no GCP resources or credentials. GCP provider snippets are review-only. Do not commit service-account keys, secret values or access tokens. Terraform's \`sensitive\` marking does not remove values from state. Authored tests are not evidence of executed tests or live cloud acceptance.

## 1. Learning outcomes

Design least-privilege IAM across organization/folder/project/resource hierarchy; distinguish IAM allow, deny, principal access boundaries, organization policy and conditional bindings; implement secure service accounts and Workload Identity Federation (WIF); design Cloud KMS key rings, CryptoKeys, key versions, rotation, CMEK, Secret Manager, VPC Service Controls and Cloud Audit Logs; protect Terraform state; rehearse revocation, lost access, key disablement and recovery with production change controls.

## 2. Reference architecture

~~~text
Organization / Folder / Org Policy / IAM Deny
                   |
         Prod project boundary
          /        |         \
    WIF Pool     Cloud KMS   Secret Manager
      |             |              |
  OIDC CI/CD    CMEK for GCS/SQL   Secret metadata
      |             |              |
  SA impersonation + scoped IAM + VPC Service Controls
      |
  Terraform provider -> private GCS state / VPC / GKE / Cloud SQL
      |
  Cloud Audit Logs -> Logging -> Monitoring/SIEM
      |
  Security incident response + break-glass recovery
~~~

IAM roles are permission collections. IAM bindings grant a role to a principal at a scope, with inheritance and optional conditions. IAM Deny policies, principal access boundaries and organization policies address different control planes; none automatically makes a broad grant safe. Prefer service-specific predefined roles or carefully maintained custom roles over primitive Owner/Editor. Review Google-managed service agents before granting CMEK permissions.

## 3. IAM and identity fundamentals

- **Principals:** users, groups, service accounts, federated identities and supported workforce identities. Use groups for human access and workload identity for applications.
- **Allow policy:** evaluate inherited project/folder/organization grants; use conditional bindings when supported. Avoid IAM policy resources that unintentionally replace unrelated bindings.
- **IAM Deny:** use only after dry-run/impact analysis and explicit exemptions for recovery principals.
- **Organization policy:** constrain key creation, allowed regions, public access and other supported service settings; evaluate effective constraints.
- **Service accounts:** separate CI deployer, Terraform state accessor, GKE workload and database operators; disable service-account key creation by default; do not grant project-wide token creation.
- **Privileged access:** just-in-time, approval, short TTL, audit and independently recoverable break-glass account. Test the break-glass path without bypassing logging.

## 4. Workload Identity Federation and impersonation

CI OIDC -> Google Security Token Service -> scoped federated principal -> optional service-account impersonation -> short-lived Google API access. Pin issuer, audience and subject mapping; restrict repository, branch/environment and workload attributes. Do not trust an arbitrary repository owner or wildcard subject. Keep provider credential configuration separate from Terraform state and avoid token exposure in debug logs.

For GKE, Workload Identity Federation for GKE allows Kubernetes workloads to use IAM identities without JSON keys. Review Kubernetes namespace/service account binding, pod identity, metadata server, token audience and permission scope.

## 5. Cloud KMS and CMEK

A key ring contains CryptoKeys, and keys contain versions. A key's rotation schedule does not guarantee old data has been re-encrypted or that old versions can be destroyed. Validate service-specific CMEK integration, service agent permissions, supported locations, protection levels and recovery dependencies. Disabling or destroying a key version can make protected Cloud SQL, GCS or disks unavailable. Key-version destruction is especially sensitive: use multi-person approval, retention and recovery drills.

Use Cloud HSM/EKM only where required and supported; account for latency, external dependencies, service availability and cost. Encryption at rest does not replace least-privilege data access, TLS or audit logging.

## 6. Secret Manager design

Store secret **payloads** through a separate approved delivery process, not as Terraform \`google_secret_manager_secret_version\` payload arguments. Terraform can manage metadata, replication, IAM and labels, but reading or writing a secret value through Terraform can place it in state. Configure rotation ownership, application refresh, expiry/incident response, least-privilege accessor bindings and audit logs. Use Secret Manager version states carefully: disabling an active version may break all workloads. Prefer workload identity and runtime retrieval; avoid embedding secrets in Pod manifests or startup scripts.

## 7. Terraform security patterns

Separate foundational IAM, workload identity, KMS, secret metadata and security telemetry states. Protect GCS backend with uniform bucket-level access, public access prevention, object versioning, encryption, state locking and narrowly scoped identities. Pin provider versions and module sources. Terraform plan output and state are sensitive artifacts; redact logs and control retention.

**Review-only provider resource types:** \`google_service_account\`, \`google_project_iam_member\`, \`google_iam_workload_identity_pool\`, \`google_iam_workload_identity_pool_provider\`, \`google_kms_key_ring\`, \`google_kms_crypto_key\`, \`google_secret_manager_secret\`, \`google_project_organization_policy\` or relevant v2 organization policy resources. Provider schema/version and service support must be checked before deployment.

## 8. Secure change lifecycle

1. Establish approved project ID/number, billing, organization/folder policy and owner.
2. Review permission graph, inheritance, impersonation and cross-project trust.
3. Validate CI OIDC issuer, audience, subject and WIF attribute conditions.
4. Verify KMS key location, rotation, service agent permissions, recovery and planned deletion protection.
5. Verify Secret Manager metadata only, no payloads in Terraform inputs/state.
6. Run policy gate, unit tests, Terraform validate and peer-reviewed plan.
7. Reject destructive actions, IAM privilege escalation, broad grants, disabled audit or unsafe key operations.
8. Apply only with security/DBRE approval, then test runtime access and record evidence.

## 9. Hands-on lab: offline security contracts

~~~bash
cd infrastructure-as-code/labs/chapter-048
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter048.tfplan
terraform apply chapter048.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
~~~

Four \`terraform_data\` resources model IAM, WIF, KMS/secret metadata and audit/recovery contracts. Production preconditions fail on insecure declared controls. Dev/prod environments require separate state directories. Offline contracts **do not** create service accounts, keys, secrets or cloud policies.

### Lab B — Fail-closed policy and adversarial fixtures

~~~bash
python3 security_gate.py fixtures/security-safe.json fixtures/plan-safe.json security-policy.json
python3 security_gate.py fixtures/security-unsafe.json fixtures/plan-destructive.json security-policy.json
python3 -m unittest -v test_security_gate.py
bash run-preflight.sh
~~~

Safe must pass, unsafe/destructive must fail. The policy checks declared WIF issuer/audience/subject, keyless auth, least privilege, absence of primitive roles, KMS recovery, Secret Manager payload isolation, audit, state protection, approvals and deletion/replacement. Fixtures model a narrow contract; they are not a comprehensive parser for Google provider plan JSON.

### Lab C — Optional sandbox GCP plan review

1. Review \`examples/google-security.tf.example\` as a **separate root**. Verify service API enablement and quotas.
2. Check active GCP project, ADC and impersonated identity independently with \`examples/gcp-security-preflight.sh.example\`.
3. Plan service-account, key ring, CryptoKey and Secret Manager **metadata** with no secret payloads or production IAM grants.
4. Inspect policy changes and affected principals; validate WIF trust with a non-production OIDC token.
5. With explicit approval, perform least-privilege access checks, key recovery drill and secret metadata access tests; preserve sanitized evidence and cleanup.

## 10. SRE/DBRE production incident scenarios

| Incident | Signals | First action | Recovery validation |
|---|---|---|---|
| WIF subject drift | STS/impersonation 403 | verify issuer/audience/claims | CI identity obtains only scoped token |
| Accidental broad IAM grant | audit policy change | revoke grant, preserve logs | effective permissions review |
| Key version disabled | CMEK data unavailable | freeze key changes, inspect versions | decrypt and application read/write |
| KMS service-agent access revoked | storage/DB error | restore exact grant | service operation succeeds |
| Secret version disabled | application auth failures | identify version/consumer | controlled version recovery |
| Secret payload in state | state leak alert | restrict state, rotate secret | verify rotation and state remediation |
| GCS state 403 | Terraform backend failure | verify IAM and org perimeter | state read/lock and drift |
| VPC Service Controls deny | perimeter error | inspect access level/ingress rules | approved request succeeds |
| Break-glass inaccessible | recovery blocked | invoke alternate approved path | audited, time-limited access |
| Audit log gap | missing security events | restore sinks/retention | new events observed |

## 11. Troubleshooting commands

~~~bash
gcloud auth list
gcloud config get-value project
gcloud projects get-iam-policy PROJECT_ID --format=json
gcloud iam service-accounts list --project=PROJECT_ID
gcloud iam workload-identity-pools list --location=global --project=PROJECT_ID
gcloud kms keyrings list --location=REGION --project=PROJECT_ID
gcloud secrets list --project=PROJECT_ID
gcloud logging read 'protoPayload.methodName:*' --project=PROJECT_ID --limit=20
terraform providers
terraform state list
~~~

Commands require scoped permissions and may expose sensitive metadata. Avoid \`gcloud secrets versions access\` in shared logs or terminals. Use Cloud Audit Logs and Policy Troubleshooter/Policy Analyzer where supported to diagnose effective access, not just a single IAM binding.

## 12. Production runbooks

**Pre-change:** confirm target project/number, security owner, WIF trust, IAM diff, KMS/secret dependencies, state backup, audit, rollback and ticket; block privileged or destructive changes.

**IAM lockout:** preserve audit evidence, verify inherited/deny policies and principal scope, use audited break-glass under approval, restore least-privilege access, revoke emergency privilege.

**WIF failure:** inspect OIDC claims, provider attribute mapping and service-account impersonation; correct narrowly. Never fall back to JSON keys.

**CMEK outage:** identify affected service/key version, check service-agent IAM, restore authorized key access/version if recoverable, validate decrypt and data integrity. Never destroy versions during incident response.

**Secret exposure:** restrict access, rotate upstream credential, update consumers, revoke old version, audit state/history and affected applications. Do not print the secret.

**State leak or outage:** freeze writers, protect state versions and logs, rotate compromised credentials, repair bucket IAM/perimeter, verify lock ownership and drift before resuming.

**Disaster recovery:** test restoration of identity, KMS, DNS and database dependencies together. Record observed RPO/RTO and explicit security sign-off.

## 13. Assessment — 100 points

| Domain | Points |
|---|---:|
| IAM hierarchy, conditions, deny and least privilege | 20 |
| WIF, service accounts and identity recovery | 20 |
| Cloud KMS, CMEK, Secret Manager and state protection | 20 |
| Terraform labs and negative policy tests | 15 |
| SRE/DBRE incident response and recovery | 15 |
| Audit, monitoring, cost and approvals | 10 |

**Pass >=85/100 with zero critical failures:** primitive production Owner/Editor, static keys, secrets in state, destructive KMS changes, unreviewed IAM escalation, missing recovery or absent security approval. Publication is not production acceptance.

## 14. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
~~~

Destroy offline contract state only or an explicitly disposable sandbox after approval. Review: Why can \`sensitive\` still leak into state? What happens when a CMEK version is disabled? How do IAM Deny and org policy differ? Why must WIF subject mapping be specific? What evidence proves secret rotation succeeded?

**Next proposed:** Chapter 049 — GCP Compute, GKE and Application Infrastructure with Terraform.
