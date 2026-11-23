# Chapter 007 — OpenShift Projects, ResourceQuotas, LimitRanges and Multitenancy

**Track:** Platform Engineering / OCP Administration · **Duration:** 60 minutes · **Baseline:** Red Hat OCP 4.22 · **Status:** Draft; no live cluster validation.

## Objectives and prerequisites

Understand project governance, the difference between ResourceQuota and LimitRange, how admission affects workload creation, and why project membership does not by itself establish tenant isolation. Requires a compatible `oc` CLI, an authorized read-only cluster/project account, and optionally a separately approved disposable non-production project. Confirm exact cluster version, target, and RBAC before every exercise.

Review the [existing Kubernetes namespace chapter](../../kubernetes/chapters/012-namespaces-labels-and-annotations.md) for generic namespace concepts; this chapter concentrates on OpenShift project operations and governance.

## 1. OpenShift project governance

An OpenShift **Project** is a Kubernetes namespace exposed with OpenShift project metadata and management workflows. Project requests and templates can standardize annotations, labels and policy defaults. Not all users can create projects; organizations may disable self-service project creation.

A production project should have a named application owner, cost center, environment classification, support contact, data classification, SLO, access review schedule, approved image sources, and retention/backup responsibility. Project labels are useful for inventory, but labels alone do not enforce network or data security.

| Control | What it limits | What it does **not** guarantee |
| --- | --- | --- |
| `ResourceQuota` | Aggregate namespace consumption/counts and selected quota-scoped resources | Fair scheduling, CPU throttling or security isolation |
| `LimitRange` | Per-container/pod/PVC min/max and defaults, depending on configured type | Aggregate namespace consumption |
| RBAC | Who may perform API actions | Network separation between tenants |
| SCC | Allowed pod security context at admission | Complete runtime/data isolation |
| NetworkPolicy | Permitted network flows for selected pods | Access to the Kubernetes API or storage data |
| Storage/RBAC policy | Access and provisioning controls | Application-level authorization |

A `LimitRange` default may be injected into new pods at admission; existing pods are not retroactively changed. Quota counts depend on API resource type, and resource-quota usage is admission-controlled rather than a historical capacity forecast.

## 2. Safe read-only project inventory

Replace all placeholders; do not type literal angle brackets into PowerShell or Bash.

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get clusterversion
oc get projects
oc get namespace <project-name> --show-labels
oc describe namespace <project-name>
oc get resourcequota -n <project-name>
oc describe resourcequota -n <project-name>
oc get limitrange -n <project-name>
oc describe limitrange -n <project-name>
oc get networkpolicy -n <project-name>
oc auth can-i get resourcequotas -n <project-name>
oc auth can-i get limitranges -n <project-name>
```

A `Forbidden` response means the identity lacks permission; it does not prove the resource is absent. An empty resource list means no objects of that type were returned for the accessible project. Do not use `oc get secrets` or `oc get ... -o yaml` on sensitive configuration as routine evidence collection.

## 3. Interpret quotas and limit ranges

Example *illustrative* ResourceQuota for a disposable project (not an instruction to apply in production):

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: training-compute-budget
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    pods: "10"
```

Example *illustrative* LimitRange:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: training-container-bounds
spec:
  limits:
  - type: Container
    min:
      cpu: 50m
      memory: 64Mi
    max:
      cpu: "1"
      memory: 1Gi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    default:
      cpu: 500m
      memory: 512Mi
```

**Admission interaction:** A new pod with two containers can receive per-container defaults. The resulting summed requests and limits count toward project quota. A request exceeding per-container max may be rejected by LimitRange; a pod whose total would exceed remaining quota may be rejected by ResourceQuota. Quotas do not stop existing pods immediately when usage rises above a changed limit; new admissions are affected. For an SCC-constrained cluster, ensure any test image and pod configuration are compatible with the default restricted SCC.

Use `oc describe resourcequota -n <project-name>` to compare **Used** versus **Hard**; investigate unexpected discrepancies using current workload inventory, not assumptions about capacity.

## 4. Non-production lab and governance exercise

Follow [Lab 007](../labs/007-project-quota-and-limitrange-audit.md). The core exercise is read-only. Optional mutation is only allowed after project owner authorization in an isolated training project, using `oc apply --dry-run=server` first and explicit approval for `oc apply`. Never change quota or LimitRange in a production project merely to unblock a workload.

**Example RBAC prechecks:**

```bash
oc auth can-i create resourcequotas -n <training-project>
oc auth can-i create limitranges -n <training-project>
oc auth can-i delete resourcequotas -n <training-project>
oc auth can-i delete limitranges -n <training-project>
```

Permission checks do not replace change approval.

## 5. Common incidents

| Symptom | Diagnosis | Escalation |
| --- | --- | --- |
| `exceeded quota` admission failure | Inspect namespace quota Used/Hard and pod resource requirements | Project owner + platform capacity owner |
| `maximum cpu/memory usage per Container` | Compare pod requests/limits with LimitRange min/max | App owner + platform policy owner |
| New pod rejected despite free node capacity | Admission quota may be exhausted independent of node headroom | Platform team |
| Cross-tenant access concern | Inspect authorized RBAC, network policy and storage boundaries | Security/platform incident response |
| Project creation denied | Inspect self-service project policy and access | Platform provisioning owner |

Do not grant `cluster-admin`, disable SCC, or remove tenant quotas as a quick workaround. For triage use [Project Quota and LimitRange Runbook](../runbooks/project-quota-limitrange-triage.md).

## 6. Change approval and rollback

For any policy change: identify affected applications, quota baseline, expected pending admissions, peak demand, resource capacity, tenant boundaries, approvers and maintenance window. Review proposed manifests and perform a server-side dry run in the intended non-production namespace. Capture the previous manifest **without sensitive fields**, and have a documented backout. Restoring previous quotas may not evict already admitted pods and may prevent future workloads from starting; verify post-change admission and utilization. Production rollback requires explicit authorization.

## 7. Acceptance evidence

Record sanitized cluster ID, OCP version, project, read-only command results, quota Used/Hard, LimitRange constraints, identified governance gaps, incident scenarios and accountable owners. Note any permission-denied results. **No live runtime validation or independent production approval has occurred.**

## Official references

- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Kubernetes Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [Kubernetes Limit Ranges](https://kubernetes.io/docs/concepts/policy/limit-range/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
