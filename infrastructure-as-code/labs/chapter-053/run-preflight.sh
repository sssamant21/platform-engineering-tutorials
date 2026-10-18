#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 workload_gate.py fixtures/workload-safe.json fixtures/plan-safe.json workload-policy.json
if python3 workload_gate.py fixtures/workload-unsafe.json fixtures/plan-destructive.json workload-policy.json; then
  echo "ERROR: unsafe workload fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_workload_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for full lab acceptance" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
