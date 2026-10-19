# Chapter 077 — Terraform/OpenTofu plan/apply safety lab

Requires Python 3.9+ and Bash; no Terraform/OpenTofu binary or cloud credentials. Run `bash run-preflight.sh`. This is an **offline self-declared evidence validator**, not native HCL/plan parsing or attestation verification. The pipeline simulator does not invoke apply.

Optional: inspect `examples/main.tf` with `tofu fmt -check`, `tofu init -backend=false`, `tofu validate` after installing OpenTofu. The example uses only `terraform_data` and has no remote resources. Do not execute `tofu apply` in production.
