# Runbook — OpenShift Project Quota and LimitRange Admission Triage

**Severity:** Based on workload impact · **Scope:** OCP 4.x · **Default:** Read-only · **Status:** Draft, untested

## Trigger

Deployment or pod creation fails with `exceeded quota`, `forbidden`, or a LimitRange min/max validation message. A project may be blocked even while cluster nodes have spare resources.

## 1. Confirm identity and impact

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get clusterversion
oc -n <project-name> get deployments,pods
oc -n <project-name> get events --sort-by=.lastTimestamp
```

Confirm affected applications, start time, number of failed admissions, production severity, recent policy changes, and project owner. Avoid collecting application logs unless authorized.

## 2. Check admission controls

```bash
oc -n <project-name> get resourcequota
oc -n <project-name> describe resourcequota
oc -n <project-name> get limitrange
oc -n <project-name> describe limitrange
oc -n <project-name> describe deployment <deployment-name>
oc auth can-i get resourcequotas -n <project-name>
```

Compare the workload's requested resources with namespace quota **Used/Hard** and per-container LimitRange constraints. If a command is forbidden, ask the authorized project/platform owner; do not bypass RBAC. Check whether other controllers are creating pods and consuming quota.

## 3. Decision tree

- **Quota exhausted:** identify which resource is at Hard; review current demand, stale workloads and business priority. Ask application owner whether requests are justified and platform owner whether capacity exists.
- **LimitRange rejected:** compare requested values and injected defaults with configured min/max; ask application owner to correct the workload manifest or request an approved policy change.
- **Missing requests/limits:** quota admission may require explicit resource values; align manifest with namespace policy.
- **No quota/LimitRange issue found:** inspect events for SCC, RBAC, image, storage or scheduling failures and route to the appropriate runbook.

## 4. Safe mitigation proposal (approval required)

Do not remove quotas or expand limits reflexively. Proposed changes must include scope, capacity impact, resource owner, risk to other tenants, approval, dry-run, planned execution window, validation and rollback. Prefer fixing incorrect application resource specifications before changing shared governance controls. No state-changing command is authorized by this runbook.

## 5. Validate and close

After an approved change, recheck events, quota Used/Hard, rollout status and app readiness; observe whether other tenant workloads were affected. Preserve sanitized incident evidence and policy diffs, never credentials or Secrets.

## Rollback caveat

Restoring an earlier ResourceQuota or LimitRange does not necessarily remove already admitted workloads; it can instead block future admissions. Recheck consumption and coordinate with application owners.

## References

- [OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Kubernetes ResourceQuota](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [Kubernetes LimitRange](https://kubernetes.io/docs/concepts/policy/limit-range/)
