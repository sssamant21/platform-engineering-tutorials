# Chapter 044 — Azure compute and AKS SRE/DBRE runbooks

## Pre-change
Verify Azure tenant/subscription, state lock, quotas, private AKS DNS, node pool surge capacity, PDBs, workload identity, ACR access, approved image digest, ingress TLS, monitoring and database connection budgets. Review all Terraform replacement actions; get SRE, security and DBRE approval.

## AKS upgrade stuck
Stop concurrent changes; inspect Kubernetes events, PDBs, drain timeouts, upgrade surge and node quota. Recover capacity and known-good workloads; verify application error budget and downstream database connectivity.

## ImagePullBackOff
Check ACR private DNS, network and kubelet identity permissions. Verify digest exists and scan status. Do not insert registry passwords into Kubernetes or Terraform state as a shortcut.

## Managed identity 403
Check workload identity issuer, federated subject, service account and scoped Key Vault/Storage roles. Restore least privilege, re-run probes, preserve audit evidence.

## Application Gateway 502
Check backend probe status, endpoints, TLS, DNS and NSGs. Roll back unhealthy revision after change authorization. Confirm application and DB metrics recover.

## Database connection storm
Pause rollout or scale-out, cap concurrency, inspect pool and database connection limits, coordinate with DBRE and confirm replication/HA health.

## Zone failure / disaster recovery
Follow tested failover plan, verify zone-independent capacity, DNS, ingress and data-tier RPO/RTO. Terraform redeployment alone does not recover data.
