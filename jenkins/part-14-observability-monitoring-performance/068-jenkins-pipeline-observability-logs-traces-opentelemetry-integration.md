# Chapter 068 — Jenkins Pipeline Observability, Logs, Traces and OpenTelemetry Integration

**Part 14 — Observability, Monitoring and Performance**  
**Audience:** Jenkins SRE, platform engineers, observability teams and incident responders  
**Prerequisites:** Chapters 066–067, disposable Jenkins LTS, representative Pipeline, OpenTelemetry Collector, supported Jenkins OpenTelemetry plugin, log backend and Grafana/Tempo/Jaeger or equivalent test environment.

## Learning objectives

Correlate Jenkins Pipeline runs with structured logs, traces, metrics and deployment events; configure telemetry export safely; distinguish Jenkins infrastructure failures from application failures; manage trace context and cardinality; investigate latency and errors with practical runbooks.

## 1. Architecture

```text
SCM webhook → Jenkins controller → Pipeline stages → agent pods → artifact/deploy
                   |                     |
           Jenkins OTel plugin       application/test logs
                   |                     |
                   v                     v
             OTel Collector <------ log collection
               /     |      \
           traces  metrics   logs
              |       |       |
          Tempo/Jaeger Prometheus Loki/Elastic
                 \    |    /
                Grafana + on-call
```

The exact signals emitted by the Jenkins OpenTelemetry plugin depend on installed plugin versions and configuration. Confirm actual spans, attributes, log events and exporters in a lab rather than assuming every stage or agent action is automatically traced.

## 2. Signal and correlation design

| Signal | Key dimensions | Purpose |
|---|---|---|
| Pipeline trace | service, job, build, stages | Critical path |
| Controller log | timestamp, level, component | Plugin and remoting errors |
| Agent log | pod/node/agent ID | Scheduling and runtime failures |
| Build console | job, build, stage | Task execution evidence |
| Metrics | bounded team/pool/environment | Trends and SLOs |
| SCM event | delivery ID, repository | Trigger correlation |
| Deployment event | artifact version, environment | Change impact |

**Correlation identifiers:** Use trace/span IDs and stable build URLs or IDs in logs, not as Prometheus metric labels. Avoid embedding user emails, credentials, full SCM tokens, secrets or sensitive payloads in span attributes.

## 3. Jenkins OpenTelemetry integration

Use the Jenkins OpenTelemetry plugin version compatible with your Jenkins core and chosen Collector. Configure the exporter endpoint through the plugin's documented UI or supported JCasC schema. Verify current supported environment variables and endpoint behavior for your installed version.

Typical **lab** OTLP endpoint:

```text
http://otel-collector.monitoring.svc.cluster.local:4317
```

Port 4317 commonly accepts OTLP/gRPC; port 4318 commonly accepts OTLP/HTTP. **Do not assume protocol compatibility from the port alone.** Use mTLS or other approved authentication and network controls for production.

## 4. OpenTelemetry Collector configuration

Example Collector configuration for an isolated lab using OTLP receivers and a debug exporter:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
    spike_limit_mib: 64
  batch: {}
