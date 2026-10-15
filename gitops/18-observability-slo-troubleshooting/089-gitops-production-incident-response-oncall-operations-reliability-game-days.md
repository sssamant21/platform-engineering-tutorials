# Chapter 089 — GitOps Production Incident Response, On-Call Operations and Reliability Game Days

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 18:** Observability, SLOs and Troubleshooting  
**Chapter:** 089 / 100  
**Audience:** SREs, Platform Engineers, Incident Commanders, Security Responders, Release Engineers and On-Call Leads

> **Safety:** Execute game days only in isolated staging environments with synthetic data, approved fault scopes, budgets, abort criteria and recovery owners. Never disable production alerting, revoke live credentials, simulate database split-brain, delete PVCs or change production traffic without authorization. Pause experiments immediately when impact escapes the approved boundary.

## 1. Mission

Establish an operationally mature GitOps incident-response program spanning GitLab pipelines, runners, artifact registries, Argo CD, ApplicationSets, Kubernetes, cloud identities, storage and user-facing services.

At completion, teams can operate on-call rotations, detect and triage incidents, assign incident command, coordinate communications, execute approved mitigations, measure recovery, run controlled game days and verify corrective actions.

## 2. Operating principles

1. Start with customer impact and data safety.
2. Prefer reversible mitigations over speculative configuration changes.
3. Use one incident commander with clear decision authority.
4. Preserve audit and incident evidence.
5. Separate mitigation, root cause investigation and permanent remediation.
6. Escalate early when access, data integrity or cross-cloud dependencies are at risk.
7. Treat game days as engineering experiments with hypotheses and abort criteria.
8. Make reliability improvements testable.

## 3. Incident command structure

| Role | Responsibility |
| --- | --- |
| Incident Commander (IC) | Coordinates priorities, decisions and escalation |
| Operations Lead | Executes approved mitigations |
| Communications Lead | Publishes impact and status updates |
| Scribe | Records UTC timeline and evidence |
| Service Owner | Validates business workflow and SLO |
| Data Lead | Verifies storage, replication and integrity |
| Security Lead | Handles identity, credential and audit risk |

In smaller incidents roles may be combined explicitly, but avoid leaving command ownership ambiguous.

## 4. Severity and escalation

| Severity | Illustrative trigger | Response |
| --- | --- | --- |
| SEV1 | Widespread outage, data integrity or security emergency | Immediate IC and executive/customer escalation |
| SEV2 | Significant regional or tenant impact | Page primary and incident team |
| SEV3 | Localized degradation or reduced redundancy | Owner investigation |
| SEV4 | No immediate customer impact | Planned issue management |

Use organization-specific definitions and on-call targets. SLO burn, synthetic failure and data safety inform severity.

## 5. Incident lifecycle

~~~text
Detection -> Acknowledge -> Triage -> Declare
    -> Assign IC -> Contain -> Mitigate
    -> Validate service and data -> Communicate
    -> Resolve -> Blameless review
    -> Corrective action verification
~~~

Do not delay urgent mitigation solely to determine a definitive root cause.

## 6. On-call service catalog

For each service, record owner, backup owner, escalation path, SLO, dependencies, dashboard, runbook, GitOps repository, deployment method, backup policy and security contact.

Include GitLab, runners, registry, Argo CD, cluster API, DNS, ingress, workload identity, secret store, database and observability.

## 7. Rotation and handoff

Handoffs should include active incidents, open changes, risk exceptions, degraded dependencies, SLO budget, expiring credentials, backup failures and pending game-day follow-ups.

No production-critical service should have a single undocumented responder.

## 8. Paging policy

Page on user impact, fast SLO burn, data-integrity risk, security compromise or imminent capacity failure. Route non-urgent hygiene to tickets.

Deduplicate alerts, test routing and prevent noisy alerts from obscuring critical signals.

## 9. First fifteen minutes

1. Confirm impact via independent synthetic check and SLI.
2. Record incident start and severity.
3. Assign IC, operations lead and communications owner.
4. Identify affected provider, cluster, region, service and cohort.
5. Inspect recent GitLab/Argo CD changes.
6. Freeze risky promotions if authorized.
7. Test high-confidence hypotheses.
8. Execute reversible mitigation and verify results.
9. Publish next update time.

## 10. GitOps incident containment

GitOps may reconcile a manual emergency fix back to undesired state. Prefer a reviewed Git revert or approved Argo CD sync policy adjustment with explicit owner, expiry and restoration plan.

