# Lab 004 — Read-only CVO and Cluster Operator Audit

**Duration:** 30 minutes  
**Environment:** Authorized OCP 4.x cluster, compatible `oc` CLI, permission to read ClusterVersion, ClusterOperators and (optionally) MachineConfigPools.  
**Risk:** Read-only API inspection; never use an update, patch, delete or restart command in this lab.  
**Status:** Not executed.

## Preflight

Confirm that the target cluster is correct independently of kubeconfig and that your session is authorized:

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc auth can-i get clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
```

Record a permission-denied result rather than requesting emergency privilege escalation.

## Exercise

1. Run `oc get clusterversion` and `oc describe clusterversion version`. Record the current version, channel, `Available`, `Progressing`, `Failing`, `Upgradeable` (if reported), and relevant messages.
2. Run `oc get clusteroperators`. Count `Available=False`, `Progressing=True`, and `Degraded=True` Operators; note that counts may overlap.
3. Choose one Operator to inspect: `oc describe clusteroperator <operator-name>`. Record its condition reason/message and last transition time.
4. Run `oc get machineconfigpools` if permitted. Determine whether configuration rollout could explain progress.
5. Classify current state as normal steady state, approved update, anomaly requiring investigation, or insufficient evidence.
6. For a hypothetical `ingress Degraded=True` alert, write a read-only investigation and escalation plan. Do **not** induce a failure.

## Expected interpretations

- Steady state typically has `ClusterVersion Available=True`, `Progressing=False`, `Failing=False`, with Cluster Operators `Available=True`, `Progressing=False`, `Degraded=False`.
- An approved update can have `Progressing=True` and MachineConfigPools updating.
- `Degraded=True` needs investigation, but is not alone proof of application outage.
- `Forbidden` means RBAC does not allow inspection; `NotFound` means the resource or name may be absent or context incorrect. Do not bypass access controls.

## Evidence worksheet

| Field | Recorded result |
| --- | --- |
| UTC time | Not executed |
| Sanitized cluster identifier and endpoint | Not executed |
| CLI and server release | Not executed |
| Current context and authorized user | Not executed |
| ClusterVersion conditions | Not executed |
| Operator condition counts | Not executed |
| One Operator's reason/message | Not executed |
| MachineConfigPool status (if permitted) | Not executed |
| Assessment and escalation owner | Not executed |
| Reviewer and approval | Pending |

Store sanitized evidence in an approved internal location; do not commit tokens, raw kubeconfigs or sensitive logs.

## Pass criteria

- The target cluster and authorization were verified.
- Condition assessment distinguishes progress from persistent degradation.
- The learner names a safe next diagnostic step and escalation owner.
- No cluster mutation occurred.
- Actual evidence is recorded and independently reviewed.

**Current result:** Not run; pass criteria not yet met.

[Return to Chapter 004](../chapters/004-cluster-operators-cvo-and-update-state.md).
