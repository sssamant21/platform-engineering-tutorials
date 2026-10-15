# Chapter 090 — Enterprise GitOps Observability, Incident Response and Reliability Acceptance Capstone

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 18:** Observability, SLOs and Troubleshooting — Final Capstone  
**Chapter:** 090 / 100  
**Audience:** SREs, Platform Engineers, Incident Commanders, Observability Engineers, Release Engineers, Security Responders and DBREs

> **Safety:** Perform all fault injection in isolated staging clusters with synthetic workloads, approved cost limits, blast-radius restrictions, rollback ownership and tested recovery. Never disrupt production traffic, disable live monitoring, delete real PVCs, revoke active credentials or promote a stateful recovery writer without explicit authorization and fencing. Stop immediately if an experiment affects an unapproved service.

## 1. Capstone mission

Prove that an enterprise GitOps platform can detect, investigate, contain, mitigate, recover from and learn from incidents spanning GitLab CI/CD, Argo CD, ApplicationSets, Kubernetes, EKS, AKS and GKE.

The capstone integrates:

- **086:** Observability architecture, metrics, logs and traces.
- **087:** SLIs, SLOs, error budgets and reliability alerting.
- **088:** Investigation, RCA and advanced troubleshooting.
- **089:** Production incident command, on-call and game days.

**Definition of done:** A reviewer can reconstruct an approved deployment and synthetic incident from GitLab commit to running Pod, validate user-facing SLOs, trace the fault through multiple signals, observe correct paging and command, verify safe recovery and confirm corrective actions through repeatable tests.

## 2. Architecture

~~~text
GitLab MR / CI / runner / signed image digest
                   |
              GitOps repository
                   |
       Argo CD / ApplicationSet fleet
              /       |       \
             EKS     AKS      GKE
              |       |        |
         app / ingress / dependency
              |       |        |
        metrics / logs / traces
              \       |       /
          OpenTelemetry / Prometheus
                    |
           Grafana / SLO engine
                    |
        Alertmanager / on-call routing
                    |
      incident command / mitigation
                    |
         GitOps rollback / DR
                    |
        RCA / verified corrective action
~~~

Preserve independent provider-local detection so a centralized telemetry outage cannot blind the entire fleet.

## 3. Required deliverables

| Deliverable | Evidence |
| --- | --- |
| Architecture and inventory | Cluster/provider/service owners |
| GitLab release traceability | MR, pipeline, commit, digest |
| Argo CD reconciliation | App, ApplicationSet, revision, target count |
| Metrics | User-facing RED and infrastructure signals |
| Logs | Structured, redacted, searchable events |
| Traces | Dependency latency and trace correlation |
| SLO | Approved objective, numerator, denominator, budget |
| Alerting | Multi-window burn, no-data, escalation |
| Incident command | UTC timeline, roles, updates, decisions |
| Recovery | Safe rollback, synthetic checks, data validation |
| RCA | Causal mechanism and tested follow-up |
| Acceptance | Signed 100-point scorecard |

## 4. Reference repository

~~~text
gitops-reliability-capstone/
  infrastructure/
    eks/
    aks/
    gke/
  applications/
    demo-api/
      base/
      overlays/
        eks-staging/
        aks-staging/
        gke-staging/
  argocd/
    appprojects/
    applicationsets/
  gitlab/
    pipelines/
    scripts/
  observability/
    otel/
    prometheus/
    dashboards/
    alerts/
    synthetics/
  slos/
    service-catalog.yaml
    sli-definitions.yaml
    budget-policy.md
  experiments/
    runner-failure/
    gitops-drift/
    pod-failure/
    network-denial/
    dependency-latency/
  runbooks/
  evidence/
    incident-timeline.md
    rca.md
    acceptance-report.md
~~~

Do not commit kubeconfigs, CI secrets, cloud tokens, decoded Kubernetes Secrets, Terraform state or sensitive logs.

## 5. Environment prerequisites

