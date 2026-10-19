#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 security_gate.py fixtures/safe.json policy.json
if python3 security_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_security_gate.py test_findings.py test_supply_chain.py
python3 -m py_compile security_gate.py findings.py supply_chain.py test_security_gate.py test_findings.py test_supply_chain.py
echo 'Offline checks complete; no infrastructure or real credentials touched'
