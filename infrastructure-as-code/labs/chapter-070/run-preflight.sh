#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 multicloud_gate.py fixtures/safe.json policy.json
if python3 multicloud_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_multicloud_gate.py
if command -v az >/dev/null; then
  az bicep build --file azure/main.bicep --outfile /tmp/ch070-azure.json
  az bicep build-params --file azure/parameters/lab.bicepparam --outfile /tmp/ch070-azure-params.json
else
  echo "Azure CLI/Bicep not installed; native compilation skipped"
fi
echo "PASS: offline policy checks; no cloud deployments performed"
