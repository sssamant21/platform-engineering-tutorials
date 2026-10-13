# Chapter 091 — GitOps with Argo CD and Flux

**Track:** Kubernetes Administration · **Part 19 — GitOps and Platform Automation**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, platform engineers, Kubernetes administrators and application delivery teams  
**Prerequisites:** Kubernetes workloads, Services, RBAC, Kustomize, Helm, Git and GitHub; Windows PowerShell, kubectl, Git CLI; approved disposable staging cluster

## 1. Production scenario and mission

A team deploys workloads to Kubernetes using manual `kubectl apply` and ad hoc CI scripts. Staging and production diverge, an emergency patch is overwritten by a later release, and no one can identify which Git commit corresponds to the running application. The team must introduce GitOps without granting broad cluster-admin permissions to every deployment pipeline.

**Mission:** understand GitOps reconciliation, evaluate Argo CD and Flux, create a safe repository structure, validate drift detection and recovery, design promotion/rollback controls, and produce production-ready operational runbooks.

**Safety:** installing controllers, enabling automated sync or pruning, changing cluster RBAC and rotating repository credentials can affect many workloads. Run labs only in approved staging namespaces/clusters. Never enable cluster-wide automated prune without a scoped impact review.

### Learning outcomes

1. Explain Git as the desired-state source and reconciliation.
2. Compare Argo CD and Flux architectures and operating models.
3. Build a multi-environment GitOps repository structure.
4. Separate application manifests from cluster/platform configuration.
5. Create an Argo CD Application with scoped destination.
6. Define Flux GitRepository and Kustomization resources.
7. Validate drift detection, health and reconciliation.
8. Design secure Git credentials and controller RBAC.
9. Implement promotion, approvals and rollback procedures.
10. Troubleshoot sync failures and GitOps incidents.

## 2. GitOps architecture

```text
Developer / platform engineer
          |
     Pull request + review
          |
     Git desired state
          |
    +-----+------------------+
    |                        |
  Argo CD                  Flux
  API/UI/Repo Server       source-controller
  Application Controller   kustomize-controller
  ApplicationSet (opt.)    helm-controller (opt.)
    |                        |
    +-----------+------------+
                |
      Kubernetes API / RBAC
                |
      Live cluster resources
                |
       Health / drift signals
```

GitOps is a continuous reconciliation process, not simply a CI job that executes `kubectl apply`. Controllers detect divergence between declared desired state and observed cluster state and take action according to their configured policy.

## 3. Argo CD versus Flux

| Dimension | Argo CD | Flux |
|---|---|---|
| Primary abstraction | Application | Source + Kustomization/HelmRelease |
| User interface | Built-in UI/API | CLI and ecosystem integrations |
| Reconciliation | Application controller | Specialized controllers |
| Multi-cluster | Application destination contexts | Per-cluster or remote reconciliation patterns |
| Helm | Application source support | HelmRepository/HelmRelease |
| Drift | OutOfSync and sync status | Reconciliation status/conditions |
| Access control | Argo CD RBAC plus Kubernetes RBAC | Kubernetes RBAC and controller permissions |
| Best fit | Application-centric UI workflows | Kubernetes-native composable controllers |

Both can manage production workloads. Select based on operating model, security, tenancy, controller lifecycle and team familiarity; do not install both against the same resources without clear ownership boundaries.

## 4. Lab 1 — Verify Git, kubectl and cluster context

```powershell
$ErrorActionPreference = 'Stop'
git --version
kubectl version --client
kubectl config current-context
kubectl cluster-info
kubectl get namespaces
kubectl auth can-i create deployments -n default
```

**Stop** if the active context is not the approved staging cluster. Controller installation requires separate permissions and approval.

**Expected:** tool versions, cluster identity and permissions recorded.

## 5. Lab 2 — Create a GitOps repository layout

Recommended layout:

```text
gitops/
├── apps/
│   └── demo/
│       ├── base/
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   └── kustomization.yaml
│       └── overlays/
│           ├── staging/
│           │   └── kustomization.yaml
│           └── production/
│               └── kustomization.yaml
├── clusters/
│   ├── staging/
│   │   ├── argocd/
│   │   │   └── demo-application.yaml
│   │   └── flux/
│   │       └── demo-kustomization.yaml
│   └── production/
├── platform/
│   ├── policies/
│   ├── ingress/
│   └── observability/
└── README.md
```

