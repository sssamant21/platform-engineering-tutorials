# Chapter 088 — GitOps Incident Investigation, Root Cause Analysis and Advanced Troubleshooting

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 18:** Observability, SLOs and Troubleshooting  
**Chapter:** 088 / 100  
**Audience:** SREs, Platform Engineers, DevOps Engineers, Incident Commanders and Security Responders

> **Lab safety:** All destructive or fault-injection activities belong in disposable staging namespaces and clusters with synthetic workloads. Never delete production resources, revoke live credentials, disable security policy, induce regional failures, or alter stateful storage without authorization and verified recovery procedures.

## 1. Objectives

Learn to detect and scope incidents, construct evidence-driven hypotheses, distinguish symptoms from causes, trace GitLab-to-Argo-CD-to-Kubernetes failures, diagnose cloud and application dependencies, mitigate safely, preserve audit evidence, and produce actionable blameless RCA and corrective actions.

## 2. End-to-end failure map

~~~text
GitLab source / protected branch / merge approval
                 |
pipeline jobs / runner / OIDC / registry / signature
                 |
GitOps repository / revision / Helm rendering
                 |
Argo CD API / repo-server / controller / ApplicationSet
                 |
cluster registration / RBAC / admission / network
                 |
Deployment / StatefulSet / Pod / Service / ingress
                 |
DNS / identity / secrets / storage / database
                 |
user-facing request / SLI / error budget
~~~

Investigate in both directions: from user impact down to dependencies, and from recent changes forward to deployed resources.

## 3. First ten minutes

1. Confirm customer impact through user-facing SLIs and synthetic checks.
2. Assign incident commander, operations lead and communications owner.
3. Identify affected provider, region, cluster, namespace, service and cohort.
4. Freeze unsafe promotions and destructive automation where approved.
5. Capture recent GitLab, GitOps, Argo CD and cloud changes.
6. Form competing hypotheses and test the least disruptive first.
7. Apply a reversible mitigation with validation and rollback criteria.
8. Preserve logs, traces, audit and exact UTC timeline.

## 4. Severity model

| Severity | Example | Response |
| --- | --- | --- |
| SEV1 | Widespread user outage or data-integrity risk | Immediate incident command |
| SEV2 | Material regional or tenant degradation | Page owner and coordinate |
| SEV3 | Limited impact or reduced redundancy | Timely investigation |
| SEV4 | Non-urgent defect without current impact | Planned remediation |

Adapt severity to organization policy; do not infer severity solely from an Argo CD health badge.

## 5. Evidence preservation

~~~bash
kubectl config current-context
kubectl -n demo-staging get pods,deploy,svc,ingress -o wide
kubectl -n demo-staging get events --sort-by=.lastTimestamp
kubectl -n demo-staging describe deploy demo-api
kubectl -n demo-staging logs deploy/demo-api --since=30m --timestamps
kubectl -n demo-staging get deploy demo-api -o yaml
~~~

Redact Secret values, token-bearing annotations and sensitive environment variables before sharing output. Avoid dumping all Kubernetes Secrets or kubeconfigs into tickets.

## 6. Incident timeline contract

~~~text
Timestamp (UTC):
Evidence source:
Observed user impact:
GitLab pipeline / MR / commit:
Argo CD Application and revision:
Cluster / namespace / Pod:
Action and approver:
Expected result:
Observed result:
Next hypothesis:
~~~

Different systems may have clock skew. Normalize timestamps to UTC and retain source timestamps.

## 7. Hypothesis-driven troubleshooting

For each hypothesis, state expected evidence, falsifying evidence, safe test, mitigation and confidence. Do not conclude that the most recent deployment caused an outage without correlation and mechanism.

## 8. GitLab pipeline failures

Inspect failed stage, runner status, job timeout, cache, image pull, registry auth, protected variable scope, OIDC audience, branch rules, artifact retention and deployment approvals.

A green pipeline does not prove a healthy application. Correlate commit and immutable digest with the running Pod imageID.

## 9. GitLab runner and Kubernetes executor

~~~bash
kubectl -n gitlab-runner get pods -o wide
kubectl -n gitlab-runner get events --sort-by=.lastTimestamp
kubectl -n gitlab-runner describe pods
~~~

Namespace and installation method vary. Check pending Pods, scheduling, image pull, ServiceAccount permissions, job concurrency and node pressure.

## 10. Container artifact integrity

Check registry endpoint, digest, signature, attestation, imagePullSecrets, admission denial and architecture compatibility. Never bypass image signature policy simply to complete a rollout.