exporters:
  debug:
    verbosity: basic
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
```

**Lab-only warning:** This listens on all interfaces without TLS/auth and exports traces to Collector logs. Isolate the service. Production should use restricted network access, authenticated OTLP, approved trace backend, resource limits and sensitive-attribute filtering. Validate against the deployed Collector version.

## 5. Pipeline instrumentation

```groovy
pipeline {
  agent { label 'trusted-ci' }
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Unit tests') {
      steps { sh './ci/unit-tests.sh' }
    }
    stage('Package') {
      steps { sh './ci/package.sh' }
    }
  }
  post {
    always {
      echo "Pipeline result: ${currentBuild.currentResult}"
    }
  }
}
```

This example generates meaningful stages and timestamps but does not itself create OpenTelemetry spans. Trace generation depends on Jenkins instrumentation and plugin configuration. Scripts are repository-specific and must exist on the agent.

## 6. Distributed trace investigation

1. Start with a slow build and locate its Jenkins trace in the trace backend.
2. Identify elapsed time between queue, agent allocation, checkout, tests, artifact upload and deployment.
3. Compare critical-path spans with agent pod events and controller logs.
4. Distinguish wall-clock wait from CPU-intensive work.
5. Compare baseline and regression build cohorts without exposing sensitive attributes.
6. Link root cause to capacity, SCM, storage, plugins or downstream services.

Avoid assuming trace spans fully cover all build steps; missing instrumentation creates gaps.

## 7. Structured log practices

Prefer JSON or consistently parseable text for controller and infrastructure logs:

```json
{"timestamp":"2026-10-16T00:00:00Z","service":"jenkins-controller","level":"WARN","component":"agent-provisioning","message":"agent provisioning delayed","pool":"ci-k8s"}
```

The sample is synthetic. Never log access tokens, credentials, secret environment variables or entire build payloads. Protect console logs, thread dumps and exported telemetry as potentially sensitive. Enforce retention and access control by environment.

## 8. Log pipeline design

Collect controller stdout/system logs, Kubernetes pod events, agent pod logs and Jenkins console output where authorized. Do not automatically ship all build console logs to a central backend without redaction and retention review. Record the origin of each log and avoid duplicate ingestion.

## 9. Trace propagation and context

For downstream application calls, W3C Trace Context headers (`traceparent`, `tracestate`) can correlate requests when instrumentation supports them. Jenkins Pipeline shell steps do not automatically propagate trace context into arbitrary scripts. Test propagation explicitly and never blindly forward baggage containing sensitive data.

## 10. Sampling, retention and cost

Start with a modest sampling strategy, preserve error/slow traces according to approved Collector/backend capabilities, and use bounded resource attributes. Review ingest bytes, high-cardinality tags, span volume per build, log retention and sensitive data policies. Tail sampling requires appropriate Collector processor/distribution and capacity planning.

## 11. Operational dashboards

- Pipeline latency p50/p95 by bounded workload class.
- Queue and agent provisioning latency alongside traces.
- SCM checkout failures and duration.
- Build infrastructure failure rate versus test failures.
- Controller plugin/remoting errors.
- OTel Collector receive/export errors, queue saturation and dropped spans.
- Log ingestion volume and trace backend latency.
- Deployment annotations and plugin/JCasC changes.

## 12. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| No traces | Plugin disabled/endpoint wrong | Plugin config/Collector logs |
| OTLP connection refused | Port/protocol/network | Endpoint and Service |
| TLS handshake fails | CA/SNI/client auth | Cert chain |
| Spans missing | Sampling/instrumentation gaps | Pipeline and Collector |
| Trace missing stages | Plugin version/coverage | Validate spans |
| Build trace fragmented | Context not propagated | Trace headers |
| High Collector CPU | Span volume/processing | Rate and limits |
| Dropped spans | Export queue/backpressure | Collector telemetry |
| Console logs missing | No log integration | Collector source |
| Duplicate logs | Multiple collectors | Deduplicate pipelines |
| Secret in span | Unsafe attribute | Revoke/redact |
| Trace cardinality high | Build IDs as metric labels | Relabel/redesign |
| Timestamps misaligned | Clock skew/timezone | NTP/UTC |
| Trace backend slow | Ingest/index pressure | Backend health |
| Build marked failed | App tests vs infrastructure | Failure taxonomy |
| Agent log absent | Pod deleted/retention | Central collection |

## 13. Five production runbooks

### A. Slow Pipeline investigation
1. Select impacted build cohort and baseline.
2. Inspect queue/agent metrics and trace critical path.
3. Correlate SCM, tests, artifact and deployment spans.
4. Review agent/controller logs and infrastructure events.
5. Fix bottleneck and compare p95 after remediation.

### B. Missing telemetry
1. Check Jenkins plugin status and exporter endpoint.
2. Validate OTLP protocol, TLS, DNS and network policy.
3. Inspect Collector receiver/exporter errors.
4. Confirm trace backend ingestion and sampling.
5. Run synthetic build and verify trace visibility.

### C. Collector backpressure
1. Review Collector CPU/memory and dropped data.
2. Identify unexpected span/log volume and attributes.
3. Apply bounded sampling/batching and scale capacity.
4. Restore exporter connectivity.
5. Confirm dropped-data rate recovers.

### D. Sensitive data in telemetry
1. Restrict access and stop offending export path.
2. Identify exposed values and affected retention stores.
3. Revoke/rotate credentials as appropriate.
4. Purge data per platform policy and add filtering.
5. Verify negative tests and record security incident.

### E. Agent-related build failure
1. Correlate build trace with agent pod and controller logs.
2. Inspect scheduling, image pulls, remoting and resource limits.
3. Separate application test failures from agent failures.
4. Restore agent capacity/configuration safely.
5. Verify representative build and latency recovery.

## 14. Acceptance criteria

- [ ] Compatible Jenkins OTel plugin configured.
- [ ] Collector receives a synthetic Pipeline trace.
- [ ] Traces correlate to build and stage evidence.
- [ ] Logs retained with redaction and access controls.
- [ ] Metrics labels have bounded cardinality.
- [ ] Queue and agent wait visible alongside stage timings.
- [ ] Collector drops/export errors monitored.
- [ ] TLS/auth and retention documented for production.
- [ ] Failure injection and recovery verified in lab.
- [ ] On-call runbooks and evidence complete.

**Companion:** [Chapter 068 hands-on lab](labs/068-jenkins-pipeline-observability-logs-traces-opentelemetry-integration-check.md).  
**Next:** Chapter 069 — Jenkins Controller, JVM, Queue and Agent Performance Analysis.
