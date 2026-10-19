#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 telemetry_gate.py fixtures/safe.json policy.json
if python3 telemetry_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_telemetry_gate.py test_slo_engine.py test_cardinality_gate.py test_dashboard_gate.py
python3 -m py_compile telemetry_gate.py slo_engine.py cardinality_gate.py dashboard_gate.py test_telemetry_gate.py test_slo_engine.py test_cardinality_gate.py test_dashboard_gate.py
echo 'Offline observability checks complete; no Prometheus, OTLP, cloud or DB access'
