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

## Tutorial format

Every chapter will include learning objectives, architecture, concepts, working commands and configuration examples, safe hands-on labs, validation, troubleshooting, rollback/cleanup and production acceptance criteria.

This is an educational reference architecture, not an assertion that any specific organization has implemented these controls.
