"""Explicit opt-in, read-only Kubernetes and Docker SDK inventory.

Never print credentials, kubeconfig, raw API errors or container environment.
"""
import argparse
import json
from inventory import limited,pod_records,deployment_records,docker_records

def collect(namespace: str, *, use_docker: bool=False, in_cluster: bool=False,
            context: str | None=None, max_records: int=100) -> dict:
    from kubernetes import client,config
    if in_cluster:
        config.load_incluster_config()
    else:
        config.load_kube_config(context=context)
    api_client=client.ApiClient()
    docker_client=None
    try:
        core=client.CoreV1Api(api_client)
        apps=client.AppsV1Api(api_client)
        records=list(pod_records(core,namespace))
        records.extend(deployment_records(apps,namespace))
        if use_docker:
            import docker
            docker_client=docker.from_env()
            records.extend(docker_records(docker_client))
        return limited(records,max_records)
    finally:
        if docker_client is not None: docker_client.close()
        api_client.close()

def main(argv=None):
    parser=argparse.ArgumentParser(description="Approved read-only Kubernetes/Docker inventory")
    parser.add_argument("--namespace",required=True)
    parser.add_argument("--context")
    parser.add_argument("--in-cluster",action="store_true")
    parser.add_argument("--docker",action="store_true")
    parser.add_argument("--max-records",type=int,default=100)
    parser.add_argument("--allow-live",action="store_true")
    args=parser.parse_args(argv)
    if not 1<=args.max_records<=1000:
        parser.error("max-records must be 1..1000")
    if not args.allow_live:
        print(json.dumps({"dry_run":True,"network_calls":0,
                          "namespace":args.namespace,"docker":args.docker}))
        return 0
    try:
        result=collect(args.namespace,use_docker=args.docker,
                       in_cluster=args.in_cluster,context=args.context,
                       max_records=args.max_records)
    except Exception:
        print(json.dumps({"status":"inventory_failed","detail":"see approved audit logs"}))
        return 4
    print(json.dumps({"mode":"live-read-only",**result},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
