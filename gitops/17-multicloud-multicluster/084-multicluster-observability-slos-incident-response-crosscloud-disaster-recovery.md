# Chapter 084 — Multi-Cluster Observability, SLOs, Incident Response and Cross-Cloud Disaster Recovery

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 17:** Multi-Cloud and Multi-Cluster GitOps  
**Chapter:** 084 / 100  
**Audience:** SREs, Platform Engineers, DBREs, Observability Engineers, Incident Commanders and Disaster Recovery Leads

> **Safety:** Run all experiments in isolated EKS, AKS and GKE staging clusters with synthetic data and preapproved cost limits. Do not disrupt production routing, fail over live databases, delete volumes, disable audit collection or execute destructive chaos tests without a change plan. Recovery is complete only after application and data integrity checks.

## 1. Learning objectives

1. Design an observability architecture spanning EKS, AKS and GKE.
2. Normalize cluster, cloud, region, tenant, environment and service identities.
3. Implement metrics, logs, traces, audit and synthetic probes.
4. Define SLIs, SLOs, error budgets and multi-window burn alerts.
5. Detect GitOps reconciliation, fleet rollout and dependency failures.
6. Correlate cloud events, Kubernetes events, Argo CD and GitLab releases.
7. Design cross-cloud failure domains and recovery dependency graphs.
8. Establish application-specific RPO and RTO.
9. Execute backup validation, failover, failback and incident communications.
10. Demonstrate operational acceptance with measured evidence.

## 2. Reference architecture

~~~text
GitLab protected MR -> Argo CD fleet controllers
                               |
                    EKS / AKS / GKE
                     /     |     \
               Metrics   Logs   Traces
                  |       |       |
             OTel collectors / approved agents
                       |
             Per-cloud telemetry storage
                       |
           Federated query / SLO dashboards
                       |
          Alert routing / incident commander
                       |
              Runbooks / DR automation
                       |
       Recovery cluster + verified data restore
                       |
          DNS/traffic shift + validation
~~~

Use provider-native integrations where they fit: CloudWatch/CloudTrail for AWS, Azure Monitor/Activity Logs for Azure, and Cloud Monitoring/Cloud Audit Logs for Google Cloud. A common observability interface does not require sending all raw data to one region.

## 3. Signals and ownership

| Signal | Primary question | Typical source |
| --- | --- | --- |
| Metrics | Is user experience degrading? | Prometheus, cloud monitoring |
| Logs | What event or error occurred? | App, ingress, control plane |
| Traces | Which dependency caused latency? | OpenTelemetry |
| Audit | Who changed access or configuration? | Cloud and Kubernetes audit |
| Events | Why did a workload fail to schedule? | Kubernetes events |
| GitOps | Is desired state reconciled? | Argo CD metrics/status |
| Synthetic | Can a user complete the critical flow? | Probes from approved regions |
| Backup | Is a recent recoverable copy available? | Backup jobs and restore tests |

Define retention, access, encryption, data residency, incident ownership and cost limits for each signal.

## 4. Canonical telemetry labels

~~~yaml
service: demo-api
environment: staging
cluster_id: eks-staging-us-east-1
provider: aws
region: us-east-1
namespace: demo-staging
team: platform-sre
release: git-sha-placeholder
~~~

Avoid placing user identifiers, tokens or secrets in labels. Control cardinality: Pod UID, request ID and customer ID should generally not be unbounded metric labels.

## 5. OpenTelemetry collection strategy

Deploy an approved OpenTelemetry Collector topology (DaemonSet, gateway or sidecar as appropriate) with bounded memory, retry/backoff, batching, authentication and TLS.

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

This is an illustrative collector configuration. The actual collector distribution and exporter support must be verified; configure certificates and credentials using approved secret delivery.

## 6. Metrics federation and availability

Keep critical monitoring operational within each cloud failure domain. Central dashboards may federate selected metrics, but avoid a single global metrics backend becoming the only incident detection path.

Use local alerting for cluster isolation, storage failures and regional outages, with independent notification routes.

## 7. Prometheus service discovery

Use supported Prometheus Operator ServiceMonitor/PodMonitor CRDs or native managed collectors as installed. Verify actual CRD versions before applying manifests.

~~~yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: demo-api
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [demo-staging]
  selector:
    matchLabels:
      observability: demo-api
  endpoints:
    - port: metrics
      interval: 30s
~~~

The target Service must expose a named metrics port and match the selector. NetworkPolicy must allow scrape traffic.

## 8. Logs and audit

