# Chapter 080 — Jenkins Scaling, High Availability and Reliability Acceptance Capstone

**Part 16 — Scaling, Controller Capacity and Reliability (final capstone)**  
**Audience:** Jenkins SRE, platform architects, reliability engineers, incident commanders, FinOps and service owners  
**Prerequisites:** Chapters 076–079, disposable Jenkins LTS, isolated agents/Kubernetes, test SCM/registry, metrics, approved backups and synthetic workloads.

## Mission

Demonstrate a production-style Jenkins reliability design and prove it with evidence: capacity forecasting, agent autoscaling, single-writer controller recovery, workload isolation, resilience testing, SLOs, RTO/RPO and cost controls.

**Safety:** Run only against an isolated lab. Do not run two controllers against one writable `JENKINS_HOME`; do not fault-inject production, expose credentials or delete shared volumes. Document change owner, rollback, abort thresholds and cost cap.

## 1. Reference architecture

```text
SCM/webhooks → routing → controller A (trusted releases)
                         own state + backup + probes
                                   |
                           trusted ephemeral agents

SCM/webhooks → routing → controller B (untrusted CI)
                         separate state + backup + probes
                                   |
                           sandboxed ephemeral agents

  Both → metrics/logs/synthetic CI → SLO/error budget → incident/DR
  Agents → Kubernetes scheduler → autoscaler/Karpenter → cloud nodes
```

Independent controllers provide blast-radius isolation, **not** generic shared-state active-active HA. A single controller has one active state writer and requires tested fencing, durable storage and restoration.

## 2. Architecture acceptance gates

- One active writer per Jenkins home.
- Trusted and untrusted workloads separated by authorization, credentials and agent pools.
- Controller builds avoided where appropriate; agents run builds.
- Immutable core/plugin/JCasC manifests and pinned agent images.
- Backups, keys and restore workflow documented and verified.
- Dependency SLOs for SCM, artifact registry, DNS, identity and cloud APIs.

## 3. Capacity model and load profile

Calculate offered concurrency using `arrival_rate × mean_executor_duration`, then apply a **documented** planning utilization and test burst behavior. Executor slots are not CPU cores; validate CPU, memory, disk, image pull, networking and compatible labels.

Illustrative case:
- 150 jobs/hour at 8 minutes average occupancy → 20 offered concurrent jobs.
- At 70% illustrative utilization → `ceil(20/0.70)=29` compatible slots.
- At 1 vCPU and 2 GiB requests per job → 29 vCPU and 58 GiB requested, excluding overhead.

Do not derive p95 queue guarantees from this average-only estimate. Test arrival bursts, long-tail job durations, autoscaler cold starts and failure capacity.

## 4. SLI/SLO and recovery objectives

| Indicator | Illustrative target |
|---|---|
| Critical synthetic Pipeline success | 99.9% over rolling 30 days |
| Controller external availability | 99.9% over rolling 30 days |
| Queue wait p95 | under 120 seconds |
| Agent request-to-ready p95 | under 90 seconds |
| DR RTO | at most 60 minutes |
| DR RPO | at most 15 minutes |

Targets require business approval. For 99.9% availability over exactly 30 days, allowable downtime is 43.2 minutes. Request-success error budgets instead use eligible event counts. Validate alert rules and eligibility exclusions.

## 5. End-to-end acceptance workflow

1. Capture controller/agent/cloud baseline and version manifests.
2. Create synthetic CI Pipeline that checks checkout, test and artifact digest.
3. Measure queue, agent startup, CPU, GC, storage and cost.
4. Calculate slots and run bounded steady-state and burst loads.
5. Simulate incompatible agent labels, Pending pods and node capacity loss.
6. Validate autoscaler provisioning and queue drain.
7. Test trusted/untrusted credentials with positive and negative checks.
8. Stop **test** controller and recover as single active writer.
9. Roll back a test plugin/JCasC regression.
10. Restore backup into separate state copy; measure RTO/RPO and state integrity.
11. Simulate SCM/registry interruption with bounded retries.
12. Verify synthetic CI, security, cost, SLO and incident handover.
13. Score acceptance and assign COA owners.

## 6. Failure scenarios

