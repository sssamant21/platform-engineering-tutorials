# Chapter 075 — AKS Enterprise GitOps Production Operations and Disaster Recovery Capstone

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 15:** Azure Kubernetes Service (AKS) — Final Capstone  
**Chapter:** 075 / 100  
**Audience:** Platform Engineers, SREs, DBREs, DevSecOps, Incident Commanders and Azure Architects

> **Safety:** Execute destructive tests only in a disposable AKS staging cluster using synthetic data, dedicated Azure identities and approved budgets. Never remove production node pools, alter shared private DNS, delete live persistent volumes, force-drain production workloads or expose a private API endpoint to solve a connectivity issue. Backups and restores must be tested before any disaster exercise.

## 1. Capstone mission

Build, secure, operate, troubleshoot and recover a production-oriented Azure Kubernetes Service platform managed with Terraform, GitLab CI/CD and Argo CD.

This capstone integrates:

- Chapter 071 — AKS architecture, Terraform provisioning and platform foundations.
- Chapter 072 — Node pools, autoscaling, scheduling and capacity.
- Chapter 073 — Networking, ingress, Azure Disk and Azure Files CSI.
- Chapter 074 — Microsoft Entra security, workload identity, observability and upgrades.

**Required result:** An independent reviewer can reproduce the AKS platform, deploy a signed immutable image through an approved GitOps workflow, verify least-privilege cloud access, restore a stateful workload from tested backups and confirm SLOs after simulated failures.

## 2. End-to-end reference architecture

~~~text
Microsoft Entra ID / MFA / PIM / Azure RBAC
                     |
           Azure subscription + policy
                     |
        GitLab protected Terraform MR
                     |
     VNet / private DNS / NSGs / UDRs / egress
                     |
             Private AKS API
                     |
       System node pool across AZs
            /                \
         CoreDNS           Argo CD
            |                |
       Azure CNI        GitOps reconciliation
            |                |
      User node pools <- autoscaler/HPA
            |
  signed application images from ACR
            |
  Workload ID -> Azure Key Vault / Storage
            |
       Internal ingress + TLS
            |
    Deployments / StatefulSets
       /                 \
 Azure Disk CSI       Azure Files CSI
       \                 /
        backup + isolated restore
                 |
 Azure Monitor / Prometheus / Grafana
                 |
        SRE alerts and runbooks
                 |
   Recovery AKS cluster / approved cutover
~~~

**Ownership:** Terraform manages Azure infrastructure, identities and foundational AKS configuration; Argo CD manages delegated Kubernetes workloads and controllers; AKS-managed control loops own node scaling and managed control-plane operations. Avoid overlapping ownership.

## 3. Capstone acceptance contract

| Domain | Minimum demonstration | Evidence |
| --- | --- | --- |
| Azure landing zone | Correct tenant, subscription, region and policies | Azure inventory |
| Infrastructure | Repeatable private AKS Terraform provisioning | Plan and outputs |
| Identity | Scoped Entra, RBAC and Workload ID | Positive/negative tests |
| Compute | Resilient system/user pools and autoscaling | Node and HPA events |
| Networking | DNS, CNI, internal ingress and TLS | Connectivity tests |
| Storage | Encrypted PVCs and verified restore | Backup/checksum |
| Delivery | Signed digest via reviewed GitLab GitOps MR | Pipeline and Argo CD |
| Security | Admission, Key Vault and audit logs | Denial/audit evidence |
| Observability | Alerts, dashboards and SLOs | Synthetic incident |
| Disaster recovery | Rebuild and data restoration | RPO/RTO transcript |
| FinOps | Tagged resources, budgets and cleanup | Cost report |

## 4. Recovery objectives

Set workload-specific RPO/RTO and availability objectives before testing. Illustrative staging acceptance targets:

| Indicator | Exercise target |
| --- | --- |
| Required workload replicas | All Ready after recovery |
| Private API connectivity | Available to approved operators |
| Internal ingress | Healthy TLS and backend targets |
| Backup integrity | Checksum/application consistency pass |
| RPO | No more than 15 minutes in the selected design |
| RTO | No more than 60 minutes in the selected design |
| Unauthorized cloud access | Denied |
| Untrusted image admission | Denied in enforced scope |