Collect app, ingress/Gateway, node, control plane and GitOps logs. Maintain immutable or appropriately protected audit evidence for identity, cluster access, CI and release actions.

CloudTrail, Azure Activity Logs and Google Cloud Audit Logs cover different APIs and have different enablement/retention behavior. Verify Kubernetes audit collection separately.

## 9. Distributed tracing

Instrument request entrypoints, database calls, queues and external dependencies. Propagate W3C trace context through services; sample according to traffic and error requirements.

A trace crossing cloud boundaries may incur network egress and residency implications. Do not export sensitive request bodies or credentials.

## 10. Service-level indicators

Use user-facing measures rather than controller status alone.

~~~text
Availability SLI =
  successful eligible requests / all eligible requests

Latency SLI =
  requests below threshold / all eligible requests

Error budget =
  1 - SLO target
~~~

Exclude only documented non-user-impacting events. For example, 99.9% monthly availability corresponds to about 43.2 minutes of error budget in a 30-day month.

## 11. Example SLO contract

| Service | SLI | Illustrative objective |
| --- | --- | --- |
| Public API | Successful requests | 99.9% over rolling 30 days |
| API latency | Requests under 500 ms | 99% over rolling 30 days |
| Fleet promotion | Healthy deployments by deadline | 99% over rolling 30 days |
| GitOps convergence | Approved changes reconciled | 99% within 10 minutes |
| Backup recoverability | Verified restore drills | 100% of scheduled tests |

Targets require owner approval and measured baselines. A global SLO should not mask a severe outage for a smaller tenant or region.

## 12. Multi-window burn-rate alerts

For a 99.9% SLO, the permitted error fraction is 0.001. Burn rate is observed error fraction divided by 0.001.

~~~promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total[5m])), 1)
~~~

This query is a starting-point error fraction, not a complete burn-rate alert. Scope it by service/environment and exclude ineligible traffic; combine short and long windows with approved thresholds.

## 13. Fleet and GitOps SLIs

Measure Argo CD reconciliation errors, Application OutOfSync age, sync duration, cluster API connectivity, generated Application count, promotion wave duration and rollback time.

Use application health checks and synthetic probes to prevent false confidence from a successful Argo CD sync.

## 14. Dashboard design

Create views for executive SLO, provider comparison, cluster health, namespace workload health, ingress and DNS, data dependencies, GitOps deployment timeline and backup recovery readiness.

Every dashboard should identify owner, source, update interval, known blind spots and links to runbooks.

## 15. Alert routing

Route alerts by service owner and severity. Deduplicate related provider, cluster, ingress and workload alerts to avoid alert storms. Page on user-impacting error budget burn and high-confidence recovery blockers.

Provide alert context: cluster ID, provider, region, service, SLO, last deployment, runbook, incident channel and dashboard.

## 16. Dependency mapping

~~~text
User DNS / traffic manager
        |
   regional ingress
        |
  app Pods / identity
        |
  database / cache / queue
        |
  storage / backup / KMS
        |
  CI/GitOps / artifact registry
~~~

A recovery cluster without database, keys, secrets, DNS and registry is not a usable disaster recovery environment.

## 17. Cross-cloud DR patterns

| Pattern | Advantages | Limitations |
| --- | --- | --- |
| Backup and restore | Lower standby cost | Longer RTO, backup age |
| Warm standby | Faster recovery | Ongoing capacity cost |
| Active-passive replication | Reduced RPO | Failover fencing complexity |
| Active-active | Potential continuity | Conflict resolution, consistency, cost |

Do not equate multi-cloud application replicas with multi-cloud database replication. Stateful replication semantics must be designed and tested separately.

## 18. RPO, RTO and recovery validation

RPO measures acceptable data loss; RTO measures acceptable service restoration time. Record incident start, last recoverable data timestamp, restore completion, application integrity validation and traffic cutover.

A snapshot may be crash-consistent rather than application-consistent. Use database-native backups, WAL/binlog/oplog or approved replication as appropriate.

## 19. Data integrity and split-brain

For active-passive stateful systems, fence the old writer before promoting a new writer. Validate replication lag, transaction durability, backup consistency and idempotent replay.

Never promote two writable primaries simply to restore availability. Prefer controlled failover and documented reconciliation over silent data divergence.

## 20. Traffic failover

DNS, global load balancing and traffic management require independent health checks and TTL/propagation planning. Some clients cache DNS longer than expected.

Verify certificates, firewall, routes, identity, session state, regional allowlists and synthetic user journeys before declaring cutover complete.

## 21. GitOps and recovery bootstrap

