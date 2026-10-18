# Chapter 101 — Python Production Security Architecture and Secure Coding

**Part 11 — Production Security and Performance | Chapter 101 of 120 | Python 3.11+**

[Executable lab](labs/101/README.md) · [Full SRE/DBRE lab](labs/101-production-security-secure-coding-sre-dbre-lab.md)

## Objectives

Apply defense in depth to production Python services and operational automation. Build a threat model, validate input and output, enforce authentication/authorization boundaries, mitigate common OWASP risks, protect credentials, verify dependency provenance and write regression tests. Distinguish an offline educational control from production-grade enforcement.

## Architecture

```text
Untrusted API / CLI / event / CI input
               |
     strict schema, length, type, encoding
               |
    verified workload identity + authentication
               |
       resource-scoped authorization
               |
      safe business operation / least privilege
               |
      output encoding / secrets redaction
               |
  structured audit, trace IDs, metrics, alerting
               |
  independent change approval for risky actions
```

Separate a data plane (requests and telemetry), a control plane (cloud/Kubernetes/DB administration), and a trust plane (identity, signing, approval and audit). Do not allow low-trust telemetry or LLM output to become privileged instructions.

## 1. Threat modeling

Define assets: patient/PII data, DB credentials, cloud IAM roles, Kubernetes tokens, CI artifacts, logs, backups, audit integrity and service availability. Enumerate actors and entry points: external clients, CI runners, build dependencies, webhooks, operators, third-party SDKs and compromised pods.

Use STRIDE:
- **Spoofing:** stolen service tokens; mitigate short-lived workload identity, verified issuers/audience and MFA for humans.
- **Tampering:** altered build artifacts or change plans; verify trusted digests/signatures and protected branches.
- **Repudiation:** missing audit attribution; preserve immutable actor, request, resource, decision and timestamp.
- **Information disclosure:** secrets in logs, stack traces or Kubernetes Secret reads; redact and restrict.
- **Denial of service:** unbounded input, expensive regex, retries and pagination; enforce budgets.
- **Elevation of privilege:** overly broad cloud roles, confused deputy and missing object-level authorization; scope every operation.

Build abuse cases: cross-tenant resource enumeration, unauthorized database failover, cloud metadata SSRF, dependency takeover, SQL injection, path traversal, replayed approval and log poisoning. Assign likelihood/impact, owners, controls, detection and residual risk. Review the model after architectural changes.

## 2. Input validation and output safety

Accept only known fields; reject unknown keys, booleans masquerading as integers, invalid types, excessive lengths and unsafe resource identifiers. Validate at trust boundaries, not just UI. Normalize Unicode and encodings deliberately. Parameterize SQL queries; never concatenate user input into SQL identifiers or shell commands. Use subprocess argument arrays with `shell=False` and allowlisted commands; never execute untrusted Python expressions.

For filesystem paths, lexical checks alone cannot defeat symlink races. In production, use restricted directory handles, `openat`-style operations and `O_NOFOLLOW` where supported, plus OS sandboxing. For SSRF, validate the **resolved destination at connection time**, deny private/link-local/loopback/metadata endpoints, handle DNS rebinding, proxies and redirects, and preferably enforce egress network policy. The executable lab deliberately makes no HTTP or filesystem calls.

Escape untrusted output according to context (HTML, JSON, shell, logs). Redaction is defense in depth: prevent secret material from entering telemetry at all. The lab demonstrates key-based redaction, which does not find secrets embedded in arbitrary strings.

## 3. Authentication and authorization

Authentication establishes principal identity; authorization checks **this principal may perform this action on this resource in this environment**. Validate token signature, issuer, audience, expiry, nonce/replay properties and key rotation using vetted identity libraries. Do not implement JWT cryptography from scratch. For SRE automation, prefer AWS IAM roles, Azure managed identities, GCP Workload Identity Federation and Kubernetes service-account federation.

Apply deny-by-default, least privilege, separation of duties and object-level authorization. Use distinct roles for read-only inventory, policy review and production remediation. Include tenant/account/subscription/project/namespace scope in every decision. Do not rely solely on group membership or a request-supplied `is_admin` flag. Log allow/deny decisions without logging bearer tokens.

The executable lab models an already-authenticated principal with a tiny role matrix; it does **not** implement an authentication provider or cryptographic token validation.

## 4. OWASP-aligned secure coding

| Risk | Production Python mitigation |
|---|---|
| Broken access control | Object-level, tenant-scoped checks and deny-by-default |
| Cryptographic failures | TLS, vetted cryptography, KMS and rotation |
| Injection | SQL parameters, no `eval`, safe subprocess arguments |
| Insecure design | Threat models, abuse cases, security gates |
| Security misconfiguration | Secure defaults, IaC policy, no public debug endpoints |
| Vulnerable/outdated components | Lockfiles, provenance, scanning and patch SLAs |
| Identification/authentication failures | OIDC/OAuth verification, MFA and short-lived tokens |
| Software/data integrity failures | Signed releases, verified artifact provenance |
| Logging/monitoring failures | Structured redacted audit, retention and alerts |
| SSRF | Destination allowlists, egress controls, DNS/redirect protection |

