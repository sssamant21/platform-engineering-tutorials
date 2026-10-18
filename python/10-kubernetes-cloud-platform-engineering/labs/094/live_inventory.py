"""Explicitly opt-in, read-only AWS inventory using boto3. Never changes resources."""
import argparse,json
from aws_lab import Scope,LabError,inventory

def collect(profile,region,expected_account,max_items=100):
    if not profile or not region or not expected_account:raise LabError("explicit profile, region and account required")
    scope=Scope(expected_account,region);scope.validate()
    try:import boto3
    except ImportError as exc:raise LabError("install boto3 in an isolated environment") from exc
    session=boto3.Session(profile_name=profile,region_name=region)
    sts=session.client("sts")
    identity=sts.get_caller_identity()
    if identity.get("Account")!=expected_account:raise LabError("STS account mismatch; stopped")
    ec2=session.client("ec2");eks=session.client("eks");rds=session.client("rds")
    resources={"ec2":[],"eks":[],"rds":[]}
    # Enforce an item budget as records are streamed, not only after collection.
    def append(kind,record):
        if sum(len(v) for v in resources.values())>=max_items:raise LabError("resource budget exceeded")
        resources[kind].append(record)
    for page in ec2.get_paginator("describe_instances").paginate(PaginationConfig={"PageSize":50}):
        for reservation in page.get("Reservations",[]):
            for obj in reservation.get("Instances",[]):
                append("ec2",{"id":obj["InstanceId"],"status":obj.get("State",{}).get("Name","unknown")})
    for page in eks.get_paginator("list_clusters").paginate(PaginationConfig={"PageSize":50}):
        for name in page.get("clusters",[]):
            # ListClusters does not include cluster status; resolve via DescribeCluster.
            obj=eks.describe_cluster(name=name)["cluster"]
            append("eks",{"id":name,"status":obj.get("status","unknown")})
    for page in rds.get_paginator("describe_db_instances").paginate(PaginationConfig={"PageSize":50}):
        for obj in page.get("DBInstances",[]):
            append("rds",{"id":obj["DBInstanceIdentifier"],"status":obj.get("DBInstanceStatus","unknown")})
    result=inventory(scope,resources["ec2"],resources["eks"],resources["rds"],max_resources=max_items)
    result.update({"mode":"live-read-only","caller_arn":identity.get("Arn"),"mutations":0})
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description="Read-only boto3 AWS inventory; explicit opt-in")
    p.add_argument("--allow-live",action="store_true")
    p.add_argument("--profile",required=True)
    p.add_argument("--region",required=True)
    p.add_argument("--expected-account",required=True)
    p.add_argument("--max-items",type=int,default=100)
    args=p.parse_args(argv)
    if not args.allow_live:p.error("--allow-live required to call AWS APIs")
    print(json.dumps(collect(args.profile,args.region,args.expected_account,args.max_items),sort_keys=True))
if __name__=="__main__":main()
