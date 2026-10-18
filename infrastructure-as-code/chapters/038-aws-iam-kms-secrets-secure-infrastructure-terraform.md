# Chapter 038 — AWS IAM, KMS, Secrets and Secure Infrastructure with Terraform

**Part 08 — AWS Infrastructure as Code · Chapter 038/120**  
**Audience:** SRE, DBRE, Cloud Security, Platform Engineering, DevSecOps  
**Prerequisites:** Chapters 001–037 · **Tools:** Terraform >=1.7, Python >=3.9, Bash  
**Lab posture:** Offline by default; built-in \`terraform_data\` only. AWS examples are **review-only** and never automatically deployed. Published content and authored tests are not execution or security-acceptance evidence.

## 1. Learning objectives and threat model

Design identity, encryption, secret lifecycle and deployment controls as first-class infrastructure contracts. By completion, you can distinguish identity-based policies, trust policies, resource policies, permission boundaries, service control policies (SCPs), KMS key policies and grants; safely configure Terraform provider authentication; reason about secret material in state; test dangerous privilege patterns; and respond to credential or key incidents.

**Threats:** compromised CI token, confused-deputy AssumeRole, overbroad IAM wildcard actions, privilege escalation through PassRole, unrestricted KMS decrypt, public secrets access, secrets written to Terraform state, cross-environment state access, unapproved key deletion, and unverified key/secret recovery.

## 2. Architecture

~~~text
Git pull request + CODEOWNERS + branch protection
       |
       +-- format / validate / policy / plan JSON / review
       |
CI OIDC token (short lived, audience and subject restricted)
       |
AWS STS AssumeRoleWithWebIdentity
       |
IAM deployment role (permissions boundary + scoped policy)
       |
       +--> Terraform AWS provider (allowed_account_ids, region)
       +--> encrypted, versioned, locked remote state (separate role)
       +--> workload IAM roles (no static keys)
       +--> KMS CMKs and tightly scoped grants
       +--> Secrets Manager (runtime retrieval via workload identity)
       |
CloudTrail + AWS Config + CloudWatch + GuardDuty / Security Hub
       |
SRE/DBRE evidence: auth health, decrypt failures, rotation, backup restore
~~~

Separate the **deployment role**, **state access role**, **workload role**, **break-glass role** and **security audit role**. Avoid sharing a powerful Terraform role with runtime applications.

## 3. IAM evaluation and least privilege

IAM evaluates applicable identity policies, resource policies, permission boundaries, SCPs, session policies and explicit denies; the exact intersection/union behavior depends on principal type and resource-policy grants. **An explicit deny overrides an allow.** Never assume an SCP grants access: it is a guardrail, not a grant. Permission boundaries constrain permissions; they do not grant them.

Design narrowly scoped \`Action\`, \`Resource\` and \`Condition\` fields. Evaluate service-specific resource support and condition keys. Use \`iam:PassRole\` restrictions to specific role ARNs and approved services. \`AdministratorAccess\`, \`iam:*\`, \`kms:*\`, \`secretsmanager:*\` and \`Resource: "*"\` require exceptional scrutiny; some discovery/list actions legitimately require a wildcard resource, so a production policy should distinguish allowed read-only exceptions.

**Role trust policy** controls who can assume the role. **Permissions policy** controls what the role can do after assumption. For GitHub OIDC, constrain \`token.actions.githubusercontent.com:aud\` and \`token.actions.githubusercontent.com:sub\` to the expected repository and environment/ref. For GitLab, validate the issuer, audience and subject for the exact GitLab instance and pipeline identity.

## 4. STS, OIDC and Terraform provider authentication

Prefer ephemeral credentials via IAM Identity Center for humans and OIDC federation for CI. Do not store AWS access keys in Terraform variables, state, source control or CI artifacts. Use provider \`allowed_account_ids\` to reduce wrong-account mistakes; verify the actual caller via \`aws sts get-caller-identity\` before planning.

~~~bash
aws sts get-caller-identity
aws configure list-profiles
AWS_PROFILE=approved-sandbox aws sts get-caller-identity
~~~

AWS session duration and token scope must match pipeline operations; long applies need carefully managed credential refresh. Never print the environment or debug credential-bearing requests in shared logs.

## 5. KMS fundamentals and key governance

Understand symmetric encryption keys, envelope encryption, AWS-managed versus customer-managed keys, aliases, key policies, grants and encryption context. **KMS key policies are essential to authorization**; IAM policy alone may not be sufficient. Limit decrypt and data-key generation by workload identity and service context, and review \`kms:ViaService\` and encryption-context conditions when supported.

Key rotation changes backing key material for supported keys; it does **not** re-encrypt all historical data or migrate ciphertext to a new KMS key. Key deletion is destructive and subject to a waiting period. Plan recovery for disabled keys, revoked grants, inaccessible backups, cross-region key design and multi-region replica limitations. A Terraform rollback cannot restore a deleted KMS key.

## 6. Secrets Manager and state safety

Secrets Manager manages encrypted secret values, versions and rotation integrations. Store secret metadata, resource policies and rotation schedules in Terraform where appropriate, but **do not put production secret values in \`aws_secretsmanager_secret_version.secret_string\`** unless your design explicitly accepts state exposure and has approved controls. Even sensitive Terraform values may be retained in state or plan files. Prefer application runtime retrieval using workload identity and an SDK, with scoped resource policies and rotation.

Secret rotation requires testing consumers, connection pools, replicas, database credentials, cache TTLs, failover and rollback. A rotated password can break DB clients before IaC drift appears. Use dual-credential or staged rotation where the backend supports it.

## 7. Terraform architecture and change controls

Child modules publish narrow outputs: role ARN, key ARN, secret ARN, and contract version. Do not output secret plaintext. Keep the provider configuration at the root, pin provider versions in the lockfile and module releases independently. Use separate accounts, backends and CI identities by environment.

Review \`terraform plan\` for changes to role trust, wildcard IAM actions, KMS key policy, key deletion window, secret resource policies and secret rotation settings. Apply via a locked backend and approved change ticket. Use \`prevent_destroy\` selectively for critical keys/secrets, but understand that it does not prevent out-of-band deletion and may impede emergency recovery.

## 8. Executable lab layout

~~~text
labs/chapter-038/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/{aws-iam-kms-secrets.tf.example,oidc-trust-policy.json.example,identity-preflight.sh.example}
  security-policy.json
  fixtures/{security-safe.json,security-unsafe.json,plan-safe.json,plan-destructive.json}
  security_gate.py, test_security_gate.py, run-preflight.sh
  runbook.md, acceptance.md, .gitignore
~~~

The root models IAM, KMS, secret metadata and audit contracts with \`terraform_data\`. It **does not** create an IAM role, key or secret. The policy gate validates declared JSON evidence and plan actions; it does not parse AWS IAM JSON policy documents or prove live AWS security.

## 9. Lab A — Offline contract plan

~~~bash
cd infrastructure-as-code/labs/chapter-038
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter038.tfplan
terraform apply chapter038.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expect four \`terraform_data\` resources: \`identity_contract\`, \`kms_contract\`, \`secrets_contract\`, \`audit_contract\`. The second unchanged plan should exit 0. Use a distinct backend/state for prod; **never switch dev state to prod variables**.

## 10. Lab B — Positive and negative security gates

~~~bash
python3 security_gate.py fixtures/security-safe.json fixtures/plan-safe.json security-policy.json
python3 security_gate.py fixtures/security-unsafe.json fixtures/plan-destructive.json security-policy.json
python3 -m unittest -v test_security_gate.py
bash run-preflight.sh
~~~

Safe input must pass and unsafe input must fail. Tests mutate trust issuer, audience, subject, policy wildcards, PassRole, static keys, state isolation, KMS deletion/rotation, unrestricted decrypt, secret plaintext in state, rotation, logging, ownership, change approval, and destructive plan actions.

## 11. Lab C — Review-only AWS integration

1. Obtain a dedicated AWS sandbox account, a cost budget and security approval.
2. Verify STS identity, expected account ID, region and assumed role.
3. Inspect the example Terraform and OIDC trust policy; replace placeholders with approved values.
4. In a **separate root**, initialize the AWS provider and secure remote backend; inspect provider lockfile.
5. Run \`terraform validate\` and \`terraform plan\` without apply.
6. Review effective IAM permissions with IAM Access Analyzer and the policy simulator where appropriate; inspect key policies and secret resource policies.
7. Validate CloudTrail audit coverage, KMS access and rotation integration separately before production use.

## 12. SRE/DBRE production scenarios

| Service | Security change | Reliability check |
|---|---|---|
| RDS / Aurora / PostgreSQL | secret rotation, KMS grants | authentication, PITR, read/write, failover |
| EKS / IRSA / Pod Identity | role trust or service account | workload startup, STS exchange, least privilege |
| OpenSearch | domain IAM policy or KMS key | query access, snapshot restore, encryption |
| ElastiCache / Redis | auth token and TLS | reconnect, replication, failover |
| MSK / Kafka | IAM authentication or TLS | producer/consumer auth, ISR, lag |
| S3 backups | KMS decrypt / bucket policy | restore from independent role |
| Snowflake integration | external ID or IAM role | ingestion auth, audit, data freshness |

## 13. Troubleshooting matrix

| Symptom | Possible cause | Safe response |
|---|---|---|
| \`AccessDenied\` on AssumeRole | trust subject/audience mismatch | inspect STS principal and exact claim conditions |
| KMS \`AccessDeniedException\` | key policy, grant, context | inspect CloudTrail, key policy and context |
| Secret retrieval fails | resource policy, KMS decrypt, VPC endpoint | verify path without logging secret value |
| Database auth fails after rotation | stale pool, old credential | staged rotation and consumer refresh |
| Provider targets wrong account | profile/role drift | stop, verify STS and account allowlist |
| Plan replaces KMS key | immutable argument change | freeze, impact and decrypt/backup review |
| Key disabled | incident or policy error | security approval, inspect dependent resources |
| CI logs contain credentials | debug output or artifact leak | contain, revoke, rotate, audit |
| State lock contention | concurrent run | wait, investigate; do not blindly force-unlock |

## 14. Production runbooks

**Secure deployment:** verify identity and account → code owner approval → least-privilege and trust review → KMS/secret policy review → test and plan gate → state backup and lock → deploy → validate audit, decrypt and application auth.

**Credential compromise:** revoke affected sessions/keys, disable malicious trust paths, preserve CloudTrail and CI evidence, rotate secrets, verify downstream systems and report through security incident command.

**KMS incident:** freeze key changes, identify affected ciphertext and services, verify key state/policy/grants, restore authorized access under dual control, validate database backups and application reads. Never delete a key as a quick fix.

**Secret rotation failure:** stop further rotation, identify version stages, validate prior credential viability, coordinate DBRE cutover, recycle pools, verify replication and client health, and document recovery.

**DR:** separately test state recovery, key availability, encrypted backup decryptability, secret access and actual data restore. RPO/RTO acceptance requires observed evidence.

## 15. 100-point acceptance

| Domain | Points |
|---|---:|
| IAM trust, permissions, SCP/boundary design | 25 |
| OIDC/STS identity and state isolation | 15 |
| KMS key policies, grants and recovery | 20 |
| Secrets lifecycle and state hygiene | 15 |
| Automated security gates and negative tests | 15 |
| SRE/DBRE incident and audit evidence | 10 |

Pass >=85 with **zero critical failures**: leaked production secret, unbounded CI trust, public secret policy, unreviewed KMS deletion, production wildcard admin policy, wrong account, missing backup decryptability or bypassed tests. Record real evidence in \`acceptance.md\`; authored fixtures do not constitute approval.

## 16. Cleanup and knowledge check

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Only destroy disposable local \`terraform_data\` resources.

Review: Why do trust and permission policies differ? Does an SCP grant access? Why does \`sensitive = true\` not remove secrets from state? Can key rotation decrypt historical ciphertext? What breaks after Secrets Manager rotation? How does OIDC subject scoping prevent confused-deputy access? Why must encrypted backups be restore-tested?

**Next: Chapter 039 — AWS Compute, EKS and Application Infrastructure with Terraform.**