- Isolated EKS, AKS and GKE staging environments, or one approved cluster for local labs with other providers simulated.
- GitLab protected branches, runner, image registry and signed synthetic artifact.
- Argo CD, ApplicationSet controller, restricted AppProjects and known-good GitOps revision.
- Metrics backend, dashboards, log backend, trace backend and supported OpenTelemetry Collector.
- Alertmanager or approved alerting provider with test receiver.
- Synthetic API, ingress and disposable downstream dependency.
- User-facing SLI definitions, error-budget policy and no-data behavior.
- On-call contacts, incident commander, escalation owner and communications template.
- Approved rollback and isolated restore procedures.
- Documented fault-injection abort conditions.

## 6. Preflight and evidence capture

~~~bash
kubectl config get-contexts
kubectl config current-context
kubectl -n argocd get applications,applicationsets,appprojects
kubectl -n demo-staging get deploy,pods,svc,endpointslices -o wide
kubectl -n demo-staging get events --sort-by=.lastTimestamp
~~~

Run only against verified staging contexts. Capture GitLab commit, image digest, Argo CD revision and baseline SLI before fault injection.

## 7. Service ownership

~~~yaml
service: demo-api
environment: staging
owner: platform-sre
escalation: sre-oncall
criticality: tier-2
clusters:
  - eks-staging
  - aks-staging
  - gke-staging
dependencies:
  - synthetic-database
  - identity-provider
  - ingress
slo:
  availability: 99.9
  window: 30d
~~~

This is an example service catalog entry, not a Kubernetes CRD. Validate owners and dependencies with the service team.

## 8. Telemetry label contract

~~~yaml
service.name: demo-api
deployment.environment.name: staging
k8s.cluster.name: eks-staging
cloud.provider: aws
cloud.region: us-east-1
team: platform-sre
release: git-sha-placeholder
~~~

Use bounded dimensions. Keep request IDs in logs/traces rather than high-cardinality metric labels.

## 9. Prometheus metrics

~~~promql
sum by (cluster) (rate(http_requests_total{service="demo-api"}[5m]))

sum by (cluster) (rate(http_requests_total{service="demo-api",status=~"5.."}[5m]))

histogram_quantile(
  0.99,
  sum by (le,cluster) (rate(http_request_duration_seconds_bucket{service="demo-api"}[5m]))
)
~~~

These examples assume matching classic histogram/counter names. Verify actual instrumentation, environment scope and eligible request filters.

## 10. OpenTelemetry collector configuration

~~~yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
  batch: {}
exporters:
  otlp:
    endpoint: telemetry-gateway.example.internal:4317
    tls:
      insecure: false
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
~~~

Example only. Supply valid trust roots, scoped credentials and approved collector distribution. Test retry/backpressure without exhausting application resources.

## 11. Structured logs and trace correlation

~~~json
{
  "timestamp": "2026-10-15T10:00:00Z",
  "level": "ERROR",
  "service": "demo-api",
  "cluster": "eks-staging",
  "release": "synthetic-revision",
  "trace_id": "00000000000000000000000000000001",
  "message": "synthetic dependency timeout"
}
~~~

Use real SDK-generated trace IDs in applications. Redact credentials, customer identifiers and protected data.

## 12. SLI specification

~~~text
Good events: eligible HTTP requests completed successfully
Total events: all eligible HTTP requests
Excluded events: explicitly approved health probes and client errors
Source: instrumented application counter
Dimensions: service, environment, cluster, region
Window: rolling 30 days
Missing data: unknown, never assumed healthy
~~~

A 4xx can represent either user error or service fault; agree exclusions with product owners.

## 13. Error-budget math

~~~text
SLO target = 99.9%
Error budget fraction = 0.001
Eligible requests = 1,000,000
Allowed bad requests = 1,000
Observed bad requests = 250
Consumed budget = 25%
Remaining budget = 750 bad requests
~~~

Do not convert request-based budgets directly to outage minutes without a documented traffic model.

## 14. Burn-rate alert

~~~yaml
groups:
  - name: demo-api-slo
    rules:
      - alert: DemoApiFastBurn
        expr: |
          (
            sum(rate(http_requests_total{service="demo-api",status=~"5.."}[1h]))
            /
            clamp_min(sum(rate(http_requests_total{service="demo-api"}[1h])), 0.001)
          ) > 0.0144
          and
          (
            sum(rate(http_requests_total{service="demo-api",status=~"5.."}[5m]))
            /
            clamp_min(sum(rate(http_requests_total{service="demo-api"}[5m])), 0.001)
          ) > 0.0144
        labels:
          severity: critical
          team: platform-sre
        annotations:
          summary: Synthetic API error budget burning rapidly
