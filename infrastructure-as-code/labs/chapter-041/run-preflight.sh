#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 azure_gate.py fixtures/azure-safe.json fixtures/plan-safe.json azure-policy.json
if python3 azure_gate.py fixtures/azure-unsafe.json fixtures/plan-destructive.json azure-policy.json; then
  echo "ERROR: unsafe Azure fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_azure_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for full lab acceptance" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
