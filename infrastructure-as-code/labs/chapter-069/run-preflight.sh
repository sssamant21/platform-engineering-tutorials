#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 deployment_gate.py fixtures/safe.json policy.json
if python3 deployment_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_deployment_gate.py
if command -v az >/dev/null; then
  az bicep build --file main.bicep --outfile /tmp/ch069-main.json
  az bicep build-params --file parameters/lab.bicepparam --outfile /tmp/ch069-params.json
else
  echo "Azure CLI/Bicep not installed; native compilation skipped"
fi
echo "PASS: offline checks only; no Azure deployment performed"
