#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 identity_gate.py fixtures/safe.json policy.json
if python3 identity_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_identity_gate.py test_iam.py test_rbac.py
python3 -m py_compile identity_gate.py iam.py rbac.py test_identity_gate.py test_iam.py test_rbac.py
echo 'Offline checks complete; no IAM, Kubernetes or database mutations'
