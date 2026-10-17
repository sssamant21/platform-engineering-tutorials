"""Safe local desired-state drift demo. Never use this example on production paths."""
import argparse
from pathlib import Path

DESIRED = "owner=sre-platform\nmanaged_by=python-reconciler\n"

def permitted(path: Path) -> bool:
    return "iac-chapter-003-python" in path.resolve().parts and path.name == "desired.txt"

def reconcile(path: Path, apply: bool = False) -> int:
    if not permitted(path):
        raise ValueError("Only iac-chapter-003-python/desired.txt is permitted")
    actual = path.read_text(encoding="utf-8") if path.exists() else None
    if actual == DESIRED:
        print("IN_SYNC")
        return 0
    print("DRIFT: desired content differs from observed content")
    if not apply:
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DESIRED, encoding="utf-8")
    print("RECONCILED")
    return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        return reconcile(args.path, args.apply)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
