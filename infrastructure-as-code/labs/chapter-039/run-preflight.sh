#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 compute_gate.py fixtures/compute-safe.json fixtures/plan-safe.json compute-policy.json
if python3 compute_gate.py fixtures/compute-unsafe.json fixtures/plan-destructive.json compute-policy.json; then
  echo "ERROR: unsafe compute fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_compute_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for complete lab acceptance" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
