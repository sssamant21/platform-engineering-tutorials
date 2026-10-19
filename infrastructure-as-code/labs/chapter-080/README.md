# Chapter 080 — Enterprise IaC CI/CD reliability capstone

**Offline, non-provisioning lab.** Requires Python 3.10+ and Bash. Run `bash run-preflight.sh`. Safe fixture should pass, unsafe fixture should be rejected; 84 unit tests are authored. **Tests have not been executed by the publisher.**

`capstone_gate.py` checks self-declared evidence only, `delivery.py` simulates fail-closed promotion, and `dr.py` evaluates self-declared recovery readiness. No tool calls to Terraform, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes, Argo CD or Flux occur. Production evidence must come from independently verified identity, state, plan, backup and monitoring systems.

The GitLab/GitHub CI examples execute offline tests only. Do not enable cloud apply without scoped OIDC, protected approvals, signed artifacts, state locks, DBRE restore and SLO gates.
