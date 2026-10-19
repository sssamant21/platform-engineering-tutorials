# Chapter 083 — IaC Security Scanning and Supply Chain Lab

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`. This is a non-provisioning lab with **78 authored tests; runtime execution has not been verified**.

- `security_gate.py`: fail-closed **self-declared** scanner/compliance evidence
- `findings.py`: synthetic secret/vulnerability finding triage and expiring suppressions
- `supply_chain.py`: digest and builder metadata **schema validation**, not cryptographic verification
- `fixtures/`: synthetic safe/unsafe evidence, findings and attestation metadata

No Gitleaks, TruffleHog, Checkov, Trivy, Cosign, OPA, Terraform, cloud or Kubernetes tools are invoked. A passing fixture does not prove signatures, scanner execution, secret safety or compliance certification. The example CI workflows execute offline tests only; they do not deploy.
