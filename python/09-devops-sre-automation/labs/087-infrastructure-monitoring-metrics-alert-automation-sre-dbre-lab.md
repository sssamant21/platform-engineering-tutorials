# Chapter 087 — Infrastructure Monitoring, Metrics and Alert Automation SRE/DBRE Lab

**Standalone executable project:** [labs/087/README.md](087/README.md). Includes [monitor.py](087/monitor.py), [24 offline tests](087/test_monitor.py), [Prometheus exporter](087/exporter.py) and [OpenTelemetry SDK demonstration](087/otel_demo.py).

## Mission

Build a safe monitoring pipeline for CPU, memory, disk, alert state transitions, SLO availability and error-budget consumption. Run deterministic tests before optional local psutil sampling, Prometheus HTTP exporter and OTEL in-memory metric instrumentation.

## Architecture

\`\`\`text
psutil -> validated Sample -> Prometheus gauges / OTEL instruments
                         -> threshold/hysteresis/cooldown engine
request outcomes -> rolling SLO window -> budget remaining
                         -> JSON report / local metrics endpoint
                         -> production Alertmanager (design extension)
\`\`\`

## Exercise 1 — Test without dependencies

\`\`\`bash
cd python/09-devops-sre-automation/labs/087
python -m compileall -q monitor.py test_monitor.py exporter.py otel_demo.py
python -m unittest -v test_monitor.py
python monitor.py --dry-run
\`\`\`

Tests use synthetic host samples and no live network connections. They cover input validation, warning/critical/clear, alert dedup, cooldown, hysteresis, SLO windows, budget exhaustion and Prometheus text output.

## Exercise 2 — Inspect live host metrics locally

\`\`\`bash
python -m pip install -r requirements.txt
python monitor.py --format json
python monitor.py --format prometheus
\`\`\`

This reads only local host metrics. On Windows choose a valid disk path using \`--disk-path C:\\\` where appropriate. Disk utilization percent is not a measure of storage latency, throughput or IOPS.

## Exercise 3 — Prometheus Python client exporter

\`\`\`bash
python exporter.py --dry-run
python exporter.py --port 9109 --interval 15
curl http://127.0.0.1:9109/metrics
\`\`\`

The exporter listens only on loopback and emits \`sre_host_cpu_usage_percent\`, \`sre_host_memory_usage_percent\`, \`sre_host_disk_usage_percent\`, \`sre_monitor_sample_errors_total\` and \`sre_monitor_last_success_timestamp_seconds\`. Production deployments require approved authentication/network controls, resource budgets, scraping and alerting rules.

## Exercise 4 — OpenTelemetry

\`\`\`bash
python otel_demo.py
\`\`\`

The SDK demo records a counter using an in-memory reader and prints local metadata; it does **not** export to an OTLP collector. For production add reviewed OTLP exporter packages, endpoint TLS, authentication, batch readers and collector retry policies.

## Exercise 5 — Incident simulations

| # | Scenario | Expected action | Coverage |
|---|---|---|---|
| 1 | CPU warning | Emit warning | Automated |
| 2 | CPU critical | Emit critical | Automated |
| 3 | CPU normal | No alert | Automated |
| 4 | Duplicate warning | Suppress | Automated |
| 5 | Cooldown expiry | Repeat alert | Automated |
| 6 | Hysteresis band | Preserve state | Automated |
| 7 | CPU recovery | Emit clear | Automated |
| 8 | Warning-to-critical | Escalate | Automated |
| 9 | Invalid threshold | Reject | Automated |
| 10 | Negative cooldown | Reject | Automated |
| 11 | NaN sample | Reject | Automated |
| 12 | Negative utilization | Reject | Automated |
| 13 | Utilization >100 | Reject | Automated |
| 14 | Invalid timestamp | Reject | Automated |
| 15 | Synthetic sampler | Stable metrics | Automated |
| 16 | Prometheus text | Valid gauge values | Automated |
| 17 | No request traffic | SLO undefined | Automated |
| 18 | Mixed successes/failures | Compute availability | Automated |
| 19 | Remaining error budget | Compute fraction | Automated |
| 20 | Budget exhausted | Negative remainder | Automated |
| 21 | Invalid SLO input | Reject | Automated |
| 22 | Bounded SLO window | Evict old samples | Automated |
| 23 | Dry-run | No sampling | Automated |
| 24 | Exporter missing | Restore scrape path | Guided |
| 25 | OTLP outage | Inspect collector/backpressure | Guided |
| 26 | Alert storm | Group and dedup | Guided |
| 27 | High cardinality | Reduce labels | Guided |
| 28 | Disk IOPS saturation | Correlate cloud/storage metrics | Guided |
| 29 | Kubernetes cgroup mismatch | Compare container metrics | Guided |
| 30 | Stateful DB pressure | Check replication/quorum before action | Guided |

## Troubleshooting and runbooks

**Exporter outage:** verify process, loopback port, scrape target and last successful sample timestamp; never treat missing telemetry as healthy.

**High CPU/memory:** inspect per-process usage, cgroup pressure, query latency, traffic, deployments and throttling before changing capacity.

**Disk alert:** verify filesystem path, inode utilization, retention and storage latency; follow owner-approved cleanup/expansion.

**SLO burn:** validate eligible request definition and minimum sample size, check change timeline and downstream dependencies, pause risky deployments.

**Alert storm:** group duplicate alerts, apply hysteresis/sustained windows and preserve critical signal; do not permanently silence without RCA.

## 100-point final assessment

| Competency | Points |
|---|---:|
| Host metrics and input validation | 20 |
| Prometheus instrumentation and exporter | 15 |
| OpenTelemetry SDK and collector design | 15 |
| SLO and error-budget calculations | 15 |
| Alert thresholds, hysteresis and deduplication | 15 |
| Automated tests and incident simulations | 10 |
| Troubleshooting, runbooks and security | 10 |
| **Total** | **100** |

**Acceptance:** ≥90/100, independently executed tests, reviewed dependency pins, and approved network/telemetry controls before any production deployment.

**Validation:** 24 offline prototype tests passed in a working container; the GitHub-committed version and optional live exporters still require separate execution and CI validation.