Never disable reconciliation fleet-wide as a default workaround. Treat prune, replace and force-sync as high-risk for stateful workloads.

## 11. GitLab and artifact failures

Check runner scheduling, protected refs, OIDC trust, registry availability, image signature, immutable digest and artifact retention.

Do not bypass supply-chain controls to make a failing release green.

## 12. Argo CD controller and ApplicationSet failures

Inspect repo-server, application-controller, API, cluster credentials, AppProject restrictions, generator inputs and generated target count.

An ApplicationSet selector change may alter many destinations. Freeze destructive reconciliation until targets are validated.

## 13. Kubernetes workload response

~~~bash
kubectl config current-context
kubectl -n demo-staging get deploy,pods,svc,endpointslices -o wide
kubectl -n demo-staging get events --sort-by=.lastTimestamp
kubectl -n demo-staging describe deploy demo-api
kubectl -n demo-staging logs deploy/demo-api --since=20m --timestamps
~~~

Check Pod lifecycle, resource pressure, probes, networking, CSI and storage. Redact secrets before attaching logs to incidents.

## 14. Cloud and multi-region escalation

Assign one lead per affected cloud provider. Maintain a shared timeline while preserving provider-specific IAM, networking, quota, region health and audit evidence.

Do not assume traffic can move to another cloud until data, secrets, certificates, registry and recovery capacity are ready.

## 15. Data integrity and backup safety

A service may return HTTP 200 while writing corrupt or stale data. Verify transaction consistency, queue replay, replication state, backup recovery point and downstream processing before resolution.

For primary/standby databases, fence the former writer before promotion to avoid split-brain.

## 16. Incident communications

Provide observed impact, affected users/regions, mitigation, data status, current uncertainty, next update and responsible owner. Separate internal technical detail from externally verified facts.

Use a consistent update cadence appropriate to severity and policy.

## 17. Decision log

~~~text
Incident ID:
UTC timestamp:
Decision:
Evidence:
Alternatives considered:
Risk:
Approver:
Executor:
Validation:
Rollback:
~~~

Record emergency exceptions and their expiry.

## 18. Safe mitigation hierarchy

1. Stop further rollout.
2. Restore previously known-good signed artifact.
3. Shift traffic only to validated healthy capacity.
4. Scale or restart targeted components if supported by evidence.
5. Restore cloud IAM/network access narrowly.
6. Execute stateful failover only under approved data runbook.
7. Use emergency exceptions only with audit and expiry.

## 19. Reliability game-day design

Every experiment specifies hypothesis, target system, fault injection, expected user impact, SLO detection, abort criteria, blast radius, backup/recovery plan, evidence, owner and post-test review.

Start with tabletop exercises, then staging fault injection, and only consider tightly controlled production experiments after separate authorization.

## 20. Fault-injection guardrails

~~~yaml
experiment:
  name: staging-api-latency
  environment: staging
  namespace: demo-staging
  duration_minutes: 5
  hypothesis: error-budget alert detects elevated latency
  abort_if:
    - impact_outside_namespace
    - unexpected_data_integrity_risk
    - observability_unavailable
  rollback: restore reviewed staging deployment
  approver: platform-sre-lead
~~~

This is an experiment specification, not an executable chaos framework CRD. Implement with approved tooling and verify its real safeguards.

## 21. Game-day maturity ladder

| Level | Exercise | Objective |
| --- | --- | --- |
| 1 | Tabletop | Decision and escalation clarity |
| 2 | Single Pod fault | Detection and local recovery |
| 3 | GitOps drift/release regression | Rollback governance |
| 4 | Identity/network dependency | Cross-layer diagnosis |
| 5 | Cluster/region staging outage | Recovery dependencies |
| 6 | Integrated fleet simulation | Command and RPO/RTO |

Advance only when prior level passes safety and recovery acceptance.

## 22. Metrics for response quality

Track detection time, acknowledgement, time to mitigate, time to recover, customer impact, error budget consumed, escalation latency, alert precision, rollback duration and corrective action closure.

Avoid using a single MTTR number to judge individual responders.

## 23. Post-incident reviews

A blameless review documents the triggering event, technical failure mechanism, contributing conditions, detection gaps, recovery bottlenecks and testable prevention actions.

Assign owners and dates; verify changes through drills or automated regression tests.

## 24. On-call sustainability

