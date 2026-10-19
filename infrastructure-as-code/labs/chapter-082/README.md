# Chapter 082 — Policy as Code Lab

Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`. The lab implements a self-declared enterprise policy gate, exception lifecycle and fail-closed promotion simulator. **74 unit tests authored; execution not yet verified.**

The included Rego v1 example is illustrative; native OPA and Sentinel integration are optional and not part of the offline test suite. Policy evidence is **self-declared**, not cryptographically verified. Do not deploy using these fixtures as authorization.

Optional OPA command: `opa eval -d examples/guardrails.rego -i examples/opa-input.json 'data.iac.security.allow'`.

No Terraform apply, Pulumi up, CloudFormation execute-change-set, Azure deployment, Ansible playbook or Kubernetes admission call occurs.
