#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 compliance_gate.py fixtures/safe.json policy.json
if python3 compliance_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_compliance_gate.py test_mapping_gate.py test_evidence_chain.py test_exception_gate.py
python3 -m py_compile compliance_gate.py mapping_gate.py evidence_chain.py exception_gate.py test_compliance_gate.py test_mapping_gate.py test_evidence_chain.py test_exception_gate.py
echo 'Offline compliance tests complete; no external certification or cloud mutation'
