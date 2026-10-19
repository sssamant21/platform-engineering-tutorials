#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 incident_gate.py fixtures/safe.json policy.json
if python3 incident_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_incident_gate.py test_correlate.py test_timeline.py test_reliability.py
python3 -m py_compile incident_gate.py correlate.py timeline.py reliability.py test_incident_gate.py test_correlate.py test_timeline.py test_reliability.py
echo 'Offline incident checks complete; no native cloud, CI or DB access'
