#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 reliability_gate.py fixtures/safe.json policy.json
if python3 reliability_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_reliability_gate.py test_slo_math.py test_alert_policy.py test_change_gate.py
python3 -m py_compile reliability_gate.py slo_math.py alert_policy.py change_gate.py test_reliability_gate.py test_slo_math.py test_alert_policy.py test_change_gate.py
echo 'Offline SLO checks complete; no live Prometheus, paging, cloud or DB access'
