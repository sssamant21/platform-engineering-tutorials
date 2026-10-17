#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 lifecycle_policy.py sample-safe-plan.json lifecycle-policy.json
if python3 lifecycle_policy.py sample-replace-plan.json lifecycle-policy.json; then
  echo "ERROR: replacement unexpectedly allowed" >&2
  exit 1
fi
python3 -m unittest -v test_lifecycle_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
