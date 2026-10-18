# Chapter 048 — GCP Security SRE/DBRE Runbooks

## Pre-change
Verify project, IAM effective grants, WIF trust, service agents, org policy, KMS key versions, Secret Manager metadata, state protection, audit and security/DBRE approval. Deny destructive key actions.

## IAM lockout
Preserve audit logs; inspect inherited allow/deny and org policy. Use audited break-glass approval and time-limited access. Restore least privilege.

## Workload Identity Federation failure
Inspect OIDC issuer, audience, subject and attribute mapping, STS and service-account impersonation. Repair trust narrowly; never issue JSON keys as workaround.

## CMEK outage
Freeze changes; check key version state, service-agent IAM, region and KMS availability. Restore authorized key access/version and validate decrypt and DB read/write.

## Secret exposure or disabled version
Restrict access; rotate source credential; update consumers; revoke compromised version; investigate Terraform state/history and logs without printing payloads.

## Terraform state leak/outage
Freeze writers; preserve object versions; rotate compromised credentials; restore GCS IAM/perimeter; validate lock ownership and drift.

## Security DR
Rebuild IAM, KMS, DNS, private network and data dependencies in tested order. Record RPO/RTO and security sign-off.
