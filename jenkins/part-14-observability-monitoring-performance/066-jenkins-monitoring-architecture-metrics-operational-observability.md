# Chapter 066 — Jenkins Monitoring Architecture, Metrics and Operational Observability

**Part 14 — Observability, Monitoring and Performance**  
**Audience:** Jenkins SRE, platform engineering, DevOps, on-call engineers  
**Prerequisites:** Chapters 061–065, disposable Jenkins LTS controller, Prometheus/Grafana lab, Kubernetes or VM test agent.

## Outcomes

Build production-grade Jenkins monitoring, distinguish controller from build-agent signals, establish golden signals and service-level indicators, instrument pipelines and plugins, create actionable alerts, and troubleshoot reliability incidents without exposing credentials.

## 1. Observability architecture

```text
Jenkins controller + plugins + build queue
       | metrics / logs / events
       v
 Prometheus scrape → recording/alert rules → Alertmanager
       |                                |
       v                                v
   Grafana dashboards               On-call routing
       ^
 Kubernetes/VM metrics, JVM/JMX, agent nodes
       ^
 SCM webhook + pipeline stage + artifact telemetry
```

A Jenkins monitoring solution should cover controller availability, authentication, executor and queue health, Pipeline success and latency, agent provisioning, SCM integrations, storage, plugins and JVM resource pressure. Prometheus metrics are only one signal: logs, audit trails, synthetic builds and external probes are necessary.

## 2. Signal inventory

| Layer | Metrics / events | Failure mode |
|---|---|---|
| Controller | HTTP availability, uptime, restart, JVM heap/GC, CPU | Outage, OOM |
| Queue | queue length, wait duration, blocked/stuck reasons | Build starvation |
| Executors | busy/idle/offline executors | Insufficient capacity |
| Pipelines | result, duration, stage timings, retries | Slow/failing delivery |
| Agents | online/offline, provisioning, startup latency | Pod/image/cloud failure |
| Plugins | failed loads, version changes, errors | Compatibility regression |
| SCM | webhook failures, checkout latency, rate limits | Builds not triggered |
| Security | auth failures, admin changes, secret access | Unauthorized activity |
| Storage | Jenkins home usage, inode pressure, latency | Startup/build failure |
| Kubernetes | pod pending, OOMKilled, evictions, API errors | Agent unavailability |

## 3. Golden signals and SLIs

Define SLIs at the Jenkins service boundary:
- **Availability:** fraction of successful external synthetic controller checks, excluding approved maintenance.
- **Queue wait:** percentile time from queued to execution, segmented by workload class.
- **Build execution reliability:** fraction of infrastructure-attributable failures, distinct from application test failures.
- **Agent provisioning:** percentile time from provisioning request to ready executor.
- **Change health:** failed controller upgrades, plugin startup errors, JCasC/seed failures.

Do not label every failed build a Jenkins infrastructure incident; separate application, test, SCM, infrastructure and policy failures.

## 4. Prometheus integration

The Jenkins Prometheus plugin can expose metrics via an HTTP endpoint. **Endpoint paths, metric names and plugin configuration vary by version**; inspect your installed plugin and confirm authentication/network controls. Restrict metrics access to trusted collectors; labels and job names may reveal internal metadata.

Example scrape configuration for an **illustrative** endpoint:

```yaml
scrape_configs:
  - job_name: jenkins-controller
    metrics_path: /prometheus/
    scrape_interval: 30s
    static_configs:
      - targets: ['jenkins.monitoring.svc.cluster.local:8080']
```

This example assumes an explicitly configured lab endpoint reachable on that address. In production use TLS, service discovery and approved authentication, and verify that the actual plugin endpoint and URL context path match.

## 5. JVM and controller resources

Track heap used/max, GC pauses, process CPU, file descriptors, thread counts, controller restart frequency and Jenkins home I/O. Combine JVM metrics with OS/container metrics; heap alone does not explain native memory or Kubernetes OOMKilled events. Use JFR/thread dumps under controlled diagnostic procedures; protect dumps as potentially sensitive.

## 6. Queue and executor saturation

Correlate queue depth with:
1. Available compatible agents/executors.
2. Label constraints and offline agents.
3. Throttle/lock restrictions and concurrency controls.
4. Agent startup and image-pull latency.
5. SCM or external dependencies.

Queue length without wait-time and workload classification can mislead. An increase during a planned deployment burst is not necessarily a failure.

## 7. Agent and Kubernetes telemetry

Observe pod phase, scheduling failures, CPU/memory requests/limits, eviction reasons, image pulls, service-account permissions, remoting disconnects and cluster autoscaler/Karpenter events. Label metrics with **bounded-cardinality** team/pool/environment, not raw build IDs, commit hashes or user IDs. High-cardinality labels can overload Prometheus.

## 8. Pipeline instrumentation

Use Pipeline timestamps, structured stage names, stable result categories and build metadata. Emit custom metrics only through an approved telemetry path; avoid a unique time series per build. Correlate a build URL or ID in logs/traces, not in unbounded metric labels.

Illustrative Jenkinsfile:

```groovy
pipeline {
  agent { label 'trusted-ci' }
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Test') { steps { sh './ci/test.sh' } }
  }
  post {
    always {
      echo "Build result: ${currentBuild.currentResult}"
    }
  }
}
```

Supply the repository's test script and a trusted agent. Do not echo credentials or full environment dumps.

