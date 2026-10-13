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

## Tutorial format

Every chapter will include learning objectives, architecture, concepts, working commands and configuration examples, safe hands-on labs, validation, troubleshooting, rollback/cleanup and production acceptance criteria.

This is an educational reference architecture, not an assertion that any specific organization has implemented these controls.