~~~

This is a 14.4x example for a 99.9% SLO. Add regional grouping, low-traffic thresholds, no-data alerts and runbook URLs in a production implementation.

## 15. SLO release gate

~~~text
Approved GitLab MR
       |
CI tests / provenance / policy
       |
Staging Argo CD canary
       |
SLO + synthetic + data checks
     /   \
   pass  fail/no-data
    |       |
  promote  stop and investigate
~~~

A release gate must not pass when telemetry is missing. Require human approval for documented emergency exceptions.

## 16. Argo CD drift and release evidence

Capture Application sync, health, Git revision, generated ApplicationSet targets and actual Pod imageID. Avoid assuming a successful sync proves user availability.

## 17. Dashboard acceptance

Provide fleet, GitLab, Argo CD, Kubernetes, service RED, SLO budget, synthetic probes, dependency traces, cloud audit and telemetry pipeline health views.

Dashboards must show source freshness, owner, affected environment and runbook.

## 18. Alerting and escalation

Test critical paging, warning tickets, grouping, inhibition, acknowledgement, backup escalation and resolved notifications.

Do not silence broad alert groups to make a game day appear successful.

## 19. Incident command

Assign IC, operations lead, communications lead, scribe, service owner and data/security specialists as needed. Record severity, customer impact, decisions, UTC timestamps and recovery criteria.

## 20. Safe mitigation hierarchy

1. Stop unsafe promotion.
2. Verify impact and latest known-good release.
3. Roll back through reviewed GitOps change.
4. Restore scoped cloud/network/identity dependency.
5. Scale or restart only when evidence supports it.
6. Validate application and data integrity.
7. Resume delivery after SLO recovery and approval.

## 21. Game-day experiment contract

~~~yaml
experiment:
  id: gitops-capstone-090
  environment: staging
  namespace: demo-staging
  hypothesis: bad canary triggers SLO burn and safe rollback
  duration_minutes: 10
  abort_if:
    - impact_outside_approved_scope
    - telemetry_unavailable
    - unexpected_data_integrity_risk
  rollback: restore approved GitOps revision
  owner: platform-sre
  approver: sre-lead
~~~

This is a documentation schema, not a directly executable chaos experiment. Verify actual tooling and admission controls.

## 22. Root cause analysis model

Separate trigger, technical failure mechanism, contributing conditions, detection gaps, mitigation and preventive controls. Tie each corrective action to owner, due date and verification test.

## 23. Data safety

Backups must be application-consistent where required. A snapshot success is not equivalent to a verified restore. If the exercise involves a stateful primary/standby system, explicitly fence the former writer before promotion.

## 24. FinOps and telemetry governance

Measure log ingestion, metric series, trace sampling, cross-cloud egress, storage retention, staging capacity and game-day cost. A reliability design is incomplete without cost and ownership.

## 25. Capstone acceptance

All mandatory controls must pass: customer-impacting regression detected, release traceable, paging reaches an on-call owner, incident command coordinates recovery, no sensitive telemetry leakage, no unauthorized fleet target, data integrity verified and RCA actions tested.

## 26. Lab A — Platform baseline

1. Inventory staging clusters, namespaces and owners.
2. Capture GitLab pipeline and artifact digest.
3. Record Argo CD Application and ApplicationSet revisions.
4. Verify synthetic API health.
5. Capture SLO and alert state.
6. Archive redacted baseline.

**Pass:** initial state reproducible.

## 27. Lab B — GitLab delivery trace

1. Run protected synthetic pipeline.
2. Record commit, MR, job and runner.
3. Build and sign test image.
4. Promote immutable digest through GitOps MR.
5. Confirm running Pod imageID.
6. Link evidence in dashboard.

**Pass:** complete release trace.

## 28. Lab C — Argo CD reconciliation

