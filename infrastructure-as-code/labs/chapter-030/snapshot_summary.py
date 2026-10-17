"""Emit limited state metadata and SHA-256, never resource attributes or outputs."""
import hashlib,json,sys
from pathlib import Path
def inspect(path):
    raw=Path(path).read_bytes()
    state=json.loads(raw)
    if not isinstance(state,dict) or not isinstance(state.get("resources"),list):
        raise ValueError("invalid state metadata")
    return {"sha256":hashlib.sha256(raw).hexdigest(),"size_bytes":len(raw),"lineage":state.get("lineage"),"serial":state.get("serial"),"terraform_version":state.get("terraform_version"),"resource_count":len(state["resources"])}
if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: python3 snapshot_summary.py <private-state-json>")
    try: print(json.dumps(inspect(sys.argv[1]),indent=2,sort_keys=True))
    except (OSError,ValueError) as exc:
        print("ERROR:",type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
