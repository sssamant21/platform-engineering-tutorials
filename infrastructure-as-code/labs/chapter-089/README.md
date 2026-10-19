# Chapter 089 — IaC Continuous Compliance, Drift and Audit Automation

Python 3.10+ and Bash. Run `bash run-preflight.sh`. **92 Python unit tests authored; execution not verified.**

- `drift_gate.py`: exact synthetic target, 30 declared controls, observation age, critical findings, RPO/RTO
- `risk_engine.py`: deterministic synthetic exposure/data/destructive risk scoring
- `remediation.py`: quarantine, approval and closure state machine; no mutation
- `audit_chain.py`: SHA-256 canonical JSON hash-chain verification; NOT signer authentication
- `fixtures/`: synthetic safe/unsafe and risk examples

Native Terraform/OpenTofu plans, Pulumi/CloudFormation/Bicep, AWS/Azure/GCP audit, OPA/Sentinel, Kubernetes, GitOps, DBRE restore and remediation **are not executed**. Passing synthetic tests is not proof of runtime compliance.
