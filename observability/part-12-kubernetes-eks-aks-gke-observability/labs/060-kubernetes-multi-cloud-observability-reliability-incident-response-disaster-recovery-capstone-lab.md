# Chapter 060 — Kubernetes Multi-Cloud Observability and DR Capstone Lab

**Part 12 final capstone — EKS, AKS and GKE Observability**

## Offline acceptance

Copy `healthy.json`, `multicloud_capstone_gate.py` and `test_multicloud_capstone_gate.py` from [Chapter 060](../060-kubernetes-multi-cloud-observability-reliability-incident-response-disaster-recovery-capstone.md).

```bash
cd chapter060
python3 multicloud_capstone_gate.py healthy.json
python3 -m unittest -v test_multicloud_capstone_gate.py
```

Expected PASS and 30 authored tests.

## Approved staging game day

1. Record EKS/AKS/GKE contexts, owners and cloud monitoring differences.
2. Confirm node, workload, control-plane, network, CSI and autoscaler telemetry.
3. Retrieve known synthetic logs and traces.
4. Verify independent RED SLOs and alert routing.
5. Simulate bounded DNS failure in staging.
6. Simulate storage/CSI latency and node autoscaler stall.
7. Simulate telemetry exporter outage.
8. Restore monitored service and collection pipelines.
9. Conduct approved backup/restore and failover rehearsal.
10. Measure RPO/RTO, document rollback and score the capstone.

## Twelve negative drills

1. EKS visibility unreviewed.
2. AKS visibility unreviewed.
3. GKE visibility unreviewed.
4. Control-plane review missing.
5. DNS review missing.
6. Storage review missing.
7. Autoscaling review missing.
8. Logs or traces unreviewed.
9. Tenant isolation unverified.
10. Restore untested.
11. RPO or RTO threshold missed.
12. Rollback untested.

## Evidence worksheet

```text
UTC / operator / change ID:
Multi-cloud telemetry coverage:
User-impact RED metrics:
DNS/CNI/CSI/autoscaler:
Log/trace known IDs:
Security / privacy:
Backup/restore / RPO-RTO:
Recovery / rollback:
Offline gate / 30 tests:
Final score / reviewer:
```

Offline acceptance is not a substitute for live DR evidence.
