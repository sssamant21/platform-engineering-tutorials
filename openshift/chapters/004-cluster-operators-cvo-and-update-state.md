# Chapter 004 — Cluster Operators, CVO and Update State

**Audience:** OpenShift platform administrators, SREs and DBREs  
**Duration:** 60 minutes (15 concepts, 30 read-only lab, 15 incident triage)  
**Reference baseline:** Red Hat OCP 4.22. Validate against the actual server release before operational changes.  
**Status:** Documentation draft; no runtime validation or independent review.

## Learning outcomes

1. Explain how the Cluster Version Operator (CVO) reconciles the cluster release payload and collects Cluster Operator status.
2. Distinguish `ClusterVersion`, `ClusterOperator`, and OLM-installed add-on Operators.
3. Interpret `Available`, `Progressing`, `Degraded`, `Upgradeable`, and `Failing` in context.
4. Perform a safe read-only health investigation and document escalation evidence.
5. Identify why update initiation, force updates and manual spec patches are outside this lab.

For Kubernetes controllers and reconciliation basics, see [Kubernetes Chapter 003](../../kubernetes/chapters/003-kubernetes-architecture-and-components.md). For node and MachineConfigPool relationships, see [Chapter 003](003-ocp-control-plane-rhcos-crio-and-nodes.md).

## 1. OpenShift lifecycle model

The CVO monitors the singleton `ClusterVersion` object, reconciles the desired release and manages OpenShift platform components delivered with the release payload. A `ClusterOperator` object reports conditions for a platform capability such as `authentication`, `ingress`, `network`, `etcd`, or `machine-config`. The CVO aggregates health and update progress.

**Do not confuse these with OLM add-on Operators:** OLM-managed Operators generally use Subscriptions, InstallPlans and ClusterServiceVersions (CSVs). Default platform Cluster Operators are CVO-managed and do not have OLM Subscriptions. See Chapter 011 for OLM administration.

| Resource | What it describes | Read-only inspection |
| --- | --- | --- |
| `clusterversion.config.openshift.io/version` | Desired/current release, update channel, history and conditions | `oc describe clusterversion version` |
| `clusteroperators.config.openshift.io` | Availability, progression and degradation of platform components | `oc get clusteroperators` |
| `machineconfigpools.machineconfiguration.openshift.io` | Node configuration rollout and convergence | `oc get machineconfigpools` |

### Condition semantics

| Condition | Interpretation | Important nuance |
| --- | --- | --- |
| ClusterOperator `Available=True` | Operator's managed capability is available | Does not prove every application is healthy |
| ClusterOperator `Progressing=True` | Component moving toward a new state | May be normal during an approved update |
| ClusterOperator `Degraded=True` | Persistent deviation from required state | Investigate; not proof of immediate user downtime |
| ClusterOperator `Upgradeable=False` | An update-related safety concern | Read exact reason/message; impacts update eligibility |
| ClusterVersion `Available=True` | Current release available | Pair with `Progressing` and `Failing` |
| ClusterVersion `Failing=True` | Cannot reach desired state | Escalate urgently with impact and condition details |
| ClusterVersion `Invalid=True` | Invalid desired state | Do not manually patch the object as a shortcut |

**Steady-state baseline:** Typically ClusterVersion `Available=True`, `Progressing=False`, `Failing=False`; Cluster Operators `Available=True`, `Progressing=False`, `Degraded=False`. During approved updates, transient progression is expected. An Operator can be degraded but still available, so correlate with user impact and condition messages.

## 2. Safe preflight

All `oc` operations below are read-only and require the corresponding RBAC grants. Use the approved cluster inventory to confirm the endpoint.

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc auth can-i get clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i get clusteroperators.config.openshift.io
```

A `no` answer is a permission boundary, not an instruction to elevate your role. Do not capture kubeconfig contents or tokens.

## 3. Inspect the cluster release

```bash
oc get clusterversion
oc describe clusterversion version
oc get clusterversion version -o jsonpath='{.spec.channel}{"\n"}'
oc get clusterversion version -o jsonpath='{range .status.conditions[*]}{.type}{": "}{.status}{" | "}{.reason}{" | "}{.message}{"\n"}{end}'
```

The JSONPath examples use single quotes and work in common Bash and PowerShell sessions. Output may contain sensitive environment details; sanitize before sharing. `oc describe` includes update history and condition messages; do not assume that an available update is automatically approved or safe for this cluster.

**Example only — not observed output:**

```text
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.x.y     True        False         2d      Cluster version is 4.x.y
```

The `4.x.y` placeholder is illustrative, not a validated real version.

## 4. Inspect Cluster Operators

```bash
oc get clusteroperators
oc get clusteroperator authentication ingress network etcd
oc describe clusteroperator <operator-name>
```

Only inspect names that actually exist. Check the condition's `Reason`, `Message`, `LastTransitionTime`, reported version and related objects. If the operator is `Degraded`, determine whether it is also `Available`, whether an update is underway, and which users or services are affected.

Optional, if authorized and an Operator's namespace is known:

```bash
oc get pods -n <operator-namespace>
oc get events -n <operator-namespace> --sort-by=.lastTimestamp
```

Avoid assuming that the Operator's namespace name matches its ClusterOperator name. Use `oc describe clusteroperator` and the official component documentation to locate related namespaces. Logs may contain secrets or user data; do not gather indiscriminately.

## 5. Check node configuration convergence

```bash
oc get machineconfigpools
oc get nodes -o wide
```

During upgrades, CVO status and MachineConfigPool state must be considered together. A `Progressing=True` cluster with an updating pool can be normal. A stuck pool, unexpected node `NotReady`, or a persistent Operator `Degraded` condition requires diagnosis, not an immediate reboot or force update.

## 6. Incident scenario: ingress Degraded, cluster Available

A hypothetical alert reports `clusteroperator/ingress` with `Degraded=True` while ClusterVersion remains `Available=True`.

1. Verify the current context, release and change window.
2. Capture `oc get clusteroperators` and `oc describe clusteroperator ingress`.
3. Inspect the exact condition message and transition time, then check related resources only with appropriate permissions.
4. Correlate ingress/router pod readiness and externally observed route availability; a degraded condition alone does not establish outage scope.
5. Document business impact, cluster version, recent changes, evidence and escalation owner.
6. Do not patch the ClusterOperator, restart router pods, or change the update channel without an approved recovery procedure.

Use [the Cluster Operator triage runbook](../runbooks/clusteroperator-cvo-degraded-triage.md) and [Lab 004](../labs/004-clusteroperator-cvo-read-only-audit.md).

## 7. Production change boundary

**No update or configuration mutation is performed here.** Updating the cluster, changing `ClusterVersion.spec`, bypassing `Upgradeable=False`, modifying release channels, deleting Operator resources or restarting platform pods requires separate supported procedures and change approval. Before any such change, record compatibility, upgrade path, control-plane health, etcd recovery readiness, storage and stateful-workload risks, rollback/forward-recovery strategy and validation owners. In-place OpenShift downgrades are not a general rollback method.

## Acceptance

A learner must explain CVO vs OLM, classify each relevant condition, collect sanitized version/Operator evidence, identify a non-mutating next step, and state when to escalate. This chapter is **drafted only** until a permitted cluster lab and independent review are completed.

## Official Red Hat references

- [Understanding OpenShift updates — 4.22](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/updating_clusters/understanding-openshift-updates-1)
- [Cluster version and status validation — 4.22](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/validation_and_troubleshooting/validating-an-installation)
- [Troubleshooting Operator issues — 4.22](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/pdf/support/getting-support)