Targets are examples, not claims of production suitability. If data replication, backup frequency or Azure resource provisioning cannot meet these values, revise the architecture or targets before approval.

## 5. Prerequisites

- Dedicated staging Azure subscription/resource group and cost budget.
- Azure CLI, kubelogin, Terraform, kubectl and Helm.
- Approved AKS region, Kubernetes version, VM SKUs and quotas.
- Private API access through approved network and DNS.
- Entra groups, Azure RBAC and workload identity federation.
- System and user node pools with availability and autoscaling plan.
- Azure CNI, CoreDNS, Azure Disk/Files CSI and ingress controller.
- Azure Container Registry with signed synthetic images.
- GitLab protected branches, CI identity and GitOps repository.
- Argo CD with restricted AppProjects and approved bootstrap method.
- Azure Monitor, Log Analytics, managed Prometheus/Grafana.
- Synthetic stateful data, backup target and recovery region plan.
- Security review, change approval, incident commander and teardown owner.

## 6. Environment preflight

~~~bash
az account show --output table
kubectl config current-context
az aks show -g rg-aks-staging -n aks-staging \
  --query '{name:name,version:kubernetesVersion,state:provisioningState,private:apiServerAccessProfile}' -o json
az aks nodepool list -g rg-aks-staging --cluster-name aks-staging -o table
kubectl get nodes -o wide
kubectl get pods -A
kubectl get storageclasses,csidrivers
kubectl -n argocd get applications.argoproj.io
~~~

**Stop conditions:** wrong subscription, unexpected cluster context, missing backup, unknown Terraform state owner, inadequate budget, missing private connectivity or unresolved production impact.

## 7. Reference repository

~~~text
aks-enterprise-capstone/
  terraform/
    backend.tf
    versions.tf
    providers.tf
    networking.tf
    identities.tf
    aks.tf
    nodepools.tf
    diagnostics.tf
    outputs.tf
    environments/
      staging.tfvars
  gitops/
    bootstrap/
      argocd/
    clusters/
      aks-staging/
        platform/
          security/
          networking/
          ingress/
          storage/
          observability/
        applications/
          stateless-demo/
          stateful-demo/
    policies/
  ci/
    validate-terraform.sh
    validate-manifests.sh
    verify-image-signature.sh
    check-aks-policy.sh
    generate-evidence.sh
  runbooks/
    private-api-recovery.md
    nodepool-capacity.md
    workload-identity.md
    ingress-dns.md
    storage-restore.md
    gitops-rollback.md
    cluster-rebuild.md
  evidence/
    acceptance-report.md
~~~

Script names are illustrative and must be implemented and tested. Never commit Terraform state, plan artifacts containing sensitive data, kubeconfigs, credentials or Key Vault secret values.

## 8. Terraform state and infrastructure governance

Use approved Azure remote backend with encryption, access control, versioning and state locking. Pin Terraform and AzureRM provider versions. Review every plan, including resource deletions and role assignment changes.

~~~bash
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=environments/staging.tfvars -out=staging.tfplan
terraform -chdir=terraform show staging.tfplan
~~~

Apply only through protected change control. Plan files can contain sensitive information and should not be published as unrestricted CI artifacts.

## 9. AKS private networking

Validate Azure CNI mode, nonoverlapping VNet/Pod/Service CIDRs, NSGs, UDRs, egress, CoreDNS and private DNS. The private AKS API must remain reachable from approved operators and GitLab runners without broadening public exposure.

Check actual network mode and policy dataplane before relying on NetworkPolicy manifests. Private endpoints for Key Vault, ACR or Storage introduce additional DNS and routing dependencies.

## 10. Node pools and capacity

Keep a stable On-Demand system pool for critical add-ons and Argo CD. Use user pools for applications, with documented autoscaling bounds, VM-family quota, AZ spread, workload requests and Spot restrictions.

Use HPA for Pod replicas and supported AKS Cluster Autoscaler or node auto-provisioning for node capacity. Do not configure conflicting autoscaler ownership or assume NAP is compatible with every existing cluster configuration.

## 11. Azure Disk and Azure Files recovery

Azure Disk CSI is suited to supported block-storage workloads with topology constraints; Azure Files CSI supports appropriate shared filesystem patterns. Neither replaces application-consistent backup.

For disaster recovery, verify:

