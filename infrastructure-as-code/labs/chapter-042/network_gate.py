"""Fail-closed declared Azure network policy; not live effective-route/NSG verification."""
import ipaddress,json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
UUID=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_locations","required_subnets","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_nonoverlap","require_private_cidrs","require_nsg_review","deny_public_management","require_udr_review","require_private_endpoint","require_private_dns","require_database_delegation","deny_public_database","require_network_audit","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment");sub=m.get("subscription_id")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(sub,str) or not re.fullmatch(UUID,sub):errors.append("invalid subscription ID")
    if m.get("location") not in policy["allowed_locations"]:errors.append("unapproved Azure location")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(sub)+"-network":errors.append("state isolation mismatch")
    vnet=None
    try:
        vnet=ipaddress.ip_network(m.get("vnet_cidr"),strict=True)
        if vnet.version!=4 or not vnet.is_private:errors.append("VNet must be private IPv4")
    except (ValueError,TypeError):errors.append("invalid VNet CIDR")
    subnets=m.get("subnets")
    if not isinstance(subnets,dict):subnets={}
    parsed=[]
    for key in policy["required_subnets"]:
        try:
            network=ipaddress.ip_network(subnets.get(key),strict=True)
            if network.version!=4 or not network.is_private:errors.append("subnet not private IPv4 "+key)
            if network.prefixlen>27:errors.append("subnet capacity too small "+key)
            if vnet is not None and not network.subnet_of(vnet):errors.append("subnet outside VNet "+key)
            for other_name,other in parsed:
                if network.overlaps(other):errors.append("overlapping subnets "+key+"/"+other_name)
            parsed.append((key,network))
        except (ValueError,TypeError):errors.append("invalid subnet CIDR "+key)
    security=m.get("security")
    if not isinstance(security,dict):security={}
    for key in ("nsg_reviewed","udr_reviewed","forced_tunnel_next_hop_reviewed","nat_reviewed"):
        if security.get(key) is not True:errors.append("missing network security control "+key)
    for key in ("management_ports_public","allow_any_any_inbound"):
        if security.get(key) is not False:errors.append("forbidden public access "+key)
    conn=m.get("private_connectivity")
    if not isinstance(conn,dict):conn={}
    for key in ("private_endpoint_enabled","private_dns_zone_linked","private_dns_resolution_tested","database_subnet_delegated","public_database_access_disabled","private_endpoint_approved"):
        if conn.get(key) is not True:errors.append("missing private connectivity "+key)
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("flow_logs_enabled","network_watcher_enabled","security_reviewed","dbre_connectivity_tested"):
        if audit.get(key) is not True:errors.append("missing audit control "+key)
    tags=m.get("tags")
    if not isinstance(tags,dict):tags={}
    for key in policy["required_tags"]:
        if not isinstance(tags.get(key),str) or not tags[key].strip():errors.append("missing tag "+key)
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
    if len(argv)!=4:print("Usage: python3 network_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared Azure network and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
