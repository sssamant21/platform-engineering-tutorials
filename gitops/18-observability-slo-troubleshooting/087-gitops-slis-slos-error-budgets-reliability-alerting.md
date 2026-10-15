# Chapter 087 — GitOps Service-Level Indicators, SLOs, Error Budgets and Reliability Alerting

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 18:** Observability, SLOs and Troubleshooting  
**Chapter:** 087 / 100  
**Audience:** SREs, Platform Engineers, Reliability Engineers, Release Engineers and Incident Commanders

> **Safety:** Use synthetic traffic and staging environments for alert testing and error injection. Do not intentionally degrade production traffic, silence critical pages or halt live deployments without approved change control. SLO targets and release policies are examples; adopt them only after business-owner agreement and baseline measurement.

## 1. Learning outcomes

By the end, you can define user-centric SLIs, construct rolling SLOs, calculate error budgets, write correct PromQL for rates and latency, configure multi-window multi-burn-rate alerts, correlate GitLab and Argo CD changes, implement safe release gates, avoid low-traffic and missing-data pitfalls, and operate incident response from SLO evidence.

## 2. Reliability operating model

~~~text
User journey and business criticality
                 |
          SLI specification
                 |
         approved SLO target
                 |
       error budget + burn rate
                 |
      Prometheus recording rules
                 |
        alerting + SRE routing
                 |
    GitLab/Argo CD release policy
                 |
       rollback / incident RCA
                 |
       monthly SLO review
~~~

Do not equate Kubernetes Pod Ready, Argo CD Healthy or a successful GitLab pipeline with end-user availability.

## 3. SLI versus SLO versus SLA

- **SLI:** a measured indicator such as fraction of eligible requests that succeed.
- **SLO:** a target for an SLI over a specified period, e.g., 99.9% availability over rolling 30 days.
- **SLA:** an externally committed service agreement, potentially with remedies; do not assume internal SLOs are contractual SLAs.
- **Error budget:** allowed amount of bad events/time within the SLO window.

## 4. Define eligible events

A reliable SLI specifies the population, success criteria, excluded traffic, source of truth, label filters, aggregation and missing-data behavior.

For HTTP APIs, classify requests by actual user experience. A 4xx may be a legitimate user error or a service defect; do not universally treat all 4xx as healthy without product agreement.

## 5. Availability math

~~~text
Availability = good eligible events / all eligible events
Error fraction = bad eligible events / all eligible events
Allowed bad events = eligible events * (1 - SLO)
Budget consumed = observed bad events / allowed bad events
Burn rate = observed error fraction / (1 - SLO)
~~~

For 99.9% SLO, error-budget fraction is 0.001. For 1,000,000 eligible requests in the window, 1,000 bad requests exhaust the request-based error budget.

## 6. Time-based versus request-based availability

Time-based availability measures successful intervals; request-based availability measures eligible event success. They answer different questions, especially during zero traffic.

Choose one method deliberately. A service with no requests should not automatically be reported as 100% available if the SLI definition requires active probes.

## 7. Latency SLI

A latency SLI is often the fraction of eligible requests below an agreed threshold. This can be calculated from histogram buckets and total count, provided instrumentation uses a classic histogram with matching label sets.

~~~promql
sum(rate(http_request_duration_seconds_bucket{le="0.5",service="demo-api"}[5m]))
/
clamp_min(sum(rate(http_request_duration_seconds_count{service="demo-api"}[5m])), 0.001)
~~~

Use exact bucket boundary exposed by the instrumented histogram. This expression is illustrative and should be scoped to environment and eligible traffic.

## 8. SLO portfolio

| Layer | SLI | Illustrative objective |
| --- | --- | --- |
| User-facing API | Eligible request success | 99.9% / 30 days |
| User-facing API | Requests under 500 ms | 99% / 30 days |
| GitLab CI | Successful eligible pipelines | 99% / 30 days |
| Argo CD reconciliation | Approved changes reconciled within 10 min | 99% / 30 days |
| Fleet deployment | Healthy cohort by deadline | 99% / 30 days |
| Critical backup | Successful verified restores | 100% of scheduled drills |

Keep product SLOs separate from internal platform SLIs. An application may serve traffic while GitOps reconciliation is unavailable.

