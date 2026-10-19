#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 gate.py fixtures/safe.json policy.json
if python3 gate.py fixtures/unsafe.json policy.json; then echo 'FAIL: unsafe fixture passed' >&2; exit 1; fi
python3 -m unittest -v test_gate.py test_pipeline.py
python3 -m py_compile gate.py pipeline.py test_gate.py test_pipeline.py
echo 'PASS: offline only; no cloud changes'
