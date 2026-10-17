# Chapter 028 — Python Project Configuration, Environment Variables and Secrets Hygiene

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 2–3 hours**

## Learning objectives
Design layered configuration for operational Python tools; distinguish defaults, TOML files, environment variables and CLI overrides; validate types and cross-field constraints; protect credentials; implement safe redaction; test precedence and error paths; and prepare SRE change-management runbooks.

## 1. Configuration is an operational interface
Configuration controls which environment a script inspects, what timeout applies, and whether a potentially dangerous action is enabled. A safe automation program must **fail closed** on malformed or contradictory configuration and avoid silent fallback to production. Separate configuration **values** from credentials, policy decisions, and executable code.

Typical layers (lowest to highest precedence):
```text
built-in safe defaults → reviewed TOML file → explicitly supplied environment map → CLI flags
```
Do not silently read every environment variable in the host process. Use a documented prefix and allowlist. Distinguish an **absent** override from an explicitly empty value: empty secrets, targets and environments should fail validation.

## 2. Python sources
- `os.environ`: process environment strings; values may be inherited from parent processes, CI jobs or container configuration.
- `argparse`: explicit operator overrides with clear help and errors.
- `tomllib` (Python 3.11+): read-only TOML parser. For Python 3.10, install an approved, pinned `tomli` dependency or use JSON; this lab uses **JSON** so it runs on Python 3.10+ with no third-party dependencies.
- `dataclasses`: immutable typed configuration objects.
- Secret manager clients: separate, authenticated interfaces; not demonstrated with live credentials in this offline lab.

## 3. Safe precedence example
```python
defaults = {"environment": "staging", "timeout_seconds": 5}
file_config = {"timeout_seconds": 8}
env_overrides = {"timeout_seconds": 12}
cli_overrides = {"environment": "dev"}
effective = defaults | file_config | env_overrides | cli_overrides
assert effective == {"environment": "dev", "timeout_seconds": 12}
```
For Python 3.10+, `dict | dict` produces a new mapping. Never mutate a shared defaults dictionary.

## 4. Types and validation
Environment variables are strings; do not use `bool(os.getenv("FLAG"))` because `bool("false")` is true. Use a strict parser for `true/false`, reject unknown fields, reject booleans as numeric values, validate ranges and allowed environment names, and avoid treating `NaN` as a valid timeout.

```python
def parse_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("expected true or false")
```

## 5. Secrets hygiene
- Never put credentials in `pyproject.toml`, committed `.env` files, GitHub examples, screenshots, issue tickets or exception strings.
- Environment variables reduce hardcoding but **are not a secret vault**: child processes, diagnostic dumps and privileged process inspection can expose them.
- Prefer workload identity or approved secret managers with least privilege and rotation.
- Avoid logging entire `os.environ`, full CLI arguments, HTTP authorization headers, connection URLs or exception objects containing secrets.
- Keep secret references separate from secret values. This lab accepts a placeholder secret reference (e.g., `vault://team/service`) and never retrieves its contents.
- Do not assume `repr()`, stack traces or JSON serialization automatically redact secrets.

## 6. Production design
```text
operator CLI ─┐
prefixed env ─┤
reviewed file ├─> merge → validate → immutable Config → read-only SRE check
safe defaults ┘                     |
                                    └─> sanitized summary
```
Prefer explicit configuration injection into functions instead of accessing global environment variables deep inside business logic. This makes tests deterministic and avoids hidden dependencies.

## 7. Configuration drift and change control
Treat configuration as versioned operational policy. Record which **sources** provided values, not secret values. Require review for production targets, endpoint changes, credential scope and destructive flags. Add validation to CI and verify that staging and production use intentionally different identities and endpoints.

## 8. SRE/DBRE use cases
- Elasticsearch diagnostics: choose staging/prod endpoint via an allowlisted profile; never infer prod from missing settings.
- PostgreSQL lag checks: strict positive timeouts and read-only connection identity.
- Kubernetes inventory: namespace allowlist, read-only credentials and explicit cluster context.
- Kafka consumer health: configured bootstrap endpoints and sanitized logs.
- Snowflake metadata checks: external secret reference and bounded query timeout.

## 9. Troubleshooting
| Symptom | Cause | Safe action |
|---|---|---|
| `false` enables a flag | Incorrect string-to-bool conversion | Use strict parser |
| Production selected unexpectedly | Unsafe default or override | Default staging; require explicit prod approval |
| Unknown environment key | Typo or unexpected injection | Reject unknown prefixed variables |
| Secret appears in error output | Printing raw config | Use sanitized summaries and fixed errors |
| Empty secret reference | Empty override replaced valid file value | Fail validation |
| Timeout accepts NaN | Missing finite-number check | Use `math.isfinite` |
| Different local and CI behavior | Hidden host environment | Inject explicit environment map |
| Config file missing | Incorrect path or deployment packaging | Use explicit path and fail clearly |

## 10. Operational runbook
1. Identify source layers and expected precedence.
2. Validate file schema, environment keys, types and cross-field constraints.
3. Confirm read-only identity and non-production default.
4. Run `--show-config` and inspect only sanitized output.
5. Execute synthetic or staging test with failure injection.
6. Record change approval for production profiles.
7. On failure, roll back the reviewed file or environment deployment, not a credential value copied into logs.

## 11. Lab and acceptance
[Chapter 028 — Layered SRE Configuration and Secrets Hygiene Lab](labs/028-layered-sre-configuration-secrets-hygiene-lab.md) provides executable code, synthetic JSON fixtures, 28 unit tests, failure injection and CLI validation. The lab never contacts a secret manager or real cluster.

**Next: Chapter 029 — Python CLI Design, argparse and Operational User Experience.**
