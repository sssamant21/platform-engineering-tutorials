# Chapter 099 — Python Cloud Platform Security, Secrets and Compliance Automation

**Part 10 — Kubernetes, AWS, Azure and GCP | Chapter 099/120 | Python 3.11+**

[Complete hands-on lab](labs/099-cloud-security-secrets-compliance-sre-dbre-lab.md) · [Executable project](labs/099/README.md)

## Objectives

Build security-first SRE/DBRE automation for AWS IAM and Secrets Manager, Microsoft Entra ID and Azure Key Vault, Google Cloud IAM and Secret Manager, Kubernetes Secrets and workload identities. Evaluate credential rotation, policy-as-code, least privilege, audit trails, drift, dry-run and approval gates without reading or changing real secrets.

## Architecture

```text
AWS IAM / Secrets Manager metadata ───┐
Azure Entra / Key Vault metadata ─────┼─> read-only scoped adapters
GCP IAM / Secret Manager metadata ────┤          |
Kubernetes RBAC / Secrets metadata ───┘          v
                                normalized resource + provenance
                                            |
                              policy-as-code / age / owner / audit
                                            |
                            finding severity + evidence + exceptions
                                            |
                         version-bound SHA-256 advisory rotation plan
                                            |
                    independently authenticated expiring approval
                                            |
                         dry-run report / zero cloud writes in lab
```

## 1. Identity and trust boundaries

**AWS:** Use boto3 Sessions with short-lived role credentials, STS GetCallerIdentity, resource-scoped IAM policies and CloudTrail. Prefer IAM roles for EC2/EKS and IRSA/EKS Pod Identity where supported. Distinguish Secrets Manager metadata (`describe_secret`, `list_secrets`) from value retrieval (`get_secret_value`), which is intentionally excluded from the lab.

**Azure:** Use Entra ID managed identities and workload identity federation with Azure SDK `DefaultAzureCredential` only after confirming the intended principal. Azure Key Vault supports RBAC-based authorization and secret versioning. Use `azure-keyvault-secrets` for metadata/version listing, and avoid `get_secret` when secret values are unnecessary. Azure Activity Logs and Key Vault diagnostic logs have different coverage; configure appropriate audit sinks.

**GCP:** Use ADC with Workload Identity Federation and least-privilege Secret Manager roles. Metadata listing through Secret Manager API is distinct from `access_secret_version`, which returns secret payloads and is excluded. Use Cloud Audit Logs and project/service-account allowlists.

**Kubernetes:** Native Secrets are base64-encoded data, **not encryption by default**. Enable encryption at rest, least-privilege RBAC, audit logs and workload identities. Kubernetes API read permission for Secret objects may reveal sensitive data. Prefer metadata-only access through a carefully reviewed controller or inventory mechanism, or use external secrets operators with an explicit threat model. Do not run `kubectl get secret -o yaml` as a routine diagnostic.

## 2. Metadata-only normalized model

Track provider, scope/account/project, native resource ID, owner, environment, rotation policy, age, workload identity, public exposure indicator and audit status. Retain provider-native IDs and raw evidence references; do not store credentials, access tokens, secret values or plaintext configuration in inventory. Do not treat missing age as zero. Account for key vault version expiry, AWS rotation scheduling, GCP secret version lifecycle and Kubernetes external-secret sync.

## 3. Policy-as-code and compliance

Representative rules: production secrets require owner; public access requires security review; workloads should use identity federation rather than static credentials; audit must be enabled; age must not exceed approved rotation policy. Version policy bundles, document scope and exceptions, set exemption expiration and require security approval. A finding is evidence for investigation, not proof of exploitability.

Frameworks such as CIS Benchmarks, NIST 800-53 and SOC 2 can inform controls, but passing the toy rules does **not** establish regulatory compliance. Map evidence to actual organization policies and audit requirements.

## 4. Rotation lifecycle and DBRE safeguards

