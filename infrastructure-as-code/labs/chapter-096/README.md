# Chapter 096 — IaC Cost Observability, Cloud Billing Data, Tagging and FinOps Fundamentals

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**83 Python unit tests authored; execution not verified.**

- `billing_gate.py`: synthetic exact billing scope, source digest, export freshness, provider, USD amortized basis, tags and duplicate rejection
- `allocate.py`: Decimal USD allocation and cost-center ledger
- `anomaly.py`: completeness-aware spend classification (UNKNOWN/OK/REVIEW)
- `optimization.py`: advice-only reliability and DBRE-safe cost change classification
- `fixtures/`: safe/unsafe synthetic billing exports and staging optimization

No live AWS CUR, Azure Cost Management, GCP BigQuery billing export, IaC, Kubernetes or DBRE rightsizing validation was executed. Synthetic billing fixtures are not provider invoice evidence.
