# Chapter 085 — Multi-Cloud GitOps Enterprise Operations, Reliability and Disaster Recovery Capstone

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 17:** Multi-Cloud and Multi-Cluster GitOps — Final Capstone  
**Chapter:** 085 / 100  
**Audience:** SREs, Platform Engineers, DBREs, DevSecOps, Cloud Architects, Security Engineers and Incident Commanders

> **Safety:** Execute only in isolated non-production EKS, AKS and GKE environments with synthetic data, approved spending limits and a documented rollback. Never simulate a regional disaster by deleting a live cluster or database, changing public production DNS, disabling monitoring or compromising real credentials. All data recovery exercises must use disposable resources and independently verified backups.

## 1. Mission

Build and operate a governed GitOps fleet spanning Amazon EKS, Azure AKS and Google GKE. Demonstrate reproducible infrastructure, secure cluster onboarding, signed artifact promotion, progressive delivery, least-privilege identity, cross-cloud observability, controlled incident response and tested disaster recovery.

Integrate the previous chapters:

- 081 — Multi-cloud architecture, governance and platform foundations.
- 082 — ApplicationSets, fleet placement and progressive deployment governance.
- 083 — Workload identity, secrets, network security and policy enforcement.
- 084 — Observability, SLOs, incident response and cross-cloud disaster recovery.

**Definition of done:** A reviewer can trace an approved change from GitLab through each fleet deployment, reproduce the infrastructure, verify security boundaries, measure SLO and error-budget impact, and restore a synthetic stateful service in an independent recovery environment within explicitly accepted RPO/RTO.

## 2. End-to-end reference architecture

~~~text
              Protected GitLab source and GitOps MRs
                             |
                tests / SBOM / signature / policy
                             |
                 immutable approved image digest
                             |
                 authoritative fleet inventory
                             |
                 Argo CD / ApplicationSets
                     /       |       \
                 EKS        AKS       GKE
                  |          |         |
              AppProject  AppProject AppProject
                  |          |         |
              identity    identity   identity
              + secrets   + secrets  + secrets
                  |          |         |
             NetworkPolicy + admission controls
                     \       |       /
                      telemetry + SLOs
                             |
                   incident command / DR
                             |
           isolated recovery cluster + restored data
                             |
                  verified traffic cutover
~~~

Use Terraform or an approved IaC tool for cloud infrastructure, GitLab for validation and artifact creation, Argo CD for delegated Kubernetes desired state, and cloud-native IAM for provider resources. Avoid controller ownership conflicts.

## 3. Capstone deliverables

| Deliverable | Evidence |
| --- | --- |
| Fleet inventory | Provider, region, cluster, tenant, environment, owner |
| Infrastructure | Reviewed IaC plan and reproducible staging clusters |
| GitLab pipeline | Protected OIDC, tests, SBOM, signed digest |
| GitOps | AppProjects, ApplicationSets, bounded target counts |
| Security | Workload identity, secrets, RBAC, NetworkPolicy, admission |
| Reliability | User-facing SLO, burn alerts, local and aggregate telemetry |
| Storage | Backup catalog, integrity check, independent restore |
| Disaster recovery | Recovery infrastructure, data fencing, measured RPO/RTO |
| Operations | Incident timeline, runbooks, approvals, cost report |
| Acceptance | Scored assessment and signed critical control gates |

## 4. Reference repository

~~~text
multi-cloud-capstone/
  infrastructure/
    aws/
    azure/
    gcp/
    shared/
  fleet/
    inventory/
    schemas/
    policies/
    applicationsets/
    appprojects/
  applications/
    demo-api/
      base/
      overlays/
        eks-staging/
        aks-staging/
        gke-staging/
  ci/
    terraform-validate.sh
    inventory-validate.sh
    manifest-validate.sh
    image-verify.sh
    fleet-target-check.sh
    slo-gate.sh
  observability/
    otel/
    prometheus/
    dashboards/
    alerts/
  disaster-recovery/
    backup/
    restore/
    cutover/
    failback/
  runbooks/
  evidence/
    acceptance-report.md