OWASP Top 10 and API Security Top 10 are useful reference taxonomies; they are not a complete security standard or substitute for risk assessment.

## 5. Dependencies and software supply chain

Pin exact versions with hashes in a lockfile, use approved package indexes, isolate builds and generate SBOMs. Run `pip-audit`, Bandit, Ruff and secret scanners in CI; review results and false positives. Use protected branches, signed provenance/attestations, least-privilege CI tokens and reproducible build strategies. Rotate compromised publishing credentials and quarantine suspicious packages.

A SHA-256 digest proves bytes match a **trusted expected digest**; an attacker-controlled manifest and matching digest prove nothing about publisher authenticity. The lab verifies digest matching and checks dependency metadata but does not fetch packages or perform vulnerability scans.

## 6. Secrets handling

Prefer identity federation over static cloud keys. Retrieve secret values only in a narrow runtime boundary when absolutely necessary, never in CI logs or exception traces. Avoid command-line secrets, environment dumps, core dumps and broad Kubernetes Secret listing. Use cloud secret managers, envelope encryption and restricted KMS access. Kubernetes Secret data is base64 encoded, not inherently encrypted.

Rotation runbook: inventory consumers, stage a new version, validate connection pools, retain rollback path, monitor authentication errors, then revoke the old version. For PostgreSQL, MongoDB, Elasticsearch and Kafka, account for different credentials and application reload behaviors.

## 7. Safe automation and change control

A production change workflow separates observation, advisory plan, independently authenticated approval, execution, verification and rollback. Bind provider, scope, resource ID, action, ticket, expected version and expiry. Idempotency keys, optimistic concurrency and write-side authorization must be enforced by the executor, not merely by a UI. SHA-256 plan fingerprints are not digital signatures.

The Chapter 101 code implements advisory actions only; even valid simulated approval yields zero writes. It rejects `delete`, `restart` and other privileged actions.

## 8. SRE/DBRE production incident scenarios

| Scenario | Detection and response |
|---|---|
| SQL injection attempt in DBRE API | Reject, parameterize and inspect audit |
| Cross-tenant PostgreSQL inventory request | Enforce resource-scoped authorization |
| Cloud metadata SSRF | Deny link-local and restrict egress |
| Path traversal in log export | Reject, enforce directory containment and no-follow |
| Secret printed in exception | Contain, redact, rotate and review log retention |
| Malicious dependency update | Quarantine, verify provenance, roll back |
| CI token leaked | Revoke, audit pipelines and rotate |
| AWS role privilege escalation | Review STS, IAM and CloudTrail |
| Azure managed identity wrong scope | Deny and verify tenant/subscription |
| GCP workload identity mismatch | Verify issuer, subject, audience and project |
| Kubernetes overbroad RBAC | Reduce Secret/list and pod/exec permissions |
| Approval replay or self-approval | Reject with expiry and separation of duties |
| DB credential rotation outage | Validate consumer refresh and rollback |
| Unsafe regex/large payload DoS | Bound lengths, timeouts and budgets |

## 9. Operational runbooks

**Unauthorized access:** identify principal/resource/action and trust boundary; deny, preserve audit, assess blast radius and remediate IAM.

**Secret exposure:** contain logs, revoke compromised tokens, rotate with consumer verification and investigate downstream access.

**Dependency compromise:** freeze builds, verify SBOM/provenance, isolate affected deployments and deploy trusted artifacts.

**Injection/SSRF:** block entry point, inspect telemetry, patch validation, test egress restrictions and perform forensic review.

**Production database access incident:** confirm role, credentials, TLS, pool state, audit and recovery path before changing auth.

**Change gate failure:** verify approved ticket, separate approver, expiry, exact plan digest and rollback; do not proceed.

## 10. Labs and assessment

The [complete lab](labs/101-production-security-secure-coding-sre-dbre-lab.md) and [executable project](labs/101/README.md) cover schema validation, RBAC, path and IP guards, redaction, dependency digests, audit records, approval gates and automated unit tests.

**100-point assessment:** threat modeling (20), input/OWASP defenses (20), authn/authz and least privilege (20), dependencies/secrets (15), operational safety and incident response (15), tests and runbooks (10). Passing score ≥90 with test evidence and reviewed production limitations.

**Validation boundary:** Python source and tests are published. CI, exact committed runtime execution, live identity providers and production security review remain pending.

**Next proposed:** Chapter 102 — Python Identity, Authentication and Authorization for Production Systems.
