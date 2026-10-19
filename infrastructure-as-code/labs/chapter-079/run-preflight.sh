#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 delivery_gate.py fixtures/safe.json policy.json
if python3 delivery_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture passed' >&2; exit 1; fi
python3 -m unittest -v test_delivery_gate.py test_promotion.py
python3 -m py_compile delivery_gate.py promotion.py test_delivery_gate.py test_promotion.py
echo 'Offline governance complete; no hosts or clusters contacted'