~~~

Do not commit kubeconfigs, tokens, private keys, Terraform state, decoded Secrets or database dumps.

## 5. Prerequisites

- Isolated AWS, Azure and Google Cloud staging subscriptions/projects/accounts.
- Approved regional EKS, AKS and GKE clusters, or approved IaC for provisioning.
- GitLab protected branches, CODEOWNERS and short-lived OIDC federation.
- Argo CD/ApplicationSet controller version and CRDs recorded.
- Restricted AppProjects, cluster registration and inventory validation.
- Supported workload identity on all three providers.
- Provider-specific secret managers, CSI/external-secret integration.
- Enforced Kubernetes RBAC, Pod security, image trust and NetworkPolicy.
- Approved synthetic stateful application and application-consistent backups.
- Metrics, logs, traces, audit and alert routing.
- Recovery target, private connectivity, DNS and capacity budget.
- Incident commander, recovery lead, approver and teardown owner.

## 6. Environment preflight

~~~bash
kubectl config get-contexts
kubectl config current-context
kubectl get nodes -o wide
kubectl get namespaces
kubectl -n argocd get applicationsets,applications,appprojects
kubectl get storageclasses,csidrivers
~~~

Repeat for each staging cluster using explicitly selected contexts. Confirm actual cloud account/project, region, API endpoint, cluster name and billing before changes.

## 7. Fleet inventory and source of truth

~~~yaml
clusters:
  - id: eks-staging-us-east-1
    provider: aws
    region: us-east-1
    environment: staging
    tenant: shared
    cohort: canary
    owner: platform-sre
    approved: true
  - id: aks-staging-eastus
    provider: azure
    region: eastus
    environment: staging
    tenant: shared
    cohort: wave-2
    owner: platform-sre
    approved: true
  - id: gke-staging-us-central1
    provider: gcp
    region: us-central1
    environment: staging
    tenant: shared
    cohort: wave-2
    owner: platform-sre
    approved: true
~~~

This is a governance record, not an Argo CD cluster registration. Compare every record with the real registered API endpoint, credential owner and approval status.

## 8. Terraform and cloud ownership

Each provider module must define remote state, provider versions, networking, private API connectivity, IAM, node capacity, encryption, logging and budgets. Protect plan artifacts and state.

~~~bash
terraform -chdir=infrastructure/aws fmt -check
terraform -chdir=infrastructure/aws validate
terraform -chdir=infrastructure/azure validate
terraform -chdir=infrastructure/gcp validate
~~~

Initialize each module with approved backends first. Use provider-specific reviewed plans before apply; do not infer equivalence across AWS VPC, Azure VNet and Google VPC networking.

## 9. Argo CD topology decision

Choose central, regional or per-cluster Argo CD based on trust, latency, network reachability, recovery time and blast radius. Central controllers are operationally simpler but may become a shared failure domain.

Document controller owner, backup, registration credential recovery, repository access and break-glass path. A remote cluster must remain able to serve existing workloads during a central controller outage.

## 10. ApplicationSet governance

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: capstone-canary
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            platform.example.com/environment: staging
            platform.example.com/cohort: canary
            platform.example.com/approved: "true"
  template:
    metadata:
      name: 'capstone-{{name}}'
    spec:
      project: capstone-staging
      source:
        repoURL: https://gitlab.example.com/platform/gitops.git
        targetRevision: main
        path: applications/demo-api/base
      destination:
        server: '{{server}}'
        namespace: demo-staging
~~~

This intentionally omits automated sync and pruning. Create namespaces through a separately approved platform bootstrap. Validate cluster labels against authoritative inventory and review generated targets before reconciliation.

## 11. AppProject restrictions

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: capstone-staging
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.com/platform/gitops.git
  destinations:
    - namespace: demo-staging
      name: eks-staging
    - namespace: demo-staging
      name: aks-staging
    - namespace: demo-staging
      name: gke-staging
  clusterResourceWhitelist: []
