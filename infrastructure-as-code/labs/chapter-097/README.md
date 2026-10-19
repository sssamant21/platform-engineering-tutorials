# Chapter 097 — IaC Cost Allocation, Showback, Chargeback and Shared Platform Cost Models

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**90 Python unit tests authored; execution not verified.**

- `ledger_gate.py`: exact synthetic billing scope, immutable digest claims, ownership, USD amortized basis, line deduplication, freshness, shared weights
- `allocate.py`: deterministic integer-cent allocation, largest-remainder rounding, explicit unallocated bucket
- `reconcile.py`: zero-cent ledger reconciliation
- `chargeback_gate.py`: advice-only HOLD/QUARANTINE/READY_FOR_REVIEW, no financial transfer
- `fixtures/`: safe/unsafe billing ledger and change gate

No native cloud billing export, real Kubernetes metering, database allocation, finance settlement or SRE/DBRE production acceptance executed.
