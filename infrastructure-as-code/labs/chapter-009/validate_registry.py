"""Educational registry policy validator; not a binary signature verifier."""
import json
import re
import sys
from pathlib import Path

SOURCE = re.compile(r"^[a-z0-9.-]+/[a-z0-9_-]+/[a-z0-9_-]+$")
def validate(data):
    if not isinstance(data, dict):
        return ["policy must be object"]
    errors = []
    allowed = data.get("allowed_registries")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(x, str) or not x for x in allowed):
        errors.append("allowed_registries must be nonempty list")
        allowed = []
    if data.get("verify_checksums") is not True:
        errors.append("checksum verification required")
    cache = data.get("cache")
    if not isinstance(cache, dict) or cache.get("shared_writable") is not False:
        errors.append("shared writable cache prohibited")
    mirror = data.get("mirror")
    if not isinstance(mirror, dict):
        errors.append("mirror configuration required")
    elif mirror.get("enabled") is True and mirror.get("trusted") is not True:
        errors.append("enabled mirror must be trusted")
    providers = data.get("providers")
    if not isinstance(providers, list) or not providers:
        errors.append("providers must be nonempty list")
        providers = []
    seen = set()
    for i, p in enumerate(providers):
        if not isinstance(p, dict):
            errors.append(f"providers[{i}] must be object")
            continue
        source = p.get("source")
        if not isinstance(source, str) or not SOURCE.fullmatch(source):
            errors.append(f"providers[{i}] invalid source")
        else:
            if source in seen:
                errors.append(f"providers[{i}] duplicate source")
            seen.add(source)
            if source.split("/")[0] not in allowed:
                errors.append(f"providers[{i}] unapproved registry")
        if not isinstance(p.get("constraint"), str) or not p["constraint"].strip():
            errors.append(f"providers[{i}] missing constraint")
        if p.get("lockfile_committed") is not True:
            errors.append(f"providers[{i}] lockfile required")
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 validate_registry.py registry-policy.json")
        return 1
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("DENY:", exc)
        return 1
    errors = validate(data)
    for e in errors:
        print("DENY:", e)
    if errors:
        return 1
    print("PASS: sample provider registry policy satisfied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
