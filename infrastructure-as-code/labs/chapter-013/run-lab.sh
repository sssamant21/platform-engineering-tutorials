#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CLI="${IAC_CLI:-terraform}"
command -v "$CLI" >/dev/null || { echo "Missing $CLI" >&2; exit 1; }
python3 plan_policy.py sample-plan.json plan-policy.json
python3 -m unittest -v test_plan_policy.py
"$CLI" fmt -check
"$CLI" init -input=false
"$CLI" validate
"$CLI" plan -out=chapter013.tfplan
"$CLI" show -json chapter013.tfplan > local-plan.json
python3 plan_policy.py local-plan.json plan-policy.json
printf '%s\n' "PASS: pre-apply lab checks; inspect and apply chapter013.tfplan manually"
