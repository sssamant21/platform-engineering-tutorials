# Chapter 036 — AWS Infrastructure as Code Foundations and Terraform AWS Provider

**Part 08 — AWS Infrastructure as Code · Chapter 036/120**  
**Audience:** Platform Engineering, SRE, DBRE, DevSecOps · **Prerequisites:** Chapters 001–035  
**Safety:** Offline lab by default. AWS examples are opt-in and may incur cost. Publication is not proof of live execution.

## 1. Mission and outcomes

Engineer a secure, repeatable AWS Terraform foundation. Understand AWS accounts, organizations, IAM roles, STS, regional boundaries, provider configuration and aliases, remote state, tagging, network and data-plane ownership, and safe plan/apply workflows. Build an offline contract lab, review a real-provider example without applying it, and enforce an automated AWS configuration policy.

## 2. Enterprise architecture

~~~text
Git repository + code owners + signed release
  -> CI OIDC federation -> AWS STS AssumeRole (short-lived)
  -> Terraform root configuration
       |-- aws provider: primary region, allowed account, default tags
       |-- aws provider alias: DR region, distinct allowlist
       |-- version-constrained modules: network, data, application
       |-- S3 remote state + versioning + encryption + lockfile
  -> Plan JSON + policy gate + approval + state lock
  -> VPC / subnets / routing / SG / KMS / RDS / EKS
  -> CloudTrail, Config, CloudWatch, cost allocation, DBRE/SRE SLO
~~~

AWS provider authentication is an **identity boundary**, not a guarantee of safe infrastructure. A successful Terraform plan does not validate production recovery, workload health or budget. Use separate accounts and identities for dev/staging/prod, and separate state keys and backends. Use organizational guardrails (SCPs, IAM permissions boundaries, session conditions) in addition to IaC policy.

## 3. AWS foundations

**Organizations/accounts:** separate security/logging, shared services and workload accounts. Treat account ID, partition and region as explicit deployment parameters; never rely on the default AWS profile in production. AWS commercial, GovCloud and China partitions differ.

**Regions/AZs:** regions isolate API endpoints and resources; Availability Zones are failure domains with account-specific AZ name mappings. A second provider alias does not replicate data or make an application multi-region.

