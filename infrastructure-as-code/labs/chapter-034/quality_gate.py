"""Educational fail-closed declared architecture and Terraform plan policy."""
import json,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","required_modules","required_attestations","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    if type(policy.get("supported_schema_version")) is not int or policy["supported_schema_version"]<1:errors.append("invalid schema policy")
    for key in ("require_ticket","require_owner","require_state_isolation","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(m.get("change_ticket"),str) or not m["change_ticket"].strip():errors.append("missing change ticket")
    if not isinstance(m.get("release_owner"),str) or not m["release_owner"].strip():errors.append("missing release owner")
    if m.get("state_namespace")!="iac-"+str(env):errors.append("state isolation mismatch")
    attestations=m.get("attestations")
    if not isinstance(attestations,dict):attestations={}
    for key in policy["required_attestations"]:
        if attestations.get(key) is not True:errors.append("missing attestation "+key)
    mods=m.get("modules")
    if not isinstance(mods,list) or not mods:return errors+["modules must be nonempty list"]
    names=[];graph={}
    for i,mod in enumerate(mods):
        if not isinstance(mod,dict):errors.append("invalid module "+str(i));continue
        name=mod.get("name")
        if not isinstance(name,str) or not name:errors.append("missing module name "+str(i));continue
        names.append(name)
        if not isinstance(mod.get("owner"),str) or not mod["owner"].strip():errors.append("missing module owner "+name)
        if type(mod.get("schema_version")) is not int or mod["schema_version"]!=policy["supported_schema_version"]:errors.append("schema mismatch "+name)
        deps=mod.get("depends_on")
        if not isinstance(deps,list) or any(not isinstance(d,str) for d in deps):errors.append("invalid dependencies "+name)
        else:graph[name]=deps
    if len(names)!=len(set(names)):errors.append("duplicate module name")
    if not set(policy["required_modules"]).issubset(set(names)):errors.append("missing required module")
    visited=set();active=set()
    def visit(node):
        if node in active:errors.append("dependency cycle "+node);return
        if node in visited:return
        active.add(node)
        for dep in graph.get(node,[]):
            if dep not in graph:errors.append("unknown dependency "+dep)
            else:visit(dep)
        active.remove(node);visited.add(node)
    for node in graph:visit(node)
    if "database" in graph and "network" not in graph["database"]:errors.append("database missing network dependency")
    if "application" in graph and "database" not in graph["application"]:errors.append("application missing database dependency")
    db=m.get("database")
    if not isinstance(db,dict):errors.append("database controls missing")
    elif env=="prod":
        if type(db.get("replicas")) is not int or db["replicas"]<3:errors.append("production replicas below three")
        if db.get("backup_enabled") is not True:errors.append("production backup required")
        if db.get("encryption_enabled") is not True:errors.append("production encryption required")
    changes=plan.get("resource_changes")
    if not isinstance(changes,list):return errors+["plan resource_changes must be list"]
    for i,r in enumerate(changes):
        if not isinstance(r,dict):errors.append("invalid resource change "+str(i));continue
        if r.get("type") not in policy["allowed_resource_types"]:errors.append("unapproved resource type "+str(i))
        if not isinstance(r.get("address"),str) or not r["address"]:errors.append("missing address "+str(i))
        change=r.get("change");actions=change.get("actions") if isinstance(change,dict) else None
        if not isinstance(actions,list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):errors.append("invalid actions "+str(i))
        elif "delete" in actions:errors.append("delete/replacement denied "+str(i))
    return errors
def main(argv):
    if len(argv)!=4:print("Usage: python3 quality_gate.py <architecture> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared architecture and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
