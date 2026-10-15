# GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series

**100 chapters · 20 modules · EKS / AKS / GKE**

This track teaches production-oriented platform engineering using GitLab CI/CD for continuous integration and artifact publishing, Helm for Kubernetes packaging, and Argo CD for GitOps reconciliation.

## Reference architecture

- Shared Kubernetes cluster with separate `demo-dev`, `demo-test`, `demo-staging` and `demo-prod` namespaces (training baseline).
- Production-grade RBAC, identity, network policy, resource quotas, approval gates, observability and recovery.
- Explicit evaluation of dedicated production clusters for stronger isolation.
- Immutable artifacts and reviewed GitOps promotions; Argo CD manages Kubernetes desired state.
- All examples use generic, organization-neutral application names.

## Master module plan (5 chapters per module)

| Module | Chapters | Focus |
| --- | --- | --- |
| 01 | 001–005 | DevOps, Git, GitLab and GitOps foundations |
| 02 | 006–010 | GitLab repository governance and branching |
| 03 | 011–015 | GitLab CI/CD fundamentals and runners |
| 04 | 016–020 | Pipeline design, testing and artifacts |
| 05 | 021–025 | Container builds and software supply-chain security |
| 06 | 026–030 | Kubernetes deployment fundamentals |
| 07 | 031–035 | Enterprise Helm chart engineering |
| 08 | 036–040 | Argo CD fundamentals and installation |
| 09 | 041–045 | Argo CD Applications and ApplicationSets |
| 10 | 046–050 | Argo CD security, multi-tenancy and HA |
| 11 | 051–055 | Environment promotion and release governance |
| 12 | 056–060 | Progressive delivery, rollback and Argo Rollouts |
| 13 | 061–065 | Secrets, policy and workload identity |
| 14 | 066–070 | GitOps on Amazon EKS |
| 15 | 071–075 | GitOps on Azure AKS |
| 16 | 076–080 | GitOps on Google GKE |
| 17 | 081–085 | Multi-cloud, multi-cluster and fleet operations |
| 18 | 086–090 | Observability, SLOs and troubleshooting |
| 19 | 091–095 | Reliability, disaster recovery and FinOps |
| 20 | 096–100 | Enterprise end-to-end capstone and SRE assessment |

## Chapters

- [001 — Enterprise DevOps, GitLab CI/CD, GitOps, Helm and Argo CD Fundamentals](01-foundations/001-enterprise-devops-gitlab-cicd-gitops-helm-argocd-fundamentals.md)

- [002 — Git, GitLab Repositories, Branching and Enterprise Merge Request Governance](01-foundations/002-git-gitlab-repositories-branching-merge-request-governance.md)

- [003 — GitLab CI/CD Architecture, Pipelines, Jobs, Stages and Runners](01-foundations/003-gitlab-cicd-architecture-pipelines-jobs-stages-runners.md)

- [004 — GitLab CI/CD Variables, Secrets, Artifacts, Caching and Secure Pipeline Configuration](01-foundations/004-gitlab-cicd-variables-secrets-artifacts-caching-secure-configuration.md)

- [005 — Enterprise GitLab CI/CD Foundations Capstone](01-foundations/005-enterprise-gitlab-cicd-foundations-capstone.md)

- [006 — Enterprise GitLab Repository Administration, Groups, Projects and Access Control](02-gitlab-repository-administration/006-enterprise-gitlab-groups-projects-access-control.md)

- [007 — GitLab Protected Branches, Tags, CODEOWNERS and Approval Policies](02-gitlab-repository-administration/007-gitlab-protected-branches-tags-codeowners-approval-policies.md)

- [008 — GitLab Merge Request Workflows, Branching Strategies and Release Governance](02-gitlab-repository-administration/008-gitlab-merge-request-workflows-branching-strategies-release-governance.md)

- [009 — GitLab Repository Security, Audit Events, Compliance and Secret Protection](02-gitlab-repository-administration/009-gitlab-repository-security-audit-compliance-secret-protection.md)

- [010 — GitLab Repository Administration, Security and Governance Capstone](02-gitlab-repository-administration/010-gitlab-repository-administration-security-governance-capstone.md)

- [011 — GitLab CI/CD YAML Fundamentals, Pipeline Structure and Execution Rules](03-gitlab-cicd-fundamentals/011-gitlab-ci-yaml-fundamentals-pipeline-structure-execution-rules.md)

- [012 — GitLab CI/CD Jobs, Stages, Dependencies and DAG Optimization](03-gitlab-cicd-fundamentals/012-gitlab-ci-jobs-stages-dependencies-dag-optimization.md)

- [013 — GitLab CI/CD Variables, Environments, Secrets and Configuration Precedence](03-gitlab-cicd-fundamentals/013-gitlab-cicd-variables-environments-secrets-configuration-precedence.md)

