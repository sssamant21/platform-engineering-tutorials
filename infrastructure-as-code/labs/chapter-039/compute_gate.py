"""Fail-closed declared compute/EKS and Terraform plan policy, not live AWS verification."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_regions","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_two_azs","require_private_compute","require_imdsv2","require_ebs_encryption","require_alb_https","require_eks_private_endpoint","require_eks_logging","require_eks_encryption","require_scoped_pod_identity","require_monitoring","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    account=m.get("aws_account_id")
    if not isinstance(account,str) or not re.fullmatch(r"[0-9]{12}",account):errors.append("invalid AWS account ID")
    if m.get("region") not in policy["allowed_regions"]:errors.append("unapproved region")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(account)+"-compute":errors.append("state isolation mismatch")
    azs=m.get("availability_zones")
    if not isinstance(azs,list) or len(azs)<2 or any(not isinstance(a,str) or not a for a in azs) or len(set(map(str,azs)))!=len(azs):errors.append("at least two distinct AZs required")
    compute=m.get("compute")
    if not isinstance(compute,dict):compute={}
    for key in ("private_instances","imds_v2_required","ebs_encrypted","immutable_ami","instance_profile_scoped"):
        if compute.get(key) is not True:errors.append("missing compute control "+key)
    caps=[compute.get(k) for k in ("asg_min","asg_desired","asg_max")]
    if any(type(v) is not int for v in caps) or not (1<=caps[0]<=caps[1]<=caps[2]):errors.append("invalid ASG capacity")
    elif env=="prod" and caps[0]<2:errors.append("production ASG min below two")
    alb=m.get("alb")
    if not isinstance(alb,dict):alb={}
    for key in ("https_enabled","security_group_reviewed"):
        if alb.get(key) is not True:errors.append("missing ALB control "+key)
    if alb.get("readiness_path")!="/readyz":errors.append("unapproved readiness path")
    if type(alb.get("healthy_target_threshold")) is not int or alb["healthy_target_threshold"]<2:errors.append("ALB health threshold too low")
    eks=m.get("eks")
    if not isinstance(eks,dict):eks={}
    for key in ("private_endpoint","control_plane_logging","secrets_encrypted","managed_node_groups","pod_identity_scoped","addon_compatibility_reviewed"):
        if eks.get(key) is not True:errors.append("missing EKS control "+key)
    nodes=[eks.get(k) for k in ("node_min","node_desired","node_max")]
    if any(type(v) is not int for v in nodes) or not (1<=nodes[0]<=nodes[1]<=nodes[2]):errors.append("invalid EKS node capacity")
    elif env=="prod" and nodes[0]<2:errors.append("production node minimum below two")
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("cloudwatch_enabled","security_reviewed","slo_defined"):
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
    print("PASS: declared compute/EKS and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
