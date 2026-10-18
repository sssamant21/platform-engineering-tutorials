"""Fail-closed GCP network declared-evidence gate; not live GCP attestation."""
import ipaddress,json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_regions","required_labels","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_custom_vpc","require_nonoverlapping_cidrs","require_private_google_access","require_restricted_firewall","deny_public_management_and_database_ingress","require_nat","require_private_service_review","require_dns_review","require_hybrid_review","require_flow_logs","require_dbre_approval","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment");project=m.get("project_id")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(project,str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]",project):errors.append("invalid project ID")
    if m.get("region") not in policy["allowed_regions"]:errors.append("unapproved region")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(project)+"-network":errors.append("state isolation mismatch")
    vpc=m.get("vpc")
    if not isinstance(vpc,dict):vpc={}
    for key in ("custom_mode","shared_vpc_reviewed","private_google_access","secondary_ranges_reviewed"):
        if vpc.get(key) is not True:errors.append("missing VPC control "+key)
    ranges=[]
    for key in ("subnet_cidr","pod_cidr","services_cidr"):
        try:
            if not isinstance(vpc.get(key),str):raise ValueError("CIDR must be string")
            net=ipaddress.ip_network(vpc[key],strict=True)
            if not isinstance(net,ipaddress.IPv4Network) or not net.is_private:raise ValueError("non-private IPv4")
            ranges.append(net)
        except ValueError:errors.append("invalid private CIDR "+key)
    if len(ranges)==3 and any(a.overlaps(b) for i,a in enumerate(ranges) for b in ranges[i+1:]):errors.append("overlapping CIDRs")
    fw=m.get("firewall")
    if not isinstance(fw,dict):fw={}
    for key in ("restricted","logging","least_privilege_targets","hierarchical_policy_reviewed"):
        if fw.get(key) is not True:errors.append("missing firewall control "+key)
    for key in ("public_ssh_ingress","public_database_ingress"):
        if fw.get(key) is not False:errors.append("public ingress forbidden "+key)
    conn=m.get("connectivity")
    if not isinstance(conn,dict):conn={}
    for key in ("cloud_nat_enabled","nat_capacity_reviewed","private_service_connect_reviewed","cloud_dns_reviewed","hybrid_routes_reviewed","peering_nontransitive_reviewed"):
        if conn.get(key) is not True:errors.append("missing connectivity control "+key)
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("vpc_flow_logs_enabled","monitoring_enabled","dbre_approved","security_approved","change_approved"):
        if audit.get(key) is not True:errors.append("missing audit control "+key)
    labels=m.get("labels")
    if not isinstance(labels,dict):labels={}
    for key in policy["required_labels"]:
        if not isinstance(labels.get(key),str) or not labels[key].strip():errors.append("missing label "+key)
    if labels.get("environment")!=env or labels.get("owner")!=m.get("owner") or labels.get("managed-by")!="terraform":errors.append("label identity mismatch")
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
    print("PASS: declared GCP network and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