- [014 — GitLab CI/CD Artifacts, Caching, Reports and Pipeline Data Flow](03-gitlab-cicd-fundamentals/014-gitlab-cicd-artifacts-caching-reports-pipeline-data-flow.md)

- [015 — GitLab CI/CD Fundamentals and Pipeline Reliability Capstone](03-gitlab-cicd-fundamentals/015-gitlab-cicd-fundamentals-pipeline-reliability-capstone.md)

- [016 — GitLab Runner Architecture, Executors, Registration and Lifecycle](04-pipeline-design-testing-artifacts/016-gitlab-runner-architecture-executors-registration-lifecycle.md)

- [017 — GitLab Runner Security, Isolation, Autoscaling and Kubernetes Executors](04-pipeline-design-testing-artifacts/017-gitlab-runner-security-isolation-autoscaling-kubernetes-executors.md)

- [018 — GitLab CI/CD Reusable Pipelines, Includes, Templates and Child Pipelines](04-pipeline-design-testing-artifacts/018-gitlab-cicd-reusable-pipelines-includes-templates-child-pipelines.md)

- [019 — GitLab CI/CD Pipeline Testing, Quality Gates, Security Scanning and Failure Recovery](04-pipeline-design-testing-artifacts/019-gitlab-cicd-pipeline-testing-quality-gates-security-scanning-failure-recovery.md)

- [020 — Enterprise GitLab Pipeline Design, Testing and Runner Operations Capstone](04-pipeline-design-testing-artifacts/020-enterprise-gitlab-pipeline-design-testing-runner-operations-capstone.md)

- [021 — Secure Container Image Builds, Registries and Immutable Tags](05-container-builds-supply-chain-security/021-secure-container-image-builds-registries-immutable-tags.md)

- [022 — Container Image Vulnerability Scanning, SBOM Generation and Dependency Security](05-container-builds-supply-chain-security/022-container-image-vulnerability-scanning-sbom-dependency-security.md)

- [023 — Container Image Signing, Provenance Attestations and SLSA Supply-Chain Controls](05-container-builds-supply-chain-security/023-container-image-signing-provenance-attestations-slsa-supply-chain-controls.md)

- [024 — Secure CI/CD Supply-Chain Policies, Artifact Promotion and Registry Governance](05-container-builds-supply-chain-security/024-secure-cicd-supply-chain-policies-artifact-promotion-registry-governance.md)

- [025 — Enterprise Container Supply-Chain Security and Artifact Promotion Capstone](05-container-builds-supply-chain-security/025-enterprise-container-supply-chain-security-artifact-promotion-capstone.md)

- [026 — Kubernetes Deployment Fundamentals for GitLab CI/CD and GitOps](06-kubernetes-deployment-fundamentals/026-kubernetes-deployment-fundamentals-gitlab-cicd-gitops.md)

- [027 — Kubernetes Configuration Management, Secrets and Environment Isolation for GitOps](06-kubernetes-deployment-fundamentals/027-kubernetes-configuration-management-secrets-environment-isolation-gitops.md)

- [028 — Kubernetes Services, Ingress, DNS and Application Connectivity for GitOps](06-kubernetes-deployment-fundamentals/028-kubernetes-services-ingress-dns-application-connectivity-gitops.md)

- [029 — Kubernetes Deployment Strategies, Health Checks, Autoscaling and Release Reliability](06-kubernetes-deployment-fundamentals/029-kubernetes-deployment-strategies-health-checks-autoscaling-release-reliability.md)

- [030 — Kubernetes Deployment, Connectivity and Release Reliability Capstone](06-kubernetes-deployment-fundamentals/030-kubernetes-deployment-connectivity-release-reliability-capstone.md)

- [031 — Helm Architecture, Charts, Templates and Values Fundamentals](07-enterprise-helm-chart-engineering/031-helm-architecture-charts-templates-values-fundamentals.md)

- [032 — Advanced Helm Templates, Functions, Helpers and Values Schema Design](07-enterprise-helm-chart-engineering/032-advanced-helm-templates-functions-helpers-values-schema-design.md)

- [033 — Helm Dependencies, OCI Registries, Chart Packaging and Supply-Chain Security](07-enterprise-helm-chart-engineering/033-helm-dependencies-oci-registries-chart-packaging-supply-chain-security.md)

- [034 — Helm Release Lifecycle, Upgrades, Rollbacks and Production Troubleshooting](07-enterprise-helm-chart-engineering/034-helm-release-lifecycle-upgrades-rollbacks-production-troubleshooting.md)

- [035 — Enterprise Helm Chart Engineering, Security and Release Operations Capstone](07-enterprise-helm-chart-engineering/035-enterprise-helm-chart-engineering-security-release-operations-capstone.md)

