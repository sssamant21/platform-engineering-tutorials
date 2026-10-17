#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 acceptance_gate.py fixtures/acceptance-safe.json fixtures/plan-safe.json policy/acceptance-policy.json
if python3 acceptance_gate.py fixtures/acceptance-unsafe.json fixtures/plan-destructive.json policy/acceptance-policy.json; then
  echo "ERROR: unsafe acceptance fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_acceptance_gate.py
CLI="terraform"
if command -v "$CLI" >/dev/null 2>&1; then
  "$CLI" fmt -check -recursive
  "$CLI" init -backend=false -input=false
  "$CLI" validate
else
  echo "WARN: terraform unavailable; Terraform validation skipped" >&2
fi
