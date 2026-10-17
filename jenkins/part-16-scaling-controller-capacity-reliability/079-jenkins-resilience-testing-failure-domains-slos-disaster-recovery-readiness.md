# Chapter 079 — Jenkins Resilience Testing, Failure Domains, SLOs and Disaster Recovery Readiness

**Part 16 — Scaling, Controller Capacity and Reliability**  
**Audience:** Jenkins SRE, incident commanders, reliability engineers and platform architects  
**Prerequisites:** Chapters 076–078, isolated Jenkins LTS, disposable agents, test SCM, metrics, backups and an approved failure-injection environment.

## Objectives

Build a repeatable Jenkins resilience test program, map correlated failure domains, define user-centric SLIs/SLOs, calculate error budgets, measure restoration time, validate backup recovery and produce evidence-based go/no-go decisions.

## 1. Resilience reference architecture

```text
Git events → ingress/webhook → single-active Jenkins controller → queue
                  |                         |                  |
                SCM                     Jenkins home         agents
                  |                         |                  |
             provider SLO              backup/restore      K8s/VM pools
                   \                       |                 /
                       external synthetic CI probe
                                   |
                          metrics/logs/traces
                                   |
                       SLO + incident + DR scorecard
```

Jenkins controller state must remain single-writer. Multiple independent controllers can isolate workloads, but do not form a generic active-active cluster over one writable `JENKINS_HOME`.

## 2. Failure-domain inventory

| Domain | Example fault | Recovery boundary |
|---|---|---|
| Controller JVM | crash, GC thrash | restart or rollback |
| Plugin/JCasC | incompatible change | known-good image/config |
| Jenkins home | disk full, corruption | snapshot/restore |
| Kubernetes API | pod creation fails | control-plane recovery |
| Agent node pool | capacity loss | alternate pool |
| Network/DNS/TLS | service unreachable | scoped connectivity |
| SCM | webhook/checkout outage | provider recovery |
| Registry/artifact | upload/download failure | dependency restoration |
| Secrets/SSO | token or IdP outage | identity recovery |
| Cloud region/AZ | node/storage disruption | tested DR topology |

Dependencies can fail together; avoid treating independent synthetic checks as proof of independent failure domains.

## 3. User-centric SLI and SLO design

Use a **representative synthetic Pipeline** that checks webhook or trigger acceptance, queue scheduling, agent startup, checkout, test and artifact publication. Measure end-to-end completion and classify failures.

Example proposed SLIs:
- Critical Pipeline success rate (exclude user-code failures using a documented classification policy).
- Controller external availability.
- p95 queue wait by workload class.
- p95 agent request-to-ready time.
- Successful artifact delivery and checksum validation.
- Time to verified restore from a tested backup.

Illustrative SLOs, **not universal defaults**:

| SLI | Example target | Window |
|---|---|---|
| Critical synthetic CI success | 99.9% | rolling 30 days |
| External controller availability | 99.9% | rolling 30 days |
| Queue wait p95 | under 120 seconds | rolling 7 days |
| Agent readiness p95 | under 90 seconds | rolling 7 days |
| DR RTO | at most 60 minutes | per drill |
| DR RPO | at most 15 minutes | per drill |

The SLO owner must approve exclusions and ensure synthetic traffic represents real critical workflows.

## 4. Error budgets

For an availability target `S` and period `T`, allowable unavailability is `(1-S) × T`. At 99.9% over a 30-day period: `0.001 × 30 × 24 × 60 = 43.2 minutes`.

For request/job success SLOs, error budget is a **count of eligible failures**, not necessarily minutes. Avoid mixing the two. Define error-budget burn alerts using sustained rates and multiple windows to avoid paging on a single transient sample.

## 5. Resilience experiment lifecycle

1. Define hypothesis, scope, service owner and approval.
2. Verify isolated environment and backup/rollback.
3. Establish baseline metrics and synthetic success.
4. Inject **one bounded failure** at a time.
5. Capture detection, acknowledgment, mitigation and verified recovery UTC.
6. Check collateral impact, security boundaries and data integrity.
7. Restore original configuration and confirm cleanup.
8. Record observed SLI impact, lessons and corrective actions.

Abort immediately if blast radius exceeds approval, real credentials are exposed, backup integrity is uncertain or test costs exceed limits.

## 6. Recovery timing and state integrity

Track:
- MTTD: incident start to detection.
- MTTA: detection to acknowledgment.
- MTTM: acknowledgment to effective mitigation.
- MTTR: incident start to verified recovery.
- RTO: business-approved maximum recovery time.
- RPO: business-approved maximum data-loss exposure.

Measure restore time from the declared disaster start, including volume provisioning, keys, compatible core/plugins/JCasC, queue reconciliation and end-to-end Pipeline validation. Backup age is only a proxy for RPO; verify the restored state and last durable change.

