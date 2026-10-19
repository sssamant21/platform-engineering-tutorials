# Chapter 090 — Enterprise IaC Testing, Compliance, Drift and Audit Reliability Capstone

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**125 Python unit tests authored; execution not verified.** This is a synthetic offline lab, not real production assurance.

- `capstone_gate.py`: exact target, 40 claimed controls, test counts, critical failures, RPO/RTO, cost and cleanup
- `coverage_gate.py`: synthetic 11-layer coverage, distinct test IDs, negative policy and DBRE restore claims
- `drift_decision.py`: conservative risk-based decision without infrastructure mutation
- `reconciliation.py`: independent approval and SLO verification state machine
- `audit_chain.py`: SHA-256 canonical JSON evidence chain, **not signer authentication**
- `fixtures/`: synthetic safe/unsafe and coverage records

Native Terratest/Molecule, cloud IAM, Terraform/OpenTofu, OPA/Sentinel, Kubernetes/GitOps, real DB restores, SLO verification and security/audit acceptance remain pending. A passing fixture does not certify them.
