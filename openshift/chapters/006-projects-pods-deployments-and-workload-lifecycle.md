# Chapter 006 — OpenShift Projects, Pods, Deployments and Workload Lifecycle

**Track:** Platform Engineering / OpenShift Administration | **Duration:** 60 minutes | **Reference:** Red Hat OCP 4.22 | **Status:** Draft; runtime not tested.

## Objectives and prerequisites

Understand the relationship between OpenShift Projects and Kubernetes namespaces, Deployment → ReplicaSet → Pod reconciliation, readiness, events and rollouts. Learn the distinction between a read-only production inspection and a controlled disposable lab deployment.

Requires a compatible `oc` CLI, an authorized account, and a designated *non-production* project where your account may create Deployments, Services and pods. An administrator must provision this project in advance; do not assume `oc new-project` is permitted. Never reuse an application namespace or privileged service account. Review [Kubernetes workload fundamentals](../../kubernetes/chapters/018-deployments-replicasets-and-rollouts.md) rather than repeating generic Kubernetes architecture.

## 1. OpenShift workload model

- **Project:** OpenShift-facing abstraction over a namespace, with project metadata and access policies.
- **Deployment:** Desired state, replica count, container template and rollout strategy.
- **ReplicaSet:** Maintains the desired number of pods for a Deployment revision.
- **Pod:** Scheduled unit containing one or more containers, with lifecycle and readiness conditions.
- **Service:** Stable virtual network endpoint for a selected set of pods.
- **Route:** OpenShift ingress resource; **not needed** for this introductory internal-only lab.
- **Security Context Constraints (SCC):** OpenShift admission constraints. Avoid fixed root users, privileged mode, hostPath and elevated capabilities. Use an image compatible with arbitrary UIDs and restricted SCC.

A pod in `Running` is not necessarily `Ready`; check readiness and application-level health. `Completed` may be normal for Jobs.

## 2. Identity, namespace and authorization preflight (read-only)

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc project
oc get projects
oc get deploy,rs,pods,svc -n <authorized-project>
oc auth can-i create deployments.apps -n <authorized-project>
oc auth can-i create services -n <authorized-project>
oc auth can-i delete deployments.apps -n <authorized-project>
```

Expected: verified cluster/context and project; `yes` only for explicitly granted permissions. If `no`, do not elevate privileges or run the write lab. PowerShell users can run the same `oc` commands; angle-bracket placeholders must be replaced, not copied literally.

## 3. Production-safe workload inventory

```bash
oc -n <authorized-project> get deployments -o wide
oc -n <authorized-project> get replicasets
oc -n <authorized-project> get pods -o wide
oc -n <authorized-project> get events --sort-by=.lastTimestamp
oc -n <authorized-project> describe deployment <deployment-name>
oc -n <authorized-project> rollout status deployment/<deployment-name> --timeout=30s
```

The final command waits for a rollout but does not modify it. A timeout indicates the rollout was not observed as complete, not necessarily that the application is unavailable. For diagnostic logs, use `oc logs deployment/<deployment-name> --tail=100` **only if application log access is approved**; logs can contain sensitive data.

## 4. Non-production exercise: minimal Deployment

Complete [Lab 006](../labs/006-disposable-deployment-lifecycle.md) in a disposable, preapproved project. Use an image approved by your organization, pinned to an immutable digest, compatible with restricted SCC and non-root execution. Avoid `:latest`. Set CPU/memory requests and limits and a readiness probe validated for the chosen image. The lab provides a manifest template requiring these choices before deployment.

The authorized test workflow is: verify context → validate permissions → review manifest → `oc apply --dry-run=server` → `oc apply` → inspect Deployment/ReplicaSet/Pods → check rollout and events → remove only the specifically labeled lab resources → verify cleanup.

## 5. Troubleshooting

| Symptom | Read-only diagnosis | Likely area |
| --- | --- | --- |
| Pending | `oc describe pod <pod>` | Quota, scheduling, PVC or resource requests |
| ImagePullBackOff | `oc describe pod <pod>` | Image reference, registry credentials or egress |
| CrashLoopBackOff | `oc describe pod <pod>` and approved logs | Entrypoint, app configuration, probes |
| Running but not Ready | `oc get pod <pod> -o yaml` (review sensitivity) | Readiness probe or app dependency |
| Replica count mismatch | `oc describe deployment <name>` | Admission, scheduling, rollout or quota |
| Forbidden / SCC denial | Inspect events and `oc auth can-i` | RBAC, SCC or service-account restrictions |

Never disable SCC or grant cluster-admin merely to make a training pod start. See [workload triage runbook](../runbooks/workload-deployment-triage.md).

## 6. Production change gates

Before a production rollout: confirm owner, change approval, image provenance and digest, resource requests, security constraints, dependency health, replicas, PodDisruptionBudget, service selectors, user-impact window, monitoring, backout strategy and who can authorize rollback. `oc rollout undo` is a state-changing action and may not reverse schema/data migrations; it is not an automatic safe rollback.

## Acceptance and evidence

Record sanitized OCP version, target project, RBAC checks, manifest review, admission results, Deployment/ReplicaSet/Pod observations, rollout status, failure scenario and cleanup evidence. **Documentation drafted only; no live cluster execution, review or production approval.**

## Official references

- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Applications and deployments](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/building_applications/deployments)
- [Working with projects](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/building_applications/projects)
