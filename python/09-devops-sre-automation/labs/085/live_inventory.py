"""Optional read-only live SDK inventory; NEVER invoked by default tests.

Requires an approved least-privilege identity and explicit --allow-live.
Never print tokens or provider exception details, which can include metadata.
"""
from __future__ import annotations
import argparse
import json
from inventory import aws_ec2, azure_resources, bounded, gcp_projects

def collect(provider: str, scope: str, max_records: int) -> dict:
    if provider == "aws":
        import boto3
        from botocore.config import Config
        session=boto3.Session(region_name=scope)
        client=session.client("ec2",config=Config(
            connect_timeout=3,read_timeout=10,
            retries={"mode":"standard","max_attempts":3}))
        return bounded(aws_ec2(client,scope),max_records)
    if provider == "azure":
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True)
        try:
            client=ResourceManagementClient(credential,scope)
            return bounded(azure_resources(client,scope),max_records)
        finally:
            credential.close()
    if provider == "gcp":
        from google.cloud import resourcemanager_v3
        client=resourcemanager_v3.ProjectsClient()
        try:
            return bounded(gcp_projects(client,scope),max_records)
        finally:
            client.transport.close()
    raise ValueError("unsupported provider")

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Approved read-only multicloud inventory")
    parser.add_argument("--provider",required=True,choices=["aws","azure","gcp"])
    parser.add_argument("--scope",required=True,help="AWS region, Azure subscription ID, or numeric GCP organization ID")
    parser.add_argument("--max-records",type=int,default=100)
    parser.add_argument("--allow-live",action="store_true")
    args=parser.parse_args(argv)
    if not 1 <= args.max_records <= 1000:
        parser.error("max-records must be 1..1000")
    if not args.allow_live:
        print(json.dumps({"provider":args.provider,"scope":args.scope,
                          "max_records":args.max_records,"dry_run":True,"network_calls":0}))
        return 0
    try:
        result=collect(args.provider,args.scope,args.max_records)
    except Exception:
        # Avoid exposing credential-bearing provider exceptions.
        print(json.dumps({"status":"inventory_failed","provider":args.provider}))
        return 4
    print(json.dumps({"provider":args.provider,"scope":args.scope,"mode":"live-read-only",**result},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
