#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 stackset_gate.py parent-template.json child-template.json fixtures/safe.json policy.json
if python3 stackset_gate.py parent-template.json child-template.json fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_stackset_gate.py
echo "PASS: offline checks only; no AWS API calls"
