# Runbook — OpenShift Deployment and Pod Triage

**Scope:** OCP 4.x, namespace-scoped workloads. **Read-only investigation only.** Do not restart, scale, delete or roll back resources without an approved change.

## Trigger and ownership

Deployment unavailable, pod stuck Pending, repeated restarts, image pull failures, SCC admission denials or unexpected rollout behavior. Application team owns image/configuration and app-level diagnosis; platform/SRE owns cluster scheduling, networking and admission infrastructure; DBRE owns database dependency health when relevant. Escalate to the incident commander for cross-team impact.

## Step 1 — Confirm identity and scope

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc project
oc auth can-i get deployments.apps -n <namespace>
```

Never use `oc project` to change namespaces casually during incidents. Explicitly include `-n <namespace>` in subsequent commands.

## Step 2 — Inspect desired and actual state

```bash
oc -n <namespace> get deployment <name> -o wide
oc -n <namespace> describe deployment <name>
oc -n <namespace> get replicasets
oc -n <namespace> get pods -o wide
oc -n <namespace> get events --sort-by=.lastTimestamp
oc -n <namespace> rollout status deployment/<name> --timeout=30s
```

Check desired/available/updated replicas, latest revision, pod selectors, scheduling events, readiness and recent rollout. If the namespace contains sensitive workloads, restrict evidence sharing. Do not assume every pod in `Completed` is failed.

## Step 3 — Diagnose by symptom

| Symptom | Next safe inspection | Escalation |
| --- | --- | --- |
| Pending | `oc -n <namespace> describe pod <pod>` | Capacity, quota, node taints, PVC |
| ImagePullBackOff | Pod events; image ref and registry policy | Application owner / registry team |
| CrashLoopBackOff | Pod events; approved limited logs | Application owner; config/probe review |
| Running, not Ready | Pod readiness condition and app health | Application / dependency owner |
| SCC forbidden | Pod/ReplicaSet admission events | Security/platform team; never bypass SCC |
| Rollout stalled | Deployment conditions, ReplicaSet, events | Application and platform owners |

Logs may contain credentials or PHI. Obtain approval and redact before sharing; avoid indiscriminate `oc get ... -o yaml` of Secrets.

## Step 4 — Recovery decision gate

Before any mutation, document incident severity, application owner, approved change, blast radius, rollback criteria, database/stateful dependencies, PDBs, replica availability, image digest, configuration drift, and monitoring. `oc rollout undo` may be insufficient when database schema or external dependencies changed.

## Evidence and closeout

Capture sanitized cluster identity, OCP version, namespace, timestamps, desired versus actual replicas, selected events, hypothesis, owner, and action/approval. Record recovery separately from triage. **No runtime test or production certification has been performed for this runbook.**

## Reference

[Red Hat OpenShift 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
