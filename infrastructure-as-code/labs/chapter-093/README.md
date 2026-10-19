# Chapter 093 — IaC Incident Correlation, Root Cause Analysis, Change Failure Detection and Reliability Engineering

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**103 Python unit tests authored; execution not verified.**

- `incident_gate.py`: exact synthetic target, 32 claimed controls, event freshness, change failure rate, RPO/RTO
- `correlate.py`: candidate change ranking by temporal, service, environment, dependency and evidence overlap; **not causal proof**
- `timeline.py`: UTC event ordering, unique IDs and change identity
- `reliability.py`: deduplicated change failure rate, request-based error budget
- `fixtures/`: safe/unsafe synthetic observations, competing changes and timeline

Native Terraform/OpenTofu, CI, cloud audit, OpenTelemetry/Prometheus, Kubernetes/GitOps, DBRE restore and independent security/audit acceptance **not executed**.
