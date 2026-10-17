#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 state_dr_policy.py sample-dr-safe.json sample-state.json dr-policy.json
if python3 state_dr_policy.py sample-dr-unsafe.json sample-state.json dr-policy.json; then
  echo "ERROR: unsafe DR manifest unexpectedly passed" >&2
  exit 1
fi
python3 snapshot_manifest.py sample-state.json >/dev/null
python3 -m unittest -v test_state_dr_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
