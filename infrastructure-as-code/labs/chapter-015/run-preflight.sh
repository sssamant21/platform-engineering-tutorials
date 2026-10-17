#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_policy.py sample-plan.json change-policy.json
python3 -m unittest -v test_capstone_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: $CLI unavailable; HCL validation skipped" >&2
fi
