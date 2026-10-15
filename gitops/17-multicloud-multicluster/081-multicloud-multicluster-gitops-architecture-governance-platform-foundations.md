# Chapter 081 — Multi-Cloud and Multi-Cluster GitOps Architecture, Governance and Platform Foundations

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 17:** Multi-Cloud and Multi-Cluster GitOps  
**Chapter:** 081 / 100  
**Audience:** SREs, Platform Engineers, DevSecOps, Cloud Architects, Security Engineers and Incident Commanders

> **Safety:** Use isolated non-production EKS, AKS and GKE clusters with synthetic applications and data. Multi-cluster controllers can propagate mistakes across environments. Do not register production clusters with broad cluster-admin credentials, enable unrestricted automated pruning, or use shared wildcard destinations. Every change must have a defined blast radius, rollback and independent approval.

## 1. Learning objectives

By the end of this chapter, you can:

1. Design a GitOps control plane across EKS, AKS and GKE.
2. Compare centralized, distributed and hub-and-spoke Argo CD topologies.
3. Define cluster identity, metadata and ownership contracts.
4. Register remote clusters with least-privilege access.
5. Deploy workloads using ApplicationSets and cluster generators.
6. Isolate environments through AppProjects, namespaces and policy.
7. Implement cloud-specific workload identity without static credentials.
8. Design cross-cloud networking, DNS, registry and secret boundaries.
9. Establish safe GitLab promotion and drift management.
10. Measure multi-cluster SLOs, capacity, cost and recovery readiness.

## 2. Architecture options

| Model | Advantages | Risks | Typical use |
| --- | --- | --- | --- |
| Central Argo CD managing remote clusters | Unified inventory and rollout | Control-plane concentration, remote credential/network dependency | Small-to-medium fleets |
| Per-cluster Argo CD | Strong blast-radius isolation, local recovery | More controllers and governance overhead | Regulated and high-criticality workloads |
| Regional/hub-and-spoke controllers | Balance of local autonomy and fleet governance | More complex routing and lifecycle | Large multi-region fleets |
| Pull-based agent design | Reduces inbound connectivity requirements | Product-specific agent trust and operations | Restricted/private networks |

Choose based on failure domains, sovereignty, security, network reachability and recovery objectives. A single central Argo CD installation is not automatically highly available across clouds.

## 3. Reference architecture

~~~text
                   GitLab protected repositories
                       /              \
            Infrastructure IaC     GitOps desired state
                    |                    |
             EKS / AKS / GKE       CI policy gates
                    |                    |
          cloud IAM federation      signed image digests
                    |                    |
         Cluster inventory / ownership registry
                    |
            Fleet governance contract
                    |
          Argo CD / ApplicationSets
             /         |         \
          EKS         AKS        GKE
           |           |          |
       AppProject  AppProject  AppProject
           |           |          |
        workloads   workloads  workloads
           \           |         /
         metrics / audit / SLO aggregation
                    |
            SRE incident command
~~~

## 4. Multi-cloud is not multi-region DR

A fleet of clusters across cloud providers provides potential placement diversity but not guaranteed service recovery. Applications may still depend on one database, one identity provider, one registry, one DNS zone or one Git server.

Map shared dependencies and failure domains before claiming resilience. Define data replication, write ownership, backup integrity, traffic steering and RPO/RTO independently of cluster count.

## 5. Cluster inventory contract

Every managed cluster must have a stable identifier, environment, provider, region, tenant, owner, security tier, lifecycle state and operational contact.

~~~yaml
apiVersion: v1
kind: Secret
metadata:
  name: cluster-eks-staging
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    platform.example.com/provider: aws
    platform.example.com/environment: staging
    platform.example.com/region: us-east-1
    platform.example.com/tenant: shared
    platform.example.com/lifecycle: active
type: Opaque
stringData:
  name: eks-staging
  server: https://REPLACE_WITH_API_ENDPOINT
  config: |
    {}
~~~

