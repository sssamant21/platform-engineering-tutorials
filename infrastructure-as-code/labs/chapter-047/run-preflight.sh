#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 network_gate.py fixtures/network-safe.json fixtures/plan-safe.json network-policy.json
if python3 network_gate.py fixtures/network-unsafe.json fixtures/plan-destructive.json network-policy.json; then
  echo "ERROR: unsafe network fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_network_gate.py
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform >=1.7 required for full lab acceptance" >&2
  exit 1
fi
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
