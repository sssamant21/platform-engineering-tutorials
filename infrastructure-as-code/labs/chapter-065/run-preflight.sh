#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 capstone_gate.py fixtures/safe.json policy.json
if python3 capstone_gate.py fixtures/unsafe.json policy.json; then
  echo "ERROR: unsafe fixture passed" >&2
  exit 1
fi
python3 -m unittest -v test_capstone_gate.py
command -v ansible-playbook >/dev/null || { echo "ansible-core required" >&2; exit 1; }
ansible-inventory -i inventory/hosts.ini --list
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml --syntax-check
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml --check --diff
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml
bash backup-restore-drill.sh
if ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml -e inject_failure=true; then
  echo "ERROR: injected failure passed" >&2
  exit 1
fi
