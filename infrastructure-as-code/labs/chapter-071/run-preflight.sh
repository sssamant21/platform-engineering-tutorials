#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 pulumi_gate.py fixtures/safe.json policy.json
if python3 pulumi_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_pulumi_gate.py
python3 -m py_compile __main__.py pulumi_gate.py test_pulumi_gate.py
if command -v pulumi >/dev/null; then
  pulumi version
else
  echo "Pulumi CLI not installed; native preview/up intentionally skipped"
fi
echo "PASS: offline policy checks; no infrastructure changed"
