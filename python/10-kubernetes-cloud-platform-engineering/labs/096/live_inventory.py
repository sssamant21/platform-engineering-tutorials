"""Explicitly opted-in read-only GCP Compute/GKE inventory. No cloud writes."""
from __future__ import annotations
import argparse,json
from gcp_lab import Scope,LabError,inventory

def collect(project,zone,*,max_items=100):
    scope=Scope(project,zone);scope.validate()
    if not 1<=max_items<=10000:raise LabError("invalid item budget")
    try:
        import google.auth
        from google.cloud import compute_v1,container_v1
    except ImportError as exc:
        raise LabError("install reviewed google-auth, google-cloud-compute and google-cloud-container") from exc
    credentials,adc_project=google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if adc_project and adc_project!=project:
        raise LabError("ADC default project differs from requested project")
    compute=compute_v1.InstancesClient(credentials=credentials)
    gke=container_v1.ClusterManagerClient(credentials=credentials)
    vms=[];clusters=[]
    for obj in compute.list(project=project,zone=zone):
        if len(vms)+len(clusters)>=max_items:raise LabError("resource budget exceeded")
        vms.append({"name":obj.name,"status":obj.status or "unknown"})
    parent=f"projects/{project}/locations/{zone}"
    response=gke.list_clusters(parent=parent)
    for obj in response.clusters or []:
        if len(vms)+len(clusters)>=max_items:raise LabError("resource budget exceeded")
        clusters.append({"name":obj.name,"status":str(obj.status)})
    result=inventory(scope,compute=vms,gke=clusters,max_items=max_items)
    result.update({"mode":"live-read-only","mutations":0})
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description="Opt-in read-only GCP Compute/GKE inventory")
    p.add_argument("--allow-live",action="store_true")
    p.add_argument("--project",required=True)
    p.add_argument("--zone",required=True)
    p.add_argument("--max-items",type=int,default=100)
    args=p.parse_args(argv)
    if not args.allow_live:p.error("--allow-live is required")
    print(json.dumps(collect(args.project,args.zone,max_items=args.max_items),sort_keys=True))
if __name__=="__main__":main()
