#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 aws_foundation_gate.py fixtures/foundation-safe.json fixtures/plan-safe.json aws-foundation-policy.json
if python3 aws_foundation_gate.py fixtures/foundation-unsafe.json fixtures/plan-destructive.json aws-foundation-policy.json; then
  echo "ERROR: unsafe AWS fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_aws_foundation_gate.py
if command -v terraform >/dev/null 2>&1; then
  terraform fmt -check -recursive
  terraform init -backend=false -input=false
  terraform validate
else
  echo "WARN: Terraform unavailable; HCL validation skipped" >&2
fi
