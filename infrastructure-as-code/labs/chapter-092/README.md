# Chapter 092 — IaC Drift Observability, State Reconciliation, Change Intelligence and Automated Detection

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`.

**112 Python unit tests authored; execution not verified.**

- `drift_gate.py`: exact synthetic target, 32 claimed controls, freshness, coverage, critical findings and RPO/RTO
- `snapshot_diff.py`: three-way comparison of synthetic desired, managed and actual state; unmanaged resources flagged
- `change_intel.py`: synthetic ticket, commit, actor, policy and bounded clock-skew correlation
- `remediation_gate.py`: conservative risk classifier, never performs apply/destroy
- `fixtures/`: safe/unsafe synthetic observations, snapshots and change-intelligence examples

Native Terraform/OpenTofu, Pulumi/CloudFormation/Bicep, cloud asset inventory, Kubernetes/GitOps, DBRE restore and independent audit **not executed**. Passing synthetic fixtures is not evidence of actual drift-free production infrastructure.
