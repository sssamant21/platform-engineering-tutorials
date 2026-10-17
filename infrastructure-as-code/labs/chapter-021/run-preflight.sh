#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 provider_policy.py provider-manifest-good.json provider-policy.json
if python3 provider_policy.py provider-manifest-bad.json provider-policy.json; then
  echo "ERROR: unsafe manifest unexpectedly passed" >&2
  exit 1
fi
python3 -m unittest -v test_provider_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
  "$CLI" providers
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