Plan **discover → dependency map → issue new version → dual-credential overlap where supported → validate consumers → revoke old version → monitor → rollback**. The exact process depends on provider and credential type. For PostgreSQL/RDS/Azure PostgreSQL/Cloud SQL, validate connection pools, application reloads, replica credentials, failover behavior and recovery access before revocation. MongoDB, Elasticsearch and Kafka may have separate application/service-account rotation mechanisms. Never rotate production database credentials from an unreviewed example.

AWS Secrets Manager rotation Lambda workflows, Azure Key Vault Event Grid/automation, GCP Secret Manager version updates and Kubernetes External Secrets Operator each require provider-specific implementation and failure handling.

## 5. Least privilege, retries and audit

Use read-only listing where feasible; avoid payload retrieval. Scope by AWS account/region, Azure tenant/subscription/vault, GCP project and Kubernetes namespace. Enforce pagination, deadlines and rate budgets. Retry transient 429/5xx with bounded backoff; do not retry 403 as a transient failure. Preserve audit event IDs, resource/version IDs, change tickets, actor identity and timestamp. Redact sensitive payloads and never log authorization headers.

## 6. Approval gates, dry-run and idempotency

Bind each advisory plan to provider, scope, resource ID, action, incident ticket and expected secret version. Canonicalize JSON and hash it using SHA-256. The digest is a change identifier, **not** a signature or authenticated approval. Require a separate authenticated approver, approval expiry, resource owner, rollback rehearsal and maintenance window before production execution. The offline lab simulates these checks but **never performs secret reads or mutations**, even when approval passes.

## 7. Production incident scenarios

| Incident | Safe response |
|---|---|
| AWS IAM role lacks DescribeSecret | Inspect IAM and resource policy; no broad wildcard grant |
| Azure Key Vault 403 | Verify tenant, RBAC/data-plane roles and network controls |
| GCP Secret Manager denied | Validate ADC, IAM and project |
| Kubernetes Secret exposed in logs | Contain, revoke, investigate access and rotate |
| Production PostgreSQL credential expired | Coordinate safe dual-credential rollout and rollback |
| MongoDB application loses access after rotation | Verify user roles, connection string and pool refresh |
| Elasticsearch service account token compromised | Revoke scoped token and inspect audit |
| Rotation job partially succeeds | Halt revocation and recover with tested rollback |
| Unknown owner | Escalate to service inventory/CMDB owner |
| Secret value appears in telemetry | Quarantine/redact and assess incident scope |
| API 429 | Backoff and preserve cursor |
| Incomplete inventory | Mark coverage unknown; do not claim compliance |
| Unauthorized change | Hold and audit |

## 8. Runbooks

**Credential compromise:** restrict access, preserve audit evidence, identify consumers, rotate safely, verify downstream health and document incident.

**Rotation failure:** identify version state, consumer errors, connection pool behavior and rollback options. Do not delete prior versions before validating consumers.

**Cloud authorization:** verify principal, provider scope, role/resource policy, private endpoint and service-account federation; avoid static keys.

**Kubernetes:** check namespace/RBAC and encryption-at-rest posture without reading payloads.

**Compliance drift:** validate collector completeness, policy version, exemption status and ownership before remediation.

**Approval:** verify independent identity, expiry, exact plan fingerprint, expected version and rollback. The lab cannot mutate real secrets.

## 9. Hands-on lab and assessment

The [full lab](labs/099-cloud-security-secrets-compliance-sre-dbre-lab.md) includes an offline Python 3.11+ metadata-only simulator, 36 local automated tests, policy checks, rotation advisory planning, pagination, audit boundaries, incident drills, runbooks and a 100-point assessment.

**Validation boundary:** Local Python syntax compilation and 36 tests passed on an equivalent implementation before publication. No real AWS, Azure, GCP or Kubernetes secret API integration, credential rotation or CI run has been performed.

**Next proposed:** Chapter 100 — Python Cloud-Native Platform Engineering Production Capstone.
