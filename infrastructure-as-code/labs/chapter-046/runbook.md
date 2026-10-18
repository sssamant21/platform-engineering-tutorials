# Chapter 046 — GCP foundation SRE/DBRE runbooks

## Preflight
Confirm organization, folder, project ID and numeric project number, billing account, region, service APIs, quotas, IAM, OIDC WIF trust, GCS state isolation, labels, organization policy, Cloud Audit Logs and budget alerts.

## Wrong project or destructive Terraform plan
Stop apply, preserve state and plan, compare provider project and state namespace, assess resource replacements, obtain change authorization and reconcile safely.

## WIF/ADC 403
Inspect active ADC principal, OIDC issuer/audience/subject, IAM impersonation and effective permissions. Restore scoped trust; do not distribute JSON keys.

## Disabled API or quota
Check Service Usage, org policy, quota and service agents. Enable approved API or request quota; never broaden IAM blindly.

## GCS backend outage
Freeze writers, verify bucket IAM, VPC Service Controls, DNS and object-generation locking. Restore reviewed state object version; force unlock only after proving writer stopped.

## Cloud SQL / GKE connectivity
Inspect VPC, private service connectivity, DNS, firewall, TLS, service account permissions and application connection pools; coordinate DBRE and validate read/write.

## Region or KMS outage
Invoke tested DR; restore identity, keys, networking and data. Measure actual RPO/RTO; preserve sanitized audit evidence.
