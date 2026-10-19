# Chapter 095 — Enterprise IaC Observability, Drift, SLO and Incident Response Reliability Acceptance Capstone

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**127 Python unit tests authored; execution not verified.**

- `acceptance_gate.py`: synthetic target, 36 declared controls, inventory/telemetry freshness, no destructive actions, RPO/RTO and SLO claims
- `drift_assess.py`: synthetic desired/managed/actual inventory differences
- `slo_assess.py`: request SLO, error-budget and burn-rate mathematics
- `incident_assess.py`: UTC timeline validation and candidate incident correlation; **not causal proof**
- `remediation_assess.py`: advice-only QUARANTINE/HOLD/PROPOSAL_ONLY safety breaker
- `fixtures/`: safe/unsafe synthetic acceptance, drift, incident and change examples

No live Terraform/OpenTofu, cloud inventory, Prometheus/Alertmanager, OpenTelemetry, GitOps or DBRE restore was executed. **Curriculum Part 19 publication complete; native acceptance pending.**
