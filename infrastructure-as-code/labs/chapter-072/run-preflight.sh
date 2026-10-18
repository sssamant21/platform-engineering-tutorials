#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 resource_gate.py fixtures/safe.json policy.json
if python3 resource_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_resource_gate.py
python3 -m py_compile components.py __main__.py resource_gate.py test_resource_gate.py
if python3 -c 'import pulumi' >/dev/null 2>&1; then
  python3 -m unittest -v test_components.py
else
  echo "Pulumi Python SDK unavailable; mocked component tests skipped"
fi
echo "Offline preflight complete; no cloud resources changed"