~~~

The destination names are examples and must match actual Argo CD cluster registrations. AppProjects complement, but do not replace, Kubernetes RBAC and admission.

## 12. Protected delivery pipeline

~~~text
Source MR -> unit/integration tests
          -> SBOM and vulnerability checks
          -> build immutable image
          -> sign approved digest
          -> GitOps staging MR
          -> inventory and policy checks
          -> canary reconcile
          -> SLO and security acceptance
          -> approved wave-2 MR
          -> verify actual imageID
~~~

Use protected GitLab OIDC claims with scoped cloud roles. Avoid static AWS keys, Azure client secrets and Google service account JSON keys.

## 13. Artifact portability

Use a single verified image digest across EKS, AKS and GKE. If replicating into ECR, ACR and Artifact Registry, verify digest equivalence and signature/provenance trust after replication.

Measure registry egress, image pull time and failure behavior. A digest in Git is not enough if the recovery region cannot access the image.

## 14. Identity controls

| Provider | Workload identity | Secrets |
| --- | --- | --- |
| EKS | EKS Pod Identity or IRSA | AWS Secrets Manager |
| AKS | Microsoft Entra Workload ID | Azure Key Vault |
| GKE | Workload Identity Federation | Google Secret Manager |

Grant only required synthetic resource reads. Test unauthorized writes and cross-namespace access denial. Identity failures must be distinguished from private network failures.

## 15. Kubernetes authorization

Use namespace-scoped Roles/RoleBindings and restricted Argo CD controller access. Protect AppProjects, cluster Secrets, admission policies and shared Gateway resources from application teams.

Record positive and negative authorization tests for each provider.

## 16. Network isolation

Verify each cluster's CNI/network policy implementation supports enforcement. Deploy deny-by-default rules only after allowing required DNS, ingress, metrics, identity and secret endpoints.

Cloud firewall controls and Kubernetes NetworkPolicy operate at different layers. Verify both with real traffic tests.

## 17. Admission and supply-chain security

Enforce Pod Security Admission and supported image signature/attestation policy. Start with audit/warn and stage denial tests before production enforcement.

Verify an approved signed digest is admitted and an untrusted synthetic digest is rejected. Document exception approval and expiry.

## 18. Secret rotation

Create synthetic provider secrets, grant scoped access, rotate versions and verify application reload. Check for secret leakage into logs, GitLab artifacts, Pod environment dumps and monitoring.

Maintain an emergency rollback version until consumers are validated.

## 19. Multi-cloud telemetry

Standardize provider, cluster_id, region, environment, namespace, service, tenant and release labels. Use provider-local alerting plus aggregated dashboards.

Avoid a single central observability endpoint as the only outage detection path. Preserve audit records in approved jurisdictions.

## 20. SLOs and error budgets

~~~text
Availability = eligible successful requests / all eligible requests
Error budget fraction = 1 - approved SLO target
Burn rate = observed error fraction / error budget fraction
~~~

Define service-specific availability and latency objectives, exclusions, reporting windows, synthetic checks and owner approvals.

## 21. Fleet promotion gates

Promotion must halt on unexpected target count, unauthorized destination, untrusted digest, failed synthetic check, elevated error-budget burn, missing data backup, degraded dependency or unreconciled drift.

Argo CD sync status alone is insufficient for release acceptance.

## 22. Data protection and recovery

Select application-consistent backup methods appropriate for the database, filesystem and provider. A Kubernetes VolumeSnapshot alone may be only crash-consistent.

Record backup creation timestamp, recovered data timestamp, checksum, application validation, RPO and RTO. Store recovery credentials and encryption keys outside the primary failure domain.

## 23. Cross-cloud recovery dependencies

~~~text
Cloud account/project and quota
          |
VPC/VNet, routing and private DNS
          |
Kubernetes cluster and node capacity
          |
Cloud IAM / workload identity
          |
Artifact registry / secret manager
          |
Argo CD / policy / ingress
          |
Storage / database recovery
          |
