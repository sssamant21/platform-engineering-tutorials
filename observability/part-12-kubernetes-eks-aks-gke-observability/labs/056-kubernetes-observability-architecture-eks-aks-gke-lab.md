# Chapter 056 — Kubernetes Observability Architecture for EKS, AKS and GKE Lab

**Part 12 — Kubernetes, EKS, AKS and GKE Observability.**

## Offline acceptance

Copy `healthy.json`, `kubernetes_observability_gate.py`, and `test_kubernetes_observability_gate.py` from [Chapter 056](../056-kubernetes-observability-architecture-eks-aks-gke.md).

```bash
cd chapter056
python3 kubernetes_observability_gate.py healthy.json
python3 -m unittest -v test_kubernetes_observability_gate.py
```

Expected PASS and 28 authored tests.

## Staging cluster integration

1. Select an approved EKS, AKS or GKE staging context.
2. Inventory nodes, namespaces, workloads and kube-state-metrics.
3. Check kubelet/cAdvisor and node-exporter collection.
4. Verify ServiceMonitor and PodMonitor discovery where installed.
5. Inspect Prometheus targets and scrape health.
6. Verify Grafana cluster dashboard.
7. Collect a synthetic pod log and trace.
8. Compare provider control-plane monitoring exposure.
9. Validate RBAC, network policy and sensitive-data filtering.
10. Simulate a scrape outage, recover and document evidence.

## Twelve negative drills

1. Unsupported cloud.
2. Missing owner.
3. kube-state-metrics review absent.
4. node-exporter review absent.
5. kubelet/cAdvisor review absent.
6. Collector review absent.
7. Prometheus scrape review absent.
8. Loki review absent.
9. Tracing review absent.
10. RBAC review absent.
11. Scrape success below threshold.
12. Telemetry delay above threshold.

## Evidence

```text
UTC / operator / cluster context:
EKS/AKS/GKE provider signals:
Prometheus targets / scrape success:
Node, pod and control-plane metrics:
Loki logs / OTel traces:
RBAC / network policy / PII:
Recovery / rollback:
Offline gate / 28 tests:
Reviewer / change ID:
```

Offline checks do not prove real cluster visibility.
