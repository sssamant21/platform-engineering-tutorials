"""Fail-closed educational module contract manifest and plan validator."""
import json,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for k in ("allowed_environments","required_modules","allowed_resource_types"):
        if not isinstance(policy.get(k),list) or not policy[k]:errors.append("invalid policy "+k)
    for k in ("required_inputs","required_outputs"):
        if not isinstance(policy.get(k),dict):errors.append("invalid policy "+k)
    if type(policy.get("supported_schema_version")) is not int or policy["supported_schema_version"]<1:errors.append("invalid schema policy")
    for k in ("require_ticket","require_owners","require_nonnullable_inputs","deny_destructive_actions"):
        if policy.get(k) is not True:errors.append("fail-open policy "+k)
    if errors:return errors
    if m.get("environment") not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(m.get("change_ticket"),str) or not m["change_ticket"].strip():errors.append("missing change ticket")
    modules=m.get("modules")
    if not isinstance(modules,list) or not modules:return errors+["modules must be nonempty list"]
    names=[];graph={}
    for i,mod in enumerate(modules):
        if not isinstance(mod,dict):errors.append("invalid module "+str(i));continue
        name=mod.get("name")
        if not isinstance(name,str) or not name:errors.append("missing module name "+str(i));continue
        names.append(name)
        if not isinstance(mod.get("owner"),str) or not mod["owner"].strip():errors.append("missing owner "+name)
        if type(mod.get("schema_version")) is not int or mod["schema_version"]!=policy["supported_schema_version"]:errors.append("incompatible schema "+name)
        for direction,required in (("inputs",policy["required_inputs"].get(name,[])),("outputs",policy["required_outputs"].get(name,[]))):
            values=mod.get(direction)
            if not isinstance(values,list) or any(not isinstance(v,str) for v in values) or not set(required).issubset(set(values)):
                errors.append("missing "+direction+" contract "+name)
        nullable=mod.get("nullable_inputs")
        if not isinstance(nullable,list) or nullable:errors.append("nullable mandatory inputs "+name)
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
    elif m.get("environment")=="prod":
        if type(db.get("replicas")) is not int or db["replicas"]<3:errors.append("production replicas below three")
        if db.get("backup_enabled") is not True:errors.append("production backup required")
        if db.get("encryption_enabled") is not True:errors.append("production encryption required")
    changes=plan.get("resource_changes")
    if not isinstance(changes,list):return errors+["plan resource_changes must be list"]
    for i,r in enumerate(changes):
        if not isinstance(r,dict):errors.append("invalid plan resource "+str(i));continue
        if r.get("type") not in policy["allowed_resource_types"]:errors.append("unapproved resource type "+str(i))
        if not isinstance(r.get("address"),str) or not r["address"]:errors.append("missing address "+str(i))
        change=r.get("change");actions=change.get("actions") if isinstance(change,dict) else None
        if not isinstance(actions,list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):errors.append("invalid actions "+str(i))
        elif "delete" in actions:errors.append("delete/replacement denied "+str(i))
    return errors
def main(argv):
    if len(argv)!=4:print("Usage: python3 contract_policy.py <manifest> <plan> <policy>");return 1
    try:
        m,plan,policy=[json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors=validate(m,plan,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared module contracts and plan")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
