#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_gate.py fixtures/capstone-safe.json fixtures/plan-safe.json capstone-policy.json
if python3 capstone_gate.py fixtures/capstone-unsafe.json fixtures/plan-destructive.json capstone-policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_capstone_gate.py
if ! command -v tofu >/dev/null 2>&1; then
  echo "ERROR: OpenTofu CLI required for full lab acceptance" >&2
  exit 1
fi
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