Review paging load, after-hours interruption, handoff quality, runbook coverage and toil. Automate repeatable diagnostics with scoped read-only permissions before automating destructive remediation.

## 25. Production readiness gates

Require service ownership, tested paging, dashboards, SLO, backup integrity, rollback, access control, data-safe recovery, game-day evidence and incident communication templates before production handover.

## 26. Lab A — On-call inventory

1. List GitLab, Argo CD, Kubernetes and app owners.
2. Record primary/secondary escalation.
3. Link dashboards and runbooks.
4. Identify missing coverage.
5. Verify contact routes.
6. Archive approved service catalog.

**Pass:** no unowned critical dependency.

## 27. Lab B — Alert acknowledgement

1. Generate synthetic staging SLO alert.
2. Verify primary page.
3. Record acknowledgement timestamp.
4. Test backup escalation.
5. Resolve synthetic condition.
6. Verify closure.

**Pass:** escalation chain functions.

## 28. Lab C — Incident command tabletop

1. Declare simulated SEV1.
2. Assign IC and technical leads.
3. Record customer impact and uncertainty.
4. Agree mitigation priority.
5. Publish status update.
6. Review role clarity.

**Pass:** command is unambiguous.

## 29. Lab D — GitLab runner outage

1. Use disposable runner fixture.
2. Trigger job scheduling failure.
3. Inspect runner queue and tags.
4. Escalate to CI owner.
5. Restore runner availability.
6. Verify protected pipeline.

**Pass:** CI incident recovered.

## 30. Lab E — Registry/image failure

1. Deploy disposable invalid digest.
2. Observe ImagePullBackOff.
3. Correlate GitLab artifact record.
4. Restore signed known-good digest.
5. Verify Pod imageID.
6. Record mitigation time.

**Pass:** no signature bypass.

## 31. Lab F — Argo CD drift

1. Create harmless staging drift.
2. Observe OutOfSync and audit.
3. Compare desired/live manifests.
4. Select reviewed remediation.
5. Reconcile.
6. Verify user synthetic check.

**Pass:** desired state safely restored.

## 32. Lab G — ApplicationSet placement

1. Record approved cluster targets.
2. Introduce invalid staging selector.
3. Observe generated Application count.
4. Halt destructive actions.
5. Correct selector.
6. Verify target inventory.

**Pass:** fleet blast radius contained.

## 33. Lab H — Pod failure

1. Deploy synthetic crash-loop workload.
2. Detect restart and service error.
3. Inspect previous logs and events.
4. Restore working configuration.
5. Verify service SLO.
6. Update runbook.

**Pass:** runtime incident resolved.

## 34. Lab I — DNS/NetworkPolicy

1. Confirm CNI enforcement.
2. Block disposable synthetic traffic.
3. Observe DNS/API error.
4. Inspect Service and policy.
5. Restore narrow allowance.
6. Verify unrelated traffic remains denied.

**Pass:** no broad allow-all workaround.

## 35. Lab J — Workload identity denial

1. Use synthetic cloud resource.
2. Misconfigure test KSA trust.
3. Observe AccessDenied.
4. Inspect issuer, subject and audience.
5. Restore scoped trust.
6. Verify negative authorization test.

**Pass:** no static credential workaround.

## 36. Lab K — Secret rotation

1. Create synthetic secret.
2. Rotate provider version.
3. Observe stale app state.
4. Execute approved reload.
5. Validate new version.
6. Verify audit and rollback.

**Pass:** secret recovery understood.

## 37. Lab L — SLO burn and release halt

1. Introduce synthetic 5xx.
2. Trigger multi-window burn alert.
3. Stop wave-2 deployment.
4. Revert staging GitOps revision.
5. Verify SLO recovery.
6. Record error-budget impact.

**Pass:** reliability policy controls rollout.

## 38. Lab M — Backup recovery tabletop

1. Select synthetic stateful workload.
2. Identify recovery point and keys.
3. Review restore order and IAM.
4. Simulate primary failure in tabletop.
5. Validate writer fencing decision.
6. Document RPO/RTO gaps.

**Pass:** no unsafe dual writer promotion.

## 39. Lab N — Regional failover rehearsal

1. Use isolated staging endpoints.
2. Confirm recovery capacity and data.
3. Fence synthetic primary writer.
4. Restore/promote recovery dataset.
5. Shift synthetic traffic.
6. Measure integrity, RPO and RTO.

**Pass:** controlled failover works.

