"""Opt-in read-only Azure VM/AKS inventory. Never calls ARM write APIs."""
from __future__ import annotations
import argparse,json
from azure_lab import Scope,LabError,inventory

def collect(subscription,resource_group,*,max_items=100):
    scope=Scope(subscription,resource_group);scope.validate()
    if not 1<=max_items<=10000:raise LabError("invalid item budget")
    try:
        from azure.identity import AzureCliCredential
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.containerservice import ContainerServiceClient
    except ImportError as exc:
        raise LabError("install reviewed azure-identity, azure-mgmt-compute and azure-mgmt-containerservice") from exc
    credential=AzureCliCredential()
    compute=ComputeManagementClient(credential,subscription)
    aks=ContainerServiceClient(credential,subscription)
    vms=[];clusters=[]
    for obj in compute.virtual_machines.list(resource_group):
        if len(vms)+len(clusters)>=max_items:raise LabError("item budget exceeded")
        vms.append({"id":obj.id,"state":obj.provisioning_state or "unknown"})
    for obj in aks.managed_clusters.list_by_resource_group(resource_group):
        if len(vms)+len(clusters)>=max_items:raise LabError("item budget exceeded")
        clusters.append({"id":obj.id,"state":obj.provisioning_state or "unknown"})
    result=inventory(scope,vms=vms,aks=clusters,max_items=max_items)
    result.update({"mode":"live-read-only","mutations":0})
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description="Opt-in read-only Azure inventory")
    p.add_argument("--allow-live",action="store_true")
    p.add_argument("--subscription",required=True)
    p.add_argument("--resource-group",required=True)
    p.add_argument("--max-items",type=int,default=100)
    args=p.parse_args(argv)
    if not args.allow_live:p.error("--allow-live required")
    print(json.dumps(collect(args.subscription,args.resource_group,max_items=args.max_items),sort_keys=True))
if __name__=="__main__":main()
