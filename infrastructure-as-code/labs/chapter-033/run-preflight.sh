#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 release_gate.py fixtures/release-safe.json fixtures/plan-safe.json version-policy.json
if python3 release_gate.py fixtures/release-unsafe.json fixtures/plan-destructive.json version-policy.json; then
  echo "ERROR: unsafe release fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_release_gate.py
if command -v terraform >/dev/null 2>&1; then
  terraform fmt -recursive
  terraform fmt -check -recursive
  terraform init -backend=false -input=false
  terraform validate
else
  echo "WARN: Terraform unavailable; HCL validation skipped" >&2
fi