| # | Fault | Expected evidence |
|---|---|---|
| 01 | Controller CPU saturation | thread/CPU metrics |
| 02 | JVM GC pressure | GC/heap metrics |
| 03 | Jenkins home I/O latency | storage metrics |
| 04 | Queue backlog | labels/executor occupancy |
| 05 | Long-running job starvation | fairness evidence |
| 06 | Agent pod Pending | scheduler events |
| 07 | Autoscaler lag | node launch timestamps |
| 08 | Cloud quota exhaustion | provider error |
| 09 | ImagePullBackOff | registry events |
| 10 | Remoting timeout | agent/controller logs |
| 11 | Node loss | replacement time |
| 12 | Spot interruption | retry/idempotence |
| 13 | NetworkPolicy egress denied | connectivity test |
| 14 | DNS/TLS failure | trust/network evidence |
| 15 | Plugin upgrade failure | manifest and rollback |
| 16 | JCasC invalid schema | validation |
| 17 | Controller process crash | restart/recovery |
| 18 | Backup restore incomplete | integrity checks |
| 19 | Untrusted PR access attempt | negative auth test |
| 20 | SCM/registry outage | bounded retry |
| 21 | Shared dependency outage | correlated impact |
| 22 | Queue retry storm | backpressure |
| 23 | Excessive idle nodes | cost analysis |
| 24 | RTO/RPO breach | timed DR record |

Each fault must have injection, detection, mitigation, rollback and independent recovery proof. Mark unexecuted drills **blocked**, never passed.

## 7. Six production runbooks

### A. Controller capacity breach
Inspect CPU/GC/IO and queue metrics, isolate plugin/Pipeline cost, reduce noncritical load and apply tested sizing; validate synthetic CI and queue p95.

### B. Agent/autoscaler saturation
Correlate queue labels, pod events, quotas, node pools and cloud API limits; restore compatible capacity; verify queue drain and provisioning p95.

### C. Workload isolation failure
Stop affected workloads, notify security, rotate exposed synthetic/real credentials per incident policy, correct authorization/agent separation and validate negative access tests.

### D. Controller recovery
Preserve evidence, fence old writer, recover compatible image/plugins/JCasC and durable state; verify login, queue, agents, representative builds and artifact integrity.

### E. Backup/DR exercise
Restore verified backup to isolated copy, recover encryption keys securely, validate state, measure RTO/RPO and record deviations.

### F. Reliability acceptance and handover
Review scorecard, SLO/error budget, cloud cost, residual risks, incident timeline, COA owners and rollback. Obtain service-owner approval.

## 8. 100-point enterprise acceptance

| Category | Points |
|---|---:|
| Architecture, failure domains and trust isolation | 15 |
| Controller/executor capacity model | 15 |
| Kubernetes autoscaling and queue recovery | 15 |
| Controller single-writer recovery | 15 |
| Backup restore, RTO/RPO and integrity | 15 |
| SLI/SLO/error-budget observability | 10 |
| FinOps, dependency reliability and rollback | 10 |
| Incident RCA/COA and stakeholder sign-off | 5 |
| **Total** | **100** |

**Suggested pass:** 85/100 and all mandatory gates:
- Single active writer to Jenkins home.
- No production impact or credential exposure.
- Positive and negative workload isolation tests.
- Successful agent/node failure recovery.
- Independent controller recovery and synthetic CI success.
- Isolated backup restore with measured RTO/RPO.
- Rollback, cleanup and COA owner recorded.

Scoring cannot substitute for executed evidence.

## 9. Capacity and recovery evidence worksheet

```text
UTC / experiment ID:
Approver / abort criteria / cloud cost cap:
Controller image, Java, plugin and JCasC versions:
Controller state volume and single-writer verification:
Trust zones / credentials negative test:
Jobs/hour, mean/p95 duration, offered concurrency:
Planning utilization / compatible slots:
CPU, RSS, disk I/O, node quota:
Queue p95 before/after:
Agent readiness p95 before/after:
Synthetic CI and artifact digest:
Fault / detection / mitigation / recovery:
Backup restore point and state integrity:
Measured RTO/RPO:
SLO/error budget and alerts:
Cost per successful build:
Rollback / RCA / COA / owner:
Reviewer and decision:
```

## 10. Final acceptance checklist

- [ ] 24 fault scenarios exercised or explicitly blocked.
- [ ] Capacity model and burst load validated.
- [ ] Agent autoscaling and queue recovery measured.
- [ ] Single-writer controller recovery tested.
- [ ] Workload isolation and security verified.
- [ ] Isolated backup restore and RTO/RPO measured.
- [ ] SLO/error budget and alerts validated.
- [ ] Cloud cost and rollback reviewed.
- [ ] 100-point assessment completed.
- [ ] Service-owner sign-off and RCA/COA recorded.

**Companion:** [Chapter 080 hands-on capstone lab](labs/080-jenkins-scaling-high-availability-reliability-acceptance-capstone-check.md).  
**Part 16 complete:** Chapters 076–080.  
**Next:** Chapter 081 — Jenkins Backup Architecture, Recovery Strategy and RPO/RTO Planning (Part 17).
