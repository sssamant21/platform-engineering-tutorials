#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 ledger_gate.py fixtures/safe.json policy.json
if python3 ledger_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_ledger_gate.py test_allocate.py test_reconcile.py test_chargeback_gate.py
python3 -m py_compile ledger_gate.py allocate.py reconcile.py chargeback_gate.py test_ledger_gate.py test_allocate.py test_reconcile.py test_chargeback_gate.py
echo 'Offline synthetic chargeback checks complete; NOT native finance acceptance'
