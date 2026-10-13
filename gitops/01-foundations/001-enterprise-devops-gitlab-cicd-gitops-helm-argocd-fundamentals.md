# Chapter 001 — Enterprise DevOps, GitLab CI/CD, GitOps, Helm and Argo CD Fundamentals

**Part 01 — Foundations and Enterprise Architecture**  
**Level:** Foundation → Production Operations  
**Reference platforms:** Amazon EKS, Azure AKS, Google GKE  
**Reference environments:** Dev, Test, Staging, Production

## Learning objectives

After completing this chapter, you will be able to:
1. Distinguish DevOps, CI, CD, GitOps, Helm and Argo CD.
2. Trace a release from a GitLab merge request to Kubernetes reconciliation.
3. Explain why CI builds artifacts but Argo CD manages declared deployment state.
4. Describe a shared-cluster, multi-namespace reference topology and its limitations.
5. Validate a Kubernetes namespace baseline safely.
6. Identify approval, security, monitoring and recovery controls required for production.

## 1. Key concepts

| Concept | Responsibility | Example |
| --- | --- | --- |
| DevOps | Engineering culture and delivery practices | Collaboration, automation, operational ownership |
| GitLab | Git repository and development workflow | Merge requests, protected branches, CODEOWNERS |
| GitLab CI/CD | Build, test, scan and publish release artifacts | Container build and signed image digest |
| Helm | Package and template Kubernetes resources | Versioned chart with environment-specific values |
| GitOps | Git-controlled desired state and reconciliation | Approved change to production image digest |
| Argo CD | GitOps reconciliation controller | Detect drift, compare and synchronize applications |
| Kubernetes | Runtime orchestration | Deployments, Services, namespaces, scheduling |

**GitLab is not GitOps.** GitLab can host source and GitOps repositories and run CI/CD; Argo CD continuously reconciles the approved desired state into Kubernetes.

## 2. Production reference architecture

```text
Developer -> GitLab Merge Request
                 |
                 v
          GitLab CI pipeline
      lint -> unit test -> SAST -> build
        -> scan -> SBOM -> sign
                 |
                 v
       Immutable OCI image digest
          + versioned Helm chart
                 |
                 v
       GitOps configuration change
         (reviewed and approved)
                 |
                 v
           Argo CD Application
          (per cluster/environment)
                 |
                 v
         EKS / AKS / GKE cluster
           |     |       |      |
          dev   test   staging  prod
        namespaces with separate RBAC,
        policies, quotas and identities
```

GitLab CI must not deploy production workloads directly with privileged `kubectl apply` or `helm upgrade`. It should publish immutable artifacts and propose an audited GitOps change. Argo CD reconciles only after the required environment-specific approval and sync gates.

### Cloud-specific considerations

- **EKS:** IAM Roles for Service Accounts or EKS Pod Identity, ECR, VPC CNI, AWS load balancing and CSI drivers.
- **AKS:** Microsoft Entra Workload ID, ACR, Azure CNI, Azure load balancing and CSI drivers.
- **GKE:** Workload Identity Federation for GKE, Artifact Registry, GKE networking, load balancing and CSI drivers.

The architecture is portable, but cloud identity, networking, registry and storage integrations are not interchangeable.

## 3. Environment model

Our learning baseline uses **one Kubernetes cluster with four namespaces**, not four clusters:

| Environment | Namespace | Sync policy | Control |
| --- | --- | --- | --- |
| Dev | `demo-dev` | Automated after CI gates | Developer access scoped to namespace |
| Test | `demo-test` | Automated after integration gates | Restricted service accounts |
| Staging | `demo-staging` | Controlled promotion | Production-like testing and observability |
| Production | `demo-prod` | Approved, controlled sync | Least privilege, policy enforcement, monitoring and rollback |

Separate Argo CD Applications target each namespace. Use the **same immutable image digest** as the release is promoted, with reviewed Helm values for each environment.

**Isolation warning:** Namespaces do not provide complete fault or security isolation. Shared cluster control plane, add-ons, cluster-scoped resources and nodes can affect production. Evaluate dedicated production node pools and ultimately separate production clusters for critical or regulated workloads.

## 4. Repository responsibilities

A production platform usually has three logical repositories, even when the tutorials themselves are stored together:

```text
application-source/
  .gitlab-ci.yml
  src/
  tests/
  Dockerfile

helm-charts/
  demo-app/
    Chart.yaml
    values.yaml
    templates/

platform-gitops/
  clusters/
    eks/
    aks/
    gke/
  environments/
    dev/
    test/
    staging/
    prod/
  argocd/
    projects/
    applications/
    applicationsets/
  policies/
```

