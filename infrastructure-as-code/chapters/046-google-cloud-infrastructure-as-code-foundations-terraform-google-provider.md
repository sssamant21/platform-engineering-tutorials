# Chapter 046 — Google Cloud Infrastructure as Code Foundations and Terraform Google Provider

**Part 10 — Google Cloud Platform · Chapter 046/120**  
**Audience:** SRE, DBRE, platform engineering, cloud security and DevOps  
**Prerequisites:** Chapters 001–045; Terraform >=1.7; Python >=3.9; Google Cloud CLI for optional integration.

> **Safety:** Required labs use only built-in \`terraform_data\` and run offline without cloud credentials. The Google provider example is review-only and must not be applied without approved project, billing, IAM, API enablement, quota, network and change controls. All project IDs and numbers are fictitious.

## 1. Outcomes

Understand Google Cloud organization, folders, projects, billing accounts, regions/zones, IAM and organization policy; distinguish resource-level from project-level boundaries; authenticate Terraform securely; pin and configure the \`hashicorp/google\` provider; design a protected GCS backend; validate enabled service APIs, quotas and operational telemetry; and run automated positive/negative policy tests.

## 2. Enterprise architecture

~~~text
Organization + Organization Policies + Cloud Identity
                         |
                Folders / environments
                         |
          Projects: dev / staging / production
             |             |           |
          Billing        IAM + WIF   Audit Logs
             |             |           |
     Terraform CI ---- short-lived OIDC token
             |
       Google Provider + API calls
             |
   Service Usage / VPC / GKE / Cloud SQL / GCS
             |
     Cloud Monitoring / Logging / budgets
             |
       Private state bucket (GCS)
~~~

Project isolation is the primary billing, API enablement, quota and IAM boundary, but hierarchical IAM grants and organization policies can span projects. Terraform state is a separate sensitive asset. Use different projects, service accounts and state prefixes/buckets for environments. Folders provide hierarchy; they are not automatic network or security boundaries.

## 3. Resource hierarchy, regions and billing

Organizations contain folders and projects; projects own most resources and are attached to billing accounts. Evaluate location policies, data residency, region/zone availability, service-specific quotas and price differences. A regional service is not necessarily multi-region DR. Design budget alerts and labels (\`environment\`, \`owner\`, \`managed-by\`, \`cost-center\`) from the start. Google Cloud labels have syntax restrictions and are not equivalent to IAM controls.

## 4. Terraform Google provider

~~~hcl
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
~~~

Provider version is illustrative; validate supported releases and resource compatibility before a real deployment. Commit \`.terraform.lock.hcl\`, keep provider constraints deliberate and use \`terraform init -upgrade\` only under review. Configure provider aliases for cross-project operations, with explicit IAM and state boundaries. \`google-beta\` is a separate provider with potentially different API maturity and upgrade risk; do not adopt beta resources casually.

## 5. Authentication: local, CI and workload identity

Use \`gcloud auth application-default login\` only for approved developer workflows; distinguish ADC from \`gcloud auth login\` and from the active \`gcloud config set project\` setting. For CI, prefer Workload Identity Federation with a narrow issuer/audience/subject trust, service-account impersonation when appropriate, and short-lived credentials. For GKE, use Workload Identity Federation for GKE rather than distributing JSON service-account keys. Disable or tightly govern key creation. Never commit credential JSON, access tokens or private keys; \`sensitive = true\` does not prevent state exposure.

**Identity preflight:** verify active account, target project ID and numeric project number, quota/billing project, token source, principal, roles and trust constraints. \`roles/owner\` and \`roles/editor\` are not acceptable default deployment roles. Grant narrowly scoped permissions; use IAM Conditions where supported and test effective access.

## 6. API enablement and service dependencies

Google Cloud services commonly require enabling APIs such as \`compute.googleapis.com\`, \`container.googleapis.com\`, \`sqladmin.googleapis.com\`, \`storage.googleapis.com\`, \`iam.googleapis.com\`, and \`serviceusage.googleapis.com\`. Enabling an API may create service agents or dependencies and can be restricted by organization policy. Service Usage API permissions are distinct from resource creation permissions. A disabled API, pending service agent, or quota exhaustion can resemble provider failure. Plan retries for eventual consistency and observe API quota/throttling.

## 7. Remote state and drift

The \`gcs\` backend is configured separately from the Google provider and uses Google credentials. Bootstrap a dedicated state bucket with uniform bucket-level access, public access prevention, versioning, encryption, logging, IAM least privilege and retention/recovery design. The GCS backend uses object generation preconditions for state locking; never delete lock objects or force-unlock without checking for an active writer. Design state isolation by project/environment; audit access and test restore from previous state object versions. A Terraform state backup does not restore Cloud SQL data.

## 8. Security and networking baseline

Apply organization policy constraints, deny public buckets, restrict external IPs where appropriate, use VPC and firewall policy, private service connectivity, Cloud NAT and DNS as designed. Cloud KMS customer-managed keys introduce availability and recovery dependencies. Use Secret Manager with IAM and rotation; avoid writing secret payloads into Terraform state. Collect Cloud Audit Logs, Cloud Monitoring metrics, billing alerts and service-specific logs with retention and access controls. Review VPC Service Controls where data exfiltration requirements justify them.

## 9. SRE/DBRE production use cases

**Cloud SQL for PostgreSQL:** private IP or supported private connectivity, TLS, HA, PITR, backup retention, connection pools, query latency and restore validation. **GKE:** node pool quotas, workload identity, private control plane, upgrades and database connection storms. **Compute Engine:** instance templates, managed instance groups, autoscaling, disk performance and zone failures. **GCS:** access policies, lifecycle, versioning, recovery and cost. **Pub/Sub:** retry and backlog behavior; **Memorystore:** availability and connection health. IaC only provisions infrastructure: live application and data-plane acceptance remain separate.

## 10. Executable hands-on labs

Files: \`infrastructure-as-code/labs/chapter-046/\`.

### Lab A — Offline Terraform foundation contract

~~~bash
cd infrastructure-as-code/labs/chapter-046
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter046.tfplan
terraform apply chapter046.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
~~~

Four \`terraform_data\` resources model project/billing, identity, state and operations contracts. They do not create GCP infrastructure. Never apply production tfvars to a dev state.

### Lab B — Positive/negative security and plan policy

~~~bash
python3 gcp_gate.py fixtures/gcp-safe.json fixtures/plan-safe.json gcp-policy.json
python3 gcp_gate.py fixtures/gcp-unsafe.json fixtures/plan-destructive.json gcp-policy.json
python3 -m unittest -v test_gcp_gate.py
bash run-preflight.sh
~~~

Safe input must pass; unsafe and delete/replace actions must fail. These JSON fixtures represent declared policy evidence, not complete Terraform JSON plan parsing or live GCP verification.

### Lab C — Optional approved GCP plan review

1. Verify organization/folder, project, billing, region, quota, IAM and organization policy.
2. Inspect \`examples/google-foundation.tf.example\` as a **separate root** and \`examples/gcp-identity-preflight.sh.example\`; do not apply the example blindly.
3. Bootstrap secure GCS state and short-lived identity. Enable only approved APIs.
4. Run \`terraform init\`, \`terraform validate\`, \`terraform plan\` in a sandbox; review every new API, IAM grant, state change and cost.
5. Obtain change and security approval before any optional apply; validate audit logs, labels, service availability and cleanup.

## 11. Failure scenarios and troubleshooting

| Failure | Diagnosis | Response |
|---|---|---|
| Wrong project deployment | ADC project vs provider project vs billing project | stop apply, verify project number and state |
| WIF 403 | issuer/audience/subject, impersonation, IAM | repair exact trust; no key fallback |
| API disabled | Service Usage error | enable only approved service, wait for readiness |
| Org policy deny | constraint and audit log | correct compliant design, do not bypass |
| Quota exhausted | quota metrics, region, project | request approved quota or rightsize |
| GCS state 403 | bucket IAM, VPC-SC, identity | restore scoped access and audit |
| State lock conflict | active writer / generation | coordinate; avoid force unlock |
| Cloud SQL private DNS failure | resolver, route, private service | repair connectivity without public access |
| Unexpected replacement | plan address drift/immutable field | block change, design migration |
| Cost spike | billing export, labels, egress | halt runaway workload, review budget |

Useful optional diagnostics:

~~~bash
gcloud auth list
gcloud config get-value project
gcloud projects describe PROJECT_ID --format='value(projectNumber)'
gcloud services list --enabled --project=PROJECT_ID
gcloud compute project-info describe --project=PROJECT_ID
terraform providers
terraform state list
~~~

## 12. Production runbooks

**Pre-change:** confirm project ID/number, organization policy, billing, WIF, approved APIs, quotas, secure GCS state, monitoring and owner. Run policy gate, test suite, plan and peer review.  
**IAM outage:** preserve logs, verify principal/token/trust, restore least privilege, test API access, avoid long-lived keys.  
**State lock or corruption:** freeze writers, preserve object versions, check lock ownership, restore a reviewed version, run drift inspection.  
**Cloud SQL connectivity incident:** correlate IAM, DNS, private service connection, TLS, pool saturation and DB health; recover without opening public access.  
**Region failure:** recover identity, network, KMS and data using a tested DR plan; measure actual RPO/RTO, not estimated figures.  
**Unplanned deletion:** stop apply, preserve plan/state/audit evidence, assess data impact and escalate to service owner/DBRE.

## 13. Acceptance and review

| Gate | Points |
|---|---:|
| GCP organization, project and billing design | 20 |
| IAM, federation, organization policy and service APIs | 20 |
| GCS state security and environment isolation | 20 |
| Terraform labs and automated negative tests | 15 |
| SRE/DBRE incidents, recovery and rollback | 15 |
| Monitoring, costs, change approvals and audit | 10 |

**Pass >=85/100 with zero critical failures** (wrong production project, service-account keys in source, public state, unapproved delete/replace, missing restore evidence). Attach sanitized test logs, plan, project/identity proof, API and quota evidence, security review and DBRE sign-off. Authored tests are not executed tests; publication is not production acceptance.

Cleanup offline lab only:

~~~bash
terraform destroy -var-file=environments/dev.tfvars
~~~

**Next:** Chapter 047 — GCP VPC, Subnets, Routing, Firewall Rules and Private Connectivity with Terraform (proposed title; Part 10 roadmap only specifies GCP).
