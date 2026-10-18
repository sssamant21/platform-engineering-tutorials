#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 migration_gate.py fixtures/migration-safe.json fixtures/plan-safe.json migration-policy.json
if python3 migration_gate.py fixtures/migration-unsafe.json fixtures/plan-destructive.json migration-policy.json; then
  echo "ERROR: unsafe migration fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_migration_gate.py
if ! command -v tofu >/dev/null 2>&1; then
  echo "ERROR: OpenTofu CLI required for full lab acceptance" >&2
  exit 1
fi
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
