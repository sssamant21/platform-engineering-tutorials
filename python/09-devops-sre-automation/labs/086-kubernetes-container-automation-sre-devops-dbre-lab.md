# Chapter 086 — Kubernetes and Container Automation SRE/DevOps/DBRE Lab

[Standalone executable project](086/README.md) · [Python inventory](086/inventory.py) · [20 unit tests](086/test_inventory.py) · [Optional live SDK adapter](086/live_inventory.py)

## Mission

Build safe, read-only Pod, Deployment and Docker container inventory. Validate Kubernetes namespace scope, list pagination, Deployment rollout health, watch event parsing, bounded output, dry-run and optional live client authentication.

## Architecture

\`\`\`text
argparse CLI -> scope / dry-run gate
 -> CoreV1Api.list_namespaced_pod (continue token)
 -> AppsV1Api.list_namespaced_deployment (continue token)
 -> optional Docker SDK containers.list(all=True)
 -> normalized records + health classification
 -> bounded JSON + partial flag -> alert/runbook
\`\`\`

## Lab 1 — Offline executable tests

\`\`\`bash
cd python/09-devops-sre-automation/labs/086
python -m compileall -q inventory.py live_inventory.py test_inventory.py
python -m unittest -v test_inventory.py
python inventory.py --namespace db-prod --dry-run
python inventory.py --namespace db-prod --max-records 2
\`\`\`

No cloud credentials, Kubernetes cluster, Docker daemon or third-party Python packages are required for the offline exercises. The project has actual \`.py\` files in GitHub.

## Lab 2 — Validate Pod and Deployment readiness

The fake Pod list includes a Running/Ready Pod and a Pending/not-Ready Pod across two pages. The fake Deployment reports desired/updated/ready/available replicas of two and matching observed generation. Change the test fixtures to simulate a rollout with stale observed generation, missing available replicas or desired replicas of zero. Distinguish Pod liveness from readiness, and a scaled-down Deployment from an available workload.

## Lab 3 — Pagination, watches and budgets

\`pod_records\` and \`deployment_records\` follow Kubernetes \`metadata._continue\` tokens and reject a repeated token. \`limited\` deduplicates normalized records and flags partial results. \`watch_events\` consumes a **provided** event iterator and accepts ADDED/MODIFIED/DELETED/BOOKMARK; it is not a live watch reconnect loop. A production watcher must relist on 410 Gone, handle resourceVersion and reconnect with bounded backoff.

## Lab 4 — Optional live inventory

\`\`\`bash
python -m pip install -r requirements.txt
python live_inventory.py --namespace approved-namespace --context approved-context
# Dry-run; no network call.
python live_inventory.py --namespace approved-namespace --context approved-context --max-records 100 --allow-live
\`\`\`

The final command requires an authorized kubeconfig and read-only namespace RBAC. For a Pod service account use \`--in-cluster\`. Optional \`--docker\` accesses the Docker daemon and requires explicit approval. Never use a cluster-admin identity for a simple inventory.

## Lab 5 — Incident simulations

| # | Scenario | Expected outcome | Coverage |
|---|---|---|---|
| 1 | Valid namespace | Scope accepted | Automated |
| 2 | Path-like namespace | Scope rejected | Automated |
| 3 | Pod pagination | Two pages consumed | Automated |
| 4 | Pod Running but not Ready | Unhealthy classification | Automated |
| 5 | Invalid Pod name | InventoryError | Automated |
| 6 | Repeated continue token | InventoryError | Automated |
| 7 | Healthy Deployment | Available | Automated |
| 8 | observedGeneration behind | Not healthy | Automated |
| 9 | Missing available replica | Not healthy | Automated |
| 10 | Scaled-down Deployment | Not serving | Automated |
| 11 | Invalid replica count | InventoryError | Automated |
| 12 | Docker container inventory | Running classification | Automated |
| 13 | Invalid container name | InventoryError | Automated |
| 14 | Duplicate record | Deduplication | Automated |
| 15 | Record budget reached | Partial flag | Automated |
| 16 | Invalid budget | Rejected | Automated |
| 17 | Watch ADDED/MODIFIED | Event types accepted | Automated |
| 18 | Watch budget reached | Partial flag | Automated |
| 19 | Unknown watch event | Rejected | Automated |
| 20 | CLI dry-run and offline mode | No live API calls | Automated |
| 21 | 403 namespace RBAC | Halt and request approved role | Guided |
| 22 | Watch 410 Gone | Re-list and resume | Guided |
| 23 | API 429 / 503 | Bounded retry and QPS control | Guided |
| 24 | Docker daemon unavailable | Disable Docker adapter | Guided |
| 25 | StatefulSet quorum risk | Escalate before remediation | Guided |

## Troubleshooting and runbooks

**Pod not Ready:** inspect probe failures, image pulls, restarts, events, dependencies and node pressure.

**Deployment rollout stalled:** compare observed generation, updated/ready/available replicas, quota, affinity, PDB and application errors.

**API watch lost:** re-list after 410, reset resourceVersion and deduplicate; avoid unbounded watch retries.

**RBAC 403:** verify service-account identity and namespace-scoped get/list/watch; do not bypass authorization.

**Docker socket unavailable:** verify approved daemon access; never expose an unauthenticated Docker TCP endpoint.

**Rollback:** read-only lab has no mutation to roll back. For future approved rollout automation, capture original revision, use controlled rollback and validate SLOs.

## CI template

See [project README](086/README.md). The CI example is intentionally not installed or enabled; it runs only offline unit tests after an approved review.

## 100-point assessment

| Topic | Points |
|---|---:|
| Kubernetes API authentication and RBAC | 15 |
| Pod/Deployment pagination and readiness | 25 |
| Docker SDK and socket security | 15 |
| Watch/reconnect/retry design | 15 |
| Dry-run, idempotency and bounded inventory | 10 |
| Automated tests and incident simulations | 10 |
| Troubleshooting and runbooks | 10 |
| **Total** | **100** |

**Pass target:** ≥90/100 plus independently executed tests. Runtime, Docker and cluster integration have not been verified by publication.