**IAM/STS:** prefer CI OIDC federation and short-lived AssumeRole credentials. Require least privilege, trust-policy audience/subject restrictions, session audit and approved role chains. Do not embed AWS keys in HCL, environment files or CI logs. Use \`aws sts get-caller-identity\` to confirm the active principal before a change.

**Networking:** VPC CIDR, public/private subnet placement, routes, NAT, security groups, VPC endpoints and DNS have availability, security and cost implications. Avoid public database access.

**DBRE/SRE:** RDS/Aurora backups and PITR, KMS key lifecycle, EKS node lifecycle, OpenSearch snapshots, ElastiCache persistence, MSK broker health, quotas and cloud costs require workload-specific verification.

## 4. Terraform AWS provider architecture

~~~hcl
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region              = var.primary_region
  allowed_account_ids = [var.aws_account_id]
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner
    }
  }
}

provider "aws" {
  alias               = "dr"
  region              = var.dr_region
  allowed_account_ids = [var.aws_account_id]
}
~~~

The snippet is illustrative. Review current provider versions and feature support before production use. Provider aliases must be explicitly passed to child modules when required. Provider versions are governed by \`required_providers\` and the root \`.terraform.lock.hcl\`; modules are versioned separately. Pin the exact provider version through an approved lockfile and review any \`terraform init -upgrade\` change.

## 5. Authentication and account guardrails

For a human sandbox, AWS SSO / IAM Identity Center profiles are preferable to long-lived access keys. For CI, use OIDC → AssumeRole and scope the role trust policy to the repository, branch/environment and intended audience. Never use root credentials.

~~~bash
aws sts get-caller-identity
aws configure list-profiles
AWS_PROFILE=approved-sandbox aws sts get-caller-identity
~~~

The optional AWS example under \`examples/aws-provider.tf.example\` must be reviewed, copied into an isolated root and configured with approved credentials before use. It is **not** part of the offline lab.

## 6. State, locking and disaster recovery

For production AWS roots, use an encrypted and versioned S3 backend with access-controlled bucket and object prefix. Recent Terraform versions support S3 lockfiles with \`use_lockfile = true\`; validate the chosen Terraform version and backend support. DynamoDB-based locking is deprecated in newer Terraform releases; avoid starting new designs around it. Backend configuration cannot reference ordinary Terraform input variables. Separate backend initialization from resource provisioning, use IAM/KMS policies and block public access. Never commit state, state backups, secrets or saved plans. State restore restores mappings and metadata, **not** RDS data or AWS resources.

## 7. Hands-on lab layout

~~~text
labs/chapter-036/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/aws-provider.tf.example, examples/s3-backend.tf.example
  examples/aws-identity-preflight.sh.example
  aws-foundation-policy.json
  fixtures/foundation-safe.json, foundation-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  aws_foundation_gate.py, test_aws_foundation_gate.py
  run-preflight.sh, .gitignore
~~~

The executable root uses only \`terraform_data\` resources. It models account, region, tags and workload controls without provisioning AWS resources.

## 8. Lab A — Offline Terraform foundations

~~~bash
cd infrastructure-as-code/labs/chapter-036
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter036.tfplan
terraform apply chapter036.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected resources: \`terraform_data.aws_identity_contract\`, \`terraform_data.region_contract\`, \`terraform_data.workload_contract\`. A second unchanged plan should exit 0. **Do not apply prod inputs to dev state.**

## 9. Lab B — Positive and negative policy gates

~~~bash
python3 aws_foundation_gate.py fixtures/foundation-safe.json fixtures/plan-safe.json aws-foundation-policy.json
python3 aws_foundation_gate.py fixtures/foundation-unsafe.json fixtures/plan-destructive.json aws-foundation-policy.json
python3 -m unittest -v test_aws_foundation_gate.py
bash run-preflight.sh
~~~

The safe fixture passes; the unsafe fixture must fail. Tests cover AWS account IDs, region allowlists, region separation, mandatory tags, production database backup/encryption/Multi-AZ, S3 state versioning/encryption/locking, short-lived identity, approval ticket, owner, destructive actions, and fail-open policy mutation. Fixture claims are **not** proof of real AWS configuration.

## 10. Lab C — Optional AWS provider inspection (no apply)

1. Confirm a dedicated sandbox AWS account and approved cost budget.
2. Verify identity using STS; check expected account ID and region.
3. Review \`examples/aws-provider.tf.example\` and \`examples/s3-backend.tf.example\`.
4. In a **separate** working root, pin the provider and initialize with approved credentials.
5. Run \`terraform providers\`, \`terraform validate\`, and \`terraform plan\` only.
6. Inspect policy, IAM trust and potential resource replacement. Never apply the example automatically.
7. Remove temporary credentials, plans and sensitive artifacts.

## 11. Production SRE/DBRE scenarios

| Service | Terraform risks | Operational checks |
|---|---|---|
| RDS / Aurora / PostgreSQL | storage/engine replacement, KMS loss, subnet change | PITR, backups, Multi-AZ, replication lag, queries |
| OpenSearch | domain replacement, endpoint/security policy | snapshots, shard health, p99 latency |
| EKS | cluster/node replacement, IAM and CNI | PDBs, rollout, nodes, storage, API health |
| ElastiCache / Redis | subnet/replication changes | failover, persistence, client reconnect |
| MSK / Kafka | broker/network/ACL changes | ISR, lag, broker health |
| S3 | public access, lifecycle deletion, KMS policy | access audit, version recovery, cost |
| Cross-region DR | alias does not copy data | replication, RPO/RTO, failover tests |

## 12. Troubleshooting matrix

| Symptom | Root cause | Response |
|---|---|---|
| \`NoCredentialProviders\` / no valid credential sources | missing profile/OIDC role | verify identity and approved auth |
| \`AccessDenied\` | IAM/SCP/KMS policy | inspect denied API and principal, least-privilege fix |
| Account ID mismatch | wrong role/profile | stop; verify STS identity |
| Provider version conflict | incompatible constraints | inspect provider graph and lockfile |
| Region unsupported | wrong endpoint/partition | verify allowed regions and service support |
| S3 backend init failure | bucket, IAM, KMS, lockfile | validate backend separately |
| State lock contention | concurrent apply | wait; do not force unlock without incident approval |
| Unexpected replacement | immutable AWS argument | freeze, review plan and DBRE impact |
| RDS failover/lag | workload issue after apply | invoke DBRE service recovery runbook |
| High NAT/endpoint cost | architecture/capacity | inspect traffic, optimize with approval |

## 13. Production runbooks

**AWS onboarding:** create approved account and organizational policies → CI OIDC role → scoped permissions → CloudTrail/Config/CloudWatch → state bucket and KMS → tagging/budget → sandbox test.

**Pre-deployment:** verify STS identity/account/region → validate source/lockfile → inspect backend key and lock → run tests/policy → generate sanitized plan → owner and DBRE approvals.

**Unexpected replacement:** freeze apply → preserve state version/plan securely → inspect change → verify RDS snapshots/PITR → plan reviewed migration or rollback.

**Credential compromise:** revoke sessions/trust, rotate impacted credentials, inspect CloudTrail, quarantine CI artifacts and notify security.

**Regional incident:** declare incident → verify data replication and backup freshness → invoke tested failover plan → validate data integrity, DNS, clients and RPO/RTO; Terraform alone does not restore data.

## 14. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| AWS account/IAM/region design | 20 |
| Terraform provider, alias and lockfile governance | 20 |
| State encryption, locking and separation | 15 |
| Automated positive/negative policy tests | 20 |
| SRE/DBRE operations and DR runbooks | 15 |
| Audit evidence, tagging and cost guardrails | 10 |

Pass >=85 and zero critical failures: wrong account, static secret exposure, unapproved destructive plan, missing state isolation, disabled production backup/encryption, unverified CI role or false DR claim.

## 15. Cleanup and review questions

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the disposable offline lab.

Questions: What is an AWS account boundary? Why verify STS before apply? What does \`allowed_account_ids\` prevent? What does a provider alias *not* provide? Why can't backend configuration use input variables? What does the provider lockfile pin? What does S3 state restore not restore? Why is OIDC preferable to static CI keys? What is the DBRE acceptance gate for RDS? How do you distinguish an IaC plan from an operational recovery test?

**Next: Chapter 037 — AWS VPC, Subnets, Routing and Network Security with Terraform.**