## 11. Helm rendering and configuration

~~~bash
helm lint ./chart
helm template demo-api ./chart -f values-staging.yaml > rendered.yaml
kubectl apply --dry-run=client -f rendered.yaml
~~~

Client dry-run does not exercise all server-side admission or resource discovery. Use server-side dry-run in approved staging context when needed.

## 12. Argo CD reconciliation failures

~~~bash
kubectl -n argocd get applications.argoproj.io
kubectl -n argocd get applicationsets.argoproj.io
kubectl -n argocd get appprojects.argoproj.io
kubectl -n argocd get pods
kubectl -n argocd logs deploy/argocd-repo-server --since=20m
~~~

Inspect actual installation topology; application-controller may run as StatefulSet. Distinguish repository access, manifest generation, RBAC, project destination, API connectivity and resource health.

## 13. Argo CD drift and ownership

An OutOfSync status may result from manual edits, defaulted fields, mutating webhooks, non-deterministic templates or shared resource ownership. Compare desired and live manifests before using sync, prune or replace.

Avoid force-sync on stateful resources without a resource-level impact review.

## 14. ApplicationSet blast radius

Check generator input, selectors, merge/matrix expansion, expected Application count, cluster labels and production destination restrictions. Unexpected generated Application deletion can be more dangerous than a failed creation.

Freeze automatic destructive actions and inspect the exact diff before correction.

## 15. Kubernetes Pod lifecycle

~~~bash
kubectl -n demo-staging get pods -o wide
kubectl -n demo-staging describe pod POD_NAME
kubectl -n demo-staging logs POD_NAME --previous --timestamps
kubectl -n demo-staging get deploy demo-api -o yaml
~~~

Pending: scheduling, PVC, quota or admission. ImagePullBackOff: registry/identity/digest. CrashLoopBackOff: process exit, probes, dependencies, configuration or resource pressure.

## 16. Scheduling and autoscaling

Inspect requests/limits, node allocatable, taints/tolerations, affinity, topology spread, HPA metrics, cluster autoscaler/Karpenter and PodDisruptionBudget.

Do not increase limits or node count blindly; identify bottleneck and capacity cost.

## 17. Network and DNS

~~~bash
kubectl -n demo-staging get svc,endpointslices
kubectl -n demo-staging get networkpolicy
kubectl -n kube-system get pods
~~~

Validate DNS resolution, Service selectors, EndpointSlices, ingress/Gateway rules, TLS, CNI enforcement, cloud firewall, NAT and private endpoint access. Kubernetes NetworkPolicy depends on the active dataplane.

## 18. Workload identity and secrets

Distinguish EKS IRSA/Pod Identity, AKS Entra Workload ID and GKE Workload Identity Federation. Verify issuer, audience, subject, scoped IAM and cloud resource permission.

For CSI/External Secrets failures, check controller, SecretStore scope, provider endpoint, KMS, rotation and app reload. Never print live secret contents.

## 19. Stateful workloads and storage

Investigate PVC Pending, CSI mount errors, disk saturation, storage latency, replication lag, backup age and database errors. A storage outage can manifest as API latency or CrashLoopBackOff.

Do not delete PVCs, force-promote databases or forcemerge storage as a generic incident fix.

## 20. Observability triangulation

Use user-facing SLI and synthetic probes for impact, metrics for timing/saturation, logs for error details, traces for dependency latency, audit for actor/change, and Kubernetes events for scheduling and lifecycle.

Correlate with GitLab MR, digest, Argo CD revision and cloud provider changes.

## 21. RCA causal model

~~~text
Triggering event
     |
technical failure mechanism
     |
detection and containment gaps
     |
user-visible impact
     |
mitigation and recovery
     |
systemic contributing conditions
     |
corrective actions and validation
~~~

Separate root causes from contributing factors, detection gaps and recovery delays. A human action alone is not a sufficient technical root cause.

## 22. Corrective actions

Prioritize actions by impact and feasibility: prevent recurrence, reduce blast radius, improve detection, accelerate mitigation, verify rollback and test disaster recovery.

Every action needs an owner, due date, verification method and status.

## 23. Incident communications

Provide concise impact, affected users/regions, mitigation, data-integrity status, next update and current uncertainty. Do not promise an ETA without supporting evidence.

## 24. Post-incident review

Conduct blameless review with timeline, impact metrics, contributing conditions, what worked, what failed and testable follow-ups. Link incident evidence and changes while protecting sensitive data.

## 25. Acceptance criteria