Separate cluster bootstrap from application manifests. Use independent Git paths, namespaces and approval rules for staging and production. Avoid committing Secrets, kubeconfig credentials or private keys.

## 6. Lab 3 — Build a minimal Kustomize application

`apps/demo/base/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo
  template:
    metadata:
      labels:
        app: demo
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 250m
              memory: 128Mi
```

`apps/demo/base/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: demo
spec:
  selector:
    app: demo
  ports:
    - port: 80
      targetPort: 80
```

`apps/demo/base/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

`apps/demo/overlays/staging/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: ch091
resources:
  - ../../base
commonLabels:
  environment: staging
```

Note: legacy `commonLabels` changes selectors and may be deprecated by newer Kustomize versions; for production prefer carefully scoped `labels` transformers and review immutable selector changes.

```powershell
kubectl kustomize .\apps\demo\overlays\staging
```

**Expected:** rendered Deployment and Service with namespace `ch091`. Rendering does not create the namespace.

## 7. Lab 4 — Prepare a disposable namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch091
  labels:
    environment: staging
```

Save as `ch091-namespace.yaml` and run in approved staging:

```powershell
kubectl apply --dry-run=server -f .\ch091-namespace.yaml
kubectl apply -f .\ch091-namespace.yaml
kubectl get namespace ch091
```

**Expected:** isolated namespace ready for application reconciliation. Consider ResourceQuota and LimitRange before enabling automation.

## 8. Lab 5 — Inspect an existing Argo CD installation

```powershell
kubectl get namespaces
kubectl -n argocd get deployments,pods,services
kubectl get crds | Select-String 'argoproj.io'
```

Argo CD might be installed under a different namespace or not installed. If absent, record Not installed; installation is a separate approved platform change.

### Components to understand

- Application controller: compares and reconciles desired/live state.
- Repo server: fetches and renders sources.
- API server: API/UI and auth.
- ApplicationSet controller: generates Applications from templates.
- Notifications/Dex/Redis: optional or deployment-specific components.

**Expected:** controller inventory, version, resource scope and ownership.

## 9. Lab 6 — Define an Argo CD Application

**Review-only until the repository URL, namespace and project are approved.**

`clusters/staging/argocd/demo-application.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ch091-demo
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/REPLACE_ORG/REPLACE_REPO.git
    targetRevision: main
    path: apps/demo/overlays/staging
  destination:
    server: https://kubernetes.default.svc
    namespace: ch091
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
```

**Important:** no automated sync or prune is enabled in this initial manifest. The default Argo CD project may be too permissive for multi-tenant production use; create a restricted AppProject before rollout.

```powershell
kubectl apply --dry-run=server -f .\clusters\staging\argocd\demo-application.yaml
kubectl -n argocd get applications
kubectl -n argocd describe application ch091-demo
```

Dry-run requires the Argo CD CRD and an existing `argocd` namespace. An Argo CD Application is a declarative controller resource; applying it may cause the controller to compare desired state even without auto-sync.

## 10. Lab 7 — Argo CD reconciliation and drift review

With an approved Argo CD installation and Application:

```powershell
kubectl -n argocd get application ch091-demo -o yaml
kubectl -n argocd get pods
kubectl -n ch091 get deployments,services,pods
```

### Drift acceptance

1. Compare Git revision to observed Application sync revision.
2. Confirm Application health and sync status.
3. Review diffs before any manual sync.
4. Understand ignoreDifferences and server-side apply.
5. Confirm ownership and avoid competing controllers.
6. Record expected reconciliation interval and alert thresholds.

**Tabletop:** a human changes a replica count manually. Predict whether self-heal is enabled and whether the controller reverts it. Do not mutate production resources to demonstrate drift.

## 11. Lab 8 — Inspect an existing Flux installation

```powershell
kubectl get namespaces
kubectl -n flux-system get deployments,pods
kubectl get crds | Select-String 'fluxcd.io'
```

Flux controllers may be installed in another namespace or absent. Avoid installing controllers solely to satisfy the tutorial without change approval.

### Core controllers

- source-controller: Git/Helm/OCI sources.
- kustomize-controller: applies Kustomize resources.
- helm-controller: manages Helm releases.
- notification-controller: event/notification integrations.

