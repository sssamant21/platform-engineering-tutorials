#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 preflight.py readiness.json
python3 -m unittest -v test_preflight.py
if command -v terraform >/dev/null 2>&1; then
  terraform fmt -check
  terraform init -backend=false -input=false
  terraform validate
elif command -v tofu >/dev/null 2>&1; then
  tofu fmt -check
  tofu init -backend=false -input=false
  tofu validate
else
  echo "WARN: Terraform/OpenTofu not installed; skipped HCL validation" >&2
fi
