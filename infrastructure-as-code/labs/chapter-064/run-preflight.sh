#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 governance_gate.py fixtures/safe.json policy.json
if python3 governance_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_governance_gate.py
command -v ansible-playbook >/dev/null || { echo "ansible-core required" >&2; exit 1; }
python3 inventory/dynamic_inventory.py --list
ansible-inventory -i inventory/dynamic_inventory.py --list
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml --syntax-check
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml --check
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml
