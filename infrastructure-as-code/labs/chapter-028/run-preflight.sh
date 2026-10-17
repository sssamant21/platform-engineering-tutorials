#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 state_ops_policy.py sample-operations-safe.json sample-safe-plan.json state-ops-policy.json
if python3 state_ops_policy.py sample-operations-unsafe.json sample-destructive-plan.json state-ops-policy.json; then
  echo "ERROR: unsafe operation unexpectedly passed" >&2
  exit 1
fi
python3 -m unittest -v test_state_ops_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
