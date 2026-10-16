# Chapter 068 — Hands-on Lab: Jenkins Pipeline Logs, Traces and OpenTelemetry

**Environment:** Disposable Jenkins LTS, compatible OpenTelemetry plugin, isolated OpenTelemetry Collector, synthetic Pipeline, optional Tempo/Jaeger and log backend. Use synthetic credentials only.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record plugin/Collector versions | Baseline |
| 02 | Architecture | Diagram telemetry flow | Diagram |
| 03 | Collector | Start isolated OTLP receiver | Config |
| 04 | Endpoint | Validate protocol and connectivity | Logs |
| 05 | Plugin | Configure Jenkins OTel exporter | Settings |
| 06 | Pipeline | Run synthetic three-stage build | Build |
| 07 | Trace | Locate build trace | Trace ID |
| 08 | Stages | Inspect available stage spans | Timeline |
| 09 | Queue | Compare queue wait with trace | Correlation |
| 10 | Agents | Correlate pod events and spans | Evidence |
| 11 | Logs | Collect controller logs | Sample |
| 12 | Console | Inspect sanitized build console | Sample |
| 13 | Context | Test downstream trace propagation | Result |
| 14 | Failure | Inject test-stage failure | Trace |
| 15 | Classification | Separate app and infra failures | Report |
| 16 | Sampling | Measure trace volume | Stats |
| 17 | Cardinality | Inspect resource/span attributes | Report |
| 18 | Backpressure | Simulate backend outage in lab | Drop stats |
| 19 | Recovery | Restore exporter and confirm trace | Timeline |
| 20 | Review | Complete observability sign-off | Report |

## 12 troubleshooting drills

1. Jenkins OpenTelemetry plugin missing.
2. Wrong OTLP protocol or port.
3. Collector DNS/network failure.
4. TLS or auth failure.
5. Missing Pipeline stage spans.
6. Trace context not propagated.
7. Missing agent pod logs.
8. Duplicate log ingestion.
9. Collector memory pressure.
10. Export queue/backpressure.
11. Sensitive span attribute.
12. High-cardinality metric regression.

## Collector lab configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
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

**Lab only:** No TLS or authentication in this minimal configuration; restrict network exposure. Debug exporter writes trace details to Collector logs.

## Evidence template

```text
UTC timestamp:
Jenkins core/OTel plugin versions:
Collector version:
OTLP endpoint/protocol:
Synthetic build URL:
Trace ID and visible stages:
Controller/agent log correlation:
Queue/agent latency:
Failure classification:
Sensitive data and cardinality review:
Collector export errors:
Injected failure and recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Synthetic Pipeline trace visible.
- [ ] Trace/log correlation verified.
- [ ] Collector errors and drops monitored.
- [ ] No secrets in telemetry.
- [ ] Metrics labels bounded.
- [ ] Recovery verified.
- [ ] Reviewer signs off.

**Related:** [Chapter 068 — Jenkins Pipeline Observability, Logs, Traces and OpenTelemetry Integration](../068-jenkins-pipeline-observability-logs-traces-opentelemetry-integration.md).
