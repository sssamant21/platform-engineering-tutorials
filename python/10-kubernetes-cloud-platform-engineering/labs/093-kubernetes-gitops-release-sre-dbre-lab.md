# Chapter 093 — Kubernetes Deployment, GitOps and Release Automation SRE/DBRE Lab

[Standalone project](093/README.md) · [Executable Python](093/release.py) · [33 automated tests](093/test_release.py)

## Mission

Integrate immutable image digests, desired/observed Deployment state, GitOps drift, canary telemetry, rollout health, approval gates and rollback proposals into a deterministic Python release-planning lab. The entire lab is **offline, dry-run and read-only**.

## Architecture

```text
Git release revision -> desired immutable image
                               |
Synthetic Kubernetes Deployment observed state
                               |
generation / available / updated / image / Git revision
                               |
Canary metrics -> error rate + latency p95 + minimum requests
                               |
Simulated approval -> exact SHA-256 plan digest + rollback evidence
                               |
           promote / hold / rollback proposal
                               |
                    JSON audit-ready report
```

## Lab 1 — Execute and validate

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/093
python -m compileall -q release.py test_release.py
python -m unittest -v test_release.py
python release.py --dry-run
python release.py --fail-canary
```

Expected: healthy canary yields `propose-promotion`; failed canary yields `propose-rollback`. Both produce **zero mutations and zero network calls**.

## Lab 2 — Kubernetes deployment orchestration

Inspect the `Release` and `Observed` models. Reject mutable image tags, invalid namespaces, invalid replica counts and unapproved Git revisions. Compare `metadata.generation` against `status.observed_generation`, then desired/updated/available replicas and image digest. Investigate stale rollout, image mismatch and Git drift.

## Lab 3 — GitOps reconciliation

Use `reconcile_git` to detect synced versus out-of-sync state. Explain how Argo CD Applications and Flux Kustomizations/HelmReleases converge desired Git state, and why direct emergency Deployment edits may be reverted by the controller. Design a reviewed Git revert to a known-good immutable image digest.

## Lab 4 — Progressive delivery and SLOs

The simulator requires at least 100 request samples, error rate no greater than 1%, and latency p95 no greater than 500 ms. These are **illustrative** thresholds, not production SLO defaults. Test error spikes, high latency, missing telemetry and low traffic. Discuss comparison with a baseline, time windows, error-budget burn and statistical confidence.

## Lab 5 — Approval gates, dry-run and rollback

The release plan includes a SHA-256 digest and simulated approval checks. A missing approval, mismatched digest or untested rollback blocks promotion. A canary failure produces a rollback *proposal*, never an automatic deployment change. In production, require authenticated approval, separation of duties, protected Git branches and verified rollback compatibility.

## Incident simulations

| # | Scenario | Expected behavior | Mode |
|---|---|---|---|
| 1 | Valid immutable image | Accepted | Automated |
| 2 | Mutable image tag | Rejected | Automated |
| 3 | Invalid namespace | Rejected | Automated |
| 4 | Invalid replica count | Rejected | Automated |
| 5 | Invalid Git revision | Rejected | Automated |
| 6 | Stable plan digest | Deterministic | Automated |
| 7 | Healthy rollout | Healthy | Automated |
| 8 | Stale observed generation | Progressing | Automated |
| 9 | Unavailable replicas | Progressing | Automated |
| 10 | Image digest drift | Drift | Automated |
| 11 | Git revision drift | Drift | Automated |
| 12 | Invalid rollout counters | Rejected | Automated |
| 13 | Missing telemetry | Hold | Automated |
| 14 | Insufficient samples | Hold | Automated |
| 15 | Healthy canary | Promotion proposal | Automated |
| 16 | Elevated errors | Rollback proposal | Automated |
| 17 | High latency p95 | Rollback proposal | Automated |
| 18 | Invalid request sample | Rejected | Automated |
| 19 | Missing latency values | Rejected | Automated |
| 20 | Invalid canary policy | Rejected | Automated |
| 21 | Valid simulated approval | Proposal permitted | Automated |
| 22 | Missing approval | Hold | Automated |
| 23 | Wrong plan digest | Hold | Automated |
| 24 | Untested rollback | Hold | Automated |
| 25 | Failed canary with approval | Rollback proposal | Automated |
| 26 | Failed canary without approval | Hold for approval | Automated |
| 27 | GitOps synchronized | No drift | Automated |
| 28 | GitOps drift | Reconcile proposal | Automated |
| 29 | Dry-run | Zero mutations | Automated |
| 30 | CLI healthy/failure | Structured JSON | Automated |
| 31 | Argo CD Application OutOfSync | Investigate Git revision | Guided |
| 32 | Flux source-controller unavailable | Diagnose source/credentials | Guided |
| 33 | Kubernetes API 429 | Backoff and reduce concurrency | Guided |
| 34 | Watch 410 | Relist from fresh resourceVersion | Guided |
| 35 | PostgreSQL migration regression | Preserve data and rollback plan | Guided |
| 36 | Elasticsearch search latency | Correlate disk IOPS and rollout | Guided |
| 37 | MongoDB election during rollout | Preserve quorum | Guided |
| 38 | Kafka lag after release | Check consumer and broker health | Guided |

## Production troubleshooting runbooks

**Stalled Deployment:** inspect generations, updated/available replicas, probes, image pulls, quota, node pressure and PVCs.

**GitOps drift:** compare desired Git commit and observed resources; inspect Argo CD sync/health or Flux Kustomization conditions. Fix source-of-truth drift in Git.

**Canary failure:** validate metric freshness, eligible traffic and baseline; halt promotion, request reviewed Git revert and verify user-visible SLO recovery.

**Approval failure:** confirm signed/reviewed Git change, exact plan digest, owner, change window, rollback test and security policy.

**DBRE regression:** protect backups, replication, quorum and RPO/RTO; avoid destructive schema rollback or blind database restart.

**API failure:** distinguish RBAC 403, throttling 429, stale watch 410 and transient 5xx; use bounded retry and operator escalation.

## 100-point final assessment

| Competency | Points |
|---|---:|
| Kubernetes rollout health and immutable artifacts | 20 |
| Argo CD/Flux GitOps reconciliation | 15 |
| Progressive delivery, telemetry and SLO gates | 20 |
| Approval, dry-run, idempotency and rollback | 20 |
| Automated tests and incident simulations | 15 |
| Troubleshooting, security and runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90/100, independent test execution, correct failure simulations and operator-reviewed release/rollback runbooks.

**Validation:** 33 offline tests passed on a local development copy. Execution of the exact GitHub-committed source, CI and real-cluster integrations remains pending.