1. Record expected fleet targets.
2. Reconcile disposable Application.
3. Introduce harmless drift.
4. Observe OutOfSync and logs.
5. Restore desired state.
6. Verify synthetic user request.

**Pass:** drift observable and recoverable.

## 29. Lab D — Prometheus target discovery

1. Expose synthetic /metrics.
2. Configure supported scrape discovery.
3. Verify target Up.
4. Simulate scrape denial.
5. Confirm missing-data detection.
6. Restore scrape.

**Pass:** telemetry loss not masked.

## 30. Lab E — Structured log correlation

1. Generate synthetic API errors.
2. Emit JSON logs with cluster/release.
3. Propagate trace ID.
4. Search log backend.
5. Verify sensitive field redaction.
6. Confirm retention.

**Pass:** searchable safe logs.

## 31. Lab F — Distributed tracing

1. Instrument frontend/API/dependency.
2. Generate slow synthetic dependency.
3. Inspect span tree.
4. Identify slow span.
5. Correlate with logs and metrics.
6. Verify sampling behavior.

**Pass:** dependency cause observable.

## 32. Lab G — SLI and error budget

1. Define eligible events.
2. Generate known good/bad counts.
3. Query Prometheus.
4. Calculate 99.9% example budget.
5. Compare manual and dashboard values.
6. Document missing-data behavior.

**Pass:** SLI math verified.

## 33. Lab H — Multi-window burn alert

1. Configure staging 14.4x rule.
2. Generate controlled 5xx.
3. Confirm both windows breach.
4. Verify critical page.
5. Restore service.
6. Confirm alert resolution.

**Pass:** fast burn detected.

## 34. Lab I — Regional SLO masking

1. Generate healthy traffic in two clusters.
2. Degrade one staging cluster.
3. Compare global and regional SLIs.
4. Confirm regional alert.
5. Restore service.
6. Document masking risk.

**Pass:** local outage visible.

## 35. Lab J — GitLab release gate

1. Run approved SLO gate client.
2. Test healthy pass.
3. Test unhealthy fail.
4. Test missing metrics fail.
5. Verify manual exception requires approval.
6. Archive gate evidence.

**Pass:** no false success.

## 36. Lab K — Alert escalation

1. Fire synthetic alert.
2. Confirm primary receiver.
3. Test backup escalation.
4. Record acknowledgement.
5. Restore condition.
6. Verify resolved notification.

**Pass:** on-call route tested.

## 37. Lab L — Pod failure investigation

1. Deploy synthetic crash-loop workload.
2. Inspect Pod events and previous logs.
3. Correlate restarts with SLI.
4. Identify process failure.
5. Restore known-good config.
6. Verify stable service.

**Pass:** root cause evidenced.

## 38. Lab M — Network/identity failure

1. Use disposable synthetic cloud resource.
2. Trigger scoped IAM or NetworkPolicy denial.
3. Observe app failure.
4. Inspect audit and network signals.
5. Restore least privilege.
6. Verify negative access remains denied.

**Pass:** security preserved during recovery.

## 39. Lab N — ApplicationSet fleet anomaly

1. Record expected targets.
2. Introduce wrong staging selector.
3. Detect unexpected generated count.
4. Freeze destructive actions.
5. Correct reviewed selector.
6. Verify no unauthorized target.

**Pass:** fleet blast radius contained.

## 40. Lab O — Telemetry pipeline failure

1. Simulate central collector export outage.
2. Confirm provider-local alerts remain active.
3. Inspect collector queues and TLS.
4. Restore secure export.
5. Generate synthetic event.
6. Document missing-data interval.

**Pass:** telemetry resilient.

## 41. Lab P — Incident command exercise

1. Declare synthetic SEV2.
2. Assign IC, operations, communications and scribe.
3. Publish verified impact update.
4. Log hypotheses and decisions.
5. Validate mitigation and recovery.
6. Publish final update.

**Pass:** command and communications coherent.

## 42. Lab Q — RCA and regression verification

1. Build UTC incident timeline.
2. Identify trigger and technical mechanism.
3. Quantify SLO/error-budget impact.
4. Assign preventive and detection actions.
5. Re-run fault after fix.
6. Record reviewer approval.

