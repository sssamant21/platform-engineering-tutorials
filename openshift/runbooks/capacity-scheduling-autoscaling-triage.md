# Runbook — OCP Capacity, Scheduling and Autoscaling Triage

**Status:** Draft; not runtime-validated or approved for production remediation. **Applies to:** OCP 4.22 subject to deployment-specific review.

## Trigger and severity
Pending pods, `FailedScheduling`, node MemoryPressure/DiskPressure/PIDPressure, HPA unable to scale, or autoscaler capacity ceiling. Declare incident severity using application SLO and quorum impact, not just pod count.

## Read-only first response
1. Confirm `oc whoami`, `oc config current-context`, scope and RBAC. Avoid collecting credentials.
2. `oc get nodes -o wide`; `oc describe node <node>` for conditions, allocatable, requests and taints.
3. `oc get pods -n <project> -o wide`; `oc describe pod <pending-pod> -n <project>`; `oc get events -n <project> --sort-by=.metadata.creationTimestamp`.
4. `oc get resourcequota,limitrange,pdb -n <project>`; inspect selectors, affinity, PVC binding and topology for the affected workload.
5. If authorized, inspect `oc get hpa -n <project>`, `oc get clusterautoscalers.autoscaling.openshift.io`, `oc get machineautoscalers.autoscaling.openshift.io -A`. Check platform support before interpreting missing objects.
6. `oc adm top nodes` if metrics are available; correlate with monitoring trends rather than using a single sample.

## Decision tree
- **Insufficient cpu/memory:** compare *requested* resources to eligible-node allocatable and existing allocations; involve platform and application owners.
- **Taint/affinity/topology:** validate intended placement policy and fault-domain design; do not bypass it to force a pod to schedule.
- **PVC unbound or volume topology:** coordinate with storage/DBRE; see [storage triage](pvc-csi-storage-triage.md).
- **Quota exceeded:** confirm project policy and workload request; see [quota triage](project-quota-limitrange-triage.md).
- **Autoscaler inactive/maxed:** confirm support, cloud quota, pool min/max, permissions and provisioning errors. No blind scaling.
- **Node pressure:** correlate disk/memory/PID condition with events and telemetry; avoid deleting runtime files or restarting nodes.

## Ownership and safe change gate
Platform/SRE leads scheduler, node pools and Machine API; application owner validates requests/HPA; DBRE approves stateful placement and data-risk assessment; infrastructure validates cloud limits/cost. Before any mutation require ticket, explicit approvals, impact/maintenance window, baseline, known-good configuration, rollback feasibility, and abort criteria. For stateful services confirm replica quorum, anti-affinity, PDB, zone capacity, backups and restore plan. Escalate immediately on data unavailability or multi-zone loss.

**Rollback:** Revert approved configuration through normal change control only after verifying whether rescheduling, eviction, storage attachment or persistent data changed. Reverting autoscaler values does not automatically undo data-plane effects. Validate node readiness, Pending count, pod readiness, service SLO and storage/quorum health; attach sanitized evidence.

## Expected errors
`Forbidden`: RBAC issue; `Metrics API not available`: telemetry unavailable; `No resources found`: potentially no configured autoscaler; `FailedScheduling`: inspect full event and eligibility constraints. Never classify solely from an isolated message.

[Chapter 013](../chapters/013-capacity-resource-pressure-and-autoscaling.md) · [Lab 013](../labs/013-capacity-pressure-read-only-audit.md)
