# Chapter 088 — IaC Compliance Testing, Audit Evidence and Continuous Assurance

Python 3.10+ and Bash. Run `bash run-preflight.sh`. **97 Python unit tests authored; execution not yet verified.**

- `compliance_gate.py`: exact synthetic target, eight control IDs, 32 claimed controls, RPO/RTO and evidence freshness
- `mapping_gate.py`: control register owner, framework reference, implementation and evidence mapping
- `evidence_chain.py`: SHA-256 canonical JSON payload and previous-hash chain (NOT signer authentication)
- `exception_gate.py`: scoped, independent, time-limited, compensating exceptions
- `fixtures/`: synthetic safe/unsafe control, catalog and exception evidence

The scripts do not execute OPA/Sentinel, cloud IAM, Kubernetes admission, real DB restore, or an external audit. A passing fixture is not proof of control operation, SOC 2/HIPAA/PCI/NIST certification or regulatory compliance.
