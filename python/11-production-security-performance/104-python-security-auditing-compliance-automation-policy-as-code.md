# Chapter 104 — Python Security Auditing, Compliance Automation and Policy-as-Code

**Part 11 — Production Security and Performance | Chapter 104/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/104-security-auditing-compliance-policy-as-code-sre-dbre-lab.md) · [Executable offline project](labs/104/README.md)

## Learning objectives

Design reliable multi-cloud audit evidence pipelines and policy-as-code checks for AWS, Azure, GCP and Kubernetes. Map technical controls to CIS Benchmarks, NIST SP 800-53 and SOC 2 criteria without claiming certification. Detect drift, preserve evidence integrity, manage exceptions and approvals, and build fail-closed SRE/DBRE automation.

## Architecture

```text
AWS CloudTrail / Config / IAM ──────┐
Azure Activity / Policy / Entra ────┼──> scoped read-only collectors (design)
GCP Cloud Audit Logs / SCC / IAM ──┤                 |
Kubernetes audit / RBAC / admission┘                 v
                            normalized evidence + provenance
                                            |
                             freshness / completeness / dedup
                                            |
                         versioned policy-as-code + control mapping
                                            |
                             findings / exception expiry / drift
                                            |
                        canonical SHA-256 evidence report fingerprint
                                            |
                       approval-gated advisory plan / audit export
```

## 1. Governance, risk and compliance foundations

Compliance is an ongoing evidence and control process, not a one-time scanner result. Distinguish policy intent, technical implementation, operating effectiveness, audit evidence, exceptions and independent assessment. Inventory gaps, inaccessible accounts and missing telemetry must be reported as **unknown**, never passing.

**CIS Benchmarks:** prescriptive configuration recommendations, versioned by product and release; apply only the applicable benchmark and profile.

**NIST SP 800-53:** a catalog of security and privacy controls (for example AC, AU, CM, IA, SC, SI families), not an automatic compliance certification. Map control implementations to selected baselines and organizational overlays.

**SOC 2:** an attestation based on Trust Services Criteria, control design/operation and auditor testing. A Python rule cannot independently establish SOC 2 compliance.

## 2. Example control mappings

| Technical check | CIS-style configuration objective | NIST family | SOC 2 theme |
|---|---|---|---|
| Audit logging enabled | Centralized activity logging | AU | Security monitoring |
| Least-privilege IAM/RBAC | Restrict broad permissions | AC | Logical access |
| Encryption at rest | Protect stored information | SC | Confidentiality/security |
| Resource owner assigned | Accountable asset inventory | CM/PM | Governance |
| Backup restore tested | Recovery readiness | CP | Availability |

These are **illustrative mappings**, not normative control identifiers or audit opinions. Map precise benchmark versions, NIST controls and Trust Services Criteria with a qualified compliance owner.

## 3. AWS audit evidence

Use scoped CloudTrail trails/event selectors, AWS Config configuration history/rules, IAM Access Analyzer, Security Hub findings and AWS Organizations account inventory. Verify CloudTrail coverage, organization trails, management/data event selection, log retention, access controls and evidence timestamp. S3 Object Lock and CloudTrail log file validation can strengthen tamper resistance when properly configured. The executable lab does not call boto3.

## 4. Azure audit evidence

Collect Azure Activity Logs, Azure Policy assignments/compliance states, Microsoft Entra sign-in/audit logs, Defender for Cloud recommendations and relevant resource diagnostic logs. Activity Logs alone do not cover all data-plane access. Validate tenant/subscription scope, RBAC, retention, Log Analytics export and private endpoints. The lab does not call Azure SDKs.

## 5. GCP audit evidence

Collect Cloud Audit Logs (Admin Activity, Data Access when enabled, System Event and Policy Denied as applicable), Cloud Asset Inventory, IAM policy analysis, Security Command Center and organization policies. Data Access logs can require explicit configuration and have different cost/coverage. Validate folder/project scope, log sinks, exclusions and retention. The lab does not call GCP SDKs.

## 6. Kubernetes evidence

