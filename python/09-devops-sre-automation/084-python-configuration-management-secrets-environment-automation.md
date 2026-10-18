# Chapter 084 — Python Configuration Management, Secrets and Environment Automation

**Part 09 — DevOps, SRE and Automation | Chapter 084 of 120 | SRE/DBRE**

## Mission

Build a validated, observable and secure configuration pipeline for Python services. Combine TOML, safe YAML, environment variables and explicit command-line overrides with Pydantic Settings v2. Distinguish configuration from secrets, validate before connecting to external services, detect drift, and safely roll out and roll back changes.

**Lab:** [Chapter 084 — Configuration and Secrets Automation](labs/084-configuration-secrets-environment-automation-sre-dbre-lab.md). It contains independently runnable Python files and automated tests. All secrets in the lab are synthetic; no production secret manager or cloud account is required.

## 1. Architecture and trust boundaries

\`\`\`text
       version-controlled TOML/YAML (nonsecret)
                        |
                 safe parsing
                        |
         defaults < file < environment < CLI
                        |
              Pydantic validation
                        |
       immutable effective configuration
                        |
      redacted diagnostics + config fingerprint
                        |
    service / database client / health readiness
                        |
       audit, canary, rollback, rotation
\`\`\`

The ordering above is a **deliberate policy** for this chapter. Many libraries choose a different default precedence; document and test yours. Secrets are injected separately from configuration files. A source may be syntactically valid but still unauthorized: validate allowed environments, endpoints, timeouts, feature flags and tenant boundaries.

## 2. TOML and YAML

Python 3.11+ ships \`tomllib\` for reading TOML; it does not include a TOML writer. TOML is useful for typed application settings:

\`\`\`toml
service_name = "postgres-health"
environment = "lab"
endpoint = "https://example.invalid/health"
timeout_seconds = 3.0
max_retries = 2
\`\`\`

YAML is common in Kubernetes, Helm and GitOps. Use \`yaml.safe_load\` rather than unsafe object construction, reject non-mapping roots and unexpected fields, and bound file size. YAML supports aliases and complex structures; untrusted inputs need additional depth/size and resource controls. Prefer one canonical format for each deployed service and define how merges work. Do not silently combine two conflicting base files.

## 3. Layered configuration and environment variables

A predictable precedence example:

| Priority | Source | Example | Safety rule |
|---|---|---|---|
| 1 | Typed defaults | \`timeout_seconds=3\` | Conservative and documented |
| 2 | TOML/YAML file | \`max_retries=2\` | Reviewed, nonsecret |
| 3 | Environment | \`APP_TIMEOUT_SECONDS=5\` | Strict allowlist and parsing |
| 4 | Explicit CLI | \`--timeout-seconds 6\` | Operator-scoped override |

Do not dump the full environment to logs. An unset variable differs from an empty string. Treat boolean parsing explicitly; the string \`"false"\` is not falsy in Python. Avoid accidental overrides from inherited CI environments. Environment variables are not an ideal place for high-value secrets because they may appear in diagnostics, child processes or debugging tools.

## 4. Pydantic Settings v2

\`pydantic-settings\` integrates environment-based settings with Pydantic v2 validation. \`BaseSettings\` normally applies its own source precedence (initialization arguments before environment, dotenv, file secrets and defaults); this chapter's executable loader explicitly merges sources before calling a \`BaseModel\` so that the policy is visible and testable. Use \`ConfigDict(extra="forbid")\`, \`Field\` bounds, \`Literal\` environment allowlists, \`AnyUrl\` or custom endpoint validation and \`SecretStr\` for sensitive values. \`SecretStr\` masks routine representations but does **not** encrypt data or guarantee secrets cannot leak; never serialize raw values.

## 5. Secrets lifecycle

Secrets must be supplied through an approved provider in production (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, Kubernetes external-secret integration or equivalent). Apply least-privilege IAM/RBAC, scoped identities, short TTLs, rotation, revocation, audit logging and startup fail-closed behavior. Never commit secrets, tokens or production DSNs. File-mounted secrets should have restrictive permissions, a known ownership model and atomic rotation; symlink changes and inode replacement require careful reloading. Avoid printing secret bytes or embedding credentials in URLs.

The lab uses a **synthetic** \`SecretStr\` value passed in memory. A production secret-provider adapter is an explicit extension; no connector is contacted.

## 6. Validation, secure defaults and drift

Validate schema and semantics before opening a network connection. Enforce HTTPS for remote endpoints, prohibit \`verify=False\`, reject production overrides that disable TLS, and bound retries/timeouts. Configuration drift can be detected by hashing a canonical **redacted, nonsecret** projection; a hash of the entire configuration including secrets risks leakage through offline guessing and is not needed for ordinary drift alerts. Do not infer authorization from a matching fingerprint.

Use a two-phase rollout: validate candidate, emit redacted diff, canary, check error budget and dependent services, promote, then monitor. Roll back to a previously validated version, not an unreviewed file.

## 7. SRE/DBRE scenarios

- **PostgreSQL:** reject unapproved hosts, validate TLS and connection pool budgets, rotate credentials without exhausting connections.
- **Elasticsearch/OpenSearch:** validate index names, shard/retention thresholds and feature-flagged maintenance windows; do not perform index deletion from a config reload.
- **MongoDB:** validate replica-set and TLS settings; avoid logging connection strings with credentials.
- **Kafka/MSK:** validate SASL/TLS and broker allowlists; treat credentials as secrets.
- **Kubernetes:** compare ConfigMap/Secret mounts, detect rollout drift and avoid printing \`Secret\` manifests.
- **Snowflake:** validate account/warehouse allowlists and secret-provider identities; reject expensive default concurrency.

## 8. Observability

Track \`config_load_success_total\`, \`config_validation_failure_total\`, last successful reload time, config version, approved source, drift events and rotation status. Emit structured events with correlation ID and a redacted fingerprint. Never label metrics with secrets or arbitrary user-provided values. Treat configuration reload as a change with an owner, approval and rollback path.

## 9. Incident simulations

1. Invalid TOML syntax.
2. Unsafe YAML object payload.
3. YAML non-mapping root.
4. Unexpected configuration key.
5. Oversized configuration file.
6. Missing required secret.
7. Secret accidentally printed.
8. Environment override precedence mismatch.
9. Boolean string parsing bug.
10. Timeout outside approved range.
11. Retry storm from excessive retry count.
12. HTTP endpoint without TLS.
13. Wrong production endpoint.
14. Secret rotation without connection refresh.
15. Secret provider outage.
16. Stale ConfigMap mounted into a pod.
17. Drift between staging and production.
18. Inherited CI variable overrides a safe default.
19. Concurrent reload during request processing.
20. Invalid feature flag combination.
21. Rollback to a revoked credential.
22. Database pool exhaustion after config rollout.
23. YAML alias/depth resource exhaustion.
24. Credentials exposed in exception logs.

## 10. Troubleshooting matrix

| Signal | Likely cause | Response |
|---|---|---|
| Startup validation fails | Missing field, bad type, unknown key | Fix candidate config; do not bypass validator |
| Unexpected endpoint | Override precedence or stale deployment | Inspect redacted source trace and effective endpoint |
| Authentication failure | Expired or rotated secret | Check provider identity and rotation; do not print value |
| TLS error | Trust bundle/hostname mismatch | Repair trust chain; never disable verification |
| Config drift | Multiple rollout versions | Compare approved fingerprints and deployment revisions |
| Increased 5xx after rollout | Unsafe timeout/retry/pool settings | Revert to validated config and check downstream saturation |
| Reload races | Mutable global settings | Use immutable snapshot and controlled swap |

## 11. Runbooks

**Configuration deployment:** review schema, run tests, inspect redacted plan, verify owner and change window, canary, promote and monitor.

**Secret rotation:** confirm provider access, rotate credential, refresh clients/pools, test new identity, revoke old credential after overlap, record audit evidence.

**Validation failure:** fail closed, preserve previous working configuration if already running, alert owner and reject the candidate.

**Config drift:** compare deployment revision and redacted fingerprint, find precedence source, reconcile through GitOps or approved change.

**Incident rollback:** restore last-known-good nonsecret configuration, validate secret references separately, verify SLO and document RCA.

## 12. Hands-on lab and assessment

The [lab](labs/084-configuration-secrets-environment-automation-sre-dbre-lab.md) supplies TOML/YAML examples, \`pydantic\` v2, \`pydantic-settings\` v2, an \`argparse\` CLI, explicit source precedence, redacted JSON output, secret handling, 20+ automated tests, incident exercises, runbooks and a 100-point assessment. Runtime execution and production provider integration are separate validation steps.

**Next proposed:** Chapter 085 — Python Cloud Infrastructure Automation with AWS, Azure and GCP.
