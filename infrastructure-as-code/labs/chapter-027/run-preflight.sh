#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 backend_security.py backend-inventory.json backend-policy.json
if python3 backend_security.py backend-inventory-unsafe.json backend-policy.json; then
  echo "ERROR: unsafe backend unexpectedly passed" >&2
  exit 1
fi
python3 -m unittest -v test_backend_security.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