- [036 — Argo CD Architecture, GitOps Reconciliation and Core Components](08-argocd-fundamentals-installation/036-argocd-architecture-gitops-reconciliation-core-components.md)

- [037 — Argo CD Installation, Namespaces, RBAC and Initial Configuration](08-argocd-fundamentals-installation/037-argocd-installation-namespaces-rbac-initial-configuration.md)

- [038 — Argo CD CLI, UI, Authentication and Repository Connectivity](08-argocd-fundamentals-installation/038-argocd-cli-ui-authentication-repository-connectivity.md)

- [039 — Argo CD Application Creation, Synchronization, Health and Drift Detection](08-argocd-fundamentals-installation/039-argocd-application-creation-synchronization-health-drift-detection.md)

- [040 — Argo CD Installation, Application Operations and Recovery Capstone](08-argocd-fundamentals-installation/040-argocd-installation-application-operations-recovery-capstone.md)

- [041 — Argo CD Application Architecture, Sources, Destinations and Multi-Environment Design](09-argocd-applications-applicationsets/041-argocd-application-architecture-sources-destinations-multi-environment-design.md)

- [042 — Argo CD ApplicationSets, Generators, Templates and Automated Application Provisioning](09-argocd-applications-applicationsets/042-argocd-applicationsets-generators-templates-automated-application-provisioning.md)

- [043 — Argo CD ApplicationSet Git and Cluster Generators for Multi-Environment Operations](09-argocd-applications-applicationsets/043-argocd-applicationset-git-cluster-generators-multi-environment-operations.md)

- [044 — Argo CD Multi-Source Applications, Helm Values Repositories and ApplicationSet Governance](09-argocd-applications-applicationsets/044-argocd-multi-source-applications-helm-values-repositories-applicationset-governance.md)

- [045 — Argo CD Applications and ApplicationSets Production Operations Capstone](09-argocd-applications-applicationsets/045-argocd-applications-applicationsets-production-operations-capstone.md)

- [046 — Argo CD Enterprise RBAC, SSO, AppProject Security and Multi-Tenancy](10-argocd-security-multitenancy-ha/046-argocd-enterprise-rbac-sso-appproject-security-multitenancy.md)

- [047 — Argo CD High Availability, Scaling and Production Resilience](10-argocd-security-multitenancy-ha/047-argocd-high-availability-scaling-production-resilience.md)

- [048 — Argo CD Security Hardening, Auditability and Operational Governance](10-argocd-security-multitenancy-ha/048-argocd-security-hardening-auditability-operational-governance.md)

- [049 — Argo CD Multi-Cluster Access, Credential Management and Secure Fleet Operations](10-argocd-security-multitenancy-ha/049-argocd-multicluster-access-credential-management-secure-fleet-operations.md)

- [050 — Argo CD Security, Multi-Tenancy and High Availability Production Capstone](10-argocd-security-multitenancy-ha/050-argocd-security-multitenancy-high-availability-production-capstone.md)

- [051 — Environment Promotion Architecture and Release Governance](11-environment-promotion-release-governance/051-environment-promotion-architecture-release-governance.md)

- [052 — GitLab Promotion Pipelines, Approval Gates and Release Automation](11-environment-promotion-release-governance/052-gitlab-promotion-pipelines-approval-gates-release-automation.md)

- [053 — Production Change Windows, Release Evidence and Compliance Automation](11-environment-promotion-release-governance/053-production-change-windows-release-evidence-compliance-automation.md)

- [054 — GitOps Release Rollback, Disaster Recovery and Deployment Safety Controls](11-environment-promotion-release-governance/054-gitops-release-rollback-disaster-recovery-deployment-safety-controls.md)

- [055 — Enterprise Environment Promotion and Release Governance Capstone](11-environment-promotion-release-governance/055-enterprise-environment-promotion-release-governance-capstone.md)

- [056 — Progressive Delivery Fundamentals: Canary, Blue-Green and Release Risk](12-progressive-delivery-advanced-deployment-strategies/056-progressive-delivery-fundamentals-canary-blue-green-release-risk.md)

- [057 — Argo Rollouts Canary Analysis, Traffic Routing and Automated Promotion](12-progressive-delivery-advanced-deployment-strategies/057-argo-rollouts-canary-analysis-traffic-routing-automated-promotion.md)

- [058 — Blue-Green Deployment, Preview Validation and Zero-Downtime Cutover Operations](12-progressive-delivery-advanced-deployment-strategies/058-blue-green-deployment-preview-validation-zero-downtime-cutover-operations.md)

- [059 — Feature Flags, Experimentation and Progressive Release Observability](12-progressive-delivery-advanced-deployment-strategies/059-feature-flags-experimentation-progressive-release-observability.md)

- [060 — Enterprise Progressive Delivery and Automated Recovery Capstone](12-progressive-delivery-advanced-deployment-strategies/060-enterprise-progressive-delivery-automated-recovery-capstone.md)