1. StorageClass and reclaim policy.
2. Encryption/key availability in recovery environment.
3. Backup retention and independent access.
4. Snapshot and backup restore semantics.
5. PVC topology and node placement.
6. Database or application integrity.
7. Traffic cutover and rollback criteria.

## 12. Microsoft Entra and Workload ID

Use Microsoft Entra groups, Azure RBAC and Kubernetes authorization appropriately. Federated Workload ID trust must match the exact AKS OIDC issuer and ServiceAccount subject; the managed identity requires separately scoped Azure resource permissions.

Never use long-lived client secrets when workload federation is supported. Test both permitted and denied operations, and confirm Key Vault access does not leak into Git or CI logs.

## 13. GitLab and Argo CD release chain

~~~text
Source MR -> unit/integration tests
          -> SBOM and vulnerability scan
          -> immutable OCI image digest
          -> signing/provenance verification
          -> protected GitOps MR
          -> CODEOWNERS/security approval
          -> Argo CD sync
          -> admission verification
          -> Pod imageID + readiness + SLO
~~~

CI should not hold persistent cluster-admin kubeconfig. Argo CD AppProjects should restrict repositories, destinations and privileged resource kinds. Rollback through reviewed Git history rather than untracked imperative mutation.

## 14. Illustrative GitLab pipeline

~~~yaml
stages: [validate, test, build, verify, promote]

validate:
  stage: validate
  image: registry.example.internal/ci/platform-tools:PINNED_DIGEST
  script:
    - ./ci/validate-terraform.sh
    - ./ci/validate-manifests.sh

test:
  stage: test
  image: registry.example.internal/ci/test-tools:PINNED_DIGEST
  script:
    - ./ci/run-application-tests.sh

build:
  stage: build
  image: registry.example.internal/ci/oci-builder:PINNED_DIGEST
  script:
    - ./ci/build-and-push.sh

verify:
  stage: verify
  image: registry.example.internal/ci/security-tools:PINNED_DIGEST
  script:
    - ./ci/verify-image-signature.sh
    - ./ci/check-aks-policy.sh

promote:
  stage: promote
  image: registry.example.internal/ci/gitlab-tools:PINNED_DIGEST
  script:
    - ./ci/propose-protected-gitops-mr.sh
~~~

Images and scripts are illustrative, not supplied executable assets. Implement protected artifact transfer, short-lived Azure federation and independent approvals.

## 15. Operational observability

Capture Azure Activity Log, AKS Kubernetes audit logs, Azure Monitor Container Insights, managed Prometheus metrics, Grafana dashboards, Argo CD reconciliation and application traces.

Critical signals include node Ready capacity, Pod Pending duration, Azure CNI/DNS failures, ingress target health, TLS expiry, CSI attach/mount failures, Workload ID token exchange, Key Vault errors, GitOps drift and application error/latency SLOs.

Set alert severity by user impact and owner; avoid paging for every transient Pod restart.

## 16. Change and upgrade readiness

Before an AKS upgrade, inventory Kubernetes APIs, node images, CNI/CSI drivers, ingress, admission, Argo CD and autoscaling. Confirm surge capacity, PDBs, topology, backup and forward-repair procedures.

AKS control-plane downgrade is not a standard rollback mechanism. Test compatible forward repair or replacement-cluster recovery in staging.

## 17. Disaster recovery design

A second AKS cluster is not automatically a disaster recovery solution. Define whether the recovery region has preprovisioned network/identity dependencies, data replication, container registry availability, private DNS, Key Vault access and sufficient quota.

Design warm standby, cold rebuild or active-active based on actual RPO/RTO and cost. Store infrastructure, GitOps and backup evidence in locations accessible during primary-region failure. Test dependencies explicitly.

## 18. Incident response governance

Use a declared incident commander, platform lead, security lead, application owner and communications owner. Record event timestamps, change IDs, affected services, containment decisions, recovery steps, measured RTO and corrective actions.

Do not perform unreviewed destructive commands merely to clear alerts. Prioritize data integrity and security boundaries.

## 19. Lab A — Azure landing zone audit

1. Verify tenant, subscription, region and AKS context.
2. Review Terraform state, role assignments and Azure Policy.
3. Inspect VNet, NSGs, UDRs and private DNS.
4. Confirm Azure budget and required tags.
5. Validate break-glass access procedure.
6. Archive redacted evidence.

