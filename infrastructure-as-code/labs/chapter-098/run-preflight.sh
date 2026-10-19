#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 billing_gate.py fixtures/safe.json policy.json
if python3 billing_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_billing_gate.py test_forecast.py test_budget_gate.py test_anomaly.py test_automation_gate.py
python3 -m py_compile billing_gate.py forecast.py budget_gate.py anomaly.py automation_gate.py test_billing_gate.py test_forecast.py test_budget_gate.py test_anomaly.py test_automation_gate.py
echo 'Offline synthetic forecast and budget checks complete; NOT native FinOps acceptance'
