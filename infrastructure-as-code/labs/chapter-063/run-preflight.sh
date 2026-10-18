#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 execution_gate.py fixtures/safe.json policy.json
if python3 execution_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_execution_gate.py
command -v ansible-playbook >/dev/null || { echo "ansible-core required" >&2; exit 1; }
ansible-inventory -i inventory.ini --list
ansible-playbook -i inventory.ini playbooks/rolling.yml --syntax-check
ansible-playbook -i inventory.ini playbooks/rolling.yml --check --diff
ansible-playbook -i inventory.ini playbooks/rolling.yml
ansible-playbook -i inventory.ini playbooks/rolling.yml
if ansible-playbook -i inventory.ini playbooks/rolling.yml -e inject_failure=true; then
  echo "ERROR: injected failure passed" >&2
  exit 1
fi
