# Chapter 091 — IaC Observability Architecture, Telemetry, SLOs and Operational Dashboards

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**101 Python unit tests authored; execution not verified.**

- `telemetry_gate.py`: exact synthetic target, 30 claimed controls, 12 required metric families, freshness, RPO/RTO and SLO claims
- `slo_engine.py`: real numeric request-based availability, error budget and burn-rate calculations
- `cardinality_gate.py`: real arithmetic for static label-cardinality estimates and high-cardinality label rejection
- `dashboard_gate.py`: synthetic coverage and freshness checks for eight dashboard sections
- `fixtures/`: safe/unsafe synthetic evidence and dashboard example

Native OpenTelemetry Collector, Prometheus/Grafana, cloud, Kubernetes, GitOps and DBRE recovery validation **not executed**. A passing fixture is not proof of operational telemetry or SLO attainment.