**Pass:** no unapproved subscription, network or identity ownership.

## 20. Lab B — Terraform reproducibility

1. Pin approved provider/module versions.
2. Run fmt, validate and plan.
3. Review plan for destructive changes.
4. Apply to disposable staging environment.
5. Verify Azure resources match desired state.
6. Document rollback and state recovery.

**Pass:** infrastructure is reproducible through reviewed IaC.

## 21. Lab C — Entra and Kubernetes RBAC

1. Create staging observer role assignment.
2. Authenticate using kubelogin.
3. Verify permitted namespace read.
4. Verify Secret read and cluster mutation are denied.
5. Capture Azure Activity and Kubernetes audit events.
6. Revoke test access.

**Pass:** least privilege is demonstrated.

## 22. Lab D — Workload ID and Key Vault

1. Create user-assigned managed identity.
2. Configure exact AKS OIDC federated credential.
3. Deploy labeled synthetic ServiceAccount workload.
4. Read synthetic Key Vault secret with scoped access.
5. Attempt unauthorized resource access.
6. Rotate synthetic secret and verify reload.

**Pass:** no static Azure credentials and negative authorization test passes.

## 23. Lab E — System/user pool resilience

1. Inspect system pool and user pool AZ placement.
2. Verify critical add-ons on stable system capacity.
3. Increase synthetic workload requests.
4. Observe user pool autoscaling.
5. Drain one approved disposable application node.
6. Verify recovery and SLO impact.

**Pass:** platform controllers remain healthy during user capacity changes.

## 24. Lab F — Spot and batch interruption

1. Deploy retryable synthetic batch job on isolated Spot pool.
2. Confirm taints, tolerations and node affinity.
3. Simulate interruption using approved test mechanism.
4. Verify retries/checkpoint handling.
5. Validate On-Demand fallback if designed.
6. Record cost and recovery evidence.

**Pass:** batch workload tolerates interruption.

## 25. Lab G — Azure CNI and CoreDNS

1. Record CNI mode and Pod/Service CIDRs.
2. Deploy synthetic DNS client and API Service.
3. Verify Service discovery and EndpointSlices.
4. Simulate isolated DNS misconfiguration.
5. Restore DNS without changing private API exposure.
6. Validate connectivity.

**Pass:** DNS and Pod networking are diagnosable.

## 26. Lab H — Internal ingress and TLS

1. Deploy synthetic application.
2. Configure approved internal ingress controller.
3. Provision private DNS and test certificate.
4. Verify HTTPS and backend health.
5. Simulate backend readiness failure.
6. Restore service and validate no public exposure.

**Pass:** ingress meets security and availability objectives.

## 27. Lab I — Azure Disk CSI persistence

1. Create encrypted disposable Azure Disk PVC.
2. Mount into synthetic StatefulSet.
3. Write data with checksum.
4. Restart Pod and verify persistence.
5. Simulate incompatible AZ placement.
6. Restore scheduling and verify integrity.

**Pass:** storage topology and persistence are understood.

## 28. Lab J — Azure Files CSI shared storage

1. Provision approved Azure Files RWX PVC.
2. Mount on two synthetic Pods.
3. Test shared read/write behavior.
4. Inspect SMB/NFS network dependencies.
5. Simulate blocked protocol path in staging.
6. Restore access and verify consistency.

**Pass:** shared filesystem works without broad storage account access.

## 29. Lab K — Signed image GitOps promotion

1. Build synthetic application and produce SBOM.
2. Scan and sign image digest.
3. Propose protected GitOps MR.
4. Obtain independent approval.
5. Merge and verify Argo CD reconciliation.
6. Confirm running Pod imageID matches approved digest.

**Pass:** release chain is traceable end-to-end.

## 30. Lab L — GitOps rollback and admission

1. Deploy a reviewed healthy revision.
2. Introduce synthetic application regression.
3. Confirm alert and Argo CD health.
4. Revert through reviewed GitOps MR.
5. Validate admission policy remains enforced.
6. Confirm service recovery.

**Pass:** rollback does not bypass security or erase stateful data.

## 31. Lab M — Audit and observability

