# Chapter 101 — Production Security Architecture and Secure Coding SRE/DBRE Lab

[Executable project](101/README.md) · [Source](101/secure_ops.py) · [Tests](101/test_secure_ops.py)

## Mission

Protect a Python-based operational control plane that inventories cloud resources and supports PostgreSQL, Elasticsearch, MongoDB and Kubernetes incident workflows. Prevent low-trust requests from crossing identity, resource or approval boundaries. All execution remains offline and advisory-only.

## Architecture

```text
Untrusted CLI / API request
  -> strict schema and bounded values
  -> externally verified identity (production design only)
  -> deny-by-default resource authorization
  -> safe operation and redacted audit
  -> version-bound advisory plan
  -> independent expiring approval and rollback evidence
  -> zero mutation in published simulator
```

## Lab 1 — Setup and tests

```bash
cd python/11-production-security-performance/labs/101
python -m compileall -q secure_ops.py test_secure_ops.py
python -m unittest -v test_secure_ops.py
python secure_ops.py --dry-run
```

Record interpreter version, test output and commit SHA. Tests are provided but execution of the exact committed revision is not independently verified.

## Lab 2 — Threat model and trust boundaries

Assets: DB credentials, cloud roles, workload tokens, patient/PII data, production deployments, audit evidence and backups. Actors: authorized SRE, compromised CI runner, external API caller and malicious dependency maintainer. Identify STRIDE threats and assign controls, detection, incident owner and residual risk.

## Lab 3 — Input and OWASP defenses

Reject unknown fields, invalid identifiers, boolean-as-integer limits, unsafe paths and cloud metadata IP addresses. Explain why lexical path checks cannot defeat symlinks and why DNS resolution/redirects need connect-time SSRF protection. Add design notes for SQL parameters and `subprocess.run([...],shell=False)`; do not execute arbitrary commands.

## Lab 4 — Identity and least privilege

Compare read-only viewer and policy auditor roles. Verify environment scoping and deny-by-default behavior. Design real OIDC verification, tenant-level resource authorization and IAM/Kubernetes RBAC for production; the sample actor is synthetic and not authenticated.

## Lab 5 — Dependencies and secrets

Verify a package digest against a trusted expected hash and reject unpinned metadata. Design SBOM generation, `pip-audit`, Bandit, secret scanning and artifact provenance in CI. Demonstrate recursive redaction of keys named `token` and `password`, and document limitations. Do not use real credentials.

## Lab 6 — Approval and audit

Create structured audit events, canonical plan fingerprint and simulated independent approval. Reject self-approval, expired approval, wrong digest, missing rollback and destructive actions. Verify no secret retrieval or cloud write path exists.

## Production incident simulations

| # | Scenario | Expected outcome | Mode |
|---|---|---|---|
| 1 | Valid bounded request | Accept | Automated |
| 2 | Unknown/missing schema fields | Reject | Automated |
| 3 | Path traversal in service ID | Reject | Automated |
| 4 | Invalid environment | Reject | Automated |
| 5 | Boolean or excessive limit | Reject | Automated |
| 6 | Invalid request ID | Reject | Automated |
| 7 | Viewer authorized in staging | Allow | Automated |
| 8 | Viewer requests policy review | Deny | Automated |
| 9 | Viewer requests prod | Deny | Automated |
| 10 | Unknown role | Deny | Automated |
| 11 | Auditor reviews incident | Allow | Automated |
| 12 | Malformed principal | Deny | Automated |
| 13 | Safe relative path | Accept | Automated |
| 14 | Parent/absolute/backslash path | Reject | Automated |
| 15 | Percent-encoded traversal attempt | Reject | Automated |
| 16 | Public IP literal | Accept syntax | Automated |
| 17 | Loopback/private/metadata IP | Reject | Automated |
| 18 | DNS hostname supplied as IP | Reject | Automated |
| 19 | Nested secret-bearing dictionary | Redact | Automated |
| 20 | Trusted digest matches | Accept | Automated |
| 21 | Wrong or malformed digest | Reject | Automated |
| 22 | Pinned dependency metadata | Accept | Automated |
| 23 | Unpinned dependency version | Reject | Automated |
| 24 | Structured allow/deny audit | Record | Automated |
| 25 | Destructive action plan | Reject | Automated |
| 26 | Tampered plan fingerprint | Reject | Automated |
| 27 | No approval | Hold | Automated |
| 28 | Independent simulated approval | Advisory only | Automated |
| 29 | Expired or self-approval | Hold | Automated |
| 30 | Missing rollback or wrong digest | Hold | Automated |
| 31 | Cloud metadata SSRF through DNS | Egress/DNS controls | Guided |
| 32 | SQL injection in DB admin API | Parameterize and audit | Guided |
| 33 | Symlink race in log exporter | Descriptor-based safe access | Guided |
| 34 | Leaked CI token | Revoke and investigate | Guided |
| 35 | Malicious PyPI dependency | Quarantine and verify provenance | Guided |
| 36 | PostgreSQL credential rotation outage | Roll back consumer credentials | Guided |
| 37 | Kubernetes RBAC privilege escalation | Reduce permissions | Guided |
| 38 | Elasticsearch service token leak | Revoke and audit | Guided |
| 39 | Cloud role confused deputy | Bind actor, scope and audience | Guided |
| 40 | Unsafe deployment approval replay | Expiring signed authorization | Guided |

## Operational runbooks

**Authentication/authorization incident:** identify principal, issuer/audience, resource scope and action. Deny, preserve audit, isolate compromised identity and review downstream access.

**Secrets leak:** contain logging, revoke tokens, rotate credentials with application pool validation and inspect access history.

**Supply-chain compromise:** freeze builds, validate lockfile/provenance/SBOM, quarantine artifacts, rotate CI tokens and rebuild from trusted sources.

**Injection or SSRF:** block entry point, audit access, restrict network egress, patch and add regression tests.

**DBRE control-plane outage:** protect data, verify read-only fallback, check IAM/DB roles and backups, avoid broad production privileges.

**Approval failure:** check ticket, scope, plan digest, independent approver, expiry and rollback. No action until validated.

## 100-point final assessment

| Competency | Points |
|---|---:|
| Threat modeling and architecture | 20 |
| Input validation and OWASP defenses | 20 |
| Authentication, authorization and least privilege | 20 |
| Supply-chain security and secrets | 15 |
| Approval, incident response and audit | 15 |
| Automated tests and operational runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, locally executed tests, explicit no-write evidence, reviewed threat model and production extension checklist.

**Validation boundary:** The simulator is not a production identity, SSRF, filesystem, package scanning or remediation system. GitHub CI and runtime execution of the committed revision remain pending.
