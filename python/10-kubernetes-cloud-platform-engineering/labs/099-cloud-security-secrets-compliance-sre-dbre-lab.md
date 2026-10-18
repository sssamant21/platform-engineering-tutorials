# Chapter 099 — Cloud Platform Security, Secrets and Compliance SRE/DBRE Lab

[Executable project](099/README.md) · [Offline simulator](099/security_lab.py) · [36 automated tests](099/test_security_lab.py)

## Mission

Design safe security automation across AWS IAM/Secrets Manager, Azure Entra ID/Key Vault, GCP IAM/Secret Manager and Kubernetes Secrets, without retrieving or changing real credentials.

```text
Synthetic four-provider secret metadata -> validate identity/scope
  -> bounded pagination -> policy-as-code findings
  -> rotation-age, owner, identity, exposure and audit checks
  -> version-bound SHA-256 advisory rotation plan
  -> simulated independent, expiring approval + rollback evidence
  -> JSON audit report / zero secret reads / zero writes
```

## Lab 1 — Run and test

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/099
python -m compileall -q security_lab.py test_security_lab.py
python -m unittest -v test_security_lab.py
python security_lab.py --dry-run
```

## Lab 2 — IAM, Entra ID, GCP IAM and Kubernetes RBAC

Compare AWS STS role credentials, Azure managed identities, GCP Workload Identity Federation and Kubernetes service accounts. Identify trust boundaries and required metadata-only permissions. Design scoped read-only adapters, but do not retrieve any secret payloads.

## Lab 3 — Metadata and policy-as-code

Review synthetic secret metadata and flag missing production owner, overdue rotation, unknown age, public exposure, disabled audit and missing workload identity. Treat findings as triage signals, not certified compliance. Add policy versions, time-bounded exceptions and evidence retention in a production design.

## Lab 4 — Credential rotation and DBRE safety

Plan a PostgreSQL production password rotation using a new version, overlapping credentials where supported, application pool refresh, authentication checks, replica/HA verification, monitoring and rollback. Compare MongoDB users, Elasticsearch service tokens and Kafka credentials. Do not revoke a working credential before consumers are validated.

## Lab 5 — Pagination, audit and incident response

Exercise fake pages, invalid page/item budgets, duplicate records and pagination loops. Explain CloudTrail, Azure Key Vault diagnostic logs, Cloud Audit Logs and Kubernetes audit logs. Never emit secret values or authorization tokens.

## Lab 6 — Approval and idempotency

Bind provider, scope, resource, action, ticket and expected version to a deterministic SHA-256 plan. Reject destructive actions and invalid scopes. Test independent owner/approver, expiry, digest match and rollback evidence. All plans remain advisory; no secret mutations are implemented.

## Production incident simulations

| # | Incident | Expected behavior | Mode |
|---|---|---|---|
| 1 | Four provider metadata records | Normalize | Automated |
| 2 | Unsupported provider | Reject | Automated |
| 3 | Invalid scope | Reject | Automated |
| 4 | Invalid owner | Reject | Automated |
| 5 | Negative credential age | Reject | Automated |
| 6 | Malformed booleans | Reject | Automated |
| 7 | Rotation overdue | Finding | Automated |
| 8 | Audit disabled | Finding | Automated |
| 9 | Workload identity missing | Finding | Automated |
| 10 | Unknown rotation age | Finding | Automated |
| 11 | Production owner missing | Finding | Automated |
| 12 | Public exposure indicator | Critical finding | Automated |
| 13 | Compliant synthetic secret | No findings | Automated |
| 14 | Duplicate resource | Reject | Automated |
| 15 | Invalid record | Reject | Automated |
| 16 | Paginated records | Combine | Automated |
| 17 | Empty inventory | Empty | Automated |
| 18 | Page/item budget exceeded | Fail closed | Automated |
| 19 | Pagination loop | Reject | Automated |
| 20 | Malformed page | Reject | Automated |
| 21 | Invalid budget | Reject | Automated |
| 22 | Deterministic plan digest | Stable | Automated |
| 23 | Destructive plan | Reject | Automated |
| 24 | Invalid plan scope | Reject | Automated |
| 25 | No approval | Hold | Automated |
| 26 | Valid simulated approval | Advisory only | Automated |
| 27 | Expired approval | Hold | Automated |
| 28 | Self-approval | Hold | Automated |
| 29 | Wrong digest | Hold | Automated |
| 30 | Rollback missing | Hold | Automated |
| 31 | Approved plan with dry_run=false | Zero writes | Automated |
| 32 | AWS Secrets Manager 403 | Verify IAM/resource policy | Guided |
| 33 | Azure Key Vault access denied | Check Entra ID/RBAC/network | Guided |
| 34 | GCP Secret Manager access denied | Check ADC/IAM/project | Guided |
| 35 | Kubernetes Secret leaked in logs | Contain, redact, rotate | Guided |
| 36 | PostgreSQL credential rotation outage | Restore consumers safely | Guided |
| 37 | MongoDB role mismatch | Check user role and application auth | Guided |
| 38 | Elasticsearch service token compromise | Revoke scoped token and audit | Guided |
| 39 | Secret API throttling | Bounded retry | Guided |
| 40 | Incomplete inventory | Mark unknown, not compliant | Guided |

## Troubleshooting and runbooks

**Compromised credential:** contain access, preserve logs, identify consumers, rotate with validated overlap and audit completion.

**Rotation failure:** inspect version state, application connections, caches, replicas and rollback. Stop before revoking the last known-good credential.

**Authorization denied:** inspect identity, IAM/RBAC scope, resource policy and network access; avoid wildcard grants.

**Kubernetes Secret leak:** investigate access, enable encryption at rest, restrict RBAC and audit, and rotate impacted credentials.

**Compliance finding:** validate inventory completeness, policy version, owner and approved exemption before ticketing.

**Approval hold:** verify independent authenticated approver, expiry, ticket, expected version and rollback; no writes.

## 100-point assessment

| Competency | Points |
|---|---:|
| AWS/Azure/GCP/Kubernetes identity and secret architecture | 20 |
| Metadata-only inventory and least privilege | 20 |
| Policy-as-code, rotation and compliance | 20 |
| Audit, pagination and incident response | 15 |
| Approval, dry-run and idempotency | 15 |
| Automated tests and runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90/100, independently executed tests, no-secret-read/no-write evidence, security review and production rotation rollback plan.

**Validation:** Equivalent offline code passed 36 tests locally before publication; execution of exact committed files, CI and live integrations remain pending.