## 9. Prometheus metrics contract

~~~text
http_requests_total{service,environment,cluster,status}
http_request_duration_seconds_bucket{service,environment,cluster,le}
gitops_change_reconciled_total{service,environment,result}
gitops_change_reconcile_duration_seconds_bucket{service,environment,le}
synthetic_probe_success{service,region}
~~~

The latter two GitOps metrics are proposed custom instrumentation, not guaranteed Argo CD built-in metrics. Confirm availability before using them.

## 10. PromQL availability recording rules

~~~yaml
groups:
  - name: demo-api-sli
    interval: 30s
    rules:
      - record: demo_api:requests:rate5m
        expr: sum by (environment, cluster) (rate(http_requests_total{service="demo-api"}[5m]))
      - record: demo_api:errors:rate5m
        expr: sum by (environment, cluster) (rate(http_requests_total{service="demo-api",status=~"5.."}[5m]))
      - record: demo_api:error_ratio:rate5m
        expr: |
          demo_api:errors:rate5m
          /
          clamp_min(demo_api:requests:rate5m, 0.001)
~~~

This example counts HTTP 5xx as bad. Add documented eligibility/exclusion rules and low-traffic handling. Rate thresholds and labels must match actual instrumentation.

## 11. Rolling-window SLO

Use a consistent rolling 30-day window or an approved calendar period. Recording-rule retention and query availability must cover the full window.

~~~promql
sum(increase(http_requests_total{service="demo-api",status=~"5.."}[30d]))
/
clamp_min(sum(increase(http_requests_total{service="demo-api"}[30d])), 1)
~~~

A large-range query can be expensive; consider downsampled recording rules and tested SLO tooling for production.

## 12. Error budget worked example

For 99.9% request availability and 2,000,000 eligible events, budget = 2,000 bad events. If 750 eligible bad events occurred, 37.5% of budget is consumed and 1,250 events remain.

Do not compare request-based error budgets to time-based outage minutes without an explicit conversion model.

## 13. Burn rate math

For 99.9% target, 2% bad requests corresponds to burn rate 0.02 / 0.001 = 20. A 14.4x burn over one hour consumes approximately 2% of a 30-day error budget, assuming steady traffic/time-based proportionality in the standard multi-window model.

Burn-rate alerts detect rapid budget consumption; they do not replace immediate outage alerts or dependency-specific paging.

## 14. Multi-window multi-burn-rate design

An illustrative 30-day SLO policy:

| Severity | Burn rate | Long window | Short window |
| --- | ---: | --- | --- |
| Page: fast burn | 14.4x | 1h | 5m |
| Page: sustained burn | 6x | 6h | 30m |
| Ticket: slow burn | 3x | 1d | 2h |
| Ticket: very slow burn | 1x | 3d | 6h |

Choose thresholds based on SLO guidance and service traffic; require both long- and short-window conditions for each tier to reduce false alerts.

## 15. Prometheus fast-burn example

~~~yaml
groups:
  - name: demo-api-slo-burn
    rules:
      - alert: DemoApiFastErrorBudgetBurn
        expr: |
          (
            sum(rate(http_requests_total{service="demo-api",status=~"5.."}[1h]))
            /
            clamp_min(sum(rate(http_requests_total{service="demo-api"}[1h])), 0.001)
          ) > (14.4 * 0.001)
          and
          (
            sum(rate(http_requests_total{service="demo-api",status=~"5.."}[5m]))
            /
            clamp_min(sum(rate(http_requests_total{service="demo-api"}[5m])), 0.001)
          ) > (14.4 * 0.001)
        labels:
          severity: critical
          team: platform-sre
        annotations:
          summary: Demo API consuming error budget rapidly
          runbook_url: https://runbooks.example.internal/demo-api-slo
~~~

Scope by environment/cluster if required. A scalar aggregated across clusters can hide localized failures; implement per-service, per-region and global views.

## 16. Alertmanager routing

Group by alertname, service, environment and region as appropriate. Deduplicate related events while preserving incident severity.

Test notification receiver, escalation, inhibition, maintenance windows and resolved messages. Do not silently drop alerts when a route is misconfigured.

## 17. Missing data is not success

No requests, failed scrape, disconnected cluster or missing exporter can produce empty results. Define explicit no-data alerting and synthetic probes rather than defaulting missing measurements to 100% success.

