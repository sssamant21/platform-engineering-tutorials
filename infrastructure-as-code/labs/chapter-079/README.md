# Chapter 079 — Ansible/Kubernetes/GitOps delivery lab

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`. The lab checks **self-declared evidence only** and simulates a fail-closed promotion; it does not execute Ansible, kubectl, Helm, Argo CD or Flux.

Optional native syntax check: `ansible-playbook --syntax-check -i localhost, -c local examples/playbook.yml`. Inspect `examples/deployment.yaml` but **do not apply**. The CI examples run offline tests only and are not production deployment pipelines.
