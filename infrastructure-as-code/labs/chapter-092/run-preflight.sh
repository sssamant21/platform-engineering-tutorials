#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 drift_gate.py fixtures/safe.json policy.json
if python3 drift_gate.py fixtures/unsafe.json policy.json; then echo 'ERROR: unsafe fixture accepted' >&2; exit 1; fi
python3 -m unittest -v test_drift_gate.py test_snapshot_diff.py test_change_intel.py test_remediation_gate.py
python3 -m py_compile drift_gate.py snapshot_diff.py change_intel.py remediation_gate.py test_drift_gate.py test_snapshot_diff.py test_change_intel.py test_remediation_gate.py
echo 'Offline drift checks complete; no cloud, IaC or database mutation'