1. Enable approved AKS diagnostics and Azure Activity Log export.
2. Verify managed Prometheus targets and Grafana dashboards.
3. Generate synthetic denied API request.
4. Confirm log correlation and alert routing.
5. Generate a synthetic workload availability alert.
6. Measure detection latency.

**Pass:** security and reliability incidents are observable.

## 32. Lab N — Node image upgrade rehearsal

1. Review node pool versions and supported images.
2. Validate PDBs, surge capacity and AZ spread.
3. Perform approved staging node image update.
4. Observe cordon, drain and replacement.
5. Verify storage mounts, DNS, ingress and workloads.
6. Record disruption and forward-recovery plan.

**Pass:** node maintenance stays within SLO.

## 33. Lab O — Backup and isolated restore

1. Generate synthetic stateful dataset and checksum.
2. Perform application-consistent backup and supported snapshot.
3. Record backup timestamp and restore point.
4. Restore to new PVC and namespace.
5. Verify checksum and application semantics.
6. Measure RPO/RTO.

**Pass:** data restoration meets documented objectives.

## 34. Lab P — Recovery cluster rebuild

1. Provision isolated recovery VNet and AKS cluster.
2. Restore approved Terraform and GitOps revisions.
3. Recreate Entra/Workload ID and Key Vault trust.
4. Bootstrap Argo CD and platform add-ons.
5. Restore synthetic data from verified backup.
6. Validate DNS, ingress, identity, admission and SLO.
7. Record recovery time and cost.

**Pass:** secure workload service can be reconstructed independently.

## 35. Lab Q — Incident command simulation

1. Simulate combined Pod Pending, ingress 5xx and CSI mount failure.
2. Assign incident commander and technical leads.
3. Correlate Azure Monitor, Kubernetes events and GitOps revisions.
4. Identify independent failures versus shared dependency.
5. Recover without destructive PVC operations.
6. Produce incident timeline and corrective actions.

**Pass:** incident response is coordinated and auditable.

## 36. Lab R — FinOps and teardown

1. Inventory AKS control-plane tier, VMs, disks, Files, ingress, NAT and monitoring costs.
2. Review node pool utilization and autoscaling bounds.
3. Verify cost tags and budget alerts.
4. Identify orphaned load balancers and volumes.
5. Preserve required recovery evidence.
6. Tear down only approved disposable resources.

**Pass:** no unintended chargeable test resources remain.

## 37. Troubleshooting — twenty integrated scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | AKS API unreachable | Private DNS/routing | Restore approved access path |
| 2 | kubectl Unauthorized | Entra/kubelogin/tenant | Verify caller identity |
| 3 | kubectl Forbidden | Azure/Kubernetes RBAC | Repair scoped authorization |
| 4 | Terraform AKS create fails | Quota/region/permissions | Inspect Azure operations |
| 5 | System Pods Pending | System pool capacity | Restore stable nodes |
| 6 | Autoscaler fails | Max count/VM quota | Repair capacity bounds |
| 7 | Spot workload interrupted | Azure capacity reclaim | Retry/fallback |
| 8 | Pod networking fails | Azure CNI/subnet | Inspect dataplane and IPs |
| 9 | DNS SERVFAIL | CoreDNS/upstream/private DNS | Restore DNS dependency |
| 10 | Internal ingress unavailable | LB/NSG/route | Trace frontend/backend |
| 11 | TLS failure | Certificate/hostname | Restore approved certificate |
| 12 | Azure Disk PVC Pending | CSI/topology | Inspect provisioner |
| 13 | Azure Disk attach fails | AZ mismatch/attachment | Restore compatible node |
| 14 | Azure Files mount fails | SMB/NFS/private endpoint | Repair network/access |
| 15 | Workload ID token exchange fails | Federation subject/issuer | Repair exact trust |
| 16 | Key Vault AccessDenied | Resource RBAC | Restore minimum permission |
| 17 | ACR ImagePullBackOff | Kubelet pull access | Restore registry authorization |
| 18 | Argo CD sync denied | AppProject/admission | Correct GitOps policy |
| 19 | Node upgrade stalls | PDB/surge capacity | Restore headroom |
| 20 | DR restore invalid | Backup consistency/keys | Use verified recovery point |

## 38. Runbook — AKS private API outage

