#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 evidence_gate.py fixtures/safe.json policy.json
if python3 evidence_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_evidence_gate.py test_savings.py test_commitments.py test_optimization_gate.py test_reconcile.py
python3 -m py_compile evidence_gate.py savings.py commitments.py optimization_gate.py reconcile.py test_evidence_gate.py test_savings.py test_commitments.py test_optimization_gate.py test_reconcile.py
echo 'Offline synthetic rightsizing and commitment checks complete; NOT native FinOps acceptance'