**Pass:** action verified.

## 43. Lab R — Integrated reliability acceptance

1. Deploy signed synthetic release through GitLab.
2. Introduce staging ApplicationSet targeting mistake.
3. Inject API dependency latency.
4. Detect SLO burn and page on-call.
5. Declare incident, contain rollout and diagnose.
6. Roll back via reviewed GitOps change.
7. Verify user checks, data integrity and RCA.

**Pass:** end-to-end operational reliability demonstrated.

## 44. Troubleshooting — twenty scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Pipeline not running | Runner tags/availability | Inspect scheduling |
| 2 | CI OIDC rejected | Trust/audience | Correct federation |
| 3 | Signed image unavailable | Registry/digest | Restore artifact |
| 4 | Argo CD manifest error | Repo/Helm | Inspect repo-server |
| 5 | ApplicationSet target spike | Generator expansion | Freeze destructive sync |
| 6 | AppProject denies target | Scope restriction | Correct destination |
| 7 | Pod Pending | Scheduling/quota | Inspect events |
| 8 | CrashLoopBackOff | Process/probe | Inspect previous logs |
| 9 | Metrics target Down | Scrape/network | Restore discovery |
| 10 | Collector OOM | Unbounded queue | Bound resources |
| 11 | Trace gaps | Propagation/sampling | Fix instrumentation |
| 12 | Logs contain sensitive data | Redaction failure | Contain and rotate |
| 13 | SLO shows green during outage | Missing data | Alert no-data |
| 14 | Burn alert never fires | Query/window | Validate rule |
| 15 | Regional outage hidden | Aggregation | Segment SLI |
| 16 | Alert never pages | Routing failure | Test escalation |
| 17 | NetworkPolicy denies app | Egress rule | Restore narrow allow |
| 18 | Cloud IAM denied | Workload identity | Repair scoped trust |
| 19 | Rollback appears successful but API fails | Dependency/data | Validate user flow |
| 20 | RCA action not effective | Untested remediation | Re-run game day |

## 45. Runbook — GitLab and artifact incident

1. Identify pipeline, runner, commit and artifact digest.
2. Inspect job failure and registry dependency.
3. Check OIDC trust and signature validation.
4. Halt risky promotion.
5. Restore scoped CI/registry access.
6. Verify protected pipeline and running digest.
7. Record evidence.

## 46. Runbook — Argo CD and ApplicationSet incident

1. Capture Application, revision and expected target count.
2. Inspect repo-server/controller logs and cluster connectivity.
3. Compare desired/live state.
4. Freeze unsafe prune/force operations.
5. Restore reviewed inventory and GitOps revision.
6. Verify workload health and SLO.
7. Record blast radius.

## 47. Runbook — missing telemetry

1. Identify affected metrics/logs/traces and clusters.
2. Verify local critical alerting remains operational.
3. Inspect collectors, scrape targets, queues and TLS.
4. Restore secure collection.
5. Generate synthetic verification event.
6. Assess missing-data impact on release gates.
7. Document gap.

## 48. Runbook — fast SLO burn

1. Validate eligible event counts and data freshness.
2. Identify affected service, cluster and region.
3. Correlate GitLab and Argo CD release.
4. Halt unsafe promotion.
5. Roll back or mitigate through approved path.
6. Verify synthetic recovery and budget consumption.
7. Record incident.

## 49. Runbook — Kubernetes service outage

1. Confirm user impact.
2. Inspect Pods, nodes, events, ingress and endpoints.
3. Correlate logs, traces and metrics.
4. Check identity, network, secrets and storage.
5. Apply reversible mitigation.
6. Validate app and data integrity.
7. Preserve evidence.

## 50. Runbook — incident command

1. Declare severity and assign IC.
2. Identify operations, communications and scribe.
3. Establish UTC timeline and update cadence.
4. Record hypotheses, decisions and approvals.
5. Contain, mitigate and validate.
6. Publish recovery update.
7. Schedule review.

## 51. Runbook — RCA and corrective action

