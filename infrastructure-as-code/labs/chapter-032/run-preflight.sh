#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 contract_policy.py fixtures/contract-safe.json fixtures/plan-safe.json contract-policy.json
if python3 contract_policy.py fixtures/contract-unsafe.json fixtures/plan-destructive.json contract-policy.json; then
  echo "ERROR: unsafe contract fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_contract_policy.py
CLI="terraform"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -recursive
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: terraform unavailable; Terraform validation skipped" >&2
fi