## 12. Lab 9 — Define Flux GitRepository and Kustomization

**Review-only until source URL and controller permissions are approved.**

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: ch091-demo
  namespace: flux-system
spec:
  interval: 5m
  url: https://github.com/REPLACE_ORG/REPLACE_REPO.git
  ref:
    branch: main
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: ch091-demo
  namespace: flux-system
spec:
  interval: 5m
  path: ./apps/demo/overlays/staging
  prune: false
  sourceRef:
    kind: GitRepository
    name: ch091-demo
  targetNamespace: ch091
```

Save as `clusters/staging/flux/demo-kustomization.yaml`.

```powershell
kubectl apply --dry-run=server -f .\clusters\staging\flux\demo-kustomization.yaml
kubectl -n flux-system get gitrepositories,kustomizations
```

The Flux CRDs must be installed. `prune: false` reduces accidental deletion risk, but the controller can still create or update resources if this is applied to a live Flux installation. Keep Argo CD and Flux from managing the same application.

## 13. Lab 10 — Flux reconciliation and drift review

```powershell
kubectl -n flux-system get gitrepositories -o wide
kubectl -n flux-system get kustomizations -o wide
kubectl -n flux-system describe kustomization ch091-demo
kubectl -n ch091 get deployments,services,pods
```

### Flux acceptance

- Git source fetch status is Ready.
- Kustomization reconciliation status is Ready.
- Last applied revision is recorded.
- Reconciliation errors are observable.
- Prune, suspend and health check policies are explicit.
- Controller permissions match intended namespace/resource scope.

## 14. Lab 11 — Secure Git credentials and controller access

### Access controls

1. Prefer read-only deploy keys, GitHub Apps or short-lived credentials.
2. Rotate tokens and avoid personal access tokens with broad scopes.
3. Keep repository secrets out of manifests and logs.
4. Use SOPS/approved external secrets for encrypted or referenced secrets.
5. Restrict Argo CD AppProjects and repository/destination access.
6. Scope Flux reconciliation service accounts where possible.
7. Separate platform bootstrap from application namespaces.
8. Audit controller changes and repository access.

```powershell
kubectl get serviceaccounts -A
kubectl get roles,rolebindings -A
kubectl get clusterrolebindings
kubectl -n argocd get applications
kubectl -n flux-system get kustomizations
```

Commands for absent installations will return errors; record Not installed.

## 15. Lab 12 — Environment promotion and rollback

### Promotion flow

```text
Feature branch -> Pull request -> Review/CI checks
       |
Merge to staging desired state
       |
GitOps staging reconciliation
       |
Synthetic and SLO validation
       |
Approved production promotion PR
       |
Production reconciliation
       |
