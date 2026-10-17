"""Educational IaC toolchain manifest policy. Does not inspect a real lockfile."""
import json
import re
import sys
from pathlib import Path

SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
DIGEST = re.compile(r"^.+@sha256:[0-9a-f]{64}$")

def validate(data):
    if not isinstance(data, dict):
        return ["manifest must be object"]
    errors = []
    if data.get("engine") not in ("terraform", "tofu"):
        errors.append("engine must be terraform or tofu")
    if not isinstance(data.get("cli_version"), str) or not SEMVER.fullmatch(data["cli_version"]):
        errors.append("cli_version must be exact X.Y.Z")
    if not isinstance(data.get("ci_image"), str) or not DIGEST.fullmatch(data["ci_image"]):
        errors.append("ci_image must include immutable sha256 digest")
    if data.get("module_sources_pinned") is not True:
        errors.append("module sources must be pinned")
    providers = data.get("providers")
    if not isinstance(providers, list):
        errors.append("providers must be a list")
        providers = []
    for i, p in enumerate(providers):
        if not isinstance(p, dict):
            errors.append(f"providers[{i}] must be object")
            continue
        if not isinstance(p.get("source"), str) or "/" not in p["source"]:
            errors.append(f"providers[{i}] invalid source")
        if not isinstance(p.get("constraint"), str) or not p["constraint"].strip():
            errors.append(f"providers[{i}] missing constraint")
        if p.get("lockfile_committed") is not True:
            errors.append(f"providers[{i}] lockfile must be committed")
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 validate_toolchain.py toolchain.json")
        return 1
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DENY: {exc}")
        return 1
    errors = validate(data)
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: toolchain policy manifest valid (not an installed-tool verification)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