Document how to provision replacement clusters from Terraform, restore Argo CD controllers/AppProjects, recover repository credentials and re-register clusters with least-privilege access.

Disable unreviewed automated pruning during DR bootstrap. Review desired state against actual restored data and resource ownership.

## 22. Backup strategy

Specify data classification, frequency, retention, immutable/offsite copy, encryption keys, IAM, regional availability, restore order and regular rehearsal.

Protect backup credentials from primary-cluster compromise. Measure backup age and restore success rather than treating a successful scheduled job as proof of recoverability.

## 23. Incident command

Assign incident commander, communications lead, operations lead, data recovery lead and security lead. Track severity, scope, start time, mitigation, decisions, change approvals, customer impact and next update.

Use a shared timeline across cloud providers. Separate infrastructure recovery from service validation and data consistency.

## 24. Recovery decision matrix

| Failure | Immediate priority | Recovery path |
| --- | --- | --- |
| One Pod/node | Local workload recovery | Scheduler/autoscaler |
| One zone | Preserve regional SLO | Multi-zone capacity |
| One cluster | Shift approved workload | Alternate cluster |
| One cloud region | Restore service dependencies | DR region/cloud |
| Central GitOps outage | Freeze changes | Restore controller |
| Data corruption | Stop writes, preserve evidence | Verified backup |
| Identity outage | Scoped trust restoration | Approved break-glass |
| Telemetry outage | Maintain local alerts | Restore collection |

## 25. Cost and resilience tradeoffs

Track duplicated standby capacity, cross-cloud egress, logging ingestion, tracing sampling, backup storage, registry replication, DNS traffic management and DR drill cost.

A lower RTO usually requires more pre-provisioned resources and operational complexity. Quantify the business benefit rather than assuming active-active is always superior.

## 26. Lab A — Telemetry baseline

1. Inventory staging EKS, AKS and GKE.
2. Record metrics, logs, traces and audit sources.
3. Identify collection gaps.
4. Verify telemetry labels and owners.
5. Confirm retention and access.
6. Archive redacted baseline.

**Pass:** signal coverage is documented.

## 27. Lab B — OpenTelemetry collector

1. Deploy supported collector in staging.
2. Configure synthetic OTLP receiver.
3. Set memory limiter and batch processor.
4. Export to approved endpoint with TLS.
5. Generate synthetic traces.
6. Verify backpressure and retry behavior.

**Pass:** traces arrive without leaking secrets.

## 28. Lab C — Prometheus metrics

1. Expose synthetic app metrics.
2. Create supported ServiceMonitor or collector config.
3. Verify target discovery.
4. Inspect rate and error metrics.
5. Simulate scrape denial.
6. Restore NetworkPolicy and confirm collection.

**Pass:** metrics collection is reliable.

## 29. Lab D — Cloud audit correlation

1. Generate approved IAM change in each provider.
2. Generate denied Kubernetes API action.
3. Locate cloud and cluster audit events.
4. Normalize principal and cluster labels.
5. Correlate with change ID.
6. Verify retention and access.

**Pass:** security changes are attributable.

## 30. Lab E — Distributed tracing

1. Instrument synthetic frontend and API.
2. Propagate W3C trace context.
3. Generate slow downstream dependency.
4. Locate span latency.
5. Confirm redaction.
6. Review sampling and egress cost.

**Pass:** dependency latency is traceable.

## 31. Lab F — Availability SLO

1. Define eligible requests and exclusions.
2. Record successful/total counters.
3. Calculate rolling availability.
4. Compare to 99.9% illustrative target.
5. Verify dashboard query.
6. Document owner approval.

**Pass:** SLI matches user experience.

## 32. Lab G — Burn-rate alert

1. Create staging SLO alert.
2. Configure short and long windows.
3. Generate synthetic 5xx responses.
4. Verify alert firing and routing.
5. Recover workload.
6. Verify resolution and deduplication.

**Pass:** user impact triggers actionable paging.

## 33. Lab H — GitOps observability

1. Record Argo CD Application state.
2. Introduce harmless drift.
3. Measure OutOfSync age.
4. Trigger reviewed reconciliation.
5. Verify service synthetic check.
6. Correlate GitLab MR and revision.

**Pass:** GitOps and application health are correlated.

## 34. Lab I — Multi-cluster synthetic checks

1. Deploy synthetic API in three staging clusters.
2. Probe each approved endpoint independently.
3. Tag results by provider/region.
4. Simulate one endpoint failure.
5. Confirm localized alert.
6. Verify unaffected endpoints remain healthy.

