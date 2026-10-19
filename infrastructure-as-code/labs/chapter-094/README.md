# Chapter 094 — IaC SLO Engineering, Error Budgets, Alerting, Incident Response and Automated Reliability Controls

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**113 Python unit tests authored; execution not verified.**

- `reliability_gate.py`: exact synthetic target, 34 claimed controls, freshness, error budget, alert delivery, RPO/RTO
- `slo_math.py`: numeric request-based SLO, error budget and burn-rate calculations
- `alert_policy.py`: paired-window PAGE/TICKET/OK/UNKNOWN classification, no real notifications
- `change_gate.py`: safe synthetic PROCEED/HOLD/QUARANTINE decision; never mutates resources
- `fixtures/`: safe/unsafe synthetic assurance, burn-rate windows and change controls

Native Terraform/OpenTofu, Prometheus/Alertmanager, OTel, cloud, Kubernetes/GitOps and DBRE recovery **not executed**. Passing fixtures is not evidence of real alert delivery or production SLO attainment.