1. Confirm Azure subscription and AKS provisioning state.
2. Verify operator identity and kubelogin.
3. Resolve private API FQDN from approved network.
4. Check private DNS zone links, VPN/ExpressRoute and NSGs.
5. Restore private connectivity without public exposure.
6. Validate kubectl, Argo CD and critical workloads.
7. Record incident evidence and preventive controls.

## 39. Runbook — system/user pool capacity incident

1. Identify Pending Pods, requests and scheduler events.
2. Inspect system/user pool Ready nodes and AZ distribution.
3. Check autoscaler bounds, Azure quota and VM SKU capacity.
4. Restore approved system or user pool headroom.
5. Verify Pod readiness and PDB/topology behavior.
6. Measure application SLO and cost impact.
7. Update capacity forecast.

## 40. Runbook — workload identity or Key Vault outage

1. Identify ServiceAccount, managed identity and target Key Vault.
2. Validate OIDC issuer, audience, federated subject and Pod label.
3. Check Azure role scope and Key Vault network path.
4. Restore least-privilege trust and authorization.
5. Verify synthetic allowed and denied operations.
6. Rotate exposed secrets if compromise is suspected.
7. Preserve audit evidence.

## 41. Runbook — ingress, CNI and DNS outage

1. Identify affected hostnames, Services, namespaces and AZs.
2. Inspect CoreDNS, EndpointSlices, Azure CNI and NetworkPolicy.
3. Check ingress controller, LB frontend, NSGs, TLS and routes.
4. Restore approved GitOps configuration or platform dependency.
5. Verify internal/private exposure.
6. Validate application SLO.
7. Archive logs and timeline.

## 42. Runbook — persistent volume incident

1. Identify PVC/PV, CSI driver, disk/share and encryption dependency.
2. Inspect CSI logs, Azure operations and storage topology.
3. Stop destructive changes and preserve backup evidence.
4. Restore supported attachment/mount or recover to new PVC.
5. Verify application-consistent data integrity.
6. Measure RPO/RTO and controlled cutover.
7. Record corrective actions.

## 43. Runbook — failed GitOps release

1. Identify GitLab pipeline, source SHA, image digest and Argo CD revision.
2. Distinguish admission, image pull, identity, storage and runtime failures.
3. Pause unsafe promotions.
4. Revert via reviewed GitOps MR or deploy verified forward fix.
5. Protect persistent resources from unsafe pruning.
6. Validate readiness, ingress and application SLO.
7. Record RCA and regression checks.

## 44. Runbook — AKS upgrade failure

1. Freeze concurrent changes and inspect AKS operation status.
2. Review version compatibility, deprecated APIs and webhooks.
3. Check node pool surge, PDBs and Azure quota.
4. Restore compatible CNI/CSI/ingress controllers and nodes.
5. Validate identity, DNS, storage and GitOps.
6. Plan supported forward repair or replacement-cluster migration.
7. Do not assume control-plane downgrade.
8. Document incident and approval.

## 45. Runbook — full regional disaster recovery

1. Declare disaster and agreed RPO/RTO.
2. Establish recovery subscription/region/network and private DNS.
3. Provision AKS and stable system capacity from reviewed Terraform.
4. Restore Entra/Workload ID federation, Key Vault and ACR access.
5. Bootstrap approved Argo CD controllers and GitOps state.
6. Restore application-consistent data to new storage.
7. Verify signed digest, admission, TLS, ingress and application SLO.
8. Perform approved traffic cutover and preserve recovery evidence.

## 46. Evidence template

~~~text
Capstone / change ID:
Azure tenant, subscription, region and AKS cluster:
Terraform state and reviewed plan:
AKS version, private endpoint and DNS:
System/user pools, VM SKUs, AZs and autoscaler bounds:
Azure CNI, subnet, NSG and routing:
Entra access, Kubernetes RBAC and Workload ID:
Key Vault, ACR and admission evidence:
Ingress controller, private DNS and TLS:
Azure Disk/Files CSI, PVC/PV and encryption:
GitLab pipeline, image digest and signature:
GitOps MR, Argo CD revision and approval:
Azure Monitor, Activity Log and AKS audit:
Backup point, restore checksum and measured RPO/RTO:
Failure simulations and incident timeline:
Cost inventory and teardown:
Independent reviewers and archive:
~~~