Application and synthetic tests
          |
Traffic cutover and monitoring
~~~

A second cluster is not disaster recovery without data, identity, networking and traffic continuity.

## 24. Writer fencing and split-brain prevention

For stateful primary/standby systems, fence the old writer before promoting the recovery writer. Validate replication lag, committed transaction durability, recovery point and application consistency.

Do not promote two writable primaries. For failback, establish the correct replication direction and reconcile state before traffic movement.

## 25. Operational acceptance targets

Illustrative staging goals, subject to business approval:

| Measure | Example target |
| --- | --- |
| API availability | 99.9% rolling 30 days |
| API latency | 99% under 500 ms |
| Fleet reconciliation | 99% of approved changes within 10 minutes |
| RPO | 15 minutes or less |
| RTO | 60 minutes or less |
| Unauthorized secret access | Denied |
| Unsigned image admission | Denied |
| Unapproved production placement | Denied |

These are examples, not provider guarantees. Measure actual results and document any gap.

## 26. Lab A — Fleet baseline and ownership

1. Inventory EKS, AKS and GKE staging clusters.
2. Verify cloud account, region and Kubernetes context.
3. Record cluster owner, environment and tenant.
4. Check Argo CD cluster registrations.
5. Validate cost and quota limits.
6. Archive redacted evidence.

**Pass:** no unmanaged or unapproved cluster target.

## 27. Lab B — Reproducible infrastructure

1. Pin Terraform providers and modules.
2. Initialize secure remote state.
3. Run format, validate and reviewed plan.
4. Compare plan with cloud inventory.
5. Apply only approved staging changes.
6. Verify drift and recovery documentation.

**Pass:** infrastructure can be recreated from code.

## 28. Lab C — Private API and network reachability

1. Verify private Kubernetes API access for all clusters.
2. Resolve API DNS from approved controller network.
3. Inspect firewall, NAT and routes.
4. Test certificate trust.
5. Simulate one disposable connectivity failure.
6. Restore without exposing public APIs.

**Pass:** remote GitOps access is controlled.

## 29. Lab D — Cluster registration and revocation

1. Select supported cloud auth method.
2. Register disposable staging cluster with scoped RBAC.
3. Verify Argo CD connectivity.
4. Test unauthorized API operation denial.
5. Rotate or revoke credentials.
6. Restore approved access.

**Pass:** cluster registration is reversible and least-privileged.

## 30. Lab E — ApplicationSet placement

1. Label approved canary cluster registration.
2. Apply bounded ApplicationSet without auto-prune.
3. Inspect generated Applications.
4. Compare target count to authoritative inventory.
5. Add approved wave-2 target.
6. Reject malicious/misleading metadata.

**Pass:** no unapproved placement.

## 31. Lab F — GitLab artifact pipeline

1. Build synthetic application.
2. Generate SBOM and scan.
3. Sign immutable image digest.
4. Verify signature in CI.
5. Create protected GitOps MR.
6. Record image digest and approver.

**Pass:** artifact provenance is traceable.

## 32. Lab G — Progressive multi-cloud deployment

1. Deploy to EKS canary.
2. Verify health, ingress and SLO.
3. Approve AKS/GKE wave-2.
4. Reconcile second cohort.
5. Confirm actual Pod imageID.
6. Archive promotion evidence.

**Pass:** rollout order is governed.

## 33. Lab H — Rollback and release halt

1. Introduce synthetic canary regression.
2. Trigger SLO alert.
3. Halt wave-2.
4. Revert GitOps MR.
5. Validate service and data integrity.
6. Document change failure and recovery time.

**Pass:** failure does not propagate fleet-wide.

## 34. Lab I — EKS workload identity

1. Configure synthetic KSA with IRSA or Pod Identity.
2. Grant exact AWS resource read.
3. Verify allowed call.
4. Verify denied write.
5. Inspect audit logs.
6. Revoke test trust.

**Pass:** no static AWS credentials.

## 35. Lab J — AKS workload identity