**Illustration only:** This is not a functional secure cluster registration. Never commit a live Argo CD cluster Secret or token to Git. Use a supported registration mechanism with short-lived/federated credentials or securely provisioned cluster credentials, narrow permissions and a tested rotation process. Treat labels as untrusted until governance validates them.

## 6. GitOps repository model

~~~text
gitops/
  fleet/
    inventory/
    policies/
    applicationsets/
    promotion/
  clusters/
    eks-staging/
      platform/
      applications/
    aks-staging/
      platform/
      applications/
    gke-staging/
      platform/
      applications/
  apps/
    patient-api/
      base/
      overlays/
        staging/
        production/
  security/
    projects/
    policies/
  runbooks/
    cluster-registration.md
    remote-sync.md
    credential-rotation.md
    rollback.md
    fleet-outage.md
~~~

Prefer immutable artifact references and explicit per-environment configuration. Avoid copying secrets, kubeconfigs or raw remote cluster tokens into repositories.

## 7. Fleet control-plane ownership

Terraform or the approved IaC system owns cloud infrastructure, networking, cluster IAM and foundational configuration. Argo CD owns delegated Kubernetes resources. GitLab CI validates, builds, signs and proposes promotion changes.

Fleet inventory should be reconciled through a governed source of truth. A cluster is not production-ready simply because it appears in the Argo CD UI.

## 8. Cluster onboarding lifecycle

~~~text
Request -> security review -> inventory metadata
        -> network reachability validation
        -> scoped identity / Kubernetes RBAC
        -> cluster registration
        -> platform add-ons
        -> policy and observability tests
        -> application onboarding
        -> acceptance sign-off
~~~

Onboarding should be idempotent and independently reversible. Record who approved access, which controller owns the cluster and how access is revoked.

## 9. Remote cluster authentication

For EKS, use supported AWS identity and Kubernetes access mechanisms; for AKS, use Microsoft Entra and Azure identities; for GKE, use Google Cloud IAM and supported Kubernetes authentication.

Argo CD remote cluster connectivity requires a Kubernetes API endpoint, usable authentication and RBAC. Human SSO to Argo CD does not automatically grant Argo CD controller access to remote clusters.

Where native cloud identity federation is available, prefer short-lived credentials and scoped permissions. Validate the exact Argo CD version and authentication plugin support before assuming a specific cloud auth configuration works.

## 10. Network reachability

Private clusters may require VPN, private connectivity, VPC/VNet peering, transit networks, private DNS or local Argo CD controllers. Never make Kubernetes APIs public solely to simplify GitOps.

Measure control-plane RTT, DNS resolution, egress firewall rules and TLS certificate trust. Distinguish Argo CD repository connectivity from remote Kubernetes API connectivity.

## 11. Argo CD AppProject governance

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: staging-apps
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.com/platform/gitops-apps.git
  destinations:
    - namespace: demo-staging
      server: https://REPLACE_WITH_APPROVED_CLUSTER_ENDPOINT
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
~~~

This is a sample and requires a real approved cluster endpoint. AppProject policies must be combined with Kubernetes RBAC and admission; AppProject restrictions alone are not a complete security boundary.

## 12. ApplicationSet cluster generator

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-staging-fleet
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            platform.example.com/environment: staging
            platform.example.com/lifecycle: active
  template:
    metadata:
      name: 'demo-{{name}}'
    spec:
      project: staging-apps
      source:
        repoURL: https://gitlab.example.com/platform/gitops-apps.git
        targetRevision: main
        path: apps/demo/overlays/staging
      destination:
        server: '{{server}}'
        namespace: demo-staging
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
~~~

**Safety:** The template deliberately omits automated sync and pruning. Validate generated Applications before enabling automation. The cluster selector can match the local cluster if labeled accordingly; audit inventory and generator results first.

## 13. ApplicationSet templating risks

A malicious or mistaken cluster label can cause unintended placement. Limit who may edit Argo CD cluster Secrets and ApplicationSets. Use validated inventory metadata, separate staging/production controllers or projects, and explicit allowlists for critical destinations.

