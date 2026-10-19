# Chapter 081 — IaC Security Foundations Lab

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`. The lab tests a fail-closed **self-declared** security policy, STRIDE risk register and secret rotation state machine. **74 unit tests authored; execution not verified.**

No cloud IAM, OIDC federation, secret manager, KMS, Terraform state, Kubernetes or database is accessed. A passing fixture is **not** proof of signed source, actual secret safety or security certification. Production adapters must obtain and cryptographically validate independent evidence.

The unsafe fixture includes wildcard OIDC trust, plaintext secret control failure and unencrypted state control failure. The rotation simulator never rotates real credentials.
