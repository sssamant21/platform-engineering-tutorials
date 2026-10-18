# Chapter 092 — Kubernetes Controllers, Operators and Reconciliation SRE/DBRE Lab

[Executable project](092/README.md) · [Python controller](092/controller.py) · [Offline unit tests](092/test_controller.py)

## Objective

Build a level-based, safe controller that converges custom-resource desired and observed state **as a plan**, without touching a live Kubernetes cluster. Practice watch replay, informer-style relist, bounded work queues, simulated leader fencing, finalizers, idempotency and operational diagnostics.

## Architecture

```text
Fake Kubernetes CR store
       |
synthetic watch -> deduplicating queue -> reconcile key
       |                                     |
    HTTP 410 -> relist                    get latest CR
                                             |
                                   validate and compare state
                                             |
                               finalizer/status/noop/deletion plan
                                             |
                                JSON report; zero cluster writes
```

## Lab 1 — Execute tests

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/092
python -m compileall -q controller.py test_controller.py
python -m unittest -v test_controller.py
python controller.py --dry-run
```

All commands are offline. No kubeconfig, Kubernetes Python client or cloud credentials are required.

## Lab 2 — Custom resource and reconciliation

Create an in-memory CR with a valid namespace/name, spec generation and desired health. Evaluate four conditions: absent finalizer, status drift, convergence, and deletionTimestamp with finalizer. Verify that a deleting resource retains its finalizer until an external cleanup process has been verified. The simulator does not add/remove finalizers or patch status.

## Lab 3 — Watch, informer and queue

Replay ADDED/MODIFIED/DELETED and BOOKMARK notifications. Queue only namespace/name keys; deduplicate repeated events. Simulate an expired resourceVersion (410): discard watch state and relist current resources. Trigger queue overflow and reconcile budget limits.

## Lab 4 — Leader election and retry

Test holder identity, lease epoch and expiration. Stale leaders must not proceed to an apply path. The simulator's non-dry-run option tests fencing but performs no mutations. Simulate transient API failures and bounded retry exhaustion. Discuss why a real Kubernetes Lease alone does not fence stale external database writes.

## Lab 5 — Production SRE/DBRE incident simulations

| Incident | Expected response | Validation |
|---|---|---|
| Invalid CR metadata | Reject | Automated |
| Duplicate CR | Reject | Automated |
| Resource absent | Forget key | Automated |
| Missing finalizer | Plan addition only | Automated |
| Spec/status drift | Plan status update | Automated |
| Converged resource | No-op | Automated |
| Deletion with finalizer | Hold | Automated |
| Duplicate watch events | Deduplicate | Automated |
| Watch HTTP 410 | Relist | Automated |
| Queue budget exhausted | Fail closed | Automated |
| Stale leader epoch | Reject | Automated |
| Expired leader lease | Reject | Automated |
| Transient read failure | Retry bounded | Automated |
| Retry exhausted | Surface failure | Automated |
| RBAC 403 | Escalate authorization | Guided |
| Status conflict 409 | Refetch current state | Guided |
| API server throttling | Rate limit and backoff | Guided |
| PostgreSQL primary failure | Preserve quorum, backups | Guided |
| MongoDB election | No blind stepdown | Guided |
| Elasticsearch disk pressure | No index deletion | Guided |
| Kubernetes finalizer stuck | Validate owner cleanup | Guided |
| Split-brain leaders | Fence writes and reconcile | Guided |

## Troubleshooting and runbooks

**Controller idle:** check leader status, queue length, cache synchronization, resourceVersion, RBAC and API connectivity.

**Hot loop:** inspect spec validation, status feedback loops, retries, jitter, queue budgets and error classification.

**Finalizer blocked:** verify dependent resource cleanup and backup state; never remove another operator's finalizer.

**Split brain:** halt externally visible writes, inspect Lease epoch and fencing, reconcile authoritative state.

**Database incident:** inspect replication/quorum, PVCs, disk IOPS, backup and SLOs; require explicit owner approval before changes.

**Watch gap:** relist and rebuild cache after 410, reconnect or timeout.

## 100-point capstone assessment

| Domain | Points |
|---|---:|
| CRD design and resource lifecycle | 20 |
| Reconciliation, idempotency and finalizers | 20 |
| Watches, queues and relist | 15 |
| Leader election and retries | 15 |
| RBAC, dry-run and safety | 15 |
| Automated tests, incidents and runbooks | 15 |
| **Total** | **100** |

**Acceptance:** ≥90/100 plus independent test execution, dry-run verification and an operator-reviewed production extension plan.

**Validation:** GitHub source and tests are published; committed runtime tests, CI and real-cluster integration remain pending.
