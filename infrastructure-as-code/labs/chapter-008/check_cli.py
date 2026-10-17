"""Compare installed Terraform/OpenTofu CLI with an approved manifest."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

def parse_version(output):
    match = re.search(r"(?i)\b(?:terraform|opentofu)\s+v?([0-9]+\.[0-9]+\.[0-9]+)", output)
    return match.group(1) if match else None

def compare(expected, output):
    found = parse_version(output)
    return found == expected, found

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 check_cli.py toolchain.json")
        return 1
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        engine = data["engine"]
        expected = data["cli_version"]
        if engine not in ("terraform", "tofu"):
            raise ValueError("unsupported engine")
        binary = shutil.which(engine)
        if not binary:
            print(f"FAIL: {engine} not found in PATH")
            return 1
        proc = subprocess.run([binary, "version"], capture_output=True, text=True, timeout=10, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {engine} version command returned {proc.returncode}")
            return 1
        match, actual = compare(expected, proc.stdout)
        print(f"{'PASS' if match else 'FAIL'}: {engine} expected={expected} actual={actual or 'unknown'}")
        return 0 if match else 1
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