## 7. Safe backup and restore drill

Restore into a separate namespace and **separate copy** of Jenkins home. Never start two controller processes against the same writable volume. Confirm encryption keys, plugin versions, secrets references and job definitions. Run representative builds, check artifacts and audit access. Record actual recovery time and state loss.

## 8. Failure experiment matrix

| # | Experiment | Expected validation |
|---|---|---|
| 01 | Controller process crash | restart and probe |
| 02 | JVM memory pressure (bounded) | alert and safe recovery |
| 03 | Plugin incompatibility in staging | rollback |
| 04 | JCasC invalid config | validation and revert |
| 05 | Jenkins home full in lab | storage alert/recovery |
| 06 | Slow storage simulation | I/O SLI |
| 07 | Agent node loss | replacement |
| 08 | Pod scheduling denied | queue reason |
| 09 | ImagePullBackOff | registry recovery |
| 10 | Remoting disconnect | reconnection |
| 11 | NetworkPolicy egress block | scoped fix |
| 12 | DNS outage in lab | resolution recovery |
| 13 | SCM webhook failure | event replay |
| 14 | Checkout auth failure | least-privilege fix |
| 15 | Artifact registry outage | bounded retry |
| 16 | Secret provider unavailable | fail closed |
| 17 | SSO provider unavailable | break-glass audit |
| 18 | Backup restore to isolated copy | RTO/RPO proof |
| 19 | Agent pool AZ loss simulation | capacity failover |
| 20 | Burst queue saturation | SLO and recovery |

## 9. Alerting and observability

Alert on external synthetic CI failures, controller probe failure, sustained queue p95 degradation, agent provisioning failures, controller GC/storage pressure, backup age/integrity and restore-test staleness. Annotate deploys and incident timelines. Avoid high-cardinality build IDs as Prometheus labels.

## 10. Six production runbooks

### A. SLO burn response
Verify eligible events and classification, correlate recent changes and dependencies, mitigate user impact, communicate error-budget status and initiate RCA.

### B. Controller/JCasC resilience
Capture first error and plugin manifest, fence old writer, restore tested image/configuration, verify UI/API and synthetic Pipeline.

### C. Agent/zone failure
Inspect node and pod events, compatible capacity, autoscaler and cloud quota; restore agent pool and queue p95.

### D. SCM/artifact dependency outage
Check provider health and error rates, prevent retry storms, use bounded backoff, validate checkout/artifact integrity after recovery.

### E. Backup/restore readiness
Validate backup consistency, encryption keys, version compatibility, isolated restore and actual RTO/RPO. Fail acceptance if mandatory evidence is missing.

### F. Post-drill review
Reconcile timeline, score SLO and recovery gates, document residual risk and COA owners, restore baseline and obtain sign-off.

## 11. Resilience scorecard (100 points)

| Domain | Points |
|---|---:|
| Failure-domain inventory and blast-radius design | 15 |
| SLIs, SLOs and error-budget math | 15 |
| Synthetic CI monitoring and alerts | 15 |
| Controlled fault injection and safety | 15 |
| Controller/agent/dependency recovery | 15 |
| Backup restore and measured RTO/RPO | 15 |
| RCA/COA, communication and handover | 10 |
| **Total** | **100** |

Suggested pass: **85/100** plus mandatory gates: no secret exposure, no production disruption, single active writer, successful isolated restore, measured RTO/RPO and verified synthetic Pipeline. An unexecuted drill is blocked, not passed.

## 12. Evidence template

```text
Experiment ID / UTC:
Owner / approver / abort criteria:
Baseline SLI/SLO and error budget:
Failure domain and injection:
Start / detect / acknowledge / mitigate / recover:
Impact and dependency correlation:
Recovery action and rollback:
Independent synthetic CI result:
Backup restore point and measured RTO/RPO:
Security and data-integrity checks:
Score / RCA / COA owner:
Reviewer sign-off:
```

## 13. Acceptance criteria

- [ ] Failure domains and shared dependencies documented.
- [ ] User-centric SLIs/SLOs defined and approved.
- [ ] Error-budget arithmetic verified.
- [ ] Synthetic Pipeline and alerting validated.
- [ ] Fault injection bounded and reversible.
- [ ] Controller, agent and dependency recovery tested.
- [ ] Isolated backup restore performed.
- [ ] RTO/RPO measured with state integrity proof.
- [ ] Scorecard and RCA/COA completed.
- [ ] Reviewer approval recorded.

**Companion:** [Chapter 079 hands-on lab](labs/079-jenkins-resilience-testing-failure-domains-slos-disaster-recovery-readiness-check.md).  
**Next:** Chapter 080 — Jenkins Scaling, High Availability and Reliability Acceptance Capstone.