1. Verify AKS OIDC issuer and Entra federation.
2. Configure synthetic KSA.
3. Grant scoped Key Vault access.
4. Verify allowed read.
5. Verify denied unrelated access.
6. Remove test federation.

**Pass:** short-lived Azure workload identity works.

## 36. Lab K — GKE workload identity

1. Verify Workload Identity Federation support.
2. Create synthetic KSA.
3. Grant scoped Secret Manager read.
4. Verify authorized call.
5. Verify unauthorized KSA denial.
6. Revoke IAM grant.

**Pass:** Google Cloud access is least-privileged.

## 37. Lab L — Secrets, NetworkPolicy and admission

1. Create synthetic secrets in all three providers.
2. Verify approved CSI/external-secret delivery.
3. Rotate secrets and verify reload.
4. Test allowed/denied Pod traffic.
5. Reject privileged or untrusted synthetic image.
6. Verify audit events.

**Pass:** layered security controls are enforced.

## 38. Lab M — Observability and SLO burn

1. Deploy provider-local metrics/logging.
2. Configure aggregated dashboards.
3. Run synthetic API checks.
4. Trigger controlled 5xx errors.
5. Verify multi-window burn alert and routing.
6. Restore and record recovery.

**Pass:** user impact is detected.

## 39. Lab N — Application-consistent backup

1. Generate synthetic stateful dataset.
2. Quiesce or use database-native consistent backup.
3. Record recovery point and checksum.
4. Restore to independent namespace/PVC.
5. Validate data and application behavior.
6. Measure RPO/RTO.

**Pass:** backup is demonstrably recoverable.

## 40. Lab O — Recovery infrastructure bootstrap

1. Provision isolated recovery project/account/region.
2. Restore private networking and cluster capacity.
3. Reestablish workload identities and secret access.
4. Restore Argo CD with restricted AppProjects.
5. Verify signed image availability.
6. Reconcile synthetic application.

**Pass:** recovery environment is independent.

## 41. Lab P — Cross-cloud failover

1. Select approved recovery target.
2. Verify backup/replication freshness.
3. Fence synthetic primary writer.
4. Restore/promote recovery data.
5. Shift synthetic traffic through approved DNS/route.
6. Validate user journey, data integrity and SLO.
7. Record actual RPO/RTO.

**Pass:** failover is data-safe and measured.

## 42. Lab Q — Controlled failback

1. Confirm original environment recovery.
2. Validate authoritative data source.
3. Reconcile replication and backlog.
4. Fence former recovery writer.
5. Shift traffic in controlled stages.
6. Verify no split-brain and record evidence.

**Pass:** failback preserves consistency.

## 43. Lab R — Integrated SRE game day

1. Inject synthetic ApplicationSet selector error.
2. Simulate one cloud identity denial and ingress 5xx.
3. Declare incident and assign command roles.
4. Correlate GitLab, Argo CD, metrics, logs and audit.
5. Contain rollout and restore service safely.
6. Verify backups, recovery readiness and SLO.
7. Produce RCA, FinOps report and acceptance sign-off.

**Pass:** platform team demonstrates controlled fleet operations.

## 44. Troubleshooting — twenty scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Terraform plan changes unexpected resources | State/config drift | Stop and review |
| 2 | Cluster API unreachable | Private routing/DNS | Restore approved path |
| 3 | Argo CD cluster Unknown | Auth/TLS/API | Verify registration |
| 4 | ApplicationSet targets wrong cluster | Bad selector/labels | Freeze and correct |
| 5 | Generated Application count spikes | Matrix expansion | Bound generator |
| 6 | AppProject rejects sync | Destination restriction | Review allowlist |
| 7 | EKS workload AccessDenied | IRSA/Pod Identity trust | Repair exact role |
| 8 | AKS token exchange fails | Entra issuer/subject | Repair federation |
| 9 | GKE WIF fails | Principal/pool/IAM | Repair scoped binding |
| 10 | Secret CSI mount fails | Driver/IAM/network | Inspect dependencies |
| 11 | Secret rotation not observed | Reload/cache | Restart safely |
| 12 | NetworkPolicy ignored | CNI unsupported | Verify dataplane |
| 13 | DNS blocked by default-deny | Egress rule | Allow required DNS |
| 14 | Signed image rejected | Attestation/policy | Validate provenance |
| 15 | Registry pull fails in recovery | IAM/egress/missing digest | Restore artifact |
| 16 | Canary 5xx increases | App regression | Halt and rollback |
| 17 | Fleet telemetry missing | Collector/exporter | Restore local alerts |
| 18 | Backup restore inconsistent | Wrong backup semantics | Choose verified point |
| 19 | Two writers active | Missing fencing | Stop writes immediately |
| 20 | DNS cutover incomplete | TTL/cache/health | Validate routing |

## 45. Runbook — multi-cloud cluster access incident

1. Identify provider, cluster, environment and owner.
2. Confirm API endpoint, DNS, TLS and private network path.
3. Inspect cloud authentication and Kubernetes RBAC.
4. Restore scoped access without opening public endpoints.
5. Verify Argo CD dry-run sync and audit.
6. Record incident and credential rotation.

## 46. Runbook — ApplicationSet placement incident

1. Freeze affected ApplicationSets and promotions.
2. Capture inventory, labels, generator and generated target list.
3. Identify unauthorized or duplicate destinations.
4. Correct reviewed inventory or selector.
5. Protect stateful resources from pruning.
6. Verify expected target count and project restrictions.
7. Document blast radius.

## 47. Runbook — identity or secret outage

1. Identify KSA, cloud identity and secret backend.
2. Inspect EKS/AKS/GKE trust mechanism.
3. Separate IAM denial from private network failure.
4. Restore exact least-privilege permissions.
5. Validate secret version, rotation and reload.
6. Verify unauthorized access remains denied.
7. Preserve audit logs.

## 48. Runbook — multi-cloud release regression

1. Identify signed digest, GitLab MR and affected wave.
2. Stop further promotions.
3. Correlate Argo CD health and user-facing SLO.
4. Revert through reviewed GitOps change.
5. Verify actual imageID and data integrity.
6. Record recovery time and error budget impact.
7. Update release gates.

## 49. Runbook — observability outage

1. Identify lost metrics, logs, traces or audit sources.
2. Confirm provider-local alerts remain active.
3. Inspect collectors, queues, TLS and egress.
4. Restore secure telemetry pipeline.
5. Generate synthetic event and verify ingestion.
6. Document evidence gaps.
7. Update capacity and retention.

## 50. Runbook — data restore failure

1. Identify source dataset, backup point and recovery target.
2. Protect original data and audit evidence.
3. Check IAM, encryption keys and backup format.
4. Restore into isolated storage.
5. Validate checksum and application consistency.
6. Measure RPO/RTO and choose valid recovery point.
7. Update backup controls.

## 51. Runbook — cross-cloud failover

1. Declare DR and authorize traffic/data changes.
2. Validate recovery infrastructure, quotas, IAM and registry.
3. Fence primary writer before promotion.
4. Restore/promote application-consistent data.
5. Reconcile approved GitOps state.
6. Validate TLS, DNS, ingress and synthetic user journey.
7. Shift traffic and measure RPO/RTO.
8. Communicate status and preserve evidence.

## 52. Runbook — failback and post-incident recovery

1. Confirm original environment is stable.
2. Identify authoritative writer and reconcile state.
3. Establish correct replication direction.
4. Fence previous writer before changing roles.
5. Shift traffic gradually with SLO gates.
6. Verify no divergence, backlog or security regression.
7. Close incident with RCA, costs and corrective actions.

## 53. Evidence template

~~~text
Capstone / incident ID:
Incident commander and change approver:
GitLab protected MR and pipeline:
Artifact digest, signature and SBOM:
EKS / AKS / GKE cluster IDs and owners:
Terraform plan/state and provider versions:
ApplicationSet, AppProject and generated target count:
IAM/KSA, secrets and negative access tests:
NetworkPolicy, admission and image trust:
SLO numerator/denominator and burn alerts:
Cloud audit and GitOps revision correlation:
Backup timestamp, recovered checksum and data point:
Writer fencing, DNS/traffic cutover:
Measured RPO/RTO and user validation:
Failback and data reconciliation:
Cloud cost, RCA and approval:
~~~

Do not include secret values, tokens, private keys or privileged kubeconfigs.

## 54. Enterprise readiness score — 100 points

| Domain | Points | Required evidence |
| --- | ---: | --- |
| Fleet architecture and IaC | 15 | Reproducible clusters |
| Inventory, ApplicationSets and governance | 15 | Safe bounded placement |
| GitLab CI and artifact provenance | 10 | Protected signed digest |
| Workload identity, secrets and RBAC | 15 | Positive/negative tests |
| Network and admission policy | 10 | Effective local enforcement |
| Observability and SLO operations | 10 | Alerting and incident correlation |
| Backup, DR and failback | 20 | Integrity and measured RPO/RTO |
| FinOps, runbooks and approvals | 5 | Evidence and ownership |
| **Total** | **100** | |

**Pass:** at least 85/100, all 18 labs complete, and all mandatory controls passed: no unapproved fleet placement, no persistent production cloud keys, no bypass of required artifact trust, no destructive stateful prune, verified application-consistent restore, safe writer fencing, approved traffic cutover and measured recovery objectives.

## 55. Final acceptance checklist

- [ ] EKS, AKS and GKE staging environments isolated.
- [ ] Cloud identities, inventory and cost owners verified.
- [ ] Infrastructure plans reviewed and reproducible.
- [ ] Private API connectivity and registration tested.
- [ ] AppProjects and ApplicationSets restricted.
- [ ] GitLab OIDC, SBOM, signing and digest promotion validated.
- [ ] Canary/wave-2 promotion and rollback exercised.
- [ ] EKS, AKS and GKE workload identity negative tests passed.
- [ ] Secret rotation and reload verified.
- [ ] NetworkPolicy and admission enforcement tested.
- [ ] Provider-local and aggregated observability operational.
- [ ] User-facing SLO and burn alert tested.
- [ ] Backup integrity and isolated restore verified.
- [ ] Recovery infrastructure built independently.
- [ ] Writer fencing, failover and failback rehearsed.
- [ ] RPO/RTO and cost measured.
- [ ] Eighteen integrated labs completed.
- [ ] Twenty troubleshooting scenarios reviewed.
- [ ] Eight production SRE runbooks validated.
- [ ] 100-point readiness assessment signed off.

## 56. Knowledge check

1. What shared dependencies can undermine multi-cloud resilience?
2. Why is an authoritative cluster inventory required before ApplicationSet generation?
3. How do GitLab OIDC and workload identity differ?
4. Why do AppProjects not replace Kubernetes RBAC?
5. What proves NetworkPolicy is enforced in each provider?
6. How can a signed image still be rejected by admission?
7. Why should user-facing SLO gates control progressive rollout?
8. What makes a backup application-consistent?
9. Why must a primary writer be fenced before failover?
10. What is required to safely fail back after a cross-cloud recovery?

## 57. Official references

- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [Argo CD ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [Argo CD AppProjects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [GitLab OIDC](https://docs.gitlab.com/ci/secrets/id_token_authentication/)
- [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [Azure AKS](https://learn.microsoft.com/azure/aks/)
- [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/docs)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [OpenTelemetry](https://opentelemetry.io/docs/)
- [Prometheus](https://prometheus.io/docs/)
- [Google SRE workbook](https://sre.google/workbook/table-of-contents/)

---

**Chapter 085 complete — Part 17: Multi-Cloud and Multi-Cluster GitOps complete (081–085).**

**Next:** Chapter 086 — Enterprise GitOps Observability Architecture, Metrics, Logs and Distributed Tracing, beginning Part 18.