The team must diagnose at least one CI failure, one Argo CD failure, one Kubernetes runtime issue, one identity/network issue and one stateful dependency issue; complete an integrated incident and produce RCA with verified actions.

## 26. Lab A — Incident baseline

1. Inventory staging EKS/AKS/GKE clusters.
2. Verify kube contexts and namespaces.
3. Record GitLab, Argo CD and application revisions.
4. Capture baseline SLI and synthetic checks.
5. Confirm incident roles and test contacts.
6. Archive redacted baseline.

**Pass:** reproducible pre-incident state.

## 27. Lab B — GitLab runner failure

1. Use disposable runner/job fixture.
2. Introduce invalid runner tag.
3. Observe queued job.
4. Inspect runner availability and tags.
5. Correct fixture.
6. Verify successful job and timeline.

**Pass:** scheduler/runner issue distinguished from code failure.

## 28. Lab C — OIDC federation failure

1. Create synthetic protected CI job.
2. Configure deliberately wrong test audience.
3. Observe denied cloud role exchange.
4. Inspect trust claims without logging token.
5. Correct audience.
6. Verify allowed and denied tests.

**Pass:** federation restored without static keys.

## 29. Lab D — Registry digest mismatch

1. Build signed synthetic image.
2. Reference invalid digest in staging.
3. Observe image pull failure.
4. Inspect Pod events and registry.
5. Restore approved digest.
6. Verify running imageID.

**Pass:** artifact mismatch diagnosed.

## 30. Lab E — Helm render error

1. Create disposable chart values.
2. Introduce invalid required value.
3. Run helm lint/template.
4. Capture render error.
5. Correct values.
6. Validate server-side dry-run in staging.

**Pass:** failure found before reconciliation.

## 31. Lab F — Argo CD repo-server outage

1. Use disposable staging Argo CD instance or approved isolated fixture.
2. Simulate unavailable Git source.
3. Observe manifest generation error.
4. Inspect repo-server logs.
5. Restore repository connectivity.
6. Verify reconciliation without force/prune.

**Pass:** repository dependency identified.

## 32. Lab G — AppProject denial

1. Create disposable Application.
2. Set disallowed namespace destination.
3. Observe project rejection.
4. Review AppProject destinations.
5. Correct application target.
6. Verify unauthorized target remains denied.

**Pass:** policy boundary preserved.

## 33. Lab H — ApplicationSet selector error

1. Record expected generated Applications.
2. Apply harmless wrong staging selector.
3. Inspect target count.
4. Prevent deletion/prune.
5. Correct selector.
6. Validate target inventory.

**Pass:** fleet targeting error contained.

## 34. Lab I — Pod CrashLoopBackOff

1. Deploy synthetic process that exits.
2. Observe restart/backoff.
3. Read previous container logs.
4. Inspect probes and resource limits.
5. Correct startup behavior.
6. Verify stable Pod.

**Pass:** lifecycle failure explained.

## 35. Lab J — Pod Pending

1. Create Pod with impossible test node selector.
2. Observe Pending.
3. Inspect scheduler events.
4. Remove invalid constraint.
5. Verify placement.
6. Document scheduling root cause.

**Pass:** no unnecessary node scaling.

## 36. Lab K — DNS/Service failure

1. Deploy synthetic frontend/API.
2. Misconfigure disposable Service selector.
3. Observe missing EndpointSlices.
4. Inspect DNS and service discovery.
5. Correct selector.
6. Verify traffic.

**Pass:** service routing restored.

## 37. Lab L — NetworkPolicy denial

1. Confirm active CNI enforcement.
2. Apply scoped staging egress deny.
3. Observe synthetic API timeout.
4. Verify DNS and endpoint rules.
5. Restore narrowly allowed path.
6. Verify unrelated egress remains denied.

**Pass:** policy root cause proven.

## 38. Lab M — Secret rotation lag

1. Create synthetic provider secret.
2. Mount through supported integration.
3. Rotate secret.
4. Observe stale app read.
5. Trigger approved reload.
6. Verify new version and audit.

**Pass:** provider rotation separated from app reload.

## 39. Lab N — Storage dependency failure

1. Use synthetic stateful workload.
2. Simulate unavailable disposable storage endpoint or test fault.
3. Observe latency/error and Pod events.
4. Correlate app trace and storage metrics.
5. Restore endpoint and verify data.
6. Check backup integrity.

**Pass:** storage incident mitigated without data loss.

## 40. Lab O — Multi-signal correlation

