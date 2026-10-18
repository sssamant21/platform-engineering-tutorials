# Chapter 093 — Python Kubernetes Deployment, GitOps and Release Automation

**Part 10 — Kubernetes, AWS, Azure and GCP | Chapter 093/120 | Python 3.11+**

[Hands-on lab](labs/093-kubernetes-gitops-release-sre-dbre-lab.md) · [Executable project](labs/093/README.md)

## Learning outcomes

Build a safe, Git-driven Kubernetes release workflow using immutable image digests, declarative desired state, Kubernetes Python client concepts, Argo CD and Flux reconciliation, progressive delivery, rollout status checks, error-rate and latency gates, approval controls, rollback proposals, dry-run, idempotency and auditability.

## Architecture

```text
Pull request -> reviewed Git commit -> image digest -> GitOps repository
  -> Argo CD / Flux reconciler -> Kubernetes API -> Deployment/ReplicaSet/Pods
                                         |
                              observed generation, replicas
                                         |
                            canary telemetry + SLO gates
                                         |
                      approval + plan digest + rollback evidence
                                         |
                     promote / hold / rollback proposal (offline)
```

The accompanying **offline lab** evaluates synthetic deployments and canary metrics. It never connects to or mutates a Kubernetes cluster. A production system needs authenticated approval, Git provider integration, verified metrics, change governance, controller permissions and audit retention.

## 1. Kubernetes Python client and deployment orchestration

The official `kubernetes` Python package exposes `AppsV1Api`, `CoreV1Api`, `Watch` and `config`. Use explicit kubeconfig context in development and projected service-account identity in-cluster. List/get Deployments and Pods to inspect rollout state. For writes, use a GitOps source-of-truth workflow rather than patching live Deployment specs outside Git. Direct writes can be overwritten by GitOps reconciliation.

Readiness must compare `metadata.generation` with `status.observed_generation`, desired replicas with updated and available replicas, and image digest with desired Git revision. Also inspect conditions, events, image pulls, scheduling, PVCs and app-level SLOs. A Deployment showing available replicas does not guarantee application health.

## 2. GitOps architecture: Argo CD and Flux

**Argo CD:** Application/ApplicationSet reconciles Git or Helm desired state, detects drift, and exposes sync and health status. Sync windows, RBAC, Projects, sync waves and hooks constrain change rollout. Avoid unreviewed automated prune/self-heal for stateful resources.

**Flux:** source-controller fetches Git/OCI/Helm sources; kustomize-controller and helm-controller reconcile desired state. Suspend/resume, dependency ordering and health checks support maintenance and recovery.

Git remains authoritative. A rollback is normally a **reviewed Git revert or promotion of a known-good immutable image digest**; a live kubectl rollback can be immediately undone by the GitOps controller. Validate repository revision, deployment health and metrics after rollback.

## 3. Release artifact and idempotency

A release plan should bind environment, namespace, service, image by `sha256` digest, replica count, Git revision, expected current revision, approval identity, expiration and rollback reference. Canonical JSON plus SHA-256 provides an idempotency fingerprint; the fingerprint itself is **not** authentication. Require branch protections, signed/verified provenance where applicable, and independently authorized changes.

The lab rejects mutable image tags, invalid namespace/service names and malformed release revisions. It produces only advisory proposals.

## 4. Progressive delivery

Canary strategy: baseline -> 5% -> 20% -> 50% -> 100% (illustrative; real stages depend on traffic and risk). Gate each step using enough eligible requests, error rate, latency p95, availability SLI, saturation and telemetry freshness. Compare with baseline and control for low-traffic services. Hold if telemetry is missing or sample volume is insufficient; propose rollback when guardrails fail. Avoid treating one-minute averages as statistical proof.

Blue/green strategies switch traffic after health checks, requiring backward-compatible schema changes and fast rollback paths. Stateful DB migrations should use expand/migrate/contract; never automatically roll back destructive schema changes.

## 5. Approval and release gates

Require an authenticated owner-approved plan, exact immutable digest, tested rollback, capacity readiness, fresh telemetry, no active Sev1, adequate error budget, and policy-compliant change window. Dry-run must be default. The offline lab uses booleans to *simulate* approval and emits no writes. Production enforcement belongs in CI/CD and GitOps policy, not user-supplied flags.

## 6. Watch and retry semantics

Kubernetes watch streams can disconnect or return 410 Gone; relist and rebuild cache from a fresh resourceVersion. Handle API 429 and transient 5xx with bounded exponential backoff, jitter and Retry-After. Do not retry 403. Avoid duplicate actions: re-read authoritative Git and Kubernetes state before applying changes.

## 7. SRE/DBRE incident simulations

| Scenario | Diagnostic response |
|---|---|
| Git revision drift | Halt promotion; inspect sync |
| Observed generation behind | Wait or investigate rollout |
| Insufficient available replicas | Inspect scheduling, probes and image pull |
| Canary 5xx spike | Hold, propose reviewed rollback |
| Latency p95 regression | Hold/rollback proposal |
| Missing/low-volume metrics | Hold, never assume healthy |
| Approval digest mismatch | Deny promotion |
| Rollback untested | Block promotion |
| Argo CD out-of-sync | Inspect Application conditions, repo access |
| Flux reconciliation stalled | Inspect source/Kustomization/HelmRelease |
| Kubernetes API 429 | Rate limit, backoff |
| Kubernetes API 410 | Relist, recover watch |
| PostgreSQL migration failure | Protect schema/data and rollback plan |
| Elasticsearch query latency spike | Correlate IOPS, shard pressure and rollout |
| MongoDB primary election | Preserve quorum; no blind restart |
| Kafka consumer lag | Diagnose broker/client/backpressure |

## 8. Operational runbooks

**Pre-release:** verify immutable image, signed/approved Git change, namespace scope, capacity, rollback, SLOs, backup/restore evidence, paging route and on-call ownership.

**Stalled rollout:** inspect desired/updated/available replicas, observed generation, conditions, Pod events, quota, PVC and readiness. Pause risky promotion and escalate.

**GitOps drift:** compare desired Git revision with cluster state, inspect Argo CD or Flux controller status, confirm whether emergency changes are being reverted. Repair in Git rather than fighting reconciliation.

**Canary failure:** validate sample size and metric freshness; stop traffic increase, request reviewed rollback to known-good Git commit/image digest, and verify SLO recovery.

**Stateful DBRE failure:** validate backups, replication/quorum, migration compatibility, disk IOPS and RPO/RTO before any change.

**API failure:** bound retries and concurrency, preserve context/namespace, investigate 403/429/410 separately.

## 9. Acceptance and limitations

The [executable lab](labs/093-kubernetes-gitops-release-sre-dbre-lab.md) includes deterministic Python, offline automated tests, 20+ incident exercises, runbooks and a **100-point assessment**.

The implementation does **not** call the Kubernetes Python SDK, Argo CD, Flux or a Git provider: those integrations are taught conceptually and are production extension exercises. Offline simulation is not a production-ready deployment controller.

**Next proposed:** Chapter 094 — Python AWS Infrastructure and Cloud Operations Automation.