## 18. Low-traffic services

Use synthetic checks, longer windows and minimum sample counts for sparse traffic. Five bad requests out of ten is statistically different from 5,000 bad requests out of 10,000 in terms of alert stability.

Record denominator thresholds and handle missing data separately.

## 19. Regional and tenant SLOs

Report both global and segmented SLIs. A high-volume healthy region can mask complete failure of a low-volume region.

Use controlled labels to avoid unbounded per-customer cardinality. Tenant-level reporting may require a separate aggregated system.

## 20. SLO-driven release governance

~~~text
GitLab protected MR
        |
policy / signature / test gates
        |
staging canary deployment
        |
SLO and synthetic evaluation
       / \
    pass  fail
      |     |
  wave-2  stop and rollback
      |
production approval
~~~

A release gate must have sufficient observation time and reliable telemetry. An absent SLO measurement must fail closed or require explicit documented human exception.

## 21. GitLab CI gate example

~~~yaml
slo_gate:
  stage: verify
  image: alpine:3.20
  script:
    - test -n "$SLO_GATE_URL"
    - echo "Invoke approved authenticated SLO gate client here"
    - echo "Fail pipeline if SLO gate fails or returns no data"
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

This is a skeleton, not an enforcing gate. Replace the placeholder with a reviewed client that validates TLS/authentication, JSON schema, time window, sample count and explicit pass status; otherwise do not use it for production approval.

## 22. Error-budget policy

Define objective owners, burn thresholds, freeze triggers, exceptions and recovery conditions. A depleted error budget should trigger reliability review and risk reduction, not an unthinking freeze of urgent security or incident fixes.

Use documented exception approvals with expiry and compensating controls.

## 23. SLO dashboard

Show rolling objective, current good/bad eligible events, budget consumed, remaining budget, burn-rate windows, release annotations, regional comparison and runbook links.

Display numerator/denominator and data freshness. A single green percentage without sample count can mislead.

## 24. Incident response

During an SLO alert, identify impacted user journeys, cluster/region, recent GitLab changes, Argo CD state, ingress, application and data dependencies.

Mitigate first, measure recovery, preserve evidence, and follow with RCA and error-budget review.

## 25. Governance and review cadence

Review weekly burn, release impact and false alerts; monthly review objectives, business relevance and recurring reliability investments.

Version SLI definitions and keep an audit trail when exclusions, windows or objectives change.

## 26. Lab A — SLI specification

1. Select synthetic API.
2. Define eligible traffic and success.
3. Identify metric source and labels.
4. Document exclusions.
5. Specify missing-data behavior.
6. Obtain reviewer approval.

**Pass:** SLI definition reproducible.

## 27. Lab B — Request availability

1. Generate 1,000 synthetic requests.
2. Produce known successful/failed counts.
3. Calculate availability manually.
4. Query Prometheus counters.
5. Compare results.
6. Record differences.

**Pass:** measured ratio matches known events.

## 28. Lab C — Error-budget calculation

1. Select 99.9% illustrative target.
2. Calculate budget for synthetic event volume.
3. Inject known bad-event count.
4. Calculate consumption and remainder.
5. Validate dashboard math.
6. Archive evidence.

**Pass:** budget calculation correct.

## 29. Lab D — Latency SLI

1. Instrument classic histogram.
2. Generate fast and slow requests.
3. Query bucket/count ratio.
4. Validate selected 500 ms bucket.
5. Compare with synthetic ground truth.
6. Document limitations.

**Pass:** latency SLI correct.

## 30. Lab E — Rolling window

1. Define approved rolling period.
2. Verify metrics retention.
3. Query increase over sample window.
4. Compare with recorded counters.
5. Inspect reset behavior.
6. Document cost.

**Pass:** window semantics understood.

## 31. Lab F — Fast-burn alert

1. Deploy staging 14.4x multi-window rule.
2. Generate controlled error fraction.
3. Verify both windows exceed threshold.
4. Confirm alert routing.
5. Restore healthy traffic.
6. Confirm resolution.

**Pass:** fast burn pages appropriately.

## 32. Lab G — Slow-burn alert

