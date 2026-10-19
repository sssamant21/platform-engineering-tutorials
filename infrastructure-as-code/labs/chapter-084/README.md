# Chapter 084 — Least Privilege, Zero Trust, IAM and Kubernetes Hardening

**Offline lab:** Python 3.10+ and Bash. Run `bash run-preflight.sh`. Contains **78 authored unit tests**; runtime execution not verified.

- `identity_gate.py`: fail-closed self-declared OIDC, IAM, RBAC and DBRE readiness evidence
- `iam.py`: simple scoped AWS S3 IAM allow-list simulation; **not** real IAM/SCP evaluation
- `rbac.py`: namespace ServiceAccount/Role permission simulation; **not** Kubernetes SubjectAccessReview
- `fixtures/`: synthetic safe/unsafe inputs; no live credentials

Passing offline evidence is not production authorization. Real staging acceptance requires IAM trust tests, Azure/GCP federation, Kubernetes `kubectl auth can-i`, audit logs, database restore and signed approvals.
