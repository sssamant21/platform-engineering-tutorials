"""Read-only IaC workstation audit. Uses Python standard library only."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

def check_tool(item, which=shutil.which, runner=subprocess.run):
    if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("command"), str):
        return False, "invalid tool specification"
    args = item.get("args", ["--version"])
    if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
        return False, "invalid command arguments"
    binary = which(item["command"])
    if binary is None:
        return False, "not found in PATH"
    try:
        result = runner([binary, *args], capture_output=True, text=True, timeout=8, check=False)
        summary = (result.stdout or result.stderr).strip().splitlines()
        if result.returncode != 0:
            return False, f"version command returned {result.returncode}"
        return True, (summary[0][:160] if summary else "command succeeded")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, type(exc).__name__

def audit(manifest, checker=check_tool):
    errors = []
    notes = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"], notes
    for group in ("required", "optional", "iac_engines"):
        if not isinstance(manifest.get(group), list):
            errors.append(f"{group} must be a list")
    if errors:
        return errors, notes
    for item in manifest["required"]:
        ok, detail = checker(item)
        notes.append(("PASS" if ok else "FAIL", item.get("name", "unknown"), detail))
        if not ok:
            errors.append(f"required tool missing: {item.get('name')}")
    for item in manifest["optional"]:
        ok, detail = checker(item)
        notes.append(("PASS" if ok else "WARN", item.get("name", "unknown"), detail))
    engines = [checker(item) for item in manifest["iac_engines"]]
    for item, (ok, detail) in zip(manifest["iac_engines"], engines):
        notes.append(("PASS" if ok else "WARN", item.get("name", "unknown"), detail))
    if not engines or not any(ok for ok, _ in engines):
        errors.append("at least one IaC engine (Terraform/OpenTofu) is required")
    return errors, notes

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 validate_toolchain.py workstation-manifest.json")
        return 1
    try:
        manifest = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read manifest: {exc}")
        return 1
    errors, notes = audit(manifest)
    for status, name, detail in notes:
        print(f"{status}: {name}: {detail}")
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print("PASS: required toolchain checks satisfied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
