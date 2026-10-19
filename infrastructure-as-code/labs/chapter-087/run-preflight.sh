#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 integration_gate.py fixtures/safe.json policy.json
if python3 integration_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_integration_gate.py test_lifecycle.py test_budget_gate.py test_evidence_gate.py
python3 -m py_compile integration_gate.py lifecycle.py budget_gate.py evidence_gate.py test_integration_gate.py test_lifecycle.py test_budget_gate.py test_evidence_gate.py
echo 'Offline checks complete; no cloud, Kubernetes or database mutation'
