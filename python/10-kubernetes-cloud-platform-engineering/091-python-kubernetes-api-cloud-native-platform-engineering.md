# Chapter 091 — Python Kubernetes API and Cloud-Native Platform Engineering

**Part 10 — Kubernetes, AWS, Azure and GCP | Chapter 091/120 | Python 3.11+**

[Hands-on lab](labs/091-kubernetes-api-cloud-native-sre-dbre-lab.md) · [Executable source and tests](labs/091/README.md)

## Outcomes and architecture

Use the official Kubernetes Python client to discover APIs, authenticate safely, inspect RBAC, list/paginate workloads, reason about declarative resource lifecycle and reconciliation, consume watch streams, and implement bounded retries and read-only dry-runs. Design automation that is observable, idempotent, least-privilege and resilient to API failures.

\`\`\`text
Operator / automation job
  -> configuration (in-cluster SA or trusted kubeconfig)
  -> identity + RBAC check (SelfSubjectAccessReview)
  -> Kubernetes API discovery
  -> paginated list (namespace, selector, resourceVersion)
  -> inventory + rollout-health evaluation
  -> bounded watch/relist with resourceVersion
  -> JSON report / incident diagnosis / human-approved action
\`\`\`

**Lab safety:** offline mock client by default; optional live commands are read-only and require an explicitly selected context and namespace. No production cluster mutation is implemented.

## 1. Kubernetes Python client

Install \`kubernetes\` from a reviewed/pinned version compatible with your cluster. The \`client.CoreV1Api\`, \`AppsV1Api\`, \`AuthorizationV1Api\`, \`ApisApi\`, \`CustomObjectsApi\`, \`Watch\` and \`config\` modules cover core workloads, RBAC, discovery, CRDs and watches. SDK object models change with Kubernetes API versions: test against supported server versions and handle deprecated APIs.

Never enable \`verify_ssl=False\`, log bearer tokens, or embed kubeconfigs in artifacts. Prefer workload identity / projected service-account tokens in-cluster; on developer workstations use a carefully selected kubeconfig context. In EKS, AKS and GKE, cloud identity must map to Kubernetes RBAC or managed authorization. Authentication success does not imply authorization.

## 2. Discovery and resource lifecycle

API discovery starts at \`/api\`, \`/apis\` and group/version resource endpoints. Distinguish namespaced and cluster-scoped resources; avoid assuming CRDs behave like Pods. A declarative object moves through create, reconcile, status update, deletion timestamp and finalizers. Kubernetes controllers are level-triggered reconcilers: an event means "recheck desired and observed state", not "execute this action once".

Use optimistic concurrency (\`metadata.resourceVersion\`) and server-side apply field managers for writes, with conflict handling and explicit owner-approved change gates. Never blindly remove finalizers or force-delete stateful Pods.

## 3. Authentication and RBAC

In-cluster code calls \`config.load_incluster_config()\`; a workstation uses \`config.load_kube_config(context=...)\` with an explicitly selected context. The lab's optional live adapter uses an explicit kubeconfig context and refuses mutation. Use \`SelfSubjectAccessReview\` to check a specific verb/resource/namespace, but remember authorization may change between review and actual request. Least-privilege example for a read-only inventory collector:

\`\`\`yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: python-inventory-reader
  namespace: sre-lab
rules:
  - apiGroups: [""]
    resources: ["pods", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
\`\`\`

Bind to a dedicated service account through a namespace-scoped RoleBinding after owner approval. Discovery and SelfSubjectAccessReview may require additional permissions depending on cluster configuration. No ClusterRoleBinding is needed for a namespace-only inventory lab.

## 4. Pagination and consistent snapshots

\`list_namespaced_pod(namespace, limit=N, _continue=token)\` retrieves pages. Follow the returned \`metadata._continue\` until empty; impose a maximum page and object budget. Pagination may fail with HTTP 410 when a continue token expires. Restart from a fresh list rather than mixing old and new snapshots. Record \`metadata.resource_version\` and preserve namespace/selector across pages. Some API objects expose attributes via \`_continue\`, others may be dictionaries; the lab's fake model is deliberately minimal.

## 5. Watch streams and controller semantics

A watch is not a reliable message queue. Start from a known list resourceVersion; process ADDED/MODIFIED/DELETED/BOOKMARK, honor timeout and reconnect. HTTP 410 means the resourceVersion is too old: relist and rebuild state. Handle network disconnects, duplicate events, out-of-order observations, and \`ERROR\` events. Do not trigger destructive actions from a single watch event. Production controllers need leader election, bounded work queues, exponential backoff, rate limiting and periodic full reconciliation.

## 6. Retry policy and rate limiting

Retry transient 429, 500, 502, 503 and 504 responses with capped exponential backoff and jitter, respecting Retry-After and a total deadline. Do not retry 400/401/403/404 or 409 without understanding the operation. Reads are typically safe to retry; writes need idempotency, field ownership, precondition checks and a recovery path for ambiguous outcomes. Set API request timeouts and concurrency limits; avoid overloading control-plane APIs.

## 7. Rollout and workload health

For a Deployment, compare \`metadata.generation\` with \`status.observed_generation\`, desired replicas with updated/available replicas, and rollout conditions. Pending rollout is not necessarily failure. For Pods, inspect phases, container readiness, restarts, events and scheduling pressure. A Pod being Ready does not guarantee downstream database health or application SLO compliance.

## 8. Production SRE/DBRE cases

| Platform | Read-only diagnostics | Guardrail |
|---|---|---|
| EKS / AKS / GKE | Pod placement, rollout, API throttling | Context/namespace explicit |
| PostgreSQL StatefulSet | readiness, PVC events, replica health | No blind primary restart |
| MongoDB Operator | reconciliation status, finalizers, quorum | No unsafe stepdown |
| Elasticsearch Operator | shard allocation, storage and Pod health | No automatic index deletion |
| Kafka/MSK clients | consumer lag and connectivity | Kubernetes view alone insufficient |
| Observability stack | exporter Pods, scrape errors, OTel collector | Missing metrics are unknown |

## 9. Incident simulations

1. Wrong kubeconfig context; 2. expired token; 3. RBAC forbidden; 4. missing namespace; 5. API discovery failure; 6. API 429; 7. API 503; 8. timeout; 9. invalid selector; 10. paginated listing; 11. expired continue token; 12. infinite token loop; 13. inventory budget; 14. missing Pod metadata; 15. stale resourceVersion; 16. watch 410; 17. watch disconnect; 18. duplicate event; 19. unexpected event type; 20. Deployment not observed; 21. insufficient available replicas; 22. terminating Pod; 23. image pull failure; 24. PVC pending; 25. node pressure; 26. CrashLoopBackOff; 27. finalizer stuck; 28. leader-election split brain; 29. cross-namespace leak; 30. mistaken cluster-wide permissions.

## 10. Troubleshooting and runbooks

**Authentication:** verify chosen context, cloud identity, token expiration, certificate trust and server endpoint; never disable TLS validation.

**Authorization:** use a narrow SelfSubjectAccessReview and inspect Role/RoleBinding. Do not grant cluster-admin to fix a list permission.

**429/5xx:** inspect API server health, client QPS, Retry-After, request timeouts and concurrency; back off and reduce inventory scope.

**Pagination/watch 410:** discard expired continuation state, relist, reset resourceVersion and reconcile local cache.

**Rollout stuck:** compare desired/updated/available replicas, generation, conditions, Pod events, image pulls and capacity; request approval before rollback.

**Stateful incident:** validate quorum, PVC integrity, backups and RPO/RTO; avoid deleting Pods or finalizers as first response.

## 11. Lab and assessment

The [complete executable lab](labs/091-kubernetes-api-cloud-native-sre-dbre-lab.md) provides standalone Python, fake Kubernetes clients, offline unit tests, optional read-only live inventory adapter, incident drills and a 100-point acceptance rubric. Production use requires independent security review, supported SDK version testing, CI and operator approval.

**Next proposed:** Chapter 092 — Python Kubernetes Controllers, Operators and Reconciliation Automation.
