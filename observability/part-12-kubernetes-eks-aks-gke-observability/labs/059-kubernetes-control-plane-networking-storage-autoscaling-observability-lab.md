# Chapter 059 — Kubernetes Control Plane, Networking, Storage and Autoscaling Lab

**Part 12 — EKS, AKS and GKE Observability**

## Offline acceptance

Copy `healthy.json`, `platform_signals_gate.py` and `test_platform_signals_gate.py` from [Chapter 059](../059-kubernetes-control-plane-networking-storage-autoscaling-observability.md).

```bash
cd chapter059
python3 platform_signals_gate.py healthy.json
python3 -m unittest -v test_platform_signals_gate.py
```

Expected PASS and 30 authored tests.

## Approved staging integration

1. Record context, cluster, cloud and operator.
2. Check API server latency/errors via available Prometheus or provider metrics.
3. Inspect scheduling failures and controller events.
4. Verify CoreDNS, CNI and ingress health.
5. Compare service endpoints with load balancer health.
6. Inspect CSI/PVC events and cloud disk performance.
7. Review HPA/VPA and node autoscaler behavior.
8. Simulate a bounded DNS or storage fault in staging.
9. Confirm application and DBRE SLI recovery.
10. Capture reviewer sign-off and rollback.

## Twelve negative drills

1. Unsupported cloud.
2. API server review absent.
3. Scheduler review absent.
4. DNS review absent.
5. CNI review absent.
6. CSI review absent.
7. PV review absent.
8. HPA review absent.
9. Cluster autoscaler review absent.
10. API latency over threshold.
11. DNS success below threshold.
12. Storage utilization over threshold.

## Evidence worksheet

```text
UTC / cloud / cluster / operator:
API server latency/errors:
Scheduler/controller events:
DNS/CNI/ingress and LB:
CSI/PVC/cloud disk:
HPA/VPA/autoscaler:
Application/database SLI impact:
Failure drill and rollback:
Offline gate / 30 tests:
```

Offline checks cannot prove real platform observability.
