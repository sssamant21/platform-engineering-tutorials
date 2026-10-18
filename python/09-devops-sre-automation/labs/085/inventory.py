"""Read-only bounded multicloud inventory with injectable SDK clients."""
import argparse
from dataclasses import dataclass, asdict
import json

class InventoryError(RuntimeError): pass

@dataclass(frozen=True)
class Record:
    provider: str
    scope: str
    kind: str
    resource_id: str

def bounded(items, max_records=100):
    if type(max_records) is not int or not 1 <= max_records <= 1000:
        raise ValueError("invalid max_records")
    seen=set()
    rows=[]
    for item in items:
        key=(item.provider,item.scope,item.kind,item.resource_id)
        if key in seen: continue
        seen.add(key)
        if len(rows)==max_records:
            return {"records":[asdict(r) for r in rows],"partial":True}
        rows.append(item)
    return {"records":[asdict(r) for r in rows],"partial":False}

def aws_ec2(client,region):
    if not region or not region.replace("-","").isalnum():
        raise ValueError("invalid AWS region")
    for page in client.get_paginator("describe_instances").paginate(
        PaginationConfig={"PageSize":100}
    ):
        for reservation in page.get("Reservations",[]):
            for instance in reservation.get("Instances",[]):
                rid=instance.get("InstanceId")
                if not isinstance(rid,str) or not rid.startswith("i-"):
                    raise InventoryError("invalid instance ID")
                yield Record("aws",region,"ec2-instance",rid)

def azure_resources(client,subscription):
    if not subscription or len(subscription)>80:
        raise ValueError("invalid Azure subscription")
    for resource in client.resources.list():
        rid=getattr(resource,"id",None)
        kind=getattr(resource,"type",None)
        if not isinstance(rid,str) or not rid.startswith("/") or not isinstance(kind,str):
            raise InventoryError("invalid Azure resource")
        yield Record("azure",subscription,kind,rid)

def gcp_projects(client,organization):
    if not organization or not organization.isdigit():
        raise ValueError("invalid GCP organization")
    request={"query":"parent.type:organization parent.id:"+organization}
    for project in client.search_projects(request=request,timeout=10):
        rid=getattr(project,"name",None)
        if not isinstance(rid,str) or not rid.startswith("projects/"):
            raise InventoryError("invalid GCP project")
        yield Record("gcp",organization,"project",rid)

def offline_fake(provider):
    """No SDK imports or network calls; test fixture only."""
    from types import SimpleNamespace
    if provider=="aws":
        class Paginator:
            def paginate(self,**kwargs):
                yield {"Reservations":[{"Instances":[{"InstanceId":"i-001"},{"InstanceId":"i-002"}]}]}
        class Client:
            def get_paginator(self,name):
                assert name=="describe_instances"
                return Paginator()
        return aws_ec2(Client(),"us-east-1")
    if provider=="azure":
        class Client:
            resources=SimpleNamespace(list=lambda:iter([
                SimpleNamespace(id="/subscriptions/lab/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1",type="Microsoft.Compute/virtualMachines"),
                SimpleNamespace(id="/subscriptions/lab/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/st1",type="Microsoft.Storage/storageAccounts")
            ]))
        return azure_resources(Client(),"lab-subscription")
    if provider=="gcp":
        class Client:
            def search_projects(self,**kwargs):
                return iter([SimpleNamespace(name="projects/123"),SimpleNamespace(name="projects/456")])
        return gcp_projects(Client(),"123456789")
    raise ValueError("unknown provider")

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline multicloud inventory")
    parser.add_argument("--provider",choices=["aws","azure","gcp"],required=True)
    parser.add_argument("--max-records",type=int,default=100)
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    if not 1<=args.max_records<=1000:
        parser.error("max-records must be 1..1000")
    if args.dry_run:
        print(json.dumps({"provider":args.provider,"dry_run":True,"network_calls":0}))
        return 0
    result=bounded(offline_fake(args.provider),args.max_records)
    print(json.dumps({"provider":args.provider,"mode":"offline-fake",**result},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
