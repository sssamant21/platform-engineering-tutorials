# Chapter 078 — Multi-tool CI/CD policy and promotion lab

Run `bash run-preflight.sh` using Python 3.10+ and Bash. All checks are offline and use **self-declared fixtures**, not native Pulumi/CloudFormation/Bicep evidence or verified approvals.

The safe fixture should pass, unsafe fixture should be rejected, and 55 unit tests should pass. CI YAML examples are validation-only; no deployment jobs are enabled. Optional native preview commands are described in `preview-commands.md`; do not run them against production without identity and change approval.

Files: `governance_gate.py`, `pipeline.py`, `policy.json`, `fixtures/`, `test_governance_gate.py`, `test_pipeline.py`, `run-preflight.sh`, `preview-commands.md`, `runbook.md`, `acceptance.md`, and two CI examples.
