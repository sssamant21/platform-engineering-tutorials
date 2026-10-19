#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 acceptance_gate.py fixtures/safe.json policy.json
if python3 acceptance_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_acceptance_gate.py test_drift_assess.py test_slo_assess.py test_incident_assess.py test_remediation_assess.py
python3 -m py_compile acceptance_gate.py drift_assess.py slo_assess.py incident_assess.py remediation_assess.py test_acceptance_gate.py test_drift_assess.py test_slo_assess.py test_incident_assess.py test_remediation_assess.py
echo 'Offline synthetic capstone checks complete; NOT production acceptance'