1. Introduce synthetic API latency regression.
2. Record GitLab revision and Argo CD sync.
3. Inspect Prometheus latency/error metrics.
4. Find structured log and trace.
5. Locate dependency bottleneck.
6. Roll back and verify SLO.

**Pass:** causal timeline supported by multiple signals.

## 41. Lab P — Incident communications

1. Declare synthetic SEV2.
2. Assign command and communications roles.
3. Publish impact update.
4. Document hypotheses and uncertainty.
5. Send mitigation update.
6. Close with recovery evidence.

**Pass:** stakeholders receive clear timely information.

## 42. Lab Q — Blameless RCA

1. Collect redacted timeline.
2. State trigger and failure mechanism.
3. Identify contributing conditions.
4. Quantify SLO/error-budget impact.
5. Assign corrective actions.
6. Schedule validation.

**Pass:** RCA is testable, not blame-based.

## 43. Lab R — Integrated failure game day

1. Trigger harmless GitLab runner delay.
2. Introduce staging ApplicationSet target mismatch.
3. Inject app dependency timeout.
4. Triage user impact and change history.
5. Contain fleet promotion and restore.
6. Verify application and data integrity.
7. Publish RCA and scored assessment.

**Pass:** cross-layer investigation completed.

## 44. Troubleshooting — twenty scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Pipeline stuck pending | Runner tags/capacity | Inspect runner |
| 2 | CI OIDC denied | Issuer/audience/subject | Repair trust |
| 3 | Registry auth fails | Scope/expiry | Restore scoped token |
| 4 | ImagePullBackOff | Digest/registry | Verify artifact |
| 5 | Helm render fails | Values/schema | Validate template |
| 6 | Repo-server error | Git auth/network | Inspect logs |
| 7 | Argo CD OutOfSync | Drift/defaulting | Compare diff |
| 8 | ApplicationSet target spike | Generator expansion | Freeze placement |
| 9 | AppProject denies sync | Source/destination | Correct scope |
| 10 | Pod Pending | Scheduling/quota | Inspect events |
| 11 | CrashLoopBackOff | Process/probe | Inspect previous logs |
| 12 | OOMKilled | Memory pressure | Profile workload |
| 13 | Service has no endpoints | Selector/readiness | Fix Service |
| 14 | DNS lookup fails | CoreDNS/egress | Verify resolver |
| 15 | NetworkPolicy blocks API | Egress/ingress | Test policy |
| 16 | Cloud IAM AccessDenied | Workload federation | Correct trust |
| 17 | Secret stale | CSI/reload | Verify rotation |
| 18 | PVC Pending | CSI/storage class | Inspect provisioning |
| 19 | SLO degraded but Pods Ready | Dependency/ingress | Trace user request |
| 20 | Incident repeats | Missing verified action | Improve RCA follow-up |

## 45. Runbook — GitLab pipeline and runner incident

1. Confirm affected project and pipeline.
2. Inspect runner scheduling and job stage.
3. Check registry, cache, artifact and OIDC dependencies.
4. Preserve job logs without exposing variables.
5. Restore approved runner or configuration.
6. Validate protected pipeline and digest.
7. Document incident.

## 46. Runbook — Argo CD reconciliation incident

1. Capture Application, revision, health and sync status.
2. Inspect repo-server, controller and API logs.
3. Verify repository, cluster credentials and AppProject.
4. Compare desired/live manifests and ownership.
5. Correct cause without blind force/prune.
6. Verify sync and user-facing health.
7. Record change timeline.

## 47. Runbook — ApplicationSet fleet placement incident

1. Halt unsafe fleet promotions.
2. Capture generator inputs and cluster labels.
3. Compare expected versus generated Applications.
4. Protect stateful resources from deletion.
5. Restore reviewed inventory/selector.
6. Validate all destinations and cohorts.
7. Record blast radius.

## 48. Runbook — Kubernetes runtime incident

1. Identify affected namespace and workload.
2. Inspect events, Pod state and previous logs.
3. Check scheduling, probes, limits and nodes.
4. Inspect dependency and storage metrics.
5. Apply reversible remediation.
6. Verify synthetic requests and SLO.
7. Preserve evidence.

## 49. Runbook — identity, secrets and network failure

1. Identify cloud provider and workload KSA.
2. Verify federation trust and scoped IAM.
3. Check secret driver, version and reload.
4. Test DNS, NetworkPolicy and private endpoints.
5. Restore least-privilege access.
6. Confirm negative authorization tests still fail.
7. Preserve cloud/Kubernetes audit.

