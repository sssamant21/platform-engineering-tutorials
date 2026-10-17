"""Educational fail-closed module architecture manifest and Terraform plan gate."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
PIN=re.compile(r"(?:\?ref=(?:[0-9a-fA-F]{40}|v\d+\.\d+\.\d+)|//[^?]+\?ref=[0-9a-fA-F]{40})$")
def validate(manifest,plan,policy):
    if not all(isinstance(x,dict) for x in (manifest,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","required_modules","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    if not isinstance(policy.get("required_contracts"),dict):errors.append("invalid contract policy")
    for key in ("require_ticket","require_owner","require_pinned_remote_modules","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    if manifest.get("environment") not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(manifest.get("change_ticket"),str) or not manifest["change_ticket"].strip():errors.append("missing change ticket")
    modules=manifest.get("modules")
    if not isinstance(modules,list) or not modules:return errors+["modules must be nonempty list"]
    names=[]
    for i,m in enumerate(modules):
        if not isinstance(m,dict):errors.append("invalid module "+str(i));continue
        name=m.get("name")
        if not isinstance(name,str) or not name:errors.append("missing module name "+str(i));continue
        names.append(name)
        source=m.get("source")
        if not isinstance(source,str) or not source or (not source.startswith("./") and not PIN.search(source)):
            errors.append("unpinned or invalid module source "+name)
        if not isinstance(m.get("owner"),str) or not m["owner"].strip():errors.append("missing module owner "+name)
        contract=policy["required_contracts"].get(name)
        if contract:
            for direction in ("inputs","outputs"):
                values=m.get(direction)
                if not isinstance(values,list) or not all(isinstance(v,str) for v in values) or not set(contract[direction]).issubset(set(values)):
                    errors.append("incomplete "+direction+" contract "+name)
        dependencies=m.get("depends_on")
        if not isinstance(dependencies,list) or not all(isinstance(d,str) for d in dependencies):
            errors.append("invalid dependency list "+name)
    if len(names)!=len(set(names)):errors.append("duplicate module name")
    if not set(policy["required_modules"]).issubset(set(names)):errors.append("required module missing")
    graph={m["name"]:m.get("depends_on",[]) for m in modules if isinstance(m,dict) and isinstance(m.get("name"),str)}
    visited=set();active=set()
    def visit(node):
        if node in active:errors.append("module dependency cycle "+node);return
        if node in visited:return
        active.add(node)
        for dep in graph.get(node,[]):
            if dep not in graph:errors.append("unknown module dependency "+str(dep))
            else:visit(dep)
        active.remove(node);visited.add(node)
    for node in graph:visit(node)
    if "database" in graph and "network" not in graph["database"]:errors.append("database must consume network contract")
    if "application" in graph and "database" not in graph["application"]:errors.append("application must consume database contract")
    database=manifest.get("database")
    if not isinstance(database,dict):errors.append("database controls missing")
    elif manifest.get("environment")=="prod":
        if type(database.get("replicas")) is not int or database["replicas"]<3:errors.append("production replicas below three")
        if database.get("backup_enabled") is not True:errors.append("production backup required")
        if database.get("encryption_enabled") is not True:errors.append("production encryption required")
    changes=plan.get("resource_changes")
    if not isinstance(changes,list):return errors+["plan resource_changes must be list"]
    for i,r in enumerate(changes):
        if not isinstance(r,dict):errors.append("invalid resource change "+str(i));continue
        if r.get("type") not in policy["allowed_resource_types"]:errors.append("unapproved resource type "+str(i))
        if not isinstance(r.get("address"),str) or not r["address"]:errors.append("missing resource address "+str(i))
        change=r.get("change");actions=change.get("actions") if isinstance(change,dict) else None
        if not isinstance(actions,list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):
            errors.append("invalid plan actions "+str(i))
        elif "delete" in actions:errors.append("delete or replacement denied "+str(i))
    return errors
def main(argv):
    if len(argv)!=4:print("Usage: python3 module_policy.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared module architecture and plan")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
