# Chapter 085 — Enterprise Security, Policy and Zero-Trust Capstone

Python 3.10+ and Bash required. Run `bash run-preflight.sh`.

**113 Python unit tests authored; execution not yet verified.** All data are synthetic. The suite checks self-declared identity/policy/DBRE evidence, STRIDE risk ownership, a fail-closed release promotion sequence and DR metrics.

- `readiness_gate.py`: exact targets, 40 control claims, artifact digest, zero critical findings, RPO/RTO
- `threat_model.py`: STRIDE risk-register validation
- `promotion.py`: release stage ordering and halt semantics
- `dr_gate.py`: declared backup, restore, KMS and RPO/RTO checks
- `fixtures/`: safe/unsafe synthetic evidence

No actual OIDC, AWS/Azure/GCP, Kubernetes, OPA/Sentinel, Cosign, state backend or DB restore validation occurs. A passing fixture is not production authorization. Native integration and independent security/SRE/DBRE acceptance are required.