Treat a broad selector change like a production deployment: review generated application diff and expected cluster count.

## 14. Environment promotion

~~~text
Build once -> sign immutable digest
          -> staging GitOps MR
          -> staging SLO + security gates
          -> production GitOps MR
          -> environment owner approval
          -> progressive rollout by cohort
          -> verify and continue / rollback
~~~

Do not rebuild a different artifact for production. Promote the same verified digest and record each cluster's actual deployed imageID.

## 15. Cohort-based rollout

Partition clusters by environment, region, tenant and risk. Start with a synthetic canary cohort and proceed only after explicit health gates.

Avoid fleet-wide automated sync of high-risk network, admission, RBAC or storage changes. For production, use independent approval and controlled waves.

## 16. Cloud identity boundaries

| Provider | Human/cloud IAM | Workload identity |
| --- | --- | --- |
| EKS | AWS IAM and supported Kubernetes access | EKS Pod Identity or IRSA, depending on design |
| AKS | Microsoft Entra, Azure RBAC, Kubernetes RBAC | Microsoft Entra Workload ID |
| GKE | Google Cloud IAM, Kubernetes RBAC | Workload Identity Federation for GKE |

Workload identities must be scoped to the correct cluster, namespace, service account and cloud resource. Never use one static cloud key across providers.

## 17. Secret management

Use AWS Secrets Manager, Azure Key Vault and Google Secret Manager through supported CSI or external-secret integration. Centralized governance should specify rotation, audit, naming and access requirements without forcing all secret values into one provider.

Do not copy decrypted secrets between clouds through GitLab artifacts. Test secret access denial for unrelated clusters.

## 18. Registry and artifact strategy

Signed immutable images may be replicated into ECR, ACR and Artifact Registry, or retrieved from a trusted common registry with tested network access. Preserve artifact provenance and verify digest equivalence.

Plan registry outage, rate limits, regional availability, image pull identity and cross-cloud egress costs. A registry URL alone does not guarantee an image can be pulled in a disaster.

## 19. Multi-cloud network boundaries

Design per-cloud private API connectivity, DNS, ingress/Gateway, CIDR allocation, egress and interconnect separately. Avoid overlapping Pod/Service CIDRs when direct routing is required.

Do not assume AWS VPC, Azure VNet and Google Cloud VPC firewall or load-balancer semantics are interchangeable. Standardize intent, not unsupported controller annotations.

## 20. Policy-as-code

Validate namespace ownership, restricted Pod security, signed images, allowed registries, RBAC, network isolation, quota, backup labeling and safe resource pruning.

Use a common policy contract with provider-specific adapters. Test admission in audit/warn before enforcement and document exceptions with expiry and owners.

## 21. Multi-cluster observability

Standardize cluster_id, provider, region, environment, namespace, service, tenant and release revision as telemetry labels, subject to cardinality controls.

Aggregate service SLOs and incident context while preserving local audit ownership and data residency requirements. Monitor Argo CD sync duration, controller health, cluster API connectivity, image pulls, admission denial and workload health.

## 22. Reliability objectives

Track per-cluster reconciliation SLO, fleet deployment completion, application availability, drift age and credential rotation age. Set numeric targets using measured baselines.

A healthy Argo CD Application does not prove user-facing service health. Combine Kubernetes readiness with synthetic probes, application metrics and dependency checks.

## 23. Cost governance

Measure per-cloud cluster fees, nodes, load balancers, NAT, private connectivity, logging, storage, egress, registry replication and idle standby resources.

A multi-cloud design may increase operational cost significantly. Document why the resilience, regulatory or placement benefit justifies the complexity.

## 24. Disaster recovery foundations

Decide whether GitOps controllers are centralized or per-cluster, where their configuration is backed up, how cluster credentials are recovered and how repository outage affects reconciliation.

Git desired state is not a backup of database content. A recovery cluster needs independent data restore, cloud IAM, secrets, registry and traffic routing.

## 25. Operational guardrails