Post-deploy verification
```

Use immutable image digests or approved version pinning rather than floating tags for production. Promotion should preserve provenance, review, test evidence and change approvals.

### Rollback choices

- Git revert of a bad desired-state commit.
- Restore previous known-good image digest.
- Suspend reconciliation only with an incident command decision.
- Restore external state separately; Git rollback does not roll back databases.
- Validate controller status, application health and data compatibility.

**Expected:** a documented rollback owner and RTO, not an assumption that Git revert repairs every stateful change.

## 16. Lab 13 — Drift and outage incident tabletop

**Scenario:** a GitOps controller detects an out-of-band hotfix, a repository credential expires, and a CRD upgrade causes reconciliation to fail. A second controller also attempts to manage the same Deployment.

### Incident response

1. Confirm cluster and controller ownership.
2. Inspect desired Git revision and live resource.
3. Review Application/Kustomization conditions.
4. Separate Git fetch/auth failure from Kubernetes apply failure.
5. Check CRD/API version and admission errors.
6. Detect duplicate resource ownership.
7. Decide whether to pause reconciliation under change control.
8. Restore Git credentials or revert desired state safely.
9. Validate application SLIs and data integrity.
10. Document preventive alerts and ownership controls.

**Expected:** fault tree and incident timeline with reversible remediation decisions.

## 17. Lab 14 — GitOps monitoring and SLO acceptance

| Domain | Signal | Owner |
|---|---|---|
| Git source | Fetch failures, auth errors | Platform |
| Reconciliation | Ready/OutOfSync and duration | Platform |
| Drift | Unexpected live-state divergence | SRE |
| Application | Availability, latency and errors | Application |
| Security | Repository and RBAC changes | Security |
| Delivery | Failed promotions and rollback time | Release |
| Cost | Controller footprint and CI usage | FinOps |

### Acceptance gates

- Alerts link to runbooks and Git revisions.
- Reconciliation lag and failures are measured.
- Deployment health is independent of controller status.
- Production sync/prune policies are reviewed.
- Git source outage does not imply immediate workload outage.
- Recovery includes both desired-state and application validation.

## 18. Production operations runbooks

### A. Argo CD Application OutOfSync

1. Verify Git source and target revision.
2. Inspect Application diff and health.
3. Check destination namespace and AppProject permissions.
4. Review hooks, sync waves and CRD dependencies.
5. Confirm drift is intentional or unauthorized.
6. Sync only after approval and observe application health.

### B. Flux Kustomization NotReady

1. Check GitRepository Ready condition and revision.
2. Inspect Kustomization status and Events.
3. Verify source path and rendered YAML.
4. Review Kubernetes RBAC, CRDs and admission policies.
5. Check dependency ordering and health checks.
6. Reconcile under change control and validate workloads.

### C. Accidental deletion or prune risk

1. Pause further sync/prune changes.
2. Confirm controller and resource ownership.
3. Inspect Git commit and inventory.
4. Protect PVC/PV and external data independently.
5. Restore manifests and data using approved procedures.
6. Re-enable reconciliation only after validation.

## 19. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Argo CD OutOfSync | Git/live drift | Application diff |
| Argo CD Degraded | Unhealthy resources | Pod Events/readiness |
| Flux GitRepository NotReady | Auth/network/source | Source condition |
| Flux Kustomization NotReady | Invalid YAML/RBAC | Controller Events |
| Repeated apply failure | Immutable field/CRD | API errors |
| Unexpected deletion | Prune policy | Commit/inventory |
| Credential expired | Repository auth | Controller logs |
| Reconciliation loop | Competing controllers | Resource ownership |
| Secret leaked | Git/CI controls | Security incident |
| Rollback fails | Stateful incompatibility | App/DB recovery |

## 20. Cleanup and safeguards

```powershell
kubectl config current-context
kubectl -n ch091 get deployments,services,pods
kubectl -n argocd get applications
kubectl -n flux-system get kustomizations
```

Before deleting the namespace, ensure no active GitOps Application/Kustomization will recreate it or continue managing resources. Under approval, remove or suspend the specific staging reconciliation object first, verify its resource ownership and prune policy, then delete the isolated namespace:

```powershell
kubectl delete namespace ch091
```

Do not uninstall shared Argo CD/Flux controllers, remove production Git credentials or delete cluster-wide CRDs as part of this lab.

## 21. Acceptance checklist

- [ ] Cluster and Git tooling verified.
- [ ] Argo CD versus Flux decision documented.
- [ ] Repository layout and environment separation designed.
- [ ] Kustomize base/overlay rendered.
- [ ] Disposable namespace created or marked Not run.
- [ ] Argo CD components inventoried or marked Not installed.
- [ ] Argo CD Application reviewed and validated.
- [ ] Flux controllers inventoried or marked Not installed.
- [ ] Flux GitRepository/Kustomization reviewed.
- [ ] Drift, sync and prune behavior understood.
- [ ] Controller RBAC and repository credentials reviewed.
- [ ] Promotion and rollback procedure documented.
- [ ] Drift/outage tabletop completed.
- [ ] Monitoring, alerts and operational ownership defined.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 22. References

- [Argo CD Documentation](https://argo-cd.readthedocs.io/en/stable/)
- [Argo CD Applications](https://argo-cd.readthedocs.io/en/stable/user-guide/application-specification/)
- [Argo CD AppProjects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [Argo CD Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
- [Flux Documentation](https://fluxcd.io/flux/)
- [Flux GitRepository](https://fluxcd.io/flux/components/source/gitrepositories/)
- [Flux Kustomization](https://fluxcd.io/flux/components/kustomize/kustomizations/)
- [Flux Security](https://fluxcd.io/flux/security/)
- [Kubernetes Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [OpenGitOps Principles](https://opengitops.dev/)

**Next:** Chapter 092 — Policy as Code with Kyverno and Gatekeeper.
