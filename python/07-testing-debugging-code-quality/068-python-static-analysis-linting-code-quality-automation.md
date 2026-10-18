# Chapter 068 — Python Static Analysis, Linting and Code Quality Automation

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+**

## Outcomes
Build layered SRE/DBRE quality gates with Ruff lint/format, mypy strict typing, security linting, pre-commit hooks, runtime regression tests and trusted CI. Distinguish static guarantees from runtime validation.

## Architecture
\`\`\`text
developer -> pre-commit -> Ruff check + format --check
  -> mypy --strict -> unittest -> security/dependency scans
  -> trusted CI -> review/branch protection -> production change gate
\`\`\`

## Theory
**Ruff:** Fast linting and formatting. Select \`E4,E7,E9,F,I,B,UP,SIM,S\` to cover syntax, imports, common bug patterns, modernization and security heuristics. \`ruff check --fix\` may edit files; review the diff. \`ruff format --check\` is non-mutating. Ruff security rules do not replace security testing or dependency auditing.

**mypy:** Static analysis checks annotated contracts. Use \`TypedDict\` for wire schemas, \`dataclass\` for immutable validated records, \`StrEnum\` for constrained values, \`Mapping\` for read-only policy data, and \`Final\` for constants. \`mypy --strict\` detects missing annotations and type mismatches but cannot prove external input safety. Reject booleans as metrics, NaN, Infinity, negative values, invalid units and unknown engines at runtime.

**Formatting:** Separate formatting from linting and testing. Run \`ruff format\` locally and \`ruff format --check\` in CI. Enable import sorting with Ruff's \`I\` rules.

**Security lint:** Review unsafe subprocess calls, hardcoded credentials, dynamic evaluation, insecure deserialization and unsafe filesystem access. Pair heuristics with secrets scanning, SCA, threat modeling, safe parameterized SQL and runtime tests. Suppress narrowly with a reason, owner and expiration.

**Pre-commit:** Pin reviewed hook versions (prefer immutable commit SHAs), install locally and run \`pre-commit run --all-files\`. Hooks can be skipped, so branch protection and CI must enforce policy independently.

**CI:** Split independent gates for actionable feedback; use restricted token permissions, approved dependencies, action SHA pins, no production credentials and isolated runners. Do not execute untrusted PR code with privileged secrets.

## SRE/DBRE scenarios
1. PostgreSQL replication-lag collector accepts boolean \`True\`: static type annotation is insufficient; reject at runtime.
2. Elasticsearch latency units change from milliseconds to seconds: schema and tests must reject drift.
3. Kafka lag collector admits NaN: prevent corrupt alert calculations.
4. A subprocess helper introduces \`shell=True\`: review security finding and remove dangerous behavior.
5. A developer bypasses pre-commit: protected CI must fail closed.
6. A library upgrade changes typing stubs: pin versions, review compatibility and rerun gates.
7. Toolchain drift produces local/CI disagreement: align interpreter and lockfile.

## Troubleshooting
| Symptom | Likely cause | Resolution |
|---|---|---|
| Ruff F401 | Unused import | Remove it or review safe fix |
| Ruff I001 | Import ordering | Apply Ruff import sorting |
| Format gate fails | Inconsistent formatting | Run formatter and review diff |
| mypy strict fails | Missing annotations/unsafe Any | Add explicit types and narrowing |
| Security rule fires | Potential unsafe operation | Review exploitability, remediate |
| Pre-commit fails install | Network/version drift | Use approved mirror and pin |
| CI differs from laptop | Python/tool drift | Use same lockfile and versions |
| Tests pass but typing fails | Contract drift | Repair interface and regression tests |

## Runbooks
**Quality gate failure:** capture exact tool versions and sanitized output, isolate change, repair and rerun all checks.

**Security finding:** block promotion, triage exploitability, remove dangerous behavior, add regression tests and obtain security approval.

**Supply-chain issue:** quarantine compromised dependencies, restore approved pins, rotate credentials if exposed and rebuild trusted artifacts.

**Rollback:** restore last approved revision, rerun lint/type/test/security gates, validate service SLOs and record change approval.

## Hands-on lab
[Chapter 068 — Static Analysis and Code Quality SRE/DBRE Lab](labs/068-static-analysis-linting-code-quality-sre-dbre-lab.md) provides executable code, test suite, Ruff/mypy/pre-commit/CI configuration, failure injection and a 100-point assessment.

**Next:** Chapter 069 — Python Security Testing and Dependency Auditing (provisional).
