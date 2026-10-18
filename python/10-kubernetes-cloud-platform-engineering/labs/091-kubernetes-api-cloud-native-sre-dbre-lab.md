# Chapter 091 — Kubernetes API and Cloud-Native Platform Engineering SRE/DBRE Lab

**Executable project:** [091/README.md](091/README.md) · [Python source](091/kube_lab.py) · [offline tests](091/test_kube_lab.py)

## Mission

Implement safe Kubernetes inventory, pagination, retries, Pod/Deployment health assessment and watch event reconciliation using Python. Run deterministic fake-client tests before optionally connecting to an explicitly approved **nonproduction** namespace using the official Kubernetes Python client.

## Architecture

\`\`\`text
explicit context + namespace -> Kubernetes client (optional)
                                      |
fake CoreV1Api (default) -> bounded list/pagination -> Pod summary
                                      |
                         rollout generation / replicas
                                      |
                          synthetic watch replay
                                      |
                        JSON diagnosis + runbook
\`\`\`

## Lab 1 — Offline environment and tests

\`\`\`bash
cd python/10-kubernetes-cloud-platform-engineering/labs/091
python -m compileall -q kube_lab.py test_kube_lab.py
python -m unittest -v test_kube_lab.py
python kube_lab.py --dry-run
python kube_lab.py
\`\`\`

No cluster, cloud identity, credentials, or third-party dependencies are needed.

## Lab 2 — Optional Kubernetes SDK inventory

Install a reviewed Kubernetes Python SDK and run only against a dedicated nonproduction namespace:

\`\`\`bash
python -m pip install "kubernetes>=29,<35"
kubectl config get-contexts
kubectl auth can-i list pods -n sre-lab --context YOUR_STAGING_CONTEXT
python kube_lab.py --live --context YOUR_STAGING_CONTEXT --namespace sre-lab
\`\`\`

The live adapter uses \`config.load_kube_config(context=...)\` and \`CoreV1Api.list_namespaced_pod\`. It does not write or watch cluster resources. Inspect namespace RBAC and certificate trust before running. Never use cluster-admin credentials for an inventory lab.

## Lab 3 — Discovery and RBAC design

Review \`CoreV1Api\`, \`AppsV1Api\`, \`AuthorizationV1Api\`, \`ApisApi\` and \`CustomObjectsApi\`. Compare API discovery with resource discovery. Design a namespace-scoped Role and RoleBinding for get/list/watch of Pods, Events and Deployments. Explain SelfSubjectAccessReview and the difference between authentication and authorization. This exercise is design-only: the sample code does not create RBAC objects or invoke a live SelfSubjectAccessReview.

## Lab 4 — Pagination, watch and reconciliation

Exercise fake continuation tokens and budget limits. HTTP 410 on a watch or list means relist and rebuild the cache; do not continue with stale resourceVersion. Replay ADDED/MODIFIED/DELETED/BOOKMARK and explain why events should enqueue reconciliation rather than trigger one-time destructive operations.

## Lab 5 — Deployment health

Compare desired, updated and available replicas, \`metadata.generation\` and \`status.observed_generation\`. A rollout may be pending, degraded or healthy. Inspect events and dependencies before suggesting rollback. Never restart a stateful primary solely because a Pod is not Ready.

## Production incident simulations

| # | Scenario | Expected behavior | Mode |
|---|---|---|---|
| 1 | Paginated inventory | All pages combined | Automated |
| 2 | Empty namespace | Empty inventory | Automated |
| 3 | Invalid namespace/limit | Reject | Automated |
| 4 | Object/page budget exceeded | Fail closed | Automated |
| 5 | Continuation-token loop | Reject | Automated |
| 6 | HTTP 429 | Bounded retry | Automated |
| 7 | HTTP 403 | No retry | Automated |
| 8 | HTTP 503 exhaustion | Surface failure | Automated |
| 9 | Running/ready Pod | Healthy | Automated |
| 10 | Pending Pod | Not ready | Automated |
| 11 | Missing container status | Not ready | Automated |
| 12 | Duplicate/missing Pod name | Reject | Automated |
| 13 | Healthy Deployment rollout | Healthy | Automated |
| 14 | Stale observed generation | Pending | Automated |
| 15 | Insufficient available replicas | Degraded | Automated |
| 16 | Invalid Deployment | Reject | Automated |
| 17 | Watch ADDED/DELETED | Update cache | Automated |
| 18 | Watch BOOKMARK | Advance resourceVersion | Automated |
| 19 | Watch HTTP 410 | Relist required | Automated |
| 20 | Unknown watch event | Reject | Automated |
| 21 | Watch budget exceeded | Stop | Automated |
| 22 | Invalid watch object | Reject | Automated |
| 23 | Dry-run | No API calls | Automated |
| 24 | Fake-client inventory | Zero mutations | Automated |
| 25 | Wrong kubeconfig context | Stop and verify | Guided |
| 26 | Expired cloud token | Reauthenticate | Guided |
| 27 | RBAC forbidden | Review RoleBinding | Guided |
| 28 | API server overloaded | Back off | Guided |
| 29 | ImagePullBackOff | Inspect registry and secret | Guided |
| 30 | PVC pending | Inspect StorageClass/PV | Guided |
| 31 | PostgreSQL StatefulSet failure | Preserve quorum | Guided |
| 32 | MongoDB Operator stuck finalizer | Diagnose owner/controller | Guided |

## Troubleshooting and runbooks

**Auth/RBAC:** verify kubeconfig context, cluster endpoint, identity mapping and namespace RoleBinding. Never disable TLS or grant cluster-admin to solve a list permission.

**API throttling:** limit concurrency, respect Retry-After, bound pagination and use exponential backoff with jitter in production.

**Watch expiration:** relist from a fresh resourceVersion and rebuild cache.

**Rollout stalled:** compare generations, updated/available replicas, Pod events, node pressure, images and PVC state.

**Stateful DBRE incident:** verify replica quorum, storage, backups and operator status before any approved change.

## 100-point assessment

| Domain | Points |
|---|---:|
| API discovery, authentication and RBAC | 20 |
| Pagination and inventory correctness | 20 |
| Watch semantics and reconciliation | 15 |
| Rollout and workload health | 15 |
| Retry, dry-run and security | 15 |
| Tests, incident simulations and runbooks | 15 |
| **Total** | **100** |

**Pass target:** ≥90/100 plus independent offline tests and review of optional live-cluster permissions.

**Validation:** The GitHub source and tests are published. Runtime/CI execution and live Kubernetes SDK testing remain pending.