1. Collect redacted evidence and normalize time.
2. Quantify customer impact and SLO.
3. Document technical causal mechanism.
4. Identify prevention, detection and recovery gaps.
5. Assign owners and due dates.
6. Validate actions with repeatable tests.
7. Close only with evidence.

## 52. Runbook — reliability game-day execution

1. Verify approval, environment and abort conditions.
2. Capture baseline and confirm telemetry.
3. Inject one bounded synthetic fault.
4. Observe detection, paging and response.
5. Abort if safety boundary breached.
6. Restore service and verify data.
7. Record score, costs and improvements.

## 53. Incident evidence template

~~~text
Incident ID / severity:
Incident commander:
Start, detection, mitigation, recovery UTC:
Service, provider, cluster, region:
Customer impact and SLI:
SLO target, eligible events and error budget:
GitLab MR/pipeline/commit/digest:
Argo CD Application/ApplicationSet/revision:
Metrics, logs, trace and audit evidence:
Alert route, acknowledgement and escalation:
Mitigation, approver and rollback:
Data-integrity verification:
Root failure mechanism:
Corrective actions, owners and tests:
Final score and sign-off:
~~~

## 54. Acceptance score — 100 points

| Domain | Points | Required evidence |
| --- | ---: | --- |
| Telemetry architecture and security | 15 | Metrics/logs/traces |
| GitLab and Argo CD correlation | 15 | Release trace |
| SLI, SLO and error-budget accuracy | 20 | Calculations and dashboards |
| Alerting and on-call escalation | 15 | Synthetic page |
| Investigation and incident command | 15 | Timeline and RCA |
| Safe mitigation and data validation | 10 | Rollback and integrity |
| Game-day follow-up and FinOps | 10 | Verified actions and cost |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: unapproved destructive action, telemetry missing treated as healthy, alert fails to reach an owner, unauthorized fleet placement, sensitive telemetry leak, unsafe data promotion or recovery not verified by user-facing checks.

## 55. Final acceptance checklist

- [ ] GitLab, Argo CD and Kubernetes telemetry inventoried.
- [ ] Metrics, logs and traces correlated with release.
- [ ] Service owner and escalation documented.
- [ ] SLI and SLO definitions independently validated.
- [ ] Error-budget and burn-rate alerts tested.
- [ ] Missing-data and regional masking detected.
- [ ] Protected release gate fails closed.
- [ ] ApplicationSet target safety validated.
- [ ] Incident command and communications rehearsed.
- [ ] Kubernetes and cloud dependency failures diagnosed.
- [ ] Safe GitOps rollback verified.
- [ ] Application and data integrity confirmed.
- [ ] RCA actions re-tested.
- [ ] Eighteen hands-on labs completed.
- [ ] Twenty troubleshooting scenarios reviewed.
- [ ] Eight production runbooks validated.
- [ ] 100-point assessment signed off.

## 56. Knowledge check

1. Why is a healthy Argo CD sync insufficient to declare user availability?
2. What telemetry labels should be standardized across cloud providers?
3. How do you verify the SLI numerator and denominator?
4. Why should missing metrics block an automated release gate?
5. What does multi-window burn-rate alerting add over static thresholds?
6. How do you correlate a GitLab commit with a slow distributed request?
7. Why must an ApplicationSet incident be checked for unexpected target expansion?
8. What decisions should an incident commander own?
9. Why should RCA actions be tested through another fault injection?
10. What evidence is required before signing off operational readiness?

## 57. Official references

- [OpenTelemetry](https://opentelemetry.io/docs/)
- [Prometheus](https://prometheus.io/docs/)
- [Prometheus alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana](https://grafana.com/docs/grafana/latest/)
- [Google SRE workbook](https://sre.google/workbook/table-of-contents/)
- [Google SRE: Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Argo CD monitoring](https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/)
- [Argo CD troubleshooting](https://argo-cd.readthedocs.io/en/stable/operator-manual/troubleshooting/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [Kubernetes debugging](https://kubernetes.io/docs/tasks/debug/)

---

**Chapter 090 complete — Part 18: Observability, SLOs and Troubleshooting complete (086–090).**

**Next:** Chapter 091 — Enterprise GitOps Reliability Engineering, High Availability and Resilience Architecture, beginning Part 19.