## 40. Lab O — Communication exercise

1. Prepare simulated customer impact.
2. Draft first status update.
3. State verified facts and unknowns.
4. Publish next update time.
5. Send recovery notice.
6. Review clarity and accuracy.

**Pass:** no unsupported recovery claims.

## 41. Lab P — Handoff drill

1. Prepare current incident/change summary.
2. Include open SLO risk and exceptions.
3. Transfer primary ownership.
4. Have incoming responder reproduce dashboard view.
5. Verify escalation access.
6. Sign off handoff.

**Pass:** no critical context lost.

## 42. Lab Q — Corrective action validation

1. Select previous synthetic RCA.
2. Implement detection or prevention change.
3. Re-run failure scenario.
4. Verify expected guardrail.
5. Record test evidence.
6. Close action with reviewer.

**Pass:** RCA action demonstrably effective.

## 43. Lab R — Integrated reliability game day

1. Simulate GitLab runner delay.
2. Trigger Argo CD fleet selector error.
3. Inject synthetic app latency.
4. Declare incident and coordinate leads.
5. Halt rollout, diagnose and mitigate.
6. Verify SLO and data safety.
7. Publish timeline, RCA and acceptance score.

**Pass:** team manages cross-layer incident end-to-end.

## 44. Troubleshooting — twenty scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Alert never pages | Receiver/route | Test escalation |
| 2 | Duplicate pages | Grouping failure | Tune deduplication |
| 3 | No incident commander | Ownership gap | Assign IC |
| 4 | Inconsistent timeline | Timezone/clock skew | Normalize UTC |
| 5 | Pipeline stuck | Runner unavailable | Restore capacity |
| 6 | CI token rejected | OIDC trust | Correct federation |
| 7 | Registry artifact missing | Retention/replication | Restore signed digest |
| 8 | Argo CD OutOfSync | Drift | Compare manifests |
| 9 | ApplicationSet deletes targets | Selector/generator | Freeze destructive sync |
| 10 | AppProject denies deployment | Destination restriction | Review authorization |
| 11 | Pod CrashLoopBackOff | Process/probe | Inspect previous logs |
| 12 | Service endpoints absent | Selector/readiness | Repair routing |
| 13 | DNS failure | CoreDNS/egress | Verify network |
| 14 | Secret mount denied | IAM/CSI | Repair scoped access |
| 15 | Synthetic API 5xx | App/dependency | Correlate traces |
| 16 | SLO alert fires late | Wrong burn windows | Validate rule |
| 17 | Backup restore fails | IAM/KMS/format | Test isolated restore |
| 18 | DR writer split-brain risk | Missing fencing | Stop promotion |
| 19 | Status updates contradict | Unverified information | Centralize communications |
| 20 | Repeat incident | RCA actions unverified | Re-run game day |

## 45. Runbook — incident declaration and command

1. Confirm user impact and severity.
2. Create incident record with UTC start.
3. Assign IC, operations, communications and scribe.
4. Establish incident channel and evidence links.
5. Set update cadence and escalation.
6. Approve immediate reversible mitigation.
7. Record decisions and validation.

## 46. Runbook — paging and escalation failure

1. Confirm alert expression and firing state.
2. Inspect Alertmanager routing and receiver.
3. Test approved backup notification.
4. Contact on-call lead through alternate channel.
5. Restore primary route.
6. Generate synthetic alert.
7. Document blind interval and remediation.

## 47. Runbook — GitLab delivery incident

1. Identify project, pipeline, runner and commit.
2. Inspect runner queue, job logs and OIDC.
3. Check registry, signature and digest.
4. Halt unsafe promotion.
5. Restore scoped delivery dependency.
6. Verify protected staging pipeline.
7. Record timeline.

## 48. Runbook — Argo CD fleet incident

1. Capture affected Applications, ApplicationSets and clusters.
2. Review generator input and target count.
3. Check repo-server, controller and AppProject.
4. Freeze destructive reconciliation if authorized.
5. Restore reviewed GitOps revision.
6. Verify workloads and SLO.
7. Record blast radius.

## 49. Runbook — Kubernetes service degradation

1. Confirm affected user journey and region.
2. Inspect Pod, node, Service and ingress state.
3. Correlate logs, traces and metrics.
4. Check identity, secrets, network and storage.
5. Apply reversible mitigation.
6. Verify SLO and data integrity.
7. Record RCA evidence.

## 50. Runbook — SLO burn and rollback

