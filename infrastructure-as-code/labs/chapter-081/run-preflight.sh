#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 security_gate.py fixtures/safe.json policy.json
if python3 security_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture passed' >&2; exit 1; fi
python3 -m unittest -v test_security_gate.py test_threat_model.py test_rotation.py
python3 -m py_compile security_gate.py threat_model.py rotation.py test_security_gate.py test_threat_model.py test_rotation.py
echo 'Offline checks complete; no cloud, cluster, database or secrets touched'
