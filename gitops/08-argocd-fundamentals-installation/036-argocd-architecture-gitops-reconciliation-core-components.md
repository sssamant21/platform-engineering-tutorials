# Chapter 036 — Argo CD Architecture, GitOps Reconciliation and Core Components

**Part 08 — Argo CD Fundamentals and Installation**  
**Chapter 036 of 100** | **Audience:** SREs, platform engineers, Kubernetes administrators and infrastructure operators  
**Prerequisites:** Kubernetes Chapters 026–030, Helm Chapters 031–035, GitOps/GitLab fundamentals Chapters 001–025.

> **Safety:** This chapter is architecture-first. The main lab is read-only and can be completed without installing Argo CD. Do not install cluster-wide components, expose the Argo CD API, change RBAC or enable auto-sync in a shared cluster without change approval. Use generic training resources and never place secrets in Git.

## 1. Learning objectives

By the end of this chapter, you will be able to:

1. Explain Argo CD's role as a Kubernetes GitOps continuous-delivery controller.
2. Identify Argo CD's API server, application controller, repository server, Redis and optional identity, notification and ApplicationSet components.
3. Trace desired-state reconciliation from Git through manifest generation to the Kubernetes API.
4. Describe Applications, Projects, sources, destinations, health, sync and drift.
5. Distinguish automated sync, self-heal and prune, including their failure modes.
6. Explain how Argo CD renders Helm without creating a conventional Helm CLI release.
7. Design four namespace-scoped environments within one Kubernetes cluster.
8. Identify security, high-availability, scaling and recovery considerations.
9. Inspect an existing Argo CD deployment using safe, read-only commands.
10. Produce SRE acceptance evidence and a troubleshooting decision tree.

## 2. Why Argo CD exists

Traditional deployment pipelines often push manifests directly into clusters using privileged CI credentials. This increases credential exposure, obscures drift and can make recovery dependent on an external job.

Argo CD implements a **pull-oriented GitOps model**: an in-cluster controller observes an approved desired-state source and reconciles Kubernetes resources toward it. Git remains the reviewable source of truth for declarative configuration.