1. Configure sustained-burn test.
2. Replay synthetic long-window data.
3. Verify alert threshold.
4. Confirm ticket route.
5. Test short-window recovery.
6. Record noise rate.

**Pass:** sustained degradation detected.

## 33. Lab H — Low-traffic handling

1. Simulate sparse requests.
2. Introduce one synthetic error.
3. Inspect ratio instability.
4. Add minimum sample policy.
5. Verify synthetic probe.
6. Document behavior.

**Pass:** low traffic not falsely declared healthy.

## 34. Lab I — Missing telemetry

1. Disable disposable metrics target.
2. Observe absent SLI samples.
3. Trigger no-data alert.
4. Confirm release gate blocks/needs exception.
5. Restore target.
6. Verify data freshness.

**Pass:** missing data cannot pass as success.

## 35. Lab J — Regional segmentation

1. Tag EKS, AKS and GKE staging traffic.
2. Generate errors in one cluster only.
3. Compare global and per-cluster ratios.
4. Verify localized alert.
5. Restore cluster.
6. Document masking risk.

**Pass:** regional outage visible.

## 36. Lab K — GitLab release gate

1. Create protected staging release MR.
2. Invoke reviewed SLO gate client.
3. Test healthy pass response.
4. Test unhealthy fail response.
5. Test missing/invalid response.
6. Verify gate fails closed.

**Pass:** no bypass on missing telemetry.

## 37. Lab L — Argo CD deployment correlation

1. Record GitLab commit and digest.
2. Reconcile staging Application.
3. Annotate dashboard with revision.
4. Trigger synthetic regression.
5. Correlate SLO burn with change.
6. Revert GitOps revision.

**Pass:** deployment impact traceable.

## 38. Lab M — Alertmanager escalation

1. Configure test receiver.
2. Fire staging SLO alert.
3. Verify grouping and route.
4. Simulate unresolved page.
5. Verify escalation.
6. Confirm resolved notification.

**Pass:** incident reaches owner.

## 39. Lab N — Error-budget policy tabletop

1. Present synthetic exhausted budget.
2. Identify freeze/exception rules.
3. Review urgent security fix scenario.
4. Record approvers and compensating controls.
5. Select reliability work.
6. Publish decision.

**Pass:** policy supports informed decisions.

## 40. Lab O — SLO incident capstone

1. Deploy synthetic API on three staging clusters.
2. Generate localized elevated 5xx.
3. Detect multi-window burn.
4. Correlate GitLab and Argo CD changes.
5. Halt promotion and rollback.
6. Verify recovery, budget impact and RCA.

**Pass:** SLO governs incident and release lifecycle.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Availability shows 100% during outage | Missing-data default | Add no-data alert |
| 2 | SLI denominator zero | No traffic | Use synthetic checks |
| 3 | Wrong error fraction | Incorrect status filter | Review eligibility |
| 4 | Counter rate negative/confusing | Reset/misused metric | Use rate/increase |
| 5 | Latency SLI wrong | Bucket mismatch | Inspect histogram |
| 6 | Burn-rate alert too noisy | Single short window | Add long window |
| 7 | Burn-rate alert never fires | Threshold math | Recalculate budget |
| 8 | Regional outage hidden | Global aggregation | Segment by cluster |
| 9 | Alertmanager not paging | Routing mismatch | Test receiver |
| 10 | Duplicate alerts | Grouping/inhibition | Tune routing |
| 11 | Recording rule missing | Config/load error | Validate rules |
| 12 | SLO query slow | Long raw range | Use recordings |
| 13 | CI gate passes on null | Weak client validation | Fail closed |
| 14 | CI gate times out | Telemetry/API outage | Block or exception |
| 15 | Argo CD Healthy but API down | App-only health | Probe user path |
| 16 | Budget calculation disputed | Mixed windows | Align definitions |
| 17 | Pipeline SLO hides failures | Wrong eligible jobs | Define population |
| 18 | Release freeze blocks urgent fix | Rigid policy | Use reviewed exception |

## 42. Runbook — fast error-budget burn

1. Confirm SLI query, numerator, denominator and freshness.
2. Identify affected service, region and user journey.
3. Inspect recent GitLab/Argo CD releases.
4. Halt further risky promotion.
5. Mitigate or rollback approved change.
6. Verify synthetic checks and burn reduction.
7. Record incident and budget consumption.

