# Chapter 014 — Companion Lab: Agent Provisioning, Capacity and Lifecycle Check

**Parent:** [Chapter 014](../014-jenkins-agent-provisioning-capacity-management-lifecycle-operations.md)

## Safety and goal

Use a disposable localhost controller for architecture, queue and capacity exercises. Kubernetes/cloud provisioning is tabletop or approved staging-only; do not attach production credentials or create untracked cloud resources.

## Lab 01 — Docker baseline

```bash
docker version
docker ps
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Host and engine available. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 02 — Create dedicated volume

```bash
docker volume create jenkins-ch014-home
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Home volume exists. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 03 — Launch private controller

```bash
docker run -d --name jenkins-ch014 --restart=no -p 127.0.0.1:8092:8080 --memory 4g --cpus 2 --mount source=jenkins-ch014-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Controller launched. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 04 — Startup logs

```bash
docker logs --tail 60 jenkins-ch014
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** No fatal startup error. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 05 — Verify backend exposure

```bash
docker port jenkins-ch014
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Loopback only. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 06 — Bootstrap privately

```bash
docker exec jenkins-ch014 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Action:** Unlock privately at http://127.0.0.1:8092; never record the bootstrap secret.

**Pass:** Named admin; secret not recorded. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 07 — Disable built-in executors

```bash
docker ps --filter name=jenkins-ch014
```

**Action:** Manage Jenkins → Nodes → Built-In Node → set executors to 0.

**Pass:** Built-in executors zero. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 08 — Inspect runtime

```bash
docker inspect jenkins-ch014 --format '{{.Config.Image}} {{.Config.User}}'
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Runtime identity known. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 09 — Inspect home persistence

```bash
docker inspect jenkins-ch014 --format '{{json .Mounts}}'
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Persistent mount correct. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 10 — Inspect controller capacity

```bash
docker stats --no-stream jenkins-ch014
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** CPU/memory baseline. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 11 — Review static VM pool

```bash
docker inspect jenkins-ch014 --format '{{.State.Status}}'
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Immutable VM image and SSH policy documented. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 12 — Review Kubernetes pool

```bash
docker logs --tail 25 jenkins-ch014
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Pod identity, quotas and cleanup documented. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 13 — Review cloud VM pool

```bash
docker inspect jenkins-ch014 --format '{{.Config.Image}}'
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Cloud IAM, tags and TTL documented. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 14 — Create label-based Pipeline

```bash
docker logs --tail 20 jenkins-ch014
```

**Action:** Create a Pipeline job using the labeled Jenkinsfile in the parent chapter.

**Pass:** Pipeline saved. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 15 — Observe missing-agent queue

```bash
docker stats --no-stream jenkins-ch014
```

**Action:** Run it, record the missing-agent queue reason, then cancel.

**Pass:** Queue reason recorded and build canceled. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 16 — Capacity calculation

```bash
docker stats --no-stream jenkins-ch014
```

**Action:** Calculate ceil(6 × 4 / 0.70) = 35 slots and discuss burst/CPU caveats.

**Pass:** Sizing scenario calculated. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 17 — Drain and lifecycle tabletop

```bash
docker inspect jenkins-ch014 --format '{{.State.Status}}'
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Safe node drain documented. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 18 — Incident tabletop

```bash
docker logs --tail 50 jenkins-ch014
```

**Action:** Tabletop: diagnose Pod Pending, cloud quota exhausted and orphaned VM; do not inject failures.

**Pass:** Three failures and rollback diagnosed. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 19 — SLO/FinOps review

```bash
docker exec jenkins-ch014 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Action:** Record redacted evidence and the operational implications.

**Pass:** Metrics, cost and alerts defined. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Lab 20 — Cleanup and scoring

```bash
docker stop jenkins-ch014
docker rm jenkins-ch014
# After confirming exclusive ownership: docker volume rm jenkins-ch014-home
```

**Action:** Delete only lab-owned resources and verify volume ownership.

**Pass:** Lab safely cleaned. **Rollback:** revert only lab-owned configuration; no shared resource deletion.

## Capacity worksheet

| Variable | Example | Operator value |
|---|---:|---|
| Jobs arriving per minute (λ) | 6 | |
| Mean build duration (W, min) | 4 | |
| Target utilization (u) | 0.70 | |
| Calculated slots ceil(λW/u) | 35 | |
| Burst factor and p95 queue target | Measure | |
| Provisioning p95 | Measure | |
| Agent CPU/memory per job | Profile | |
| Cloud quota / cost ceiling | Review | |

The calculation is a starting point, not a validated SLO.

## Troubleshooting matrix

| Incident | Evidence | Recovery |
|---|---|---|
| Pod Pending | Events, quotas, selectors | Correct scheduling |
| Cloud quota exhausted | API response and limits | Approved quota/capacity |
| WebSocket agent disconnected | TLS/proxy/remoting | Restore trusted connection |
| OOMKilled | Exit reason and limits | Right-size |
| Orphaned VM | Owner tags and Jenkins node state | Reconcile verified orphan |
| Queue wait | Labels and executors | Provision matching capacity |
| Cost spike | Idle time and instance inventory | Adjust TTL and pool limits |
| Trust boundary violation | Job credentials and agent IAM | Quarantine and rotate |

## Acceptance score — 100 points

| Area | Points |
|---|---:|
| Pool architecture/lifecycle | 20 |
| Cloud/Kubernetes security | 20 |
| Capacity/autoscaling | 25 |
| Cost and cleanup | 15 |
| Troubleshooting/monitoring | 10 |
| Evidence and safe teardown | 10 |
| **Total** | **100** |

**Pass:** 90+ with no security-critical failure.

## Evidence template

```text
Operator/date:
Controller URL/binding:
Built-in executor count:
Volume and runtime:
Static/cloud/Kubernetes pool designs:
Provisioning IAM/RBAC:
Immutable image policy:
Queue demo and cancellation:
Capacity calculation and caveats:
Scale-up/down and drain:
Orphan reconciliation:
Three incident diagnoses:
Queue/provisioning SLOs:
FinOps budget/owner:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 015 — Jenkins Controller, Agents and Executors Production Operations Capstone.