## 50. Runbook — stateful dependency degradation

1. Identify database/storage error and data-integrity risk.
2. Stop destructive automation and risky promotion.
3. Inspect PVC/CSI, latency, replication and backup.
4. Restore safe dependency or failover through approved runbook.
5. Validate data integrity and user requests.
6. Measure RPO/RTO if recovery required.
7. Document contributing conditions.

## 51. Runbook — high-severity incident command

1. Declare severity and assign command roles.
2. Establish timeline, impact and communication cadence.
3. Freeze high-risk changes.
4. Assign parallel investigation streams.
5. Approve reversible mitigation and validate.
6. Publish recovery and data-integrity status.
7. Schedule blameless RCA.

## 52. Runbook — RCA and corrective action verification

1. Collect evidence and normalize timestamps.
2. Quantify customer impact and error-budget consumption.
3. Document causal chain and contributing conditions.
4. Separate prevention, detection and recovery actions.
5. Assign owner, due date and verification test.
6. Run regression/game-day validation.
7. Close only after evidence review.

## 53. RCA template

~~~text
Incident ID and severity:
Start/detection/mitigation/recovery (UTC):
Customer impact, regions and SLI:
GitLab pipeline/MR/commit/digest:
Argo CD Application/ApplicationSet/revision:
Kubernetes workload and events:
Cloud IAM/network/storage dependencies:
Timeline with evidence links:
Trigger:
Technical failure mechanism:
Contributing conditions:
Detection gaps:
Containment and recovery:
Data-integrity verification:
Error budget consumed:
Preventive actions (owner, due, test):
Detection improvements (owner, due, test):
Recovery improvements (owner, due, test):
Reviewer and sign-off:
~~~

## 54. Scored investigation readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| Impact detection and incident command | 15 | SLO and timeline |
| GitLab/Argo CD investigation | 20 | Change correlation |
| Kubernetes/network/identity triage | 20 | Reproducible tests |
| Storage/data safety | 15 | Integrity checks |
| RCA and corrective actions | 20 | Causal evidence |
| Communications and recovery | 10 | Validated updates |
| **Total** | **100** | |

**Pass:** at least 85/100, all mandatory safety controls passed: no unapproved destructive operation, no unverified data restore, no security policy bypass, user-impacting failure detected, evidence preserved and corrective actions testable.

## 55. Final acceptance checklist

- [ ] Incident roles and severity model approved.
- [ ] User-facing SLO impact captured.
- [ ] GitLab pipeline and artifact revision traced.
- [ ] Argo CD and ApplicationSet status investigated.
- [ ] Kubernetes events, logs and workload state captured.
- [ ] DNS, CNI, ingress and cloud network tests completed.
- [ ] Workload identity and secret failures distinguished.
- [ ] Stateful data integrity verified.
- [ ] Metrics, logs, traces and audit correlated.
- [ ] Reversible mitigation and rollback tested.
- [ ] RCA includes technical causal mechanism.
- [ ] Corrective actions have owner, due date and verification.
- [ ] Eighteen hands-on labs completed.
- [ ] Twenty troubleshooting scenarios reviewed.
- [ ] Eight production runbooks validated.
- [ ] Readiness assessment signed off.

## 56. Knowledge check

1. Why should incident investigation begin with user impact?
2. What distinguishes trigger from root failure mechanism?
3. Why can a successful GitLab pipeline coexist with a user outage?
4. What makes ApplicationSet target expansion dangerous?
5. How do you distinguish Pod Pending from CrashLoopBackOff?
6. Why must cloud IAM and network denial be investigated separately?
7. What evidence proves a secret rotation reached an application?
8. Why is force-sync dangerous for stateful resources?
9. How can logs, metrics, traces and audit corroborate a hypothesis?
10. What makes an RCA corrective action verifiable?

## 57. References

- [Kubernetes debugging](https://kubernetes.io/docs/tasks/debug/)
- [Kubernetes events](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_events/)
- [Argo CD troubleshooting](https://argo-cd.readthedocs.io/en/stable/operator-manual/troubleshooting/)
- [Argo CD ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [GitLab CI/CD troubleshooting](https://docs.gitlab.com/ci/)
- [Prometheus](https://prometheus.io/docs/)
- [OpenTelemetry](https://opentelemetry.io/docs/)
- [Google SRE workbook](https://sre.google/workbook/table-of-contents/)

---

**Chapter 088 complete.**

**Next:** Chapter 089 — GitOps Production Incident Response, On-Call Operations and Reliability Game Days.