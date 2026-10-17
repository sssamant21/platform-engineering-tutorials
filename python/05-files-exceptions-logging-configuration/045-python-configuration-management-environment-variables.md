# Chapter 045 — Python Configuration Management and Environment Variables

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+ | 5–7 hours**

## Learning outcomes

Build an immutable validated configuration model, merge default/file/environment/CLI layers predictably, validate types and operational bounds, avoid leaking secrets, detect configuration drift, test precedence and failures, and prepare safe deployment/rollback runbooks.

## 1. Configuration as an operational contract

Configuration is part of the production system, not an unvalidated dictionary. A single incorrect timeout, retry budget or datastore endpoint can cause a reliability incident. Explicit schemas and allowlisted values reduce accidental behavior.

## 2. Precedence

The lab applies **defaults → JSON file → environment variables → explicit CLI overrides**. Each later layer replaces an earlier value for the same key. Record the *source* of each setting without recording secret values.

| Layer | Example | Priority |
|---|---|---:|
| Defaults | `timeout_seconds=5` | Lowest |
| File | `timeout_seconds=10` | 2 |
| Environment | `SRE_TIMEOUT_SECONDS=15` | 3 |
| CLI override | `timeout_seconds=20` | Highest |

This order is an intentional application contract, not a universal rule. Document precedence and make it consistent across deployments.

## 3. Environment variables

Use `os.environ` with a specific allowlist, not a dump of all environment variables. Variables arrive as strings; convert explicitly. Reject `True` as an integer, negative values, out-of-range timeouts, invalid service names, and unexpected keys. Environment variables can be visible to processes and diagnostics; avoid using them as a general-purpose secret store.

## 4. Immutable configuration

Use `@dataclass(frozen=True, slots=True)` to represent validated effective settings. Immutable objects prevent accidental in-process mutation but do not prevent external configuration changes or eliminate the need for rollout coordination.

## 5. Secrets

The lab stores **secret references**, not credentials. Supported synthetic reference schemes are `vault:`, `aws-sm:`, and `azure-kv:`. It never resolves those references or contacts a secret manager. In production, use managed identity, least-privilege secret retrieval, rotation, audited access, short-lived credentials and redacted diagnostics. A reference string may itself reveal sensitive resource naming; keep it out of reports.

## 6. Configuration drift

Compare a desired baseline to the effective configuration. Emit a sorted list of changed *public* fields. The lab reports only whether a secret reference is configured, never its value; it intentionally cannot detect changes between two nonempty secret references. Production secret-version drift requires a separate authorized check.

A SHA-256 fingerprint of sanitized public settings supports change detection; it is **not a security signature**, and it does not prove integrity of secret values.

## 7. Architecture

```text
defaults -----+
JSON file ----+--> merge --> schema validation --> immutable Config
environment --+                                   |
CLI overrides -+                            safe report + provenance
                                                  |
                                          baseline drift analysis
```

## 8. SRE/DBRE use cases

- PostgreSQL: validate synthetic replication-check timeout and retry budget.
- Elasticsearch: validate query probe configuration before rollout.
- Kafka: compare consumer-monitoring settings between staging and production.
- Redis: review logging and probe settings without exposing credentials.
- Kubernetes: map approved ConfigMap settings and secret references to an application schema.

All labs are offline; there are no real cloud or database connections.

## 9. Troubleshooting matrix

| Symptom | Likely cause | Response |
|---|---|---|
| Wrong effective value | Unexpected precedence | Inspect safe source provenance |
| Startup validation failure | Missing/unknown field | Fix schema or source |
| Invalid timeout | String conversion or bounds | Reject and correct |
| Secret in logs | Unsafe serialization | Contain, rotate, use safe report |
| Unexpected drift | File/env/CLI mismatch | Compare approved baseline |
| Configuration differs across pods | Partial rollout | Check rollout state and revision |
| Drift fingerprint mismatch | Public setting changed | Review diff; don't assume compromise |
| Configuration file rejected | Oversized or malformed JSON | Validate file and encoding |
| Duplicate JSON keys | Silent last-value-wins risk | Reject duplicate keys |
| Unknown env variable | Typo or unsupported name | Confirm documented prefix/allowlist |

## 10. Production runbooks

**Misconfiguration incident:** freeze rollout, inspect sanitized effective values and source provenance, restore approved baseline, validate and redeploy incrementally.

**Secret exposure:** restrict log/config artifact access, rotate affected credentials, audit retrieval, and remove unsafe serialization paths.

**Drift alert:** compare desired and effective public settings, identify owner and deployment revision, confirm whether change is approved; do not automatically overwrite production configuration.

**Configuration rollback:** retain last known-good version, validate in staging, roll back through GitOps or deployment controls, verify metrics and error budgets.

**Schema migration:** introduce new keys compatibly, test old and new configuration formats, enforce deprecation windows and coordinate with service owners.

## 11. Hands-on lab and acceptance

[Chapter 045 — Configuration Precedence, Secrets and Drift SRE/DBRE Lab](labs/045-configuration-precedence-secrets-drift-sre-dbre-lab.md) includes a complete executable project, CLI, synthetic fixtures, **50 automated tests**, failure injection and operational runbooks. The 50 tests passed in the Linux authoring sandbox.

**Next:** Chapter 046 — Python Command-Line Arguments and argparse for Operations.
