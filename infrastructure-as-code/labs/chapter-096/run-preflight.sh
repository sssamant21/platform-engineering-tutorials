#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 billing_gate.py fixtures/safe.json policy.json
if python3 billing_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_billing_gate.py test_allocate.py test_anomaly.py test_optimization.py
python3 -m py_compile billing_gate.py allocate.py anomaly.py optimization.py test_billing_gate.py test_allocate.py test_anomaly.py test_optimization.py
echo 'Offline synthetic FinOps checks complete; NOT native billing acceptance'