- Require protected branches and CODEOWNERS.
- Separate staging and production AppProjects.
- Review generated ApplicationSet targets.
- Restrict cluster Secret mutation.
- Disable unreviewed automated pruning for stateful resources.
- Test least-privilege remote RBAC.
- Preserve immutable artifact provenance.
- Record cluster owner and break-glass path.
- Require measured recovery exercises before production onboarding.

## 26. Lab A — Fleet inventory

1. List staging EKS, AKS and GKE clusters.
2. Record provider, region, environment, owner and API endpoint.
3. Verify each cluster's current access method.
4. Confirm no production context is active.
5. Validate inventory metadata and lifecycle.
6. Archive redacted evidence.

**Pass:** all test clusters have authoritative ownership.

## 27. Lab B — Multi-cloud network preflight

1. Verify private Kubernetes API connectivity for each cluster.
2. Resolve API hostnames from the Argo CD controller network.
3. Check TLS trust and egress firewall paths.
4. Record connection latency.
5. Simulate one isolated unreachable test endpoint.
6. Restore connectivity without public exposure.

**Pass:** remote API reachability is understood.

## 28. Lab C — Remote RBAC scope

1. Create dedicated staging remote identity.
2. Grant namespace-scoped read/write as required.
3. Verify permitted Deployment read.
4. Verify denied Secret or cluster-scoped mutation.
5. Record audit events.
6. Revoke test privileges.

**Pass:** remote controller permissions are least-privileged.

## 29. Lab D — Argo CD cluster registration

1. Select supported authentication method.
2. Register one disposable staging cluster.
3. Validate Argo CD connectivity.
4. Confirm identity and RBAC.
5. Rotate or revoke registration credential.
6. Verify controlled recovery.

**Pass:** onboarding and revocation are repeatable.

## 30. Lab E — AppProject isolation

1. Create staging AppProject.
2. Restrict repository and destination namespace.
3. Sync permitted test application.
4. Attempt unauthorized destination.
5. Confirm denial.
6. Restore reviewed configuration.

**Pass:** projects enforce intended scope.

## 31. Lab F — ApplicationSet discovery

1. Label two disposable cluster registrations as staging.
2. Apply ApplicationSet with automated sync disabled.
3. Inspect generated Application destinations.
4. Add a third authorized staging cluster.
5. Verify generated Application count.
6. Remove test registration and observe cleanup plan.

**Pass:** selectors generate only approved targets.

## 32. Lab G — Selector poisoning test

1. Create disposable cluster inventory entry.
2. Add misleading environment label.
3. Verify governance detects mismatch with source of truth.
4. Block production placement.
5. Correct metadata.
6. Record audit trail.

**Pass:** labels alone cannot bypass approval.

## 33. Lab H — Provider-specific workload identity

1. Deploy synthetic KSA in each cloud.
2. Configure EKS IRSA/Pod Identity, AKS Workload ID and GKE WIF as applicable.
3. Grant read-only synthetic cloud resource permission.
4. Verify authorized read.
5. Verify unauthorized write.
6. Revoke test grants.

**Pass:** no cross-cloud static keys.

## 34. Lab I — Secret delivery

1. Create synthetic secret in each cloud provider.
2. Configure supported secret delivery.
3. Verify correct cluster access.
4. Verify unrelated cluster denial.
5. Rotate test secret.
6. Confirm application reload and audit.

**Pass:** secrets stay within approved trust boundaries.

## 35. Lab J — Immutable artifact promotion

1. Build synthetic image once.
2. Generate SBOM and sign digest.
3. Replicate approved artifact to test registries.
4. Verify digest equivalence.
5. Deploy same digest in two clusters.
6. Confirm running imageID.

**Pass:** artifact provenance survives promotion.

## 36. Lab K — Progressive fleet rollout

1. Select staging canary cohort.
2. Propose protected GitOps MR.
3. Sync only canary Application.
4. Verify health and SLO.
5. Promote to second cohort.
6. Stop on synthetic regression and revert.

