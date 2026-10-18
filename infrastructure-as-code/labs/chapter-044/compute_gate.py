"""Fail-closed declared Azure compute/AKS policy gate; not live cluster attestation."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
UUID=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_locations","allowed_vm_skus","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_zone_spread","require_private_cluster","require_oidc","require_workload_identity","require_acr_private","require_image_digest","require_pdb","require_autoscaling","require_private_database","require_monitoring","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment");sub=m.get("subscription_id")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(sub,str) or not re.fullmatch(UUID,sub):errors.append("invalid subscription ID")
    if m.get("location") not in policy["allowed_locations"]:errors.append("unapproved location")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(sub)+"-compute":errors.append("state isolation mismatch")
    compute=m.get("compute")
    if not isinstance(compute,dict):compute={}
    if compute.get("vm_sku") not in policy["allowed_vm_skus"]:errors.append("unapproved VM SKU")
    n=compute.get("node_count")
    if type(n) is not int or n<3 or n>20:errors.append("node count outside approved bounds")
    zones=compute.get("availability_zones")
    if not isinstance(zones,list) or len(set(map(str,zones)))<2 or any(str(z) not in ("1","2","3") for z in zones):errors.append("insufficient zone spread")
    for key in ("vmss_health_probes","upgrade_reviewed"):
        if compute.get(key) is not True:errors.append("missing compute control "+key)
    aks=m.get("aks")
    if not isinstance(aks,dict):aks={}
    for key in ("private_cluster","oidc_issuer_enabled","workload_identity_enabled","kubernetes_version_reviewed","system_pool_dedicated","autoscaler_enabled","network_model_reviewed"):
        if aks.get(key) is not True:errors.append("missing AKS control "+key)
    app=m.get("application")
    if not isinstance(app,dict):app={}
    for key in ("image_digest_pinned","acr_private","acr_identity_reviewed","pdb_enabled","private_database_access","ingress_tls_enabled"):
        if app.get(key) is not True:errors.append("missing application control "+key)
    replicas=app.get("replicas")
    if type(replicas) is not int or replicas<3:errors.append("insufficient replicas")
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("diagnostics_enabled","alerting_enabled","slo_reviewed","dbre_connection_tested","rollback_drill_passed"):
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
    if len(argv)!=4:print("Usage: python3 compute_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared Azure compute/AKS and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
