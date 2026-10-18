#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 tenant_gate.py fixtures/tenant-safe.json fixtures/plan-safe.json tenant-policy.json
if python3 tenant_gate.py fixtures/tenant-unsafe.json fixtures/plan-destructive.json tenant-policy.json; then
  echo "ERROR: unsafe tenant fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_tenant_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for full lab acceptance" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
