#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 test_gate.py fixtures/safe.json policy.json
if python3 test_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_test_gate.py test_coverage_gate.py test_pipeline.py
python3 -m py_compile test_gate.py coverage_gate.py pipeline.py test_test_gate.py test_coverage_gate.py test_pipeline.py
echo 'Offline checks complete; no cloud or database mutation'
