#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 template_gate.py template.json fixtures/change-safe.json policy.json
if python3 template_gate.py template.json fixtures/change-unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_template_gate.py
echo "PASS: offline checks only; no AWS API calls"
