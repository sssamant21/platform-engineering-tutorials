# Chapter 087 — IaC Integration Testing, Terratest, Molecule and Ephemeral Environments

Python 3.10+ and Bash. Run `bash run-preflight.sh`. **105 unit tests authored; execution not verified.**

- `integration_gate.py`: exact test account, 32 declared controls, cost/TTL, zero orphan and DBRE RPO/RTO checks
- `lifecycle.py`: synthetic environment lease, teardown and quarantine state machine
- `budget_gate.py`: synthetic cost, lease age, owner and orphan checks
- `evidence_gate.py`: declared Terraform/Terratest/Molecule/Kubernetes/GitOps/restore coverage
- `fixtures/`: synthetic safe/unsafe JSON, never real credentials

These scripts do **not** run Terratest, Molecule, cloud APIs, Terraform, Kubernetes or database restores. Real integration validation needs a separately authorized ephemeral account, native test logs, resource inventory, actual restore, cleanup and independent SRE/DBRE approval.
