# Chapter 086 — Python Kubernetes and Container Automation

**Part 09 — DevOps, SRE and Automation | Chapter 086/120 | Python 3.11+**

## Outcomes

Build a read-only Kubernetes and Docker inventory tool with Kubernetes Python client, Docker SDK for Python, scoped API authentication, namespace pagination, Deployment rollout readiness, Pod health, watch-stream recovery, rate limiting, retries, dry-run and automated tests. Understand why reconciliation and idempotency matter before adding write operations.

[Hands-on lab](labs/086-kubernetes-container-automation-sre-devops-dbre-lab.md) | [Standalone project](labs/086/README.md)

## Architecture

\`\`\`text
SRE operator / CI service account
  -> validated CLI / explicit scope / dry-run
  -> Kubernetes adapter (CoreV1Api, AppsV1Api)
      -> list pods + deployments (continue token pagination)
      -> resourceVersion watch (bounded timeout and 410 recovery)
      -> desired vs observed rollout health
  -> Docker adapter (Docker Engine API)
      -> local container inventory (authorized socket)
  -> canonical records + partial / errors / JSON report
  -> metrics, alerts, runbook and approved remediation
\`\`\`

This lab is **read-only** and its default execution uses injected fake clients. It does not change deployments, restart containers or require a live cluster. An optional live client performs explicitly approved read-only calls.

## 1. Kubernetes client and authentication

Install the official \`kubernetes\` Python package. For local approved use, \`config.load_kube_config(context=...)\` reads kubeconfig; in Pods, \`config.load_incluster_config()\` uses a mounted service account. In production use a dedicated service account with narrowly scoped \`get/list/watch\` verbs and namespace restrictions. Avoid cluster-admin, long-lived static tokens and arbitrary context selection. Kubernetes RBAC is enforced by the API server, not by CLI dry-run. Never log kubeconfig, tokens or certificate private keys.

Python Kubernetes client versions generally follow Kubernetes API release lines; validate compatibility with the server. Some client calls are synchronous; do not block an \`asyncio\` event loop with them without appropriate thread offloading.

## 2. Pods and Deployment inventory

\`CoreV1Api.list_namespaced_pod(namespace=...,limit=...,_continue=...)\` and \`AppsV1Api.list_namespaced_deployment\` return list objects with \`items\` and \`metadata._continue\`. Continue until the token is empty; a 410 ResourceExpired may require a fresh list and deduplication. Kubernetes list responses may represent a consistent snapshot when following continue tokens, but a restarted list after expiry is a new snapshot. Bound pages, objects, wall-clock time and output size.

For Pods inspect \`metadata.name\`, \`status.phase\`, container statuses, readiness and restart counts; \`Running\` alone does not imply Ready. For Deployments compare \`status.observed_generation\` with \`metadata.generation\`, \`status.updated_replicas\`, \`status.ready_replicas\`, \`status.available_replicas\` and \`spec.replicas\`. Do not call a rollout healthy until the controller has observed the intended generation and desired updated/available replicas are reached. Zero-replica Deployments are valid but should be classified as intentionally scaled down rather than serving traffic.

## 3. Docker SDK

\`docker.from_env()\` connects to the configured Docker daemon and \`client.containers.list(all=True)\` enumerates containers. Docker socket access is highly privileged and often effectively root-equivalent. Never mount \`/var/run/docker.sock\` into an untrusted workload or expose it over unauthenticated TCP. Use Docker SDK only on authorized local hosts; Kubernetes production workloads should be inspected through Kubernetes APIs rather than assuming Docker is the node runtime. Modern Kubernetes uses CRI runtimes such as containerd.

## 4. Watch streams and resourceVersion

The Kubernetes watch API streams \`ADDED\`, \`MODIFIED\`, \`DELETED\` and \`BOOKMARK\` events. A robust watcher performs an initial list, records the list resourceVersion, watches with a finite timeout, handles disconnects and 410 Gone by relisting, and reconnects with bounded exponential backoff. Watch events are **not** a durable exactly-once queue. Reconcile desired state and use stable object UID/resourceVersion to deduplicate. Avoid unbounded in-memory event accumulation.

## 5. Retry, rate limiting and API load

Use short connect/read timeouts, bounded retries for 429/5xx/network failures and honor \`Retry-After\`. Do not retry 401/403 as transient errors. Watch/list requests can put load on kube-apiserver and etcd; limit QPS, concurrency, pages and namespace scope. In Kubernetes Python client, configuration can set \`client_side_validation\`, connection pool sizing and request timeouts; these are not substitutes for server-side RBAC. Coordinate SDK-level and application-level retries.

## 6. Idempotency, dry-run and safety

Dry-run must not initialize a network client or perform API calls. Read-only inventory can be repeated without mutating cluster state, but observations may change between scans. For future writes, use server-side dry-run where supported, resourceVersion preconditions, server-side apply field ownership, rollout checkpoints, policy admission and explicit change approval. Never implement a generic "delete unhealthy pod" action based only on status.

## 7. SRE/DBRE scenarios

- **PostgreSQL StatefulSets:** inspect PVC mount health, readiness and storage pressure; do not restart a primary without replication/failover planning.
- **Elasticsearch/OpenSearch:** correlate Pod readiness with shard allocation and storage IOPS, not Pod state alone.
- **MongoDB:** identify operator-managed members and avoid manual Pod deletion that bypasses quorum/backup checks.
- **Kafka:** check broker Pods, partitions and lag before rolling maintenance.
- **AKS/EKS/GKE:** verify workload identity, namespace RBAC, rollout generations, autoscaler events and managed-control-plane API quotas.

## 8. Incident drills

1. kubeconfig missing; 2. wrong context; 3. expired token; 4. namespace 403; 5. list pagination; 6. 410 expired continue token; 7. Pod Running but not Ready; 8. CrashLoopBackOff; 9. image pull failure; 10. Deployment observedGeneration lag; 11. insufficient available replicas; 12. zero desired replicas; 13. watch disconnect; 14. watch 410 Gone; 15. duplicate watch event; 16. API 429; 17. apiserver 503; 18. TLS certificate failure; 19. Docker socket permission denied; 20. Docker daemon unavailable; 21. large namespace memory pressure; 22. Pod eviction; 23. StatefulSet quorum risk; 24. accidental cross-namespace scan.

## 9. Troubleshooting

| Signal | Investigate | Response |
|---|---|---|
| 403 Forbidden | service-account RBAC and namespace | Request approved get/list/watch only |
| Pod Running, not Ready | probes, container statuses, dependencies | Inspect events and application logs |
| Deployment stalled | generation, updated/ready/available replicas | Check scheduling, probes, quota and PDB |
| 410 Gone | expired continue token / resourceVersion | Re-list and restart bounded watch |
| API throttling | QPS, pagination, concurrent scanners | Reduce rate and respect Retry-After |
| Docker connection refused | daemon/socket access | Validate authorized local daemon |
| Large inventory | page and record budgets | Emit partial and scope smaller |
| TLS failure | CA bundle, hostname, kubeconfig | Repair trust; never disable verification |

## 10. Runbooks

**Inventory preflight:** verify context, cluster identity, namespace, approved service account and read-only verbs. Run offline dry-run before any live access.

**Stalled rollout:** inspect generation, replicas, Pod events, quota, scheduling and dependencies; use approved rollback procedure rather than blind restart.

**Watch recovery:** bound stream timeout, handle 410 by relist, reset resourceVersion and deduplicate.

**API overload:** stop excessive scans, reduce concurrency/QPS and check control-plane latency.

**Docker daemon incident:** check authorized socket and daemon health; never expose daemon TCP endpoint without proper TLS and access controls.

## 11. Lab and assessment

[Chapter 086 lab](labs/086-kubernetes-container-automation-sre-devops-dbre-lab.md) provides actual source files, deterministic fake clients, offline tests, optional live read-only adapters, incident simulations, runbooks and a 100-point assessment. Tests and live integration are not assumed executed merely because files were published.

**Next proposed:** Chapter 087 — Python Infrastructure Monitoring, Metrics and Alert Automation.