**Pass:** regional failure is not hidden by global aggregate.

## 35. Lab J — Backup recoverability

1. Create synthetic stateful dataset.
2. Take application-consistent backup.
3. Record checksum and recovery point.
4. Restore into isolated namespace.
5. Validate application semantics.
6. Measure RPO/RTO.

**Pass:** restore works, not merely backup creation.

## 36. Lab K — Recovery cluster bootstrap

1. Provision disposable alternate-cluster infrastructure.
2. Restore approved cloud IAM and private networking.
3. Bootstrap Argo CD and restricted AppProjects.
4. Restore signed image and secret dependencies.
5. Deploy synthetic application.
6. Verify audit and telemetry.

**Pass:** replacement cluster is reproducible.

## 37. Lab L — Controlled failover

1. Identify primary and recovery endpoints.
2. Verify recovery data freshness.
3. Fence synthetic primary writer.
4. Promote recovery writer using approved procedure.
5. Shift synthetic traffic.
6. Validate integrity, TLS and user journey.

**Pass:** no split-brain and measured RTO.

## 38. Lab M — Failback rehearsal

1. Confirm original environment recovered.
2. Validate data reconciliation and ownership.
3. Establish safe replication direction.
4. Fence old recovery writer before role change.
5. Return synthetic traffic in approved window.
6. Verify data and SLO.

**Pass:** failback avoids divergent writes.

## 39. Lab N — Telemetry outage

1. Simulate one central dashboard unavailable.
2. Verify provider-local alerts remain operational.
3. Inspect collector queues and failures.
4. Restore aggregation path.
5. Verify missing-data detection.
6. Record observability RTO.

**Pass:** one monitoring backend failure does not blind all clusters.

## 40. Lab O — Multi-cloud incident capstone

1. Inject synthetic regional ingress failure.
2. Simulate stale GitOps reconciliation and delayed backup.
3. Declare incident and assign roles.
4. Correlate metrics, logs, traces, audit and Git revision.
5. Restore service through approved DR path.
6. Measure SLO, RPO/RTO, cost and RCA.

**Pass:** recovery is observable, data-safe and documented.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Metrics absent | Scrape/discovery | Inspect target |
| 2 | Metrics cardinality spikes | Unbounded labels | Remove high-cardinality labels |
| 3 | Collector OOM | Batch/queue limits | Tune memory |
| 4 | Trace gaps | Sampling/propagation | Repair context |
| 5 | Logs delayed | Export/ingestion | Check pipeline |
| 6 | Audit events missing | Disabled category/sink | Restore logging |
| 7 | SLO reports false healthy | Wrong denominator | Correct SLI |
| 8 | Alert storm | Missing grouping | Tune routing |
| 9 | Burn alert never fires | Wrong windows/thresholds | Test rule |
| 10 | Cluster health unknown | API/network | Restore access |
| 11 | Argo CD drift hidden | Ignore rule/ownership | Review diff |
| 12 | Recovery image unavailable | Registry dependency | Restore artifact |
| 13 | Backup restore fails | IAM/KMS/format | Repair dependencies |
| 14 | Recovery data stale | Backup/replication lag | Choose valid point |
| 15 | Two writers active | Missing fencing | Stop writes immediately |
| 16 | DNS cutover incomplete | TTL/client cache | Validate routing |
| 17 | Secret missing in DR | Provider identity | Restore scoped trust |
| 18 | Failback data divergence | Unsafe replication direction | Reconcile before cutover |

## 42. Runbook — multi-cluster SLO degradation

1. Confirm user-facing impact and affected cohorts.
2. Segment by provider, region and service.
3. Correlate last GitLab/Argo CD change.
4. Inspect ingress, Pods, nodes and dependencies.
5. Halt risky promotions and mitigate safely.
6. Verify synthetic checks and error-budget recovery.
7. Record RCA and action items.

## 43. Runbook — observability pipeline outage

1. Determine which metrics, logs, traces or audits are missing.
2. Check collectors, queues, authentication and endpoints.
3. Confirm provider-local alerts remain functional.
4. Restore secure collection and bounded resource use.
5. Generate synthetic event and verify ingestion.
6. Assess evidence gap and retention impact.
7. Document prevention.

## 44. Runbook — GitOps fleet incident

1. Freeze affected promotions.
2. Capture ApplicationSet targets and Application revisions.
3. Verify remote cluster API and credentials.
4. Review drift, controller ownership and prune risks.
5. Restore approved GitOps revision.
6. Validate application SLO and data integrity.
7. Archive timeline.

