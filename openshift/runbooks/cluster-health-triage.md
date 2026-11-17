# Runbook — OpenShift Cluster Health Triage

**Purpose:** Initial read-only assessment when cluster health warnings or application availability incidents occur.

**Applicability:** OCP 4.x; adjust for topology and product version.  
**Risk:** Read-only inspection. Do not perform recovery changes based on this checklist alone.

## Trigger

Alerts such as Cluster Operator Degraded, worker NotReady, stuck MachineConfigPool, failed workloads, or routing/connectivity problems.

## Triage

1. Validate incident severity and business impact; identify owner and escalation bridge.
2. Verify intended cluster and credential scope:
   ```bash
   oc whoami
   oc config current-context
   oc whoami --show-server
   ```
3. Capture high-level platform signals:
   ```bash
   oc get clusterversion
   oc get clusteroperators
   oc get nodes -o wide
   oc get machineconfigpools
   ```
4. Find workload impact:
   ```bash
   oc get pods -A
   oc get events -A --sort-by=.lastTimestamp
   ```
5. Inspect the affected object:
   ```bash
   oc describe node <node-name>
   oc describe clusteroperator <operator-name>
   ```
6. Assess whether a recent deployment, upgrade, maintenance change or resource pressure explains the condition.
7. Escalate with sanitized evidence: environment, start time, customer impact, condition transitions, symptoms, suspected change, proposed next step and accountable owner.

## Production safeguards

- No `oc delete`, `oc adm drain`, reboots, cluster updates, or configuration edits within this triage runbook.
- Before any node operation, validate quorum, disruption budgets, workload replicas, StatefulSets, PVCs and storage backend resilience.
- Protect tokens, kubeconfig content and sensitive workload logs.
- Record mitigations separately with change authorization and rollback criteria.

## Recovery / rollback

None; this document does not change cluster state. Follow the appropriate separately approved recovery runbook if diagnostics justify intervention.

## Source

[Red Hat OpenShift 4.22 troubleshooting guide](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/troubleshooting)
