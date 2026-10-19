#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 delivery_gate.py fixtures/safe.json policy.json
if python3 delivery_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_delivery_gate.py test_pipeline.py
python3 -m py_compile __main__.py automation_preview.py delivery_gate.py test_delivery_gate.py pipeline_sim.py test_pipeline.py
echo "PASS: offline policy and pipeline checks; no cloud deployments"
