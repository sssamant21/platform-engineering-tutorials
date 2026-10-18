# Chapter 092 — Executable Kubernetes Controller Lab

[Controller source](controller.py) · [Offline unit tests](test_controller.py)

**Python 3.11+ standard library only.** No Kubernetes credentials, cluster, SDK or network access needed.

## Execute

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/092
python -m compileall -q controller.py test_controller.py
python -m unittest -v test_controller.py
python controller.py --dry-run
```

Windows: `py -3 -m unittest -v test_controller.py`.

The controller uses an in-memory fake API. It **never mutates a real cluster**. Its non-dry-run mode tests a simulated leader fence only and still performs zero writes.

## Ten hands-on exercises

1. Validate CR namespace, name, generation, health and resourceVersion.
2. Produce deterministic reconciliation plans for drift, convergence and deletion.
3. Demonstrate idempotent no-op when observed state matches desired state.
4. Verify finalizer deletion hold pending independently verified cleanup.
5. Deduplicate namespace/name keys in a bounded work queue.
6. Replay synthetic watch ADDED, MODIFIED, DELETED and BOOKMARK events.
7. Trigger watch 410 and rebuild the queue from a fresh list.
8. Simulate a leader lease owner, epoch mismatch and expiration.
9. Test transient failures, retry budgets and terminal errors.
10. Simulate PostgreSQL primary outage and Elasticsearch storage pressure: report status without destructive remediation.

## Production incident drills

| Scenario | Expected action |
|---|---|
| Invalid CR or duplicate object | Reject |
| Missing resource | Forget key |
| Generation/status drift | Propose reconciliation |
| Stuck finalizer | Hold and escalate |
| Duplicate watch event | Deduplicate |
| Watch 410 | Relist |
| Queue overflow | Fail closed |
| Expired/stale leader lease | Fence |
| Retry exhaustion | Surface error |
| RBAC 403 | Stop, review RoleBinding |
| Status conflict 409 | Refetch before retry |
| API 429/503 | Backoff, bound attempts |
| Unknown external write outcome | Reconcile authoritative state |
| Stateful database incident | Preserve quorum/backups |

## Production extension checklist

Implement a real Kubernetes Python client list/watch cache, authenticated RBAC, Lease API leader election with fencing, optimistic resourceVersion or server-side apply, bounded work queues, metrics, jittered retry and independently approved mutations. Use a separate reviewed CRD installation process. The lab intentionally does not implement live informers, a real Kubernetes controller or finalizer removal.

## CI example (not enabled)

```yaml
name: chapter-092-controller-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/092
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q controller.py test_controller.py
      - run: python -m unittest -v test_controller.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** Published source and tests; runtime and CI execution of the committed version remain pending.
