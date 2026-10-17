#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 quality_gate.py fixtures/architecture-safe.json fixtures/plan-safe.json quality-policy.json
if python3 quality_gate.py fixtures/architecture-unsafe.json fixtures/plan-destructive.json quality-policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_quality_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for native tests" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform test -verbose