\`\`\`text
GitLab CI (build/test/scan/sign)
          |
          v
OCI image registry: app@sha256:<verified-digest>
          |
          v
Reviewed GitOps repository
          |
          v
Argo CD repository server (render)
          |
          v
Argo CD application controller (compare/reconcile)
          |
          v
Kubernetes API -> workloads/services/config
          |
          v
Health, events, metrics and SLOs
\`\`\`

GitLab CI **does not need unrestricted production kubeconfig** merely to promote an application. A reviewed GitOps merge updates the desired state; Argo CD performs deployment using its configured Kubernetes authorization.

## 3. Our enterprise reference environment

The tutorial uses **one Kubernetes cluster** with four application namespaces:

| Environment | Namespace | Argo CD Application | Typical promotion |
| --- | --- | --- | --- |
| Development | \`demo-dev\` | \`demo-app-dev\` | Automatic after approved Git change |
| Test | \`demo-test\` | \`demo-app-test\` | Approved validation gate |
| Staging | \`demo-staging\` | \`demo-app-staging\` | Reviewed promotion |
| Production | \`demo-prod\` | \`demo-app-prod\` | Protected approval/change window |

Argo CD control-plane components run in an authorized platform namespace, commonly \`argocd\`. The four application namespaces remain distinct from the Argo CD control plane.

The same approved Helm chart and verified image digest are promoted through the environments; environment-specific nonsecret values differ. During an in-progress promotion, different namespaces may temporarily run different approved digests.

**Boundary:** Namespaces share the same cluster API, networking foundations and often nodes. For high-criticality production systems, separate clusters/accounts may be required.

## 4. Argo CD core components

| Component | Function | Operational concern |
| --- | --- | --- |
| \`argocd-server\` | API, UI and CLI endpoints; authentication-facing interface | TLS, SSO, RBAC, availability |
| \`argocd-application-controller\` | Watches Applications, compares state and orchestrates sync | Reconciliation backlog, API load, sharding |
| \`argocd-repo-server\` | Fetches sources and generates manifests (Helm/Kustomize/etc.) | Repository credentials, plugins, CPU/memory |
| \`argocd-redis\` | Caching and performance support | Availability and resource pressure |
| \`argocd-dex-server\` (optional) | Identity connector when Dex is used | SSO configuration and availability |
| \`argocd-applicationset-controller\` | Generates Applications from configured generators | Unintended fan-out and scope |
| \`argocd-notifications-controller\` (optional) | Event-driven notifications | Token management and alert fatigue |
| CRDs | Application, AppProject and ApplicationSet API types | Cluster-scoped installation governance |

The exact deployment topology, component names and optional services depend on the installed Argo CD release and installation method. Verify live objects rather than assuming every component exists.

## 5. Application reconciliation lifecycle

\`\`\`text
1. GitOps MR merged
        |
2. Desired source revision changes
        |
3. Repo-server fetches and renders
        |
4. Controller compares desired/live objects
        |
5. Application sync status updated
        |
6. Policy allows manual or automated sync
        |
7. Kubernetes API receives changes
        |
8. Controller evaluates resource health
        |
9. Events, metrics and notifications emitted
\`\`\`

**Sync status and health are separate:**
- **Synced:** Live resources match the desired state according to Argo CD comparison.
- **OutOfSync:** A meaningful difference exists.
- **Healthy:** Resource health assessment considers the workload healthy.
- **Degraded / Progressing / Missing / Unknown:** Other health conditions requiring interpretation.

An Application can be **Synced but Degraded**. Likewise, a resource can be Healthy while the Application is OutOfSync. Neither state alone proves user-facing SLOs are met.

## 6. Application, AppProject and ApplicationSet

**Application:** A declarative request describing source, rendering options, destination and synchronization behavior.

**AppProject:** A policy boundary for permitted repositories, destinations, resource kinds and project roles. Use Projects to prevent an application team from targeting unauthorized namespaces or cluster-scoped resources.

**ApplicationSet:** A controller that generates multiple Applications from approved templates and generators. Useful for fleet management, but mistakes can create or modify many Applications simultaneously.

Use distinct Projects or tightly scoped project rules as needed for application/team separation. A Project is not a replacement for Kubernetes RBAC, admission policy or cluster isolation.

## 7. Example Argo CD Application (design only)

\`gitops/apps/demo-app-dev.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app-dev
  namespace: argocd
spec:
  project: demo-platform
  source:
    repoURL: https://gitlab.example.com/platform/demo-gitops.git
    targetRevision: main
    path: charts/demo-app
    helm:
      valueFiles:
        - ../../environments/dev/values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-dev
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
\`\`\`

**Important source-path caveat:** Helm \`valueFiles\` paths are resolved relative to the chart path and are subject to Argo CD's source security and path restrictions. The example's \`../../environments/... \` layout is conceptual and may be rejected by the repo-server depending on configuration. For a directly runnable first lab, place each environment values file **inside the chart directory** (for example \`charts/demo-app/env/dev-values.yaml\`) and set \`valueFiles: [env/dev-values.yaml]\`. Later chapters cover Argo CD multiple sources for external values repositories.

This example omits automated sync deliberately. Production synchronization and pruning require explicit approval and safeguards.

## 8. Safer runnable chart-local values pattern

Recommended initial GitOps structure:

\`\`\`text
demo-gitops/
├── charts/demo-app/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── templates/
│   └── env/
│       ├── dev-values.yaml
│       ├── test-values.yaml
│       ├── staging-values.yaml
│       └── prod-values.yaml
└── apps/
    ├── demo-app-dev.yaml
    ├── demo-app-test.yaml
    ├── demo-app-staging.yaml
    └── demo-app-prod.yaml
\`\`\`

For the Dev Application, use:

\`\`\`yaml
source:
  repoURL: https://gitlab.example.com/platform/demo-gitops.git
  targetRevision: main
  path: charts/demo-app
  helm:
    valueFiles:
      - env/dev-values.yaml
\`\`\`

Keep source paths consistent with actual repository structure. Do not store real credentials in these files.

## 9. AppProject least-privilege design

Illustrative \`gitops/projects/demo-platform.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  description: Approved demo applications in a single training cluster
  sourceRepos:
    - https://gitlab.example.com/platform/demo-gitops.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: demo-dev
    - server: https://kubernetes.default.svc
      namespace: demo-test
    - server: https://kubernetes.default.svc
      namespace: demo-staging
    - server: https://kubernetes.default.svc
      namespace: demo-prod
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - group: rbac.authorization.k8s.io
      kind: Role
    - group: rbac.authorization.k8s.io
      kind: RoleBinding
\`\`\`

**Governance warning:** Project policies restrict what Argo CD will sync, but do not by themselves reduce the controller's underlying Kubernetes credentials. Restrict cluster permissions, use namespace-scoped installations where appropriate, and enforce admission controls. Review whether the intended chart needs any namespaced RBAC before blocking it.

## 10. Manual, automated, self-heal and prune

A manually synchronized Application requires an authorized sync action when desired state changes.

Automated sync example:

\`\`\`yaml
syncPolicy:
  automated:
    prune: false
    selfHeal: false
\`\`\`

Important distinctions:

- **Automated sync:** Attempts synchronization when eligible desired state is OutOfSync.
- **Self-heal:** Allows automated correction of certain live-state drift.
- **Prune:** Deletes managed resources no longer present in desired state.
- **Allow empty:** Controls behavior when desired resources become empty under automated prune.

Never enable pruning in a shared environment without reviewing deletion blast radius, ownership, finalizers and data-retention consequences. Self-heal can overwrite emergency live changes; use an explicit break-glass procedure that reconciles Git afterward.

## 11. Helm integration and release ownership

Argo CD uses Helm to **render manifests** and then applies/reconciles those resources. It generally does not create a conventional Helm CLI release record.

Consequences:
- \`helm list\` may show no release for an Argo CD-managed Helm chart.
- \`helm history\` is not the authoritative application history.
- \`helm rollback\` is not the standard recovery method.
- Git commit history, chart version, OCI artifact and Application sync history provide release evidence.
- Rollback should normally revert the approved GitOps desired-state change.

Never let both Argo CD and an independent Helm release own the same Deployment, Service or ConfigMap.

## 12. Lab A — Inspect an existing Argo CD installation (read-only)

Only if your cluster already has an authorized Argo CD installation:

\`\`\`bash
kubectl config current-context
kubectl get namespaces
kubectl get deployments,statefulsets,services -n argocd
kubectl get pods -n argocd -o wide
kubectl get applications.argoproj.io -n argocd
kubectl get appprojects.argoproj.io -n argocd
kubectl get applicationsets.argoproj.io -n argocd
\`\`\`

Some commands may be denied by RBAC or unavailable if optional CRDs are not installed. Record the limitation; do not elevate privileges simply to complete the lab.

If the Argo CD CLI is already installed and access is authorized:

\`\`\`bash
argocd version --client
argocd app list
\`\`\`

Do not request or display admin credentials in terminal logs or tickets.

## 13. Lab B — Trace a single Application

Select a **nonproduction Application** that you are authorized to inspect.

\`\`\`bash
kubectl get application demo-app-dev -n argocd -o yaml
kubectl describe application demo-app-dev -n argocd
kubectl get deployments,services,configmaps -n demo-dev
kubectl get endpointslices -n demo-dev
\`\`\`

Check:
1. \`spec.source.repoURL\`, \`targetRevision\` and chart path.
2. \`spec.destination.server\` and namespace.
3. \`spec.project\` and Project source/destination restrictions.
4. \`status.sync.status\`, \`status.health.status\`, conditions and operation state.
5. Application history and resource ownership labels/annotations.
6. Kubernetes resource readiness and Service endpoints.

Do not assume \`demo-app-dev\` exists in your cluster. If absent, use an existing approved Application or complete the offline architecture exercise.

## 14. Lab C — Read-only controller diagnostics

With approved permissions:

\`\`\`bash
kubectl get pods -n argocd
kubectl get events -n argocd --sort-by=.lastTimestamp
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
kubectl logs -n argocd statefulset/argocd-application-controller --tail=100
\`\`\`

The controller may be a Deployment or StatefulSet depending on topology. Inspect the live resources first; do not assume the example resource kind is present.

**Security:** Logs can include repository URLs, metadata or accidentally exposed values. Redact before sharing.

## 15. Reconciliation failure matrix

| Failure | Symptom | Likely layer | First checks |
| --- | --- | --- | --- |
| Git repository unavailable | Comparison/render error | Repo-server/network | Git URL, DNS, proxy, auth |
| Expired Git credentials | Repository authentication error | Repo-server/secrets | Token expiry and scopes |
| Invalid Helm values | Manifest generation error | Helm/render | Chart lint and values schema |
| Missing chart dependency | Render failure | Repo-server/dependency | Chart.lock and registry |
| Unauthorized namespace | Sync denied | Project/RBAC | AppProject destination, Kubernetes auth |
| Kubernetes admission rejection | Sync failure | API/admission | Events, webhook, policy |
| ImagePullBackOff | Degraded Pods | Registry/runtime | Image digest, pull secret, network |
| Readiness failure | Progressing/Degraded | Application/runtime | Probes, logs, resources |
| Prune unexpectedly deletes object | Missing resource | Sync policy/ownership | Git diff, prune settings |
| Self-heal overwrites hotfix | Repeated live drift correction | GitOps ownership | Git desired state and sync policy |
| Repo-server overload | Slow manifest generation | Control-plane capacity | CPU/memory, queue, repo size |
| Application controller backlog | Delayed reconciliation | Controller/API capacity | Metrics, API throttling, sharding |

Always distinguish **manifest generation**, **authorization/admission**, **Kubernetes rollout** and **application SLO** failures.

## 16. Security architecture

Minimum enterprise controls:

- SSO/OIDC integration and least-privilege Argo CD RBAC.
- Scoped AppProjects with approved repositories and destinations.
- Restricted Kubernetes service account permissions.
- Protected GitLab branches, CODEOWNERS and MR approvals.
- Registry digest pinning and signature/provenance verification.
- Encrypted transport to Git and registries.
- Secret injection through approved external secret management, not plaintext Git.
- Admission controls for privileged workloads and cluster-scoped resources.
- Audit logs and controlled break-glass procedures.
- Explicit governance for custom config-management plugins and repository plugins.

**Threat model:** A compromised GitOps repository, Argo CD admin session, repository credential or repo-server plugin can lead to unauthorized Kubernetes changes. Defense-in-depth must operate across Git, CI, registry, Argo CD and Kubernetes.

## 17. Availability and scaling architecture

Argo CD control-plane availability affects deployment and reconciliation, but an existing Kubernetes application can continue serving while Argo CD is unavailable.

Consider:
- Multiple API-server replicas behind a reliable Service.
- Repository-server scaling and cache behavior.
- Application-controller capacity, reconciliation queues and sharding where supported.
- Redis availability and memory pressure.
- Kubernetes API server throttling.
- Repository size and manifest-generation time.
- HA topology, disruption budgets and node placement.
- Persistent configuration/credential backup and restore procedures.
- Version compatibility among Argo CD, Kubernetes, Helm and CRDs.

**Do not assume all Argo CD components are stateless or independently scalable.** Follow the installed release's supported HA architecture.

## 18. SRE observability and alerts

Monitor:

| Signal | Purpose |
| --- | --- |
| Application sync status | Detect desired/live drift |
| Application health status | Detect unhealthy resources |
| Reconciliation duration | Detect backlog or slowness |
| Manifest generation errors | Detect repo/Helm/plugin failures |
| Controller queue and API errors | Detect scaling issues |
| Repo-server CPU/memory | Capacity and OOM prevention |
| Git/registry authentication failures | Credential and access incidents |
| Unexpected prune events | Destructive-change detection |
| Argo CD component availability | Control-plane health |
| Application HTTP 5xx and latency | User-facing release outcome |

Set alert thresholds from measured service objectives. An Argo CD Application being Synced is not a substitute for application telemetry.

## 19. Incident runbook — OutOfSync and Degraded

**Scenario:** A GitLab-approved promotion merges successfully, but Argo CD reports OutOfSync and the application becomes Degraded.

1. Confirm the correct cluster, Application, Project and destination namespace.
2. Identify GitOps commit, chart version and verified image digest.
3. Determine whether manifest generation succeeded.
4. Check Project restrictions, Kubernetes RBAC and admission errors.
5. Inspect Deployment status, Pods, events, Service and EndpointSlices.
6. Compare application error-rate/latency against pre-release baselines.
7. Stop further promotion and preserve nonsecret evidence.
8. Revert the GitOps change to the last known-good configuration if necessary.
9. Verify Argo CD convergence and restored user-facing SLIs.
10. Document the root cause, blast radius, recovery time and preventive controls.

Do not manually edit Argo CD-managed Deployments as a normal rollback strategy. Authorized emergency actions must be reconciled with Git.

## 20. Operational commands quick reference

\`\`\`bash
# Discover the control plane
kubectl get pods,deployments,statefulsets,services -n argocd

# Inspect declarative GitOps objects
kubectl get applications.argoproj.io -n argocd
kubectl get appprojects.argoproj.io -n argocd
kubectl describe application demo-app-dev -n argocd

# Inspect application runtime
kubectl get deployment,pods,svc -n demo-dev
kubectl get endpointslices -n demo-dev
kubectl get events -n demo-dev --sort-by=.lastTimestamp

# Argo CD CLI (if already configured and authorized)
argocd app list
argocd app get demo-app-dev
argocd app history demo-app-dev
\`\`\`

Commands are illustrative; resource names and permissions vary.

## 21. Cloud considerations: EKS, AKS and GKE

| Area | Amazon EKS | Azure AKS | Google GKE |
| --- | --- | --- | --- |
| Identity | IRSA / EKS Pod Identity where supported | Microsoft Entra Workload ID | Workload Identity Federation for GKE |
| Registry | ECR or approved OCI registry | ACR or approved OCI registry | Artifact Registry or approved OCI registry |
| Ingress | AWS Load Balancer Controller or other approved controller | AKS-supported ingress/gateway integration | GKE-supported ingress/gateway integration |
| Secrets | AWS Secrets Manager and approved controllers | Azure Key Vault and approved controllers | Secret Manager and approved controllers |
| Metrics | Prometheus/managed metrics integration | Azure Monitor/Prometheus integration | Cloud Monitoring/Prometheus integration |
| Control plane | EKS-managed Kubernetes API | AKS-managed Kubernetes API | GKE-managed Kubernetes API |

Choose provider-specific identity, CNI, ingress and secret patterns deliberately. They are not interchangeable simply because the GitOps manifests look similar.

## 22. Acceptance checklist

- [ ] Explain all core Argo CD components and their responsibilities.
- [ ] Distinguish Application sync status from resource health and SLOs.
- [ ] Explain AppProject restrictions and underlying Kubernetes RBAC.
- [ ] Describe manual sync, automated sync, self-heal and prune.
- [ ] Explain Helm rendering vs Helm CLI release ownership.
- [ ] Design four namespace-scoped Applications in one cluster.
- [ ] Validate the correct Helm values-file path strategy.
- [ ] Inspect an existing Argo CD deployment or document the read-only limitation.
- [ ] Trace one Application from source to destination.
- [ ] Review security, HA, observability and disaster recovery risks.
- [ ] Demonstrate an OutOfSync/Degraded incident triage plan.
- [ ] Document GitOps rollback and acceptance evidence.

## 23. Evidence worksheet

\`\`\`text
CHAPTER 036 — ARGO CD ARCHITECTURE
Date:
Reviewer:
Cluster/context:
Argo CD version (if installed):
Control-plane namespace:
API server:
Application controller:
Repository server:
Redis:
ApplicationSet controller:
SSO/RBAC integration:
AppProject and allowed destinations:
Application source repo/revision/path:
Destination namespace:
Sync status:
Health status:
Helm chart and values path:
Verified image digest:
Controller/repo-server diagnostics:
Security and HA risks:
GitOps rollback commit:
SLO baseline:
Final decision:
Open risks/owners:
\`\`\`

## 24. Knowledge checks

1. What is the difference between GitLab CI's role and Argo CD's role?
2. Which component renders Helm manifests?
3. Which component compares desired and live Kubernetes resources?
4. Can an Application be Synced but Degraded? Why?
5. Why are AppProjects not sufficient as the only Kubernetes security boundary?
6. What are the risks of automated prune and self-heal?
7. Why does \`helm list\` not necessarily show an Argo CD-managed Helm deployment?
8. Why can applications remain available during an Argo CD outage?
9. How would you troubleshoot an Application stuck OutOfSync?
10. Why do production-critical environments sometimes need separate clusters?

## 25. Completion and next chapter

**Pass:** You can trace the full Argo CD reconciliation path, identify control-plane components and security boundaries, explain Helm ownership, and produce a read-only architecture and incident-response assessment.

**Next: Chapter 037 — Argo CD Installation, Namespaces, RBAC and Initial Configuration.**