## 9. Dashboard design

Create separate dashboards for:
- **Service overview:** availability, queue wait, controller restarts, infrastructure failure rate.
- **Controller/JVM:** CPU, heap/GC, threads, storage and plugin failures.
- **Build capacity:** queue depth/age, executor utilization, blocked jobs.
- **Agents/Kubernetes:** provisioning latency, pending pods, evictions and remoting.
- **Delivery experience:** Pipeline duration percentiles, infra failures, SCM errors.
- **Security/change:** admin changes, failed login bursts, plugin/JCasC rollout markers.

Annotate maintenance windows and configuration deployments to improve causal analysis.

## 10. Example alert rules

Metric names below are **illustrative recording rules**, not guaranteed Jenkins plugin exports. Define and test them against your real telemetry before enabling paging.

```yaml
groups:
  - name: jenkins-sre
    rules:
      - alert: JenkinsControllerUnavailable
        expr: up{job="jenkins-controller"} == 0
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "Jenkins metrics target unavailable"
      - alert: JenkinsQueueWaitHigh
        expr: jenkins_sli_queue_wait_p95_seconds > 300
        for: 15m
        labels:
          severity: ticket
        annotations:
          summary: "Jenkins queue p95 exceeds 5 minutes"
```

`up == 0` means the **metrics scrape failed**, not necessarily that the user-facing Jenkins UI is unavailable; confirm with an independent synthetic probe. The queue-wait recording metric must be implemented before using the second alert.

## 11. Alert design and noise control

Page for customer-impacting controller outages, severe persistent queue starvation, credential/authorization incidents and broad agent pool failure. Ticket on gradual saturation, plugin deprecation and moderate capacity trends. Alert on symptoms and error-budget consumption rather than every transient pod restart. Include dashboard, owner, impact, first checks, rollback and escalation.

## 12. Troubleshooting matrix

| Symptom | Likely cause | First checks |
|---|---|---|
| Metrics scrape fails | Network/TLS/auth/endpoint | Prometheus target and logs |
| UI down but metrics up | Proxy/route/auth | External synthetic probe |
| Queue depth rising | No matching executors | Labels, offline nodes |
| Long queue wait | Agent provisioning | Kubernetes events |
| Agents repeatedly disconnect | Remoting/network | Agent logs and versions |
| Controller OOMKilled | Container memory/heap/native | Pod events, memory |
| GC pauses high | Heap pressure/plugins | GC logs/JFR |
| Pipeline durations spike | SCM/build/dependency | Stage timings |
| False infra failure alerts | Bad classification | Failure taxonomy |
| Alert storm | Missing inhibition/grouping | Alertmanager routes |
| Prometheus memory spike | High-cardinality labels | Series cardinality |
| Storage pressure | Logs/artifacts/retention | Jenkins home and inode |
| Plugin metrics disappear | Plugin upgrade | Version and endpoint |
| Missing builds | Webhook/SCM failure | SCM delivery logs |
| Audit gaps | Disabled log integration | Collector pipeline |
| Time series stale | Target absent/relabeling | Service discovery |

## 13. Five production runbooks

### A. Controller unavailable
1. Verify external synthetic probe and metrics scrape separately.
2. Check controller pod/VM, restart reason, JVM and ingress.
3. Inspect recent plugin/JCasC/image changes.
4. Restore last known-good configuration if change-related.
5. Validate login, queue, agents and representative build.

### B. Queue starvation
1. Measure p95 queue wait and affected workload classes.
2. Inspect agent label compatibility and online executors.
3. Check pending pods, autoscaler, quotas and image pulls.
4. Recover capacity or reduce workload safely.
5. Verify queue drain and document bottleneck.

### C. Controller memory incident
1. Capture memory, GC, OOM and pod/OS events.
2. Inspect recent plugins, build load and heap sizing.
3. Preserve safe diagnostics and review capacity.
4. Roll back offending change or rightsize through approval.
5. Verify stability under representative load.

### D. Missing or noisy telemetry
1. Confirm plugin endpoint, auth and network policy.
2. Check Prometheus target discovery and scrape errors.
3. Review metric schema and label cardinality.
4. Fix recording/alert rules and replay test conditions.
5. Verify alerts route to the correct on-call owner.

### E. Agent provisioning failure
1. Identify impacted pool/labels and queue age.
2. Check Kubernetes events, RBAC, image pulls and quotas.
3. Review plugin/remoting compatibility and cloud limits.
4. Restore agent provisioning safely.
5. Verify sample Pipeline and provisioning latency.

## 14. Hands-on acceptance

- [ ] Prometheus endpoint configured with access controls.
- [ ] External synthetic probe distinguishes service from scrape health.
- [ ] Controller/JVM/queue/agent telemetry visible.
- [ ] Pipeline failures classified by ownership.
- [ ] Dashboards cover service, capacity and agents.
- [ ] Alert rules tested with realistic thresholds.
- [ ] Metric cardinality reviewed.
- [ ] Runbook links and on-call routes verified.
- [ ] Failure injection performed only in lab.
- [ ] Evidence retained without secrets.

**Companion:** [Chapter 066 hands-on lab](labs/066-jenkins-monitoring-architecture-metrics-operational-observability-check.md).  
**Next:** Chapter 067 — Jenkins Prometheus, Grafana Dashboards and Alertmanager Integration.
