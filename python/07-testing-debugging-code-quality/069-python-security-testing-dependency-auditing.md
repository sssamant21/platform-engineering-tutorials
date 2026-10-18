# Chapter 069 — Python Security Testing and Dependency Auditing

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 9–12 hours**

## Objectives
Build secure SRE/DBRE automation and enforce layered controls: Bandit static security scanning, pip-audit dependency vulnerability checks, secrets detection, secure subprocess invocation, strict input validation, artifact provenance, automated tests, and fail-closed CI gates.

## Architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka inputs
  -> schema validation + numeric bounds + allowlisted command templates
  -> subprocess.run(argv, shell=False, timeout=..., check=True)
  -> redacted event summaries + offline unit tests
  -> Bandit SAST -> pip-audit SCA -> secrets scanner
  -> trusted CI + review + signed/pinned dependency provenance
  -> controlled release (no live cluster access in this lab)
\`\`\`

## 1. Threat model and trust boundaries
A maintenance automation tool may consume tickets, configuration files, environment variables, command output and network responses. Treat all of these as untrusted. Protect credentials, database data, operational privileges and CI tokens. Key risks: shell injection, path traversal, secret disclosure, dependency compromise, malicious packages, unsafe deserialization, privilege escalation, SSRF and accidental destructive execution.

## 2. Bandit security linting
Bandit statically inspects Python source for common security anti-patterns. Run \`bandit -r . -x .venv -ll\` for medium/high findings and \`bandit -r . -x .venv\` for full review. Rules such as subprocess-shell usage, hardcoded credentials, insecure temporary files and unsafe pickle deserve triage. A clean Bandit report **does not prove** absence of vulnerabilities. Treat suppression comments as reviewable exceptions with owner, justification and expiry.

## 3. pip-audit dependency auditing
\`pip-audit -r requirements.txt\` checks declared packages against vulnerability advisories; \`python -m pip_audit\` can audit the current environment. Network access and advisory availability may affect results. Avoid \`--ignore-vuln\` unless documented and time-limited. Audit direct and transitive dependencies, include lockfiles and SBOMs, and maintain a response plan for critical CVEs. Advisory findings are not automatically exploitable in your usage, but require triage.

## 4. Secrets detection
Secrets may appear in source, configuration, test fixtures, commit history and CI logs. Use a dedicated scanner such as Gitleaks or detect-secrets with reviewed baselines and canary tests. Keep real credentials out of lab data. Redact both field names and values where practical, but prefer an allowlist of safe fields over attempting to scrub arbitrary free text. If exposure occurs, rotate credentials; deleting a Git line does not erase leaked Git history.

## 5. Safe subprocess execution
Avoid \`shell=True\`, string-built shell commands and \`os.system\`. Construct a fixed executable and argv list from allowlisted options. Use \`subprocess.run(..., shell=False, check=True, timeout=..., capture_output=True, text=True)\`; set a trusted executable path and constrained environment for production. Do not rely on quoting to secure untrusted shell fragments. Apply least privilege and resource/time limits; handle \`TimeoutExpired\`, \`CalledProcessError\` and \`OSError\` without leaking command output or credentials.

## 6. Runtime input validation
Type hints are not runtime validation. Reject unknown keys, invalid identifiers, booleans masquerading as numbers, NaN/Infinity, negative values, oversized batches and unrecognized metric units. Use explicit policy tables and bound maximum input size. Do not log raw payloads or return sensitive errors.

## 7. Supply-chain security
Pin dependencies and hashes in approved lockfiles, verify package provenance, review maintainers and licenses, minimize dependencies, produce an SBOM and retain build attestations. Pin GitHub Actions to reviewed commit SHAs, restrict workflow permissions and never expose production secrets to untrusted PRs. Run SAST, SCA and secret scans in CI before artifact promotion. Keep the lab offline and synthetic; any installation/audit step may require package-index or advisory network access.

## 8. Production incident scenarios
1. PostgreSQL cleanup ticket contains a malicious index identifier: validate against a strict allowlist and require human approval.
2. Elasticsearch diagnostic script interpolates a user query into a shell: replace with argv and fixed templates.
3. Kafka lag exporter includes an API token in stderr: return sanitized error codes, not raw output.
4. New transitive package has a critical CVE: block release pending risk review or approved exception.
5. Credential appears in a commit: revoke and rotate it, investigate history and affected systems.
6. CI job runs with broad write permission: reduce to \`contents: read\` and isolate privileged deployment.
7. External command hangs: enforce a timeout and bounded output.
8. Malformed telemetry includes NaN: reject before alert calculations.
9. Malicious dependency tries to run during install: use approved mirrors and isolated builders.
10. Security scan is bypassed locally: required CI status checks remain authoritative.

## 9. Troubleshooting
| Symptom | Root cause | Response |
|---|---|---|
| Bandit warning | Potential unsafe API | Investigate, remediate, document exception |
| pip-audit reports CVE | Vulnerable dependency | Patch/pin, test compatibility, triage |
| pip-audit cannot reach advisory source | Network/proxy outage | Fail closed for release; retry on trusted runner |
| Secrets scan false positive | Test fixture looks like key | Use synthetic fixture and narrowly scoped allowlist |
| Command timeout | Hung child process | Enforce timeout, inspect safe metadata, retry under policy |
| Command not found | Incorrect executable path | Verify approved executable and PATH |
| Input rejected | Schema/metric drift | Fix upstream contract; do not disable validation |
| CI differs from laptop | Tool/version drift | Use approved lockfile and reproducible runner |
| Dependency confusion | Untrusted index configuration | Pin index and verify artifact provenance |

## 10. Production runbooks
**Security gate failure:** stop promotion, preserve sanitized evidence, assign severity/owner, remediate and rerun tests and scans.

**Critical dependency advisory:** identify affected versions and usage, assess exposure, upgrade or apply a time-bound exception with compensating controls, rebuild and verify.

**Secret exposure:** revoke/rotate immediately, restrict logs and artifacts, review access and Git history, notify security and document impact.

**Suspected command injection:** disable affected automation, remove shell interpolation, constrain executable/arguments, rerun adversarial tests and restore only after approval.

**Rollback:** revert to approved source and dependency lock, rerun quality/security gates, verify service health and record change authorization.

## 11. Hands-on lab
[Chapter 069 — Security Testing and Dependency Auditing SRE/DBRE Lab](labs/069-security-testing-dependency-auditing-sre-dbre-lab.md) includes complete executable code, unit tests, scanner commands, CI template, 12 failure exercises, runbooks and a 100-point assessment.

**Next:** Chapter 070 — Testing, Debugging and Code Quality Capstone (provisional).
