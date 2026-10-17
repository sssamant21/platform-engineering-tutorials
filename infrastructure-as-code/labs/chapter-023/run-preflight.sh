#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 data_contract_policy.py sample-contract.json data-contract-policy.json
python3 -m unittest -v test_data_contract_policy.py
CLI="${IAC_CLI:-terraform}"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
  "$CLI" graph > graph.dot
else
  echo "WARN: $CLI unavailable; Terraform validation skipped" >&2
fi
