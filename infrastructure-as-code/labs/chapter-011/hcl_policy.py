"""Educational text-based source policy, not an HCL parser."""
import re
import sys
from pathlib import Path

REQUIRED = ("versions.tf", "variables.tf", "main.tf", "outputs.tf")
SECRET = re.compile(r'(?im)^\s*(?:password|secret|access_key|secret_key|api_token)\s*=\s*"[^"]+"')
VAR_BLOCK = re.compile(r'variable\s+"[^"]+"\s*\{', re.M)

def validate(root):
    root = Path(root)
    errors = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"missing {name}")
    for path in root.glob("*.tf"):
        if SECRET.search(path.read_text(encoding="utf-8")):
            errors.append(f"{path.name}: apparent hard-coded credential")
    versions = root / "versions.tf"
    if versions.is_file() and "required_version" not in versions.read_text(encoding="utf-8"):
        errors.append("versions.tf: missing required_version")
    variables = root / "variables.tf"
    if variables.is_file():
        source = variables.read_text(encoding="utf-8")
        blocks = VAR_BLOCK.findall(source)
        if not blocks:
            errors.append("variables.tf: no variables")
        if len(re.findall(r"(?m)^\s*type\s*=", source)) < len(blocks):
            errors.append("variables.tf: untyped variable")
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 hcl_policy.py <root>")
        return 1
    try:
        errors = validate(argv[1])
    except OSError as exc:
        print("DENY:", exc)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational HCL source policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
