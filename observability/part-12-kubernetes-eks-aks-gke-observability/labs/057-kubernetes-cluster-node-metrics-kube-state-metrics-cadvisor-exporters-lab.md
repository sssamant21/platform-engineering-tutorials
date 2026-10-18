# Chapter 057 — Kubernetes Cluster and Node Metrics Lab

**Part 12 — EKS, AKS and GKE Observability**

## Offline acceptance

Copy `healthy.json`, `metrics_gate.py` and `test_metrics_gate.py` from [Chapter 057](../057-kubernetes-cluster-node-metrics-kube-state-metrics-cadvisor-exporters.md).

```bash
cd chapter057
python3 metrics_gate.py healthy.json
python3 -m unittest -v test_metrics_gate.py
```

Expected PASS and 28 authored tests.

## Approved staging lab

1. Record context, cluster, cloud and owner.
2. Inventory node-exporter DaemonSet and kube-state-metrics Deployment.
3. Check kubelet/cAdvisor endpoint access without changing permissions.
4. Verify Prometheus Operator CRDs and target discovery, if installed.
5. Run the chapter PromQL examples and check labels.
6. Compare CPU throttling with node CPU usage and workload latency.
7. Review pod restarts, replica availability and HPA inputs.
8. Simulate one exporter/scrape outage in staging.
9. Verify alert routing and recover target health.
10. Document rollback, reviewer and timestamps.

## Twelve negative drills

1. Missing node-exporter review.
2. Missing kube-state-metrics review.
3. Kubelet access unreviewed.
4. RBAC review absent.
5. TLS review absent.
6. Network policy review absent.
7. Scrape target count zero.
8. Healthy targets exceed total.
9. Scrape success below budget.
10. CPU throttling over budget.
11. Recording rules unreviewed.
12. Rollback untested.

## Evidence worksheet

```text
UTC / cluster / cloud / operator:
Prometheus targets and scrape success:
Node CPU/memory/disk:
Container throttling and pod restarts:
KSM replica/HPA state:
RBAC/TLS/NetworkPolicy:
Alert route and runbook:
Recovery/rollback:
Offline gate and 28 tests:
```

Offline checks do not prove live exporter or cluster readiness.
