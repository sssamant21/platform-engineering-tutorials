"""Emit limited non-secret metadata and SHA-256 from a local private state snapshot."""
import hashlib
import json
import sys
from pathlib import Path

def inspect(path):
    raw = Path(path).read_bytes()
    state = json.loads(raw)
    if not isinstance(state, dict):
        raise ValueError("state must be JSON object")
    resources = state.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError("resources must be list")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "lineage": state.get("lineage"),
        "serial": state.get("serial"),
        "terraform_version": state.get("terraform_version"),
        "resource_count": len(resources),
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 snapshot_manifest.py <private-state-json>", file=sys.stderr)
        raise SystemExit(1)
    try:
        print(json.dumps(inspect(sys.argv[1]), indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        print("ERROR:", type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
