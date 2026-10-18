#!/usr/bin/env python3
"""Deterministic local-only dynamic inventory; never queries cloud APIs."""
import json
import sys

HOSTS = ["lab_a", "lab_b"]
def inventory():
    return {
        "_meta": {"hostvars": {host: {"ansible_connection": "local", "ansible_python_interpreter": sys.executable, "lab_tenant": "sandbox"} for host in HOSTS}},
        "sandbox": {"hosts": HOSTS, "vars": {"ansible_connection": "local"}},
        "all": {"children": ["sandbox"]},
    }
if __name__ == "__main__":
    if sys.argv[1:] == ["--list"]:
        print(json.dumps(inventory(), sort_keys=True))
    elif len(sys.argv) == 3 and sys.argv[1] == "--host":
        print(json.dumps(inventory()["_meta"]["hostvars"].get(sys.argv[2], {})))
    else:
        print("Only --list or --host NAME is supported", file=sys.stderr)
        raise SystemExit(2)
