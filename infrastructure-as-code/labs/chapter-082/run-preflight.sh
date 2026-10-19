#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 policy_gate.py fixtures/safe.json policy.json
if python3 policy_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_policy_gate.py test_exceptions.py test_promotion.py
python3 -m py_compile policy_gate.py exceptions.py promotion.py test_policy_gate.py test_exceptions.py test_promotion.py
echo 'Offline checks complete; no cloud infrastructure modified'
