#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_gate.py fixtures/safe.json policy.json
if python3 capstone_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_capstone_gate.py test_coverage_gate.py test_drift_decision.py test_reconciliation.py test_audit_chain.py
python3 -m py_compile capstone_gate.py coverage_gate.py drift_decision.py reconciliation.py audit_chain.py test_capstone_gate.py test_coverage_gate.py test_drift_decision.py test_reconciliation.py test_audit_chain.py
echo 'Offline capstone checks complete; no cloud, Kubernetes or DBRE mutation'
