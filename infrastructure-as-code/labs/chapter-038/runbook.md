# Chapter 038 — AWS security SRE/DBRE runbooks

## Pre-change checklist
1. Confirm STS principal, approved AWS account, region, deployment role and backend identity.
2. Review exact OIDC issuer, audience, subject and role trust; verify IAM boundaries and PassRole scope.
3. Review KMS key policy, grants, encryption context, deletion window and backup decrypt permissions.
4. Verify no production secret plaintext in Terraform variables, plans, state or CI logs.
5. Run tests and plan policy, inspect resource replacement, obtain security and DBRE approval.
6. Apply under remote state lock and confirm CloudTrail, application auth, backup and recovery evidence.

## IAM/OIDC failure
Freeze promotion. Inspect caller identity, token claims, role trust and CloudTrail. Correct scoped trust or permissions without granting wildcard admin. Re-run policy tests.

## Credential compromise
Contain the pipeline and affected role trust; revoke/expire credentials where feasible; rotate keys/secrets; preserve CloudTrail and CI artifacts securely; inventory affected accounts and workloads; notify security incident command.

## KMS access outage
Identify affected key ARN and ciphertext, inspect key state/policy/grants and encryption context. Restore approved decrypt access under dual control; validate encrypted RDS snapshots, S3 backups and application reads. Do not schedule deletion during recovery.

## Secrets rotation failure
Pause rotation; identify current/previous versions and dependent workloads; coordinate DBRE staged credential cutover; recycle pools, validate replicas and service SLO. Never print secret values during diagnostics.

## Disaster recovery
Test state restoration, KMS decryptability, Secrets Manager retrieval and **actual database restore** independently. Record observed RPO/RTO and incident command approvals.