Use Argo CD multi-source Applications when charts and environment values live in separate repositories. Pin chart versions and image digests. Protect production GitOps paths with code ownership and approval rules.

## 5. Release lifecycle

1. Developer submits a GitLab merge request.
2. CI runs lint, unit tests, SAST and dependency checks.
3. CI builds a container image, scans it, generates an SBOM and signs the artifact.
4. CI publishes the immutable image and versioned chart.
5. Automation proposes an environment-specific GitOps merge request.
6. Required reviewers approve the change; the promotion policy is evaluated.
7. Argo CD detects the desired-state update and syncs according to the environment policy.
8. Smoke tests, health checks and SLO signals validate the rollout.
9. On failure, halt promotion and revert the GitOps change or execute the tested rollback procedure.

Production releases should support progressive delivery, explicit abort criteria, incident escalation and traceability from deployed digest to source commit.

## 6. Hands-on lab — inspect and establish namespace baseline

### Prerequisites

- Non-production Kubernetes cluster access and `kubectl`.
- Permission to list namespaces.
- Namespace creation permission **only if performing the optional creation step**.
- No production modifications are needed for this chapter.

### Step A — Verify context (read-only)

```bash
kubectl config current-context
kubectl cluster-info
kubectl get namespaces
kubectl auth can-i create namespaces
```

**Safety check:** Verify that the context points to your disposable lab cluster before creating resources. If you are connected to production, stop after the read-only checks.

### Step B — Create example namespaces (optional, lab cluster only)

```bash
kubectl create namespace demo-dev
kubectl create namespace demo-test
kubectl create namespace demo-staging
kubectl create namespace demo-prod
```

These are **illustrative** namespaces. Creating them does not by itself make the cluster production-ready.

### Step C — Verify namespaces and workloads

```bash
kubectl get namespaces -o wide
kubectl get all -n demo-dev
kubectl get all -n demo-test
kubectl get all -n demo-staging
kubectl get all -n demo-prod
```

### Step D — Inspect available policy and access controls

```bash
kubectl get resourcequota,limitrange,networkpolicy -n demo-prod
kubectl get role,rolebinding -n demo-prod
kubectl auth can-i create deployments -n demo-prod
```

An empty policy list is a **gap to address**, not a passing security result. Real network isolation requires a CNI that enforces NetworkPolicy, verified ingress/egress policies, and tests.

### Step E — Cleanup (only namespaces created by this lab)

```bash
kubectl delete namespace demo-dev demo-test demo-staging demo-prod
```

**Destructive action:** Namespace deletion removes namespaced resources and may trigger storage cleanup. Run this command only on disposable lab namespaces that you created and verified are empty of valuable resources. Never use it against shared or production namespaces.

## 7. Production acceptance checklist

- [ ] CI runner permissions are isolated and ephemeral where feasible.
- [ ] Merge requests and protected branches enforce review and auditability.
- [ ] Artifacts are immutable, scanned, signed and traceable to source.
- [ ] Helm charts are versioned, linted and tested.
- [ ] Argo CD Projects restrict source repositories and deployment destinations.
- [ ] Each environment has distinct Kubernetes identities and permissions.
- [ ] Namespace quotas, pod security and network policies are enforced and tested.
- [ ] Production sync is controlled by an explicit release policy.
- [ ] Metrics, logs, traces, alerts and deployment health gates exist.
- [ ] Rollback, backup, restore and disaster recovery have been tested.

## 8. Troubleshooting primer

| Symptom | First checks |
| --- | --- |
| CI build fails | GitLab job logs, runner health, credentials, build context |
| Helm render fails | `helm lint`, `helm template`, chart dependencies |
| Argo CD OutOfSync | Desired vs live diff, revision, sync policy |
| Argo CD Degraded | Kubernetes events, probes, pod status |
| Workload Pending | Quotas, requests, node capacity, scheduling constraints |
| ImagePullBackOff | Registry access, image digest, workload identity |
| Promotion blocked | Required approvals, security gates, environment protection |

## 9. Knowledge checks

1. Why is GitLab CI/CD not equivalent to GitOps?
2. Which component builds the image, and which reconciles Kubernetes resources?
3. Why must production promotion reuse the same immutable image digest?
4. Why do namespaces not fully isolate production workloads?
5. Which steps are necessary before enabling automated production synchronization?

## 10. Completion criteria

You can explain the complete delivery chain, verify a Kubernetes context, inspect the four environment namespaces, describe the required security boundaries, and identify the GitOps promotion and rollback process.

**Next: Chapter 002 — Git, GitLab Repositories, Branching and Enterprise Merge Request Governance.**