- [061 — GitOps Secrets Management, External Secrets and Workload Identity Fundamentals](13-secrets-policy-workload-identity/061-gitops-secrets-management-external-secrets-workload-identity-fundamentals.md)

- [062 — SOPS, Sealed Secrets and Encryption Key Lifecycle for GitOps](13-secrets-policy-workload-identity/062-sops-sealed-secrets-encryption-key-lifecycle-gitops.md)

- [063 — Kubernetes Admission Policies, OPA Gatekeeper and Kyverno for GitOps Security](13-secrets-policy-workload-identity/063-kubernetes-admission-policies-opa-gatekeeper-kyverno-gitops-security.md)

- [064 — Policy-as-Code Supply Chain Security, Image Signing and Provenance Enforcement](13-secrets-policy-workload-identity/064-policy-as-code-supply-chain-security-image-signing-provenance-enforcement.md)

- [065 — Enterprise GitOps Security, Secrets and Policy Compliance Capstone](13-secrets-policy-workload-identity/065-enterprise-gitops-security-secrets-policy-compliance-capstone.md)

- [066 — Amazon EKS GitOps Architecture, Cluster Bootstrap and Platform Foundations](14-amazon-eks/066-amazon-eks-gitops-architecture-cluster-bootstrap-platform-foundations.md)

- [067 — EKS Managed Node Groups, Karpenter and Production Capacity Automation](14-amazon-eks/067-eks-managed-node-groups-karpenter-production-capacity-automation.md)

- [068 — EKS Networking, AWS Load Balancer Controller and Storage Integration for GitOps](14-amazon-eks/068-eks-networking-aws-load-balancer-controller-storage-integration-gitops.md)

- [069 — EKS Security, Workload Identity, Observability and Upgrade Operations](14-amazon-eks/069-eks-security-workload-identity-observability-upgrade-operations.md)

- [070 — EKS Enterprise GitOps Production Operations and Disaster Recovery Capstone](14-amazon-eks/070-eks-enterprise-gitops-production-operations-disaster-recovery-capstone.md)

- [071 — Azure AKS GitOps Architecture, Cluster Provisioning and Platform Foundations](15-azure-aks/071-azure-aks-gitops-architecture-cluster-provisioning-platform-foundations.md)

- [072 — AKS Node Pools, Autoscaling, Scheduling and Production Capacity Management](15-azure-aks/072-aks-node-pools-autoscaling-scheduling-production-capacity-management.md)

- [073 — AKS Networking, Ingress, Azure Disk and Azure Files CSI Integration for GitOps](15-azure-aks/073-aks-networking-ingress-azure-disk-azure-files-csi-gitops.md)

- [074 — AKS Security, Microsoft Entra Workload Identity, Observability and Upgrade Operations](15-azure-aks/074-aks-security-microsoft-entra-workload-identity-observability-upgrade-operations.md)

- [075 — AKS Enterprise GitOps Production Operations and Disaster Recovery Capstone](15-azure-aks/075-aks-enterprise-gitops-production-operations-disaster-recovery-capstone.md)

- [076 — Google Kubernetes Engine GitOps Architecture, Cluster Provisioning and Platform Foundations](16-google-gke/076-gke-gitops-architecture-cluster-provisioning-platform-foundations.md)

- [077 — GKE Node Pools, Autoscaling, Scheduling and Production Capacity Management](16-google-gke/077-gke-node-pools-autoscaling-scheduling-production-capacity-management.md)

- [078 — GKE Networking, Ingress, Gateway API and Persistent Storage Integration for GitOps](16-google-gke/078-gke-networking-ingress-gateway-api-persistent-storage-gitops.md)

- [079 — GKE Security, Workload Identity Federation, Observability and Upgrade Operations](16-google-gke/079-gke-security-workload-identity-federation-observability-upgrade-operations.md)

- [080 — GKE Enterprise GitOps Production Operations and Disaster Recovery Capstone](16-google-gke/080-gke-enterprise-gitops-production-operations-disaster-recovery-capstone.md)

- [081 — Multi-Cloud and Multi-Cluster GitOps Architecture, Governance and Platform Foundations](17-multicloud-multicluster/081-multicloud-multicluster-gitops-architecture-governance-platform-foundations.md)

- [082 — Multi-Cluster Argo CD ApplicationSets, Fleet Placement and Progressive Deployment Governance](17-multicloud-multicluster/082-multicluster-argocd-applicationsets-fleet-placement-progressive-deployment-governance.md)

## Tutorial format

Every chapter will include learning objectives, architecture, concepts, working commands and configuration examples, safe hands-on labs, validation, troubleshooting, rollback/cleanup and production acceptance criteria.

This is an educational reference architecture, not an assertion that any specific organization has implemented these controls.