Do not store credentials, decoded Kubernetes Secrets, private keys or Terraform state secrets in evidence archives.

## 47. Scored enterprise readiness assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| Azure landing zone and Terraform | 15 | Approved infrastructure and private access |
| Identity, Workload ID and security | 15 | Allowed/denied access, admission |
| Node pools and autoscaling resilience | 15 | Capacity and disruption labs |
| Networking, ingress and TLS | 10 | DNS, policy and endpoint tests |
| Persistent storage and disaster recovery | 20 | Verified backup and restore |
| GitLab/Argo CD release governance | 10 | Signed digest, MR and rollback |
| Monitoring and incident response | 10 | Alerts and runbooks |
| FinOps and evidence | 5 | Cost, ownership and audit |
| **Total** | **100** | |

**Pass:** at least 85/100 **and** all critical controls: no wrong-subscription changes, no unreviewed public API/ingress exposure, no unauthorized cloud or Kubernetes admin, no plaintext credentials, signed-image enforcement in required scope, and verified recovery meeting approved RPO/RTO.

## 48. Final acceptance checklist

- [ ] Azure tenant, subscription, region and budget verified.
- [ ] Terraform state, plan and change governance approved.
- [ ] Private AKS API and DNS connectivity validated.
- [ ] System/user pool resilience and autoscaling tested.
- [ ] Azure CNI, CoreDNS and NetworkPolicy validated.
- [ ] Internal ingress, TLS and endpoint health verified.
- [ ] Azure Disk/Files CSI and reclaim policy reviewed.
- [ ] Application-consistent backup and isolated restore verified.
- [ ] Entra, Azure RBAC and Kubernetes authorization tested.
- [ ] Workload ID and Key Vault access least-privileged.
- [ ] ACR signed digest and admission policy validated.
- [ ] GitLab/Argo CD promotion and rollback demonstrated.
- [ ] Azure Monitor, Activity Log and AKS audit operational.
- [ ] Node image and control-plane upgrade rehearsed.
- [ ] Eighteen labs completed with evidence.
- [ ] Eight production runbooks reviewed.
- [ ] RPO/RTO, SLO and cost objectives accepted.
- [ ] Independent platform, security and SRE sign-off completed.

## 49. Knowledge check

1. Why is a private AKS API endpoint insufficient without private DNS and approved routing?
2. How do Azure RBAC and Kubernetes RBAC interact?
3. Why is Workload ID federation preferable to static client secrets?
4. How do HPA and AKS Cluster Autoscaler coordinate?
5. Why can strict topology constraints leave Pods Pending?
6. When should Azure Disk or Azure Files be used?
7. Why must CSI snapshots be paired with application-consistent backup?
8. How can GitLab and Argo CD preserve separation of duties?
9. Why is control-plane downgrade not a standard AKS upgrade rollback?
10. What evidence proves an AKS platform can be recovered securely in another region?

## 50. References

- [Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [AKS baseline architecture](https://learn.microsoft.com/azure/architecture/reference-architectures/containers/aks/baseline-aks)
- [AKS private clusters](https://learn.microsoft.com/azure/aks/private-clusters)
- [AKS node pools](https://learn.microsoft.com/azure/aks/create-node-pools)
- [AKS Cluster Autoscaler](https://learn.microsoft.com/azure/aks/cluster-autoscaler)
- [AKS networking](https://learn.microsoft.com/azure/aks/concepts-network)
- [AKS Azure Disk CSI](https://learn.microsoft.com/azure/aks/azure-disk-csi)
- [AKS Azure Files CSI](https://learn.microsoft.com/azure/aks/azure-files-csi)
- [AKS Workload Identity](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [AKS Key Vault CSI](https://learn.microsoft.com/azure/aks/csi-secrets-store-driver)
- [AKS monitoring](https://learn.microsoft.com/azure/aks/monitor-aks)
- [AKS upgrades](https://learn.microsoft.com/azure/aks/upgrade-aks-cluster)
- [Terraform AzureRM](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 075 complete — Part 15: Azure AKS complete (Chapters 071–075).**

**Next:** Chapter 076 — Google Kubernetes Engine GitOps Architecture, Cluster Provisioning and Platform Foundations, beginning Part 16: GKE.