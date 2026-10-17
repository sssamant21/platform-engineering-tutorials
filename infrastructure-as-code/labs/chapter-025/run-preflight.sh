#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_policy.py provider-manifest.json sample-safe-plan.json capstone-policy.json
if python3 capstone_policy.py provider-manifest.json sample-replacement-plan.json capstone-policy.json; then
  echo "ERROR: destructive replacement unexpectedly passed" >&2
  exit 1
fi
python3 -m unittest -v test_capstone_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
  "$CLI" graph > graph.dot
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
