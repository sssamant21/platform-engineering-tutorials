#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 ansible_gate.py fixtures/safe.json policy.json
if python3 ansible_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_ansible_gate.py
command -v ansible-playbook >/dev/null || { echo "ansible-core required" >&2; exit 1; }
ansible-inventory -i inventory.ini --list
ansible-playbook -i inventory.ini playbooks/site.yml --syntax-check
ansible-playbook -i inventory.ini playbooks/site.yml --check --diff
ansible-playbook -i inventory.ini playbooks/site.yml
ansible-playbook -i inventory.ini playbooks/site.yml
