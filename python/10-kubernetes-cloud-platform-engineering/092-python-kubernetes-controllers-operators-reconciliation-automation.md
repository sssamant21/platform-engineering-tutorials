# Chapter 092 — Python Kubernetes Controllers, Operators and Reconciliation Automation

**Part 10 — Kubernetes, AWS, Azure and GCP · Chapter 092/120 · Python 3.11+**

[Executable SRE/DBRE lab](labs/092-kubernetes-controllers-operators-reconciliation-sre-dbre-lab.md) · [Standalone project](labs/092/README.md)

## 1. Objectives

Build a deterministic Python reconciliation engine for a custom resource (CR), with resource validation, desired/observed-state comparison, work queues, watch-to-relist recovery, bounded retries, simulated leader election, finalizer-safe deletion, idempotency, dry-run, audit events, automated tests, and production operational runbooks.

**Safety:** The executable project uses an in-memory fake Kubernetes API only. It never contacts or mutates a real cluster. The example RBAC and CRD are documentation, not automatically applied.

## 2. Architecture and reconciliation contract

```text
Kubernetes API / watch / informer cache
          | add/update/delete + resync
          v
  keyed, deduplicating work queue
          | bounded retries, backoff
          v
  leader lease/fencing check
          | fetch current CR (not event payload)
          v
  reconcile(namespace/name)
          | validate generation, finalizers, spec
          | compare desired with observed
          v
  plan only / approved, idempotent writes
          | optimistic concurrency / patch status
          v
  audit, metrics, requeue on drift
```

Reconciliation is **level-based**: converge observed state toward desired state. Watches are hints, not reliable commands. Reconcile may run repeatedly or concurrently; every operation must be idempotent, scoped, and bounded. An operator is a controller that encodes application/domain operational knowledge, such as a database lifecycle, but cannot replace human judgment for destructive DBRE actions.

## 3. CRDs and API design

A CustomResourceDefinition registers a new API resource. Choose a versioned group and a structural OpenAPI schema. Specify namespaced versus cluster-scoped explicitly. Prefer validation, defaults, status subresource, printer columns, and conversion strategy when introducing multiple served versions.

Example CRD for a **read-only synthetic** database health assessment:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databasechecks.sre.example.io
spec:
  group: sre.example.io
  scope: Namespaced
  names:
    plural: databasechecks
    singular: databasecheck
    kind: DatabaseCheck
    shortNames: [dbcheck]
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: [service, desiredHealthy]
              properties:
                service: {type: string, minLength: 1, maxLength: 40}
                desiredHealthy: {type: boolean}
            status:
              type: object
              properties:
                observedGeneration: {type: integer, minimum: 0}
                healthy: {type: boolean}
      subresources:
        status: {}
```

Use an API group owned by your organization in real deployments; the example domain is illustrative. Validate scope and names on both the API server and controller side. Never store passwords in CR specs/status.

## 4. Reconcile loop and resource lifecycle

1. Fetch latest object by key; a 404 means it was deleted and cached state can be forgotten.
2. If deletionTimestamp exists, run a **safe cleanup plan**, verify dependent resources, then remove only the controller's own finalizer. The lab intentionally **does not remove finalizers**, because no external cleanup exists.
3. If the finalizer is absent and the CR is active, plan to add it; production writes require approval and resourceVersion preconditions.
4. Compute status from observed evidence; update the status subresource only if changed, with observedGeneration matching the reconciled spec.
5. On transient error, requeue with capped backoff; on invalid spec, record a condition and wait for a spec change rather than hot-loop.
6. Periodically resync to recover missed events and drift.

For stateful workloads, avoid forced finalizer removal, PVC deletion, primary restarts or replica-set reconfiguration without owner-approved runbooks, backups and quorum checks.

## 5. Watches, informers and work queues

The Kubernetes Python client exposes `watch.Watch().stream(...)`; a production informer-like design maintains a list/watch cache, resourceVersion, indexers and resync. Handle ADDED, MODIFIED, DELETED and BOOKMARK. On HTTP 410 Gone, **relist and rebuild** rather than replaying stale events. Watch disconnects and duplicate notifications are normal.

A queue should deduplicate by namespace/name, enforce max depth, track retry attempts and implement a dead-letter or operator-escalation path. Rate limits protect the API server. Never rely on the order of events across reconnects; always fetch current state before action.

## 6. Leader election and fencing

Production leader election typically uses `coordination.k8s.io/v1 Lease` with holder identity, lease duration and renew/acquire deadlines. A lease is **not a perfect distributed fence**: an old leader may still have an in-flight request. Use resourceVersion preconditions, a fencing epoch, or transactional downstream guarantees for externally visible writes. The offline lab simulates a lease owner and monotonically increasing epoch but does not provide distributed coordination.

## 7. Idempotency, dry-run and safe mutation

- Default to `dry-run`; emit deterministic action plans and no mutations.
- Avoid side effects for unchanged desired/observed state.
- Require explicit authorization, scope, approval and ownership for production writes.
- Use server-side apply with a dedicated field manager or optimistic resourceVersion checks.
- Separate spec from status updates; avoid status feedback loops.
- For ambiguous outcomes, reread authoritative state before retry.
- Include audit correlation IDs and metrics without exposing secrets.

## 8. Authentication and RBAC

Run under a dedicated service account with a projected short-lived token and trusted API CA. The controller should have only required verbs on its CRD, plus get/list/watch on specifically needed dependencies and get/update on its own Lease. Do **not** grant cluster-admin.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: databasecheck-controller
  namespace: sre-lab
rules:
  - apiGroups: ["sre.example.io"]
    resources: ["databasechecks"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["sre.example.io"]
    resources: ["databasechecks/status"]
    verbs: ["get", "patch", "update"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "create", "update"]
```

Production finalizer addition/removal needs `patch` or `update` on the main CR resource; intentionally absent from this read-oriented example. Bind via namespace-scoped RoleBinding after review. CRD installation itself is cluster-scoped and should be a separate administrator-controlled change.

## 9. SRE/DBRE incident scenarios

| Scenario | Controller behavior |
|---|---|
| PostgreSQL primary unavailable | Record condition; no blind failover |
| MongoDB replica lag / election | Reconcile health; preserve quorum |
| Elasticsearch disk/large shards | Report saturation; no index deletion |
| Kafka consumer lag | Correlate external metrics before changes |
| Kubernetes API 429 / 503 | Bounded backoff and requeue |
| Watch 410 | Relist, reset cache and resume |
| Leader lease expired | Stop applying; reacquire and refetch |
| CR finalizer stuck | Surface condition; manual cleanup verification |
| Duplicate watch events | Deduplicated key and idempotent plan |
| Stale generation | Requeue and update status for current generation |
| Status conflict 409 | Refetch; do not blind overwrite |
| Unauthorized RBAC 403 | Fail closed and escalate |

## 10. Troubleshooting runbooks

**Controller not reconciling:** check ServiceAccount identity, RoleBinding, leader lease, queue depth, API errors, informer sync, resourceVersion and controller logs.

**Hot-loop / API throttling:** inspect retries and requeue behavior; add capped exponential backoff, jitter, queue limits and invalid-spec terminal conditions.

**Finalizer blocked:** inspect deletionTimestamp, dependent resource ownership and cleanup evidence. Never remove another controller's finalizer.

**Split-brain leaders:** stop external writes, verify Lease ownership/epoch, fence stale workers and reconcile authoritative state.

**DBRE incident:** inspect quorum, replica lag, disk IOPS, PVC health, backups and SLOs before operator-controlled changes.

**Watch gap:** relist and reconstruct cache after HTTP 410, timeout or reconnect; never assume events were complete.

## 11. Hands-on lab and assessment

The [Chapter 092 lab](labs/092-kubernetes-controllers-operators-reconciliation-sre-dbre-lab.md) includes executable Python, deterministic fake API, unit tests, incident simulations, production extension exercises, troubleshooting and a **100-point assessment**.

**Limitations:** Fake leader election, fake resource versions, no live watch, no actual Kubernetes client calls, no authenticated approval and no production writes. Real cluster and CI validation are separate acceptance gates.

**Next proposed:** Chapter 093 — Python Kubernetes Deployment, GitOps and Release Automation.