## 43. Runbook — missing SLO telemetry

1. Verify scrape target, collector and datasource.
2. Check metrics retention and label changes.
3. Confirm no-data alert and release gate behavior.
4. Restore secure telemetry collection.
5. Validate synthetic request counts.
6. Recompute impacted window carefully.
7. Document evidence gap.

## 44. Runbook — false positive or alert storm

1. Confirm real user impact with independent probes.
2. Inspect rule thresholds and sample counts.
3. Check low-traffic and reset behavior.
4. Review Alertmanager grouping and inhibition.
5. Tune rule through protected change.
6. Replay synthetic alert.
7. Record improvement.

## 45. Runbook — SLO-gated release failure

1. Identify GitLab pipeline, environment and artifact digest.
2. Inspect gate response and telemetry freshness.
3. Confirm SLO status and observation window.
4. If unhealthy, halt and mitigate.
5. If telemetry unavailable, fail closed or invoke approved exception.
6. Verify audit trail and release owner approval.
7. Retry only after criteria satisfied.

## 46. Runbook — exhausted error budget

1. Validate rolling-window budget consumption.
2. Identify major contributing incidents.
3. Review release risk and planned changes.
4. Prioritize reliability remediation.
5. Evaluate urgent fixes via documented exception.
6. Set recovery and review milestones.
7. Communicate decisions and owners.

## 47. Runbook — regional SLO regression

1. Compare global and provider/cluster SLOs.
2. Identify impacted region and traffic cohort.
3. Inspect ingress, network, app and dependencies.
4. Confirm release annotations.
5. Restore regional service safely.
6. Verify local and global SLO.
7. Document masking prevention.

## 48. Evidence template

~~~text
Service and SLO owner:
SLI definition and eligible population:
SLO target and rolling window:
Numerator, denominator and data source:
Missing-data and low-traffic handling:
Error budget allowed, consumed, remaining:
Burn rates and alert windows:
GitLab MR, digest and Argo CD revision:
Affected provider/cluster/region:
Synthetic user check:
Alert route and incident timeline:
Release gate outcome and approval:
Mitigation, recovery and RCA:
~~~

## 49. Scored SLO readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| SLI specification and instrumentation | 20 | Correct eligible events |
| SLO and error-budget math | 20 | Reproducible calculations |
| Burn-rate alerting | 20 | Multi-window tests |
| Missing data and regional segmentation | 15 | Negative tests |
| Release governance | 15 | Fail-closed gate |
| Incident runbooks and review | 10 | RCA and ownership |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: missing data treated as healthy, unauthorized production promotion, untested paging, unmeasured user impact or undefined SLO owner.

## 50. Final acceptance checklist

- [ ] SLI eligible events and exclusions documented.
- [ ] Availability and latency ratios verified.
- [ ] Rolling SLO window approved.
- [ ] Error budget calculation independently checked.
- [ ] Burn-rate multi-window rules tested.
- [ ] Alertmanager routing and escalation tested.
- [ ] No-data and low-traffic handling validated.
- [ ] Regional and fleet SLO dashboards available.
- [ ] GitLab and Argo CD revisions correlated.
- [ ] Release gate fails closed.
- [ ] Error-budget policy and exception process approved.
- [ ] Synthetic incident and rollback completed.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Six production runbooks validated.
- [ ] Readiness assessment signed off.

## 51. Knowledge check

1. What makes an SLI different from an SLO?
2. How does request-based availability differ from time-based availability?
3. Why must numerator and denominator use the same eligible traffic?
4. How do you compute error budget for 99.9% over 2 million requests?
5. What does a 14.4x burn rate mean?
6. Why do multi-window alerts reduce false positives?
7. How can no traffic make an SLO misleading?
8. Why should regional SLOs complement a global SLO?
9. What should a release gate do when metrics are missing?
10. When is an error-budget policy exception appropriate?

## 52. References

- [Google SRE workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Google SRE workbook: Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Prometheus query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Prometheus recording rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/)
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Argo CD metrics](https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [OpenTelemetry](https://opentelemetry.io/docs/)

---

**Chapter 087 complete.**

**Next:** Chapter 088 — GitOps Incident Investigation, Root Cause Analysis and Advanced Troubleshooting.