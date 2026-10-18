#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 terragrunt_gate.py fixtures/terragrunt-safe.json fixtures/plan-safe.json terragrunt-policy.json
if python3 terragrunt_gate.py fixtures/terragrunt-unsafe.json fixtures/plan-destructive.json terragrunt-policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_terragrunt_gate.py
if ! command -v tofu >/dev/null 2>&1; then
  echo "ERROR: OpenTofu CLI required for full lab acceptance" >&2
  exit 1
fi
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