## 45. Runbook — backup/restore failure

1. Identify dataset, backup timestamp and encryption dependencies.
2. Stop destructive remediation and preserve source evidence.
3. Verify backup catalog, IAM, KMS and storage accessibility.
4. Restore to isolated environment.
5. Validate checksum and application consistency.
6. Calculate actual RPO/RTO.
7. Update backup controls.

## 46. Runbook — cross-cloud regional failover

1. Declare DR and obtain authorized incident command approval.
2. Confirm failure domain and recovery dependency readiness.
3. Fence primary writer where stateful workloads require it.
4. Restore/promote data using verified recovery point.
5. Bootstrap or validate recovery cluster and GitOps.
6. Shift traffic with health checks and TLS verification.
7. Validate user journey, data integrity, RPO/RTO and audit.
8. Publish incident update and preserve evidence.

## 47. Runbook — controlled failback

1. Confirm original region health and approved window.
2. Reconcile stateful data and select authoritative writer.
3. Establish replication in correct direction.
4. Fence old writer before changing roles.
5. Shift traffic gradually with SLO checks.
6. Verify no split-brain, backlog or data divergence.
7. Close incident with documented recovery measurements.

## 48. Evidence template

~~~text
Incident/change ID:
Provider, region, cluster, environment:
Service and owner:
GitLab MR / image digest / Argo CD revision:
Metrics, logs, traces and audit sources:
SLI numerator, denominator, objective:
Error budget and alert timestamps:
Affected dependencies and failure domain:
Backup recovery point and integrity checksum:
Writer fencing and failover decision:
Traffic shift and certificate validation:
Measured RPO, RTO and user SLO:
Cost, communication timeline and approvals:
RCA and preventive action owner:
~~~

Never include secret values, bearer tokens, privileged kubeconfigs or private keys.

## 49. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| Metrics, logs, traces and audit | 20 | Coverage and correlation |
| SLIs, SLOs and actionable alerts | 20 | Burn-rate tests |
| Fleet and GitOps observability | 15 | Drift and release tracing |
| Backup and data integrity | 20 | Isolated verified restore |
| Failover and failback | 15 | Fencing, RPO/RTO |
| Incident command and FinOps | 10 | Timeline, approvals, cost |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: undetected user outage, missing required audit evidence, unverified data restore, concurrent writable primaries, failed recovery dependencies or unapproved traffic cutover.

## 50. Final acceptance checklist

- [ ] EKS, AKS and GKE telemetry sources inventoried.
- [ ] Metrics, logs, traces and audit correlation tested.
- [ ] High-cardinality metric labels controlled.
- [ ] Provider-local alerts remain functional independently.
- [ ] User-facing SLIs and SLOs approved.
- [ ] Multi-window burn alerts tested.
- [ ] GitOps revisions correlated with service health.
- [ ] Regional synthetic checks deployed.
- [ ] Application-consistent backup restored in isolation.
- [ ] Recovery cluster provisioned from reviewed IaC.
- [ ] Identity, secrets, registry and DNS dependencies validated.
- [ ] Writer fencing and controlled failover rehearsed.
- [ ] Failback and data reconciliation tested.
- [ ] RPO/RTO measured against approved objectives.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Six production runbooks validated.
- [ ] Readiness assessment signed off.

## 51. Knowledge check

1. Why should critical alerting remain available locally in each cloud?
2. What makes an SLI user-facing rather than infrastructure-facing?
3. How is SLO error-budget burn rate calculated?
4. Why does a healthy Argo CD Application not prove service availability?
5. What is the difference between cloud audit and Kubernetes API audit?
6. Why can metric label cardinality cause operational cost spikes?
7. What makes a backup application-consistent?
8. Why must a primary writer be fenced during failover?
9. Why can DNS cutover exceed the configured TTL?
10. How do you demonstrate actual RPO and RTO during a drill?

## 52. References

- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
- [Prometheus alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Google SRE workbook](https://sre.google/workbook/table-of-contents/)
- [AWS CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [AWS CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)
- [Azure Monitor](https://learn.microsoft.com/azure/azure-monitor/)
- [Google Cloud Monitoring](https://cloud.google.com/monitoring/docs)
- [Google Cloud Audit Logs](https://cloud.google.com/logging/docs/audit)
- [Argo CD monitoring](https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/)
- [Kubernetes observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 084 complete.** Next: **Chapter 085 — Multi-Cloud GitOps Enterprise Operations, Reliability and Disaster Recovery Capstone**, completing Part 17.