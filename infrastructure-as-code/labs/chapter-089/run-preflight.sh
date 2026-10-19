#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 drift_gate.py fixtures/safe.json policy.json
if python3 drift_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_drift_gate.py test_risk_engine.py test_remediation.py test_audit_chain.py
python3 -m py_compile drift_gate.py risk_engine.py remediation.py audit_chain.py test_drift_gate.py test_risk_engine.py test_remediation.py test_audit_chain.py
echo 'Offline drift checks complete; no cloud or database mutation'
