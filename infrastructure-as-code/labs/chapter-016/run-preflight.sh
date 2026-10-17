#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 validate_inputs.py environments/dev.tfvars input-policy.json
python3 validate_inputs.py environments/prod.tfvars input-policy.json
python3 -m unittest -v test_validate_inputs.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: $CLI not found; Terraform validation skipped" >&2
fi
