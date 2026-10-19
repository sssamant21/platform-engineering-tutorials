#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_gate.py fixtures/safe.json policy.json
if python3 capstone_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture passed' >&2; exit 1; fi
python3 -m unittest -v test_capstone_gate.py test_delivery.py test_dr.py
python3 -m py_compile capstone_gate.py delivery.py dr.py test_capstone_gate.py test_delivery.py test_dr.py
echo 'Offline checks complete; no cloud, host or cluster changes'