**Pass:** rollout blast radius is controlled.

## 37. Lab L — Cross-cloud policy validation

1. Define common Pod security and registry policy.
2. Deploy compliant synthetic workload on each cluster.
3. Attempt privileged or untrusted workload.
4. Verify admission denial where enforced.
5. Review provider-specific exceptions.
6. Archive policy evidence.

**Pass:** common intent has effective local enforcement.

## 38. Lab M — Drift detection

1. Deploy approved GitOps revision.
2. Introduce harmless synthetic drift.
3. Observe OutOfSync state.
4. Review expected diff.
5. Restore through approved reconciliation.
6. Record time to convergence.

**Pass:** drift is detected and recovered safely.

## 39. Lab N — Multi-cluster observability

1. Tag telemetry by provider, cluster and environment.
2. Generate synthetic application error in one cluster.
3. Confirm local and aggregated dashboards.
4. Validate incident routing to cluster owner.
5. Check telemetry cardinality and cost.
6. Restore healthy workload.

**Pass:** incidents retain cluster-level attribution.

## 40. Lab O — Fleet outage tabletop

1. Simulate central Argo CD unavailable.
2. Determine which clusters continue serving traffic.
3. Identify reconciliation and promotion impact.
4. Restore controller from reviewed configuration.
5. Validate cluster registrations and Application state.
6. Record RTO, gaps and follow-up work.

**Pass:** controller outage does not cause uncontrolled cluster mutation.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Cluster Unknown | API unreachable | Verify private path |
| 2 | TLS handshake fails | CA or endpoint mismatch | Restore trust |
| 3 | Remote sync Forbidden | RBAC insufficient | Correct scoped role |
| 4 | Remote auth expires | Token/federation issue | Rotate identity |
| 5 | ApplicationSet generates no apps | Label selector mismatch | Inspect inventory |
| 6 | ApplicationSet targets wrong cluster | Misleading metadata | Enforce allowlist |
| 7 | Production sync unexpectedly proposed | Broad AppProject | Restrict destination |
| 8 | Git repository unreachable | DNS/credentials | Restore repo access |
| 9 | EKS API auth fails | AWS identity/access | Verify auth path |
| 10 | AKS auth fails | Entra federation/RBAC | Repair scoped access |
| 11 | GKE auth fails | Google IAM/plugin | Repair supported auth |
| 12 | Secret retrieval fails | Provider IAM/CSI | Restore least privilege |
| 13 | ImagePullBackOff | Registry IAM/egress | Fix pull path |
| 14 | Admission rejects app | Policy/signature | Fix compliant artifact |
| 15 | Cluster OutOfSync | Drift/ignored differences | Review diff |
| 16 | Rollout stalls | PDB/quota/health | Restore capacity |
| 17 | Fleet metrics missing | Label/export pipeline | Repair telemetry |
| 18 | Controller recovery fails | Missing credentials/config | Restore approved bootstrap |

## 42. Runbook — remote cluster registration outage

1. Identify cluster, provider, region and owner.
2. Verify remote API DNS, TLS and private routing.
3. Check Argo CD cluster registration and authentication.
4. Inspect Kubernetes RBAC and cloud IAM.
5. Restore scoped access through approved mechanism.
6. Validate safe dry-run sync and health.
7. Record incident and credential rotation evidence.

## 43. Runbook — ApplicationSet targeting incident

1. Freeze affected ApplicationSet promotions.
2. Inspect selector, generated Applications and cluster metadata.
3. Compare against authoritative inventory.
4. Remove unauthorized destinations through reviewed GitOps change.
5. Protect stateful resources from unsafe prune.
6. Verify target count and AppProject restrictions.
7. Record blast radius and RCA.

## 44. Runbook — cross-cloud identity or secret outage

1. Identify provider, KSA, cloud identity and target resource.
2. Review federation subject/audience and scoped IAM.
3. Inspect secret CSI/external-secret controller.
4. Restore trust without static keys.
5. Verify allowed and denied access.
6. Rotate compromised credentials if necessary.
7. Archive audit events.

