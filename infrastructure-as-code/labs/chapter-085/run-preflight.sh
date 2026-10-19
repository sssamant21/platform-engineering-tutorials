#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 readiness_gate.py fixtures/safe.json policy.json
if python3 readiness_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_readiness_gate.py test_threat_model.py test_promotion.py test_dr_gate.py
python3 -m py_compile readiness_gate.py threat_model.py promotion.py dr_gate.py test_readiness_gate.py test_threat_model.py test_promotion.py test_dr_gate.py
echo 'Offline checks complete; no cloud, cluster or database mutated'
