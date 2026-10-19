# Chapter 086 — IaC Testing Strategy and Policy Test Automation

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`. **90 Python unit tests authored; execution not verified.**

- `test_gate.py`: exact target, 30 declared testing controls, destructive-change and RPO/RTO checks
- `coverage_gate.py`: synthetic required test layers, negative tests, skipped critical and age
- `pipeline.py`: fail-closed source/format/static/unit/policy/plan/integration/restore/canary/evidence/approval sequence
- `fixtures/`: synthetic safe/unsafe evidence

No Terraform, OpenTofu, Pulumi, OPA, Sentinel, Kubernetes, cloud or DB test is actually invoked. A passing fixture does **not** establish native policy, test coverage, backup restorability or production acceptance.