## 45. Runbook — fleet deployment regression

1. Identify artifact digest, GitLab MR and affected cohort.
2. Stop promotion to remaining clusters.
3. Compare local SLOs, policy and runtime state.
4. Revert affected cohort through reviewed GitOps.
5. Verify data integrity and service health.
6. Record provider-specific differences.
7. Update rollout gates.

## 46. Runbook — central Argo CD outage

1. Declare impact and freeze risky promotions.
2. Verify existing workloads continue operating.
3. Restore Argo CD controller and configuration from approved backup/IaC.
4. Recover repository access and cluster registrations.
5. Inspect generated Applications before enabling sync.
6. Verify reconciliation and application SLO.
7. Document RTO and resilience improvements.

## 47. Evidence template

~~~text
Change / incident ID:
GitLab repository and protected MR:
Argo CD version and controller topology:
Cluster IDs, provider, region and environment:
Inventory owner and approved labels:
Remote API endpoint, private routing and TLS:
Authentication method and Kubernetes RBAC:
AppProject and ApplicationSet selectors:
Generated Application destinations:
Image digest, signature and provenance:
Provider workload identity and secret access:
Admission, network and storage policy:
Per-cluster SLO and aggregated telemetry:
Rollback and recovery evidence:
Cost, approver and reviewer:
~~~

## 48. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| Architecture and cluster inventory | 20 | Approved topology and metadata |
| Authentication and RBAC | 20 | Least-privilege positive/negative tests |
| AppProjects and ApplicationSets | 20 | Safe targeting and denied destinations |
| Delivery and policy governance | 15 | Signed digest and staged rollout |
| Observability and incident response | 15 | Cluster attribution and runbooks |
| Recovery and cost governance | 10 | Tabletop, budget and evidence |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: uncontrolled production targeting, unrestricted cluster-admin remote credentials, unapproved secret propagation, unsigned image bypass, unsafe pruning or missing recovery ownership.

## 49. Final acceptance checklist

- [ ] Multi-cloud control-plane topology approved.
- [ ] EKS, AKS and GKE inventory authoritative.
- [ ] Private API reachability and TLS verified.
- [ ] Remote identity and RBAC least-privileged.
- [ ] Cluster registration rotation and revocation tested.
- [ ] AppProjects restrict repositories and destinations.
- [ ] ApplicationSet selectors validated against inventory.
- [ ] Staging/production promotion independently approved.
- [ ] Provider-specific workload identity tested.
- [ ] Secret isolation and rotation verified.
- [ ] Signed artifact digest consistent across clusters.
- [ ] Network and admission policies enforced locally.
- [ ] Drift detection and safe reconciliation tested.
- [ ] Fleet telemetry and incident routing validated.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks validated.
- [ ] Recovery and FinOps review signed off.

## 50. Knowledge check

1. What is the tradeoff between central and per-cluster Argo CD?
2. Why is cluster inventory metadata a security boundary?
3. Why does Argo CD SSO not automatically authorize remote Kubernetes operations?
4. How can an ApplicationSet cluster generator cause unintended deployment?
5. Why should production fleet rollouts use cohorts?
6. How do EKS, AKS and GKE workload identities differ?
7. Why must registry digest equivalence be verified across clouds?
8. What is the distinction between Git desired state and data backup?
9. Why does multi-cloud not automatically guarantee disaster recovery?
10. How can fleet telemetry preserve attribution without excessive cardinality?

## 51. References

- [Argo CD cluster management](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/#clusters)
- [Argo CD ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [ApplicationSet cluster generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Cluster/)
- [Argo CD AppProjects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [GitLab protected branches](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [Azure AKS](https://learn.microsoft.com/azure/aks/)
- [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/docs)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

---

**Chapter 081 complete — Part 17: Multi-Cloud and Multi-Cluster GitOps started.**

**Next:** Chapter 082 — Multi-Cluster Argo CD ApplicationSets, Fleet Placement and Progressive Deployment Governance.