Collect Kubernetes API audit logs, RBAC/ClusterRoleBindings, admission policy results, Pod Security Admission settings, encryption-at-rest configuration, service-account token policy and workload inventory. Cluster audit configuration and managed-control-plane access vary by provider. Do not expose Secret payloads in evidence collection.

## 7. Python policy engines and evidence schema

A policy engine should ingest normalized evidence with provider, scope, resource ID, control ID, outcome, collection time, source reference, owner and policy version. Use strict validation, deny-by-default on missing/invalid data, stable rule IDs and versioned policy bundles. Python is appropriate for deterministic control checks and orchestration; consider OPA/Rego or CEL when cross-language policy portability is important.

Separate **evidence collection** from **policy evaluation**. Preserve raw source references, provenance and collection completeness, and bound pagination/retries. A failed collector must not silently turn findings into passes.

## 8. Integrity, provenance and audit trail

Canonical JSON plus SHA-256 detects accidental or malicious modifications **only when the expected digest is independently trusted**. A hash is not an authenticated signature or immutable log. Production evidence integrity should use signed manifests, KMS-backed signing where appropriate, append-only/WORM retention, trusted timestamps, access controls and independent verification. Redact credentials and personal data.

## 9. Compliance drift and exceptions

Compare complete snapshots using stable resource/control identities. Mark incomplete snapshots unknown rather than asserting deletion or resolution. Exceptions require a ticket, independent risk owner, documented reason, scope, compensating controls and expiry. An approved exception changes disposition, **not the underlying technical failure**. Automatically re-evaluate expired exceptions and escalate.

## 10. Least privilege and change approvals

Inventory AWS IAM roles, Azure RBAC, GCP IAM and Kubernetes RBAC by effective scope; inspect wildcard permissions, role trust, identity federation and privileged service accounts. Avoid granting broad read permissions merely to run an auditor. Use separate collection identities and scoped resource allowlists. Remediation should follow observe → propose → independent approval → execute → verify → rollback. The offline lab stops at advisory approval; no cloud mutations.

## 11. SRE/DBRE incident scenarios

| Incident | Response |
|---|---|
| CloudTrail stopped or incomplete | Preserve last good evidence, inspect account/region coverage |
| Azure diagnostic log missing | Verify resource data-plane logging and sink |
| GCP Data Access logs absent | Validate service-specific configuration and cost |
| Kubernetes audit disabled | Restore audit policy and investigate gap |
| Overprivileged production database role | Review actual permissions, owner and approval |
| PostgreSQL backup not restore-tested | Schedule isolated restore and record evidence |
| Elasticsearch access policy drift | Inspect role mapping and API keys |
| Expired exception | Reopen finding and escalate |
| Evidence checksum mismatch | Quarantine evidence and verify trusted manifest |
| Collector throttled | Bounded retry and incomplete status |

## 12. Operational runbooks

**Audit outage:** establish blast radius, identify missing providers/accounts, preserve last complete snapshot, restore sinks, verify freshness and document blind spots.

**Unauthorized access:** contain, preserve logs, validate identity/RBAC and audit all affected resources.

**Compliance drift:** compare control versions, source freshness, exception status and owner; create an evidence-backed change ticket.

**Evidence tampering:** validate signatures/trusted digests, isolate storage, preserve immutable copies and involve incident response.

**Exception expiry:** notify risk owner, re-evaluate control and remove exception only through approved workflow.

**DBRE backup evidence:** test restore in isolation, verify RPO/RTO and record reproducible checks without exposing data.

## 13. Hands-on lab

The [full lab](labs/104-security-auditing-compliance-policy-as-code-sre-dbre-lab.md) and [executable project](labs/104/README.md) implement synthetic AWS/Azure/GCP/Kubernetes evidence, control checks, freshness, completeness, drift, SHA-256 reports, expiring exceptions, bounded pagination, independent advisory approval, incident exercises, troubleshooting and a 100-point assessment.

**Validation boundary:** The simulator does not call real cloud APIs, attest compliance, digitally sign evidence or perform remediation. Automated tests are published; execution of the exact committed revision, CI, external auditor review and live integration remain pending.

**Next proposed:** Chapter 105 — Python Secure Software Supply Chain and Dependency Risk Automation.
