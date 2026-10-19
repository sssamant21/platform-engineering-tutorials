# Chapter 098 — IaC Cost Forecasting, Budget Governance, Anomaly Detection and FinOps Automation

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**82 Python unit tests authored; execution not verified.**

- `billing_gate.py`: synthetic exact account, daily coverage, owner, USD amortized basis and freshness
- `forecast.py`: Decimal trailing mean, observed spend and remaining-period projection
- `budget_gate.py`: actual/forecast budget classification (OK/WATCH/BREACH/UNKNOWN)
- `anomaly.py`: spend ratio and absolute-dollar threshold with missing-data UNKNOWN
- `automation_gate.py`: fail-closed advice-only QUARANTINE/HOLD/PROPOSAL_ONLY
- `fixtures/`: safe/unsafe daily billing exports and non-destructive staging change

No AWS/Azure/GCP billing exports, live budget notifications, IaC mutation or DBRE reliability drills were executed. The forecast is a naive baseline, not a seasonal production forecast.
