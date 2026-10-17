"""Fail-closed declared AWS VPC topology and Terraform plan policy; not AWS attestation."""
import ipaddress,json,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for k in ("allowed_environments","required_tiers","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(k),list) or not policy[k]:errors.append("invalid policy "+k)
    for k in ("require_ticket","require_state_isolation","require_two_azs","require_private_database","require_flow_logs","require_s3_endpoint","require_least_privilege","require_same_az_nat","deny_destructive_actions"):
        if policy.get(k) is not True:errors.append("fail-open policy "+k)
    if errors:return errors
    env=m.get("environment")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    for k in ("owner","change_ticket"):
        if not isinstance(m.get(k),str) or not m[k].strip():errors.append("missing "+k)
    if m.get("state_namespace")!="iac-"+str(env)+"-network":errors.append("state isolation mismatch")
    try:
        vpc=ipaddress.ip_network(m["vpc_cidr"],strict=True)
        if vpc.version!=4:errors.append("IPv4 VPC CIDR required")
    except (KeyError,ValueError,TypeError):vpc=None;errors.append("invalid VPC CIDR")
    azs=m.get("availability_zones")
    if not isinstance(azs,list) or len(azs)<2 or len(set(map(str,azs)))!=len(azs) or any(not isinstance(a,str) or not a for a in azs):errors.append("at least two distinct AZs required");azs=[]
    subs=m.get("subnets")
    if not isinstance(subs,list) or not subs:return errors+["subnets must be nonempty list"]
    names=[];nets=[];tiers={};db_azs=set();public_azs=set()
    for i,s in enumerate(subs):
        if not isinstance(s,dict):errors.append("invalid subnet "+str(i));continue
        name=s.get("name")
        if not isinstance(name,str) or not name:errors.append("missing subnet name "+str(i))
        else:names.append(name)
        tier=s.get("tier");az=s.get("az")
        if tier not in policy["required_tiers"]:errors.append("invalid tier "+str(i))
        if az not in azs:errors.append("undeclared AZ "+str(i))
        if tier in policy["required_tiers"]:tiers.setdefault(tier,set()).add(az)
        if tier=="database":db_azs.add(az)
        if tier=="public":public_azs.add(az)
        try:
            net=ipaddress.ip_network(s["cidr"],strict=True)
            if net.version!=4 or (vpc and not net.subnet_of(vpc)):errors.append("subnet outside VPC "+str(i))
            for other in nets:
                if net.overlaps(other):errors.append("overlapping subnet "+str(i))
            nets.append(net)
        except (KeyError,ValueError,TypeError):errors.append("invalid subnet CIDR "+str(i))
    if len(names)!=len(set(names)):errors.append("duplicate subnet names")
    for tier in policy["required_tiers"]:
        if len(tiers.get(tier,set()))<2:errors.append("tier missing two AZs "+tier)
    routes=m.get("routes")
    if not isinstance(routes,dict):routes={}
    if routes.get("public_default")!="igw":errors.append("public route must use IGW")
    if routes.get("application_default") not in ("same-az-nat","endpoints-only"):errors.append("unapproved application route")
    if routes.get("database_default")!="none":errors.append("database must have no internet default route")
    nat=routes.get("nat_by_az")
    if routes.get("application_default")=="same-az-nat":
        if not isinstance(nat,dict) or any(nat.get(az)!=az for az in tiers.get("application",set())):errors.append("NAT not zonally aligned")
    security=m.get("security")
    if not isinstance(security,dict):security={}
    if security.get("database_public_ingress") is not False:errors.append("database public ingress forbidden")
    for k in ("flow_logs_enabled","s3_endpoint_enabled","least_privilege_reviewed"):
        if security.get(k) is not True:errors.append("missing security control "+k)
    tags=m.get("tags")
    if not isinstance(tags,dict):tags={}
    for k in policy["required_tags"]:
        if not isinstance(tags.get(k),str) or not tags[k].strip():errors.append("missing tag "+k)
    if tags.get("Environment")!=env or tags.get("Owner")!=m.get("owner") or tags.get("ManagedBy")!="terraform":errors.append("tag identity mismatch")
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
    if len(argv)!=4:print("Usage: python3 network_gate.py <topology> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared network topology and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
