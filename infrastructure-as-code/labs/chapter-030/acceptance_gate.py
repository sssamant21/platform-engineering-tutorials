"""Educational fail-closed state/backend capstone gate; does not verify cloud controls."""
import json,re,sys
from pathlib import Path
UUID=re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
SHA=re.compile(r"^[0-9a-fA-F]{64}$")
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_resource_types","required_controls"):
        if not isinstance(policy.get(key),list) or not policy[key] or any(not isinstance(x,str) or not x for x in policy[key]):errors.append("invalid policy "+key)
    for key in ("min_retention_days","max_rpo_minutes","max_rto_minutes"):
        if type(policy.get(key)) is not int or policy[key]<=0:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_distinct_dr_destination","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    if m.get("environment") not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(m.get("change_ticket"),str) or not m["change_ticket"].strip():errors.append("missing change ticket")
    src,dr=m.get("source_backend"),m.get("dr_backend")
    if not isinstance(src,str) or not src.strip() or not isinstance(dr,str) or not dr.strip() or src==dr:errors.append("source and DR backend must be distinct")
    lineage=m.get("lineage")
    if not isinstance(lineage,str) or not UUID.fullmatch(lineage) or m.get("snapshot_lineage")!=lineage:errors.append("invalid or mismatched lineage")
    serial=m.get("serial")
    if type(serial) is not int or serial<0 or type(m.get("snapshot_serial")) is not int or m["snapshot_serial"]!=serial:errors.append("invalid or mismatched serial")
    digest=m.get("snapshot_sha256")
    if not isinstance(digest,str) or not SHA.fullmatch(digest):errors.append("invalid snapshot digest")
    for field,limit,minimum in (("retention_days",policy["min_retention_days"],True),("rpo_minutes",policy["max_rpo_minutes"],False),("rto_minutes",policy["max_rto_minutes"],False)):
        value=m.get(field)
        if type(value) is not int or value<=0 or (value<limit if minimum else value>limit):errors.append("invalid "+field)
    addresses=m.get("resource_addresses")
    if not isinstance(addresses,list) or not addresses or any(not isinstance(a,str) or not a.strip() for a in addresses):errors.append("invalid resource addresses")
    elif len(addresses)!=len(set(addresses)):errors.append("duplicate resource addresses")
    controls=m.get("controls")
    if not isinstance(controls,dict):errors.append("controls missing");controls={}
    for control in policy["required_controls"]:
        if controls.get(control) is not True:errors.append("required control missing: "+control)
    changes=plan.get("resource_changes")
    if not isinstance(changes,list):return errors+["plan resource_changes must be list"]
    for i,item in enumerate(changes):
        if not isinstance(item,dict):errors.append("invalid plan resource "+str(i));continue
        if item.get("type") not in policy["allowed_resource_types"]:errors.append("unapproved resource type "+str(i))
        if not isinstance(item.get("address"),str) or not item["address"]:errors.append("missing plan address "+str(i))
        change=item.get("change")
        actions=change.get("actions") if isinstance(change,dict) else None
        if not isinstance(actions,list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):errors.append("invalid plan actions "+str(i))
        elif "delete" in actions:errors.append("destructive delete/replacement "+str(i))
    return errors
def main(argv):
    if len(argv)!=4:print("Usage: python3 acceptance_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,plan,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,plan,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for error in errors:print("DENY:",error)
    if errors:return 1
    print("PASS: declared capstone controls and plan")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