1. Validate numerator, denominator and freshness.
2. Identify recent releases and affected cohorts.
3. Halt further promotion.
4. Revert approved GitOps revision or shift validated traffic.
5. Confirm error-budget burn reduces.
6. Notify stakeholders.
7. Record change failure and corrective action.

## 51. Runbook — data-safe disaster recovery

1. Declare DR and authorize action.
2. Verify backup recovery point and keys.
3. Confirm recovery cluster capacity, IAM and networking.
4. Fence former primary writer.
5. Restore/promote data and verify consistency.
6. Shift synthetic/approved traffic and validate SLO.
7. Measure RPO/RTO and preserve evidence.

## 52. Runbook — post-incident review and handoff

1. Preserve UTC timeline and redacted evidence.
2. Quantify user impact and error budget.
3. Document causal mechanism and contributing conditions.
4. Assign prevention, detection and recovery actions.
5. Verify action owners, dates and tests.
6. Transfer unresolved risks to on-call handoff.
7. Schedule game-day revalidation.

## 53. Incident communication template

~~~text
Incident ID / severity:
Start time UTC:
Affected services and regions:
Customer impact (verified):
Current status:
Data integrity status:
Mitigation performed:
Remaining uncertainty:
Next update UTC:
Incident commander:
~~~

## 54. Game-day record template

~~~text
Experiment ID:
Service and staging cluster:
Hypothesis:
Fault injection:
Blast radius and safeguards:
Abort criteria:
Expected detection and paging:
Incident command roles:
Expected rollback:
Backup/data safety checks:
Actual timeline:
SLO and error budget:
RPO/RTO (if applicable):
Lessons and corrective actions:
Approver and teardown:
~~~

## 55. Scored on-call readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| On-call ownership and escalation | 15 | Tested rotation |
| Incident command and communications | 20 | Timeline and updates |
| GitLab/Argo CD response | 15 | Controlled mitigation |
| Kubernetes and cloud recovery | 15 | Safe service restoration |
| SLO alerting and rollback | 15 | Synthetic incident |
| DR and data safety | 10 | Verified fencing/restore |
| Game-day RCA and follow-up | 10 | Verified actions |
| **Total** | **100** | |

**Pass:** at least 85/100 and all critical gates: paging reaches a human, incident command is assigned, security controls not bypassed, no unsafe dual writer, recovery is verified by user-facing checks, and game-day impact stays within scope.

## 56. Final acceptance checklist

- [ ] Critical services have primary and backup owners.
- [ ] On-call rotation and handoff process documented.
- [ ] Paging and escalation tested.
- [ ] Incident command roles and severity agreed.
- [ ] GitLab, Argo CD and Kubernetes runbooks accessible.
- [ ] Fleet target containment tested.
- [ ] SLO alerts and release rollback verified.
- [ ] Identity, secrets and network recovery validated.
- [ ] Data-integrity and DR fencing procedures reviewed.
- [ ] Communications templates exercised.
- [ ] Game-day abort criteria and safeguards validated.
- [ ] Corrective actions have owners and test evidence.
- [ ] Eighteen hands-on labs completed.
- [ ] Twenty troubleshooting scenarios reviewed.
- [ ] Eight production runbooks validated.
- [ ] Readiness assessment signed off.

## 57. Knowledge check

1. What decisions belong to the incident commander?
2. Why should mitigation be separated from RCA?
3. How does GitOps reconciliation complicate emergency changes?
4. What constitutes a useful on-call handoff?
5. When should SLO burn trigger paging versus a ticket?
6. Why must ApplicationSet target counts be checked before remediation?
7. What prevents a game-day fault from escaping its scope?
8. Why does disaster recovery require writer fencing?
9. How do you measure incident response effectiveness without blaming responders?
10. What evidence proves an RCA corrective action works?

## 58. References

- [Google SRE workbook](https://sre.google/workbook/table-of-contents/)
- [Google SRE: Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Google SRE: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- [Kubernetes debugging](https://kubernetes.io/docs/tasks/debug/)
- [Argo CD troubleshooting](https://argo-cd.readthedocs.io/en/stable/operator-manual/troubleshooting/)
- [Argo CD ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [Prometheus alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [OpenTelemetry](https://opentelemetry.io/docs/)

---

**Chapter 089 complete.**

**Next:** Chapter 090 — Enterprise GitOps Observability, Incident Response and Reliability Acceptance Capstone, completing Part 18.