# Chapter 037 — Grafana Alloy Log Pipelines, Parsing, Labeling and Kubernetes Collection

**Part 08 — Centralized Logging with Loki**

## Objectives

Design reliable log collection for EKS, AKS and GKE; understand Grafana Alloy discovery, relabeling, file sources, processing and Loki writes; use stable labels; validate LogQL; and establish production SRE/DBRE runbooks.

## Architecture

```text
Kubernetes container logs -> Alloy discovery -> source -> process -> Loki
                                               |                 |
                                          bounded labels    LogQL / Grafana
```

Loki indexes streams by label set rather than indexing every log word. Prefer stable dimensions such as cluster, namespace, service and environment. Keep request IDs, trace IDs, user identifiers and SQL text out of indexed stream labels.

## Collection design

| Stage | Function | Review |
|---|---|---|
| Kubernetes discovery | identify eligible workloads | namespace scope and RBAC |
| Relabeling | attach service/cluster metadata | label cardinality |
| File source | read log files | rotation and offsets |
| Processing | parse JSON, filter noise | privacy and loss prevention |
| Loki write | deliver log streams | retries, tenant access, TLS |

DaemonSet-based node file collection and Kubernetes API log tailing have different permissions, reliability and load characteristics. Select the appropriate supported Alloy components and chart version for the cluster. Test node rotation, log file permissions and backpressure in staging.

## Local Alloy example

```hcl
local.file_match "demo" {
  path_targets = [{"__path__" = "/var/log/demo/*.log", "service" = "orders-api", "environment" = "staging"}]
}
loki.source.file "demo" {
  targets = local.file_match.demo.targets
  forward_to = [loki.process.demo.receiver]
}
loki.process "demo" {
  stage.json {
    expressions = {level = "level", message = "message"}
  }
  forward_to = [loki.write.local.receiver]
}
loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

This is a disposable local demonstration, not a complete Kubernetes deployment. The example does not implement redaction. Use only synthetic non-sensitive log lines and never expose an unauthenticated Loki endpoint publicly.

## LogQL verification

```logql
{service="orders-api"}
{service="orders-api"} | json | level="error"
sum by (service) (count_over_time({service="orders-api"}[5m]))
```

Check source timestamps, selected time range and collector health if logs are missing.

## Production controls

Require namespace-scoped discovery where feasible, reviewed service-account permissions, least-privilege network access, secret and personal-data redaction before ingestion, tenant isolation, ingestion budgets, retention, stream cardinality monitoring and documented rollback. Offline approval metadata cannot prove that redaction or RBAC actually works.

## Twenty-four hands-on exercises

1. Map the Kubernetes log path.
2. Compare DaemonSet and API collection.
3. Review namespace RBAC.
4. Review node file mounts.
5. Identify log rotation behavior.
6. Build a local file pipeline.
7. Configure Alloy source.
8. Configure Loki writer.
9. Parse JSON logs.
10. Inspect message and level.
11. Keep trace IDs as fields.
12. Review stream labels.
13. Review label churn.
14. Query LogQL.
15. Filter errors.
16. Calculate log counts.
17. Inspect ingestion errors.
18. Review tenant isolation.
19. Estimate ingestion volume.
20. Estimate stream count.
21. Test collector restart.
22. Test Loki outage.
23. Review redaction controls.
24. Perform rollback tabletop.

## Twenty-four production troubleshooting scenarios

1. **RBAC denied:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
2. **Namespace filter wrong:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
3. **Log file unreadable:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
4. **Node rotation:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
5. **Lost file offset:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
6. **Duplicate logs:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
7. **Malformed JSON:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
8. **Invalid timestamps:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
9. **Unexpected debug volume:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
10. **Loki unavailable:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
11. **Loki rate limiting:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
12. **Tenant mismatch:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
13. **TLS mismatch:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
14. **Service discovery missing:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
15. **Pod UID label explosion:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
16. **Request ID label explosion:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
17. **High ingestion cost:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
18. **Missing application logs:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
19. **Unexpected log drop:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
20. **Collector CPU pressure:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
21. **Collector OOM:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
22. **Loki disk pressure:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
23. **Sensitive data incident:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.
24. **Rollback regression:** Check collection permissions, source state, processing stages, labels, write errors and recovery evidence.

## Eight runbooks

1. **Missing logs:** verify collector health, file paths, timestamps and LogQL range.
2. **RBAC failure:** review service account, discovery scope and authorized permissions.
3. **Node rotation:** validate log source recreation and file offset behavior.
4. **Parsing regression:** replay synthetic JSON samples and inspect parsed fields.
5. **Cardinality incident:** remove volatile labels and restore stream budget.
6. **Privacy incident:** stop unsafe ingestion, restrict access and follow approved data-handling process.
7. **Write failures:** inspect tenant configuration, network path, retry and Loki limits.
8. **Rollback:** restore reviewed Alloy configuration and confirm successful ingestion and query results.

## SRE/DBRE incident game day

During an EKS node rotation, logs disappear from a PostgreSQL-backed application. A change also introduces a per-request stream label, multiplying Loki streams. Identify source failures and stream growth independently; restore safe labels, validate ingestion and document the recovery timeline. Run only in approved staging.

## 100-point assessment

| Domain | Points |
|---|---:|
| Kubernetes collection architecture | 20 |
| Alloy pipelines and LogQL | 20 |
| Security, privacy and cardinality | 20 |
| Hands-on validation | 20 |
| Incident simulation and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85. Production acceptance additionally requires real collection, redaction, RBAC, alerting and recovery verification.

**Companion:** [Chapter 037 hands-on lab](labs/037-grafana-alloy-log-pipelines-parsing-labeling-kubernetes-collection-lab.md).

**Next:** Chapter 038 — Loki LogQL Advanced Queries, Log-Based Metrics and Troubleshooting.
