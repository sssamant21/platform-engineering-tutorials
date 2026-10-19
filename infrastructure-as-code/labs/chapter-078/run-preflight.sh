#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 governance_gate.py fixtures/safe.json policy.json
if python3 governance_gate.py fixtures/unsafe.json policy.json; then
  echo 'ERROR: unsafe fixture passed' >&2
  exit 1
fi
python3 -m unittest -v test_governance_gate.py test_pipeline.py
python3 -m py_compile governance_gate.py pipeline.py test_governance_gate.py test_pipeline.py
echo 'Offline validation finished; no cloud infrastructure modified'
