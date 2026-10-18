#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 orchestration_gate.py fixtures/orchestration-safe.json fixtures/plan-safe.json orchestration-policy.json
if python3 orchestration_gate.py fixtures/orchestration-unsafe.json fixtures/plan-destructive.json orchestration-policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_orchestration_gate.py
if ! command -v tofu >/dev/null 2>&1; then
  echo "ERROR: OpenTofu CLI required for full lab acceptance" >&2
  exit 1
fi
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
