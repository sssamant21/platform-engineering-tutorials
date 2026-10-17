#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_gate.py fixtures/release-safe.json fixtures/plan-safe.json capstone-policy.json
if python3 capstone_gate.py fixtures/release-unsafe.json fixtures/plan-destructive.json capstone-policy.json; then
  echo "ERROR: unsafe release fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_capstone_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for capstone acceptance" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform test -verbose
