# Chapter 099 — IaC Cost Optimization, Rightsizing, Commitments and Reliability-Aware FinOps Engineering

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**86 Python unit tests authored; execution not verified.**

- `evidence_gate.py`: exact synthetic scope, USD amortized basis, freshness, cost, headroom and DBRE guardrails
- `savings.py`: Decimal projected savings and percent, never actual provider savings
- `commitments.py`: illustrative utilization and break-even; no purchase
- `optimization_gate.py`: advice-only QUARANTINE/HOLD/REVIEW_ONLY; no cloud action
- `reconcile.py`: synthetic projected versus realized savings classification
- `fixtures/`: safe/unsafe synthetic optimization evidence and staging proposal

No live AWS/Azure/GCP billing, Kubernetes rightsizing, financial commitment purchase, Terraform apply, DBRE restore or production acceptance executed.
