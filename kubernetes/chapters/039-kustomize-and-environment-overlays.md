# Chapter 039 — Kustomize and Environment Overlays

**Track:** Kubernetes Administration · **Part 08 — Configuration Management**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 011–020 and 036–038; kubectl, Windows PowerShell, disposable Kubernetes cluster

## 1. Production scenario

A platform team maintains the same web application in development, staging and production. Copying entire YAML manifests has caused drift: production accidentally received a staging image tag and only one replica. The team needs a single source of common configuration with explicit environment-specific patches and a reviewable deployment process.

Kustomize renders standard Kubernetes manifests from a **base** and one or more **overlays**. It is built into kubectl through `kubectl kustomize` and `kubectl apply -k`; a standalone `kustomize` CLI may support newer features than the version embedded in kubectl.

### Learning objectives

1. Explain bases, overlays, resources, patches and transformers.
2. Build reusable Deployment, Service and ConfigMap resources.
3. Customize replicas, image tags, namespaces and resource requests by environment.
4. Use strategic merge and JSON 6902 patch formats.
5. Understand ConfigMap generator name hashes and rollout implications.
6. Compare rendered manifests and diagnose patch failures before deployment.
7. Complete seven labs and an environment-drift acceptance project.

## 2. Kustomize architecture

```text
                  base/
             deployment.yaml
               service.yaml
             kustomization.yaml
                    |
           +--------+---------+
           |                  |
    overlays/staging/   overlays/production/
    kustomization.yaml  kustomization.yaml
    patch-staging.yaml  patch-production.yaml
           |                  |
      kubectl kustomize   kubectl kustomize
           |                  |
       review/apply        review/approve/apply
```

A Kustomize **base** is a directory with a `kustomization.yaml` and shared resources. An **overlay** imports a base and applies environment-specific transformations. Kustomize does not store a release history or implement rollback like Helm; use Git history, GitOps reconciliation, backups and Kubernetes rollout history as appropriate.

## 3. Lab setup and repository layout

Use an isolated cluster and local working directory. PowerShell:

```powershell
kubectl version --client
kubectl config current-context
kubectl get nodes
New-Item -ItemType Directory -Force .\ch039\base
New-Item -ItemType Directory -Force .\ch039\overlays\staging
New-Item -ItemType Directory -Force .\ch039\overlays\production
kubectl create namespace ch039-staging
kubectl create namespace ch039-production
```

Directory layout:

```text
ch039/
  base/
    kustomization.yaml
    deployment.yaml
    service.yaml
  overlays/
    staging/
      kustomization.yaml
      patch-staging.yaml
    production/
      kustomization.yaml
      patch-production.yaml
```

Use a disposable cluster. Do not run `kubectl apply -k` against an existing production namespace.

## 4. Lab 1 — Build a reusable base

Save `ch039/base/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels:
    app: web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 128Mi
```

Save `ch039/base/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: 80
  type: ClusterIP
```

Save `ch039/base/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
commonLabels:
  app.kubernetes.io/managed-by: kustomize
```

```powershell
kubectl kustomize .\ch039\base
```

**Expected:** valid Deployment and Service rendered with common labels. The `commonLabels` transformer may add labels to selectors and templates; avoid changing selector-related labels after deployment because Deployment selectors are immutable. In new projects, consider `labels` with explicit selector behavior, subject to installed Kustomize version.

## 5. Lab 2 — Staging overlay with strategic merge patch

Save `ch039/overlays/staging/patch-staging.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
```

Save `ch039/overlays/staging/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: ch039-staging
resources:
  - ../../base
namePrefix: staging-
patches:
  - path: patch-staging.yaml
```

```powershell
kubectl kustomize .\ch039\overlays\staging
kubectl apply -k .\ch039\overlays\staging
kubectl -n ch039-staging rollout status deployment/staging-web --timeout=180s
kubectl -n ch039-staging get deployment,service,pods
```

**Expected:** `staging-web` Deployment and Service in `ch039-staging`, one Ready replica. Patch targets use the original resource identity before name transformations; confirm rendered output rather than assuming patch order.

## 6. Lab 3 — Production overlay with a different capacity profile

Save `ch039/overlays/production/patch-production.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

Save `ch039/overlays/production/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: ch039-production
resources:
  - ../../base
namePrefix: prod-
patches:
  - path: patch-production.yaml
```

```powershell
kubectl kustomize .\ch039\overlays\production
kubectl apply -k .\ch039\overlays\production
kubectl -n ch039-production rollout status deployment/prod-web --timeout=180s
kubectl -n ch039-production get deployment,service,pods
```

**Expected:** three Ready production replicas with the production resource profile. This is a lab-only `production` namespace, not a real production environment.

## 7. Lab 4 — JSON 6902 patch and image transformer

Create a JSON patch to change the Deployment's readiness probe initial delay without duplicating its manifest. Save `ch039/overlays/staging/patch-readiness.yaml`:

```yaml
- op: add
  path: /spec/template/spec/containers/0/readinessProbe/initialDelaySeconds
  value: 3
```

Add the following second entry to the existing `patches` array in `ch039/overlays/staging/kustomization.yaml`:

```yaml
  - target:
      group: apps
      version: v1
      kind: Deployment
      name: web
    path: patch-readiness.yaml
```

To demonstrate image transformations, also add:

```yaml
images:
  - name: nginx
    newTag: "1.27"
```

```powershell
kubectl kustomize .\ch039\overlays\staging
kubectl apply -k .\ch039\overlays\staging
kubectl -n ch039-staging rollout status deployment/staging-web --timeout=180s
```

**Expected:** staging Deployment renders with `initialDelaySeconds: 3`. JSON 6902 patches address exact document paths; container index 0 is fragile if container ordering changes. Prefer explicit, reviewable targets and validate the rendered result.

## 8. Lab 5 — ConfigMap generator and change propagation

Add this to the staging overlay's `kustomization.yaml`:

```yaml
configMapGenerator:
  - name: web-settings
    literals:
      - APP_MODE=staging
      - LOG_LEVEL=info
```

Kustomize normally appends a content hash to generated ConfigMap names. To demonstrate name-reference rewriting, add an environment reference to the **base** Deployment's nginx container:

```yaml
          envFrom:
            - configMapRef:
                name: web-settings
```

**Important:** because the base now references `web-settings`, both overlays must generate it. Add the following to the production overlay:

```yaml
configMapGenerator:
  - name: web-settings
    literals:
      - APP_MODE=production
      - LOG_LEVEL=warn
```

Render both overlays before applying:

```powershell
kubectl kustomize .\ch039\overlays\staging
kubectl kustomize .\ch039\overlays\production
kubectl apply -k .\ch039\overlays\staging
kubectl apply -k .\ch039\overlays\production
```

**Expected:** each overlay generates an environment-specific ConfigMap with a hash suffix, and the Deployment's `envFrom.configMapRef.name` points to the generated name. Change staging `LOG_LEVEL` from `info` to `debug`, rerender and apply; the changed hash causes a Pod-template reference update and a rollout.

**Caution:** generated ConfigMaps from previous versions may remain in the namespace after `kubectl apply -k`; do not assume automatic garbage collection. Avoid `kubectl apply --prune` without a carefully defined inventory/ownership boundary.

## 9. Lab 6 — Detect an unsafe environment overlay

In the disposable staging overlay only, intentionally change `replicas` to 0 in `patch-staging.yaml`, then render without applying:

```powershell
kubectl kustomize .\ch039\overlays\staging
kubectl diff -k .\ch039\overlays\staging
```

**Expected:** rendered Deployment shows zero replicas; `kubectl diff` identifies the proposed change. Exit code 1 from `kubectl diff` normally means differences exist, not necessarily a command failure. **Do not apply** the unsafe change.

Restore staging replicas to 1, then rerender:

```powershell
kubectl kustomize .\ch039\overlays\staging
kubectl diff -k .\ch039\overlays\staging
```

For production, add automated policy checks: minimum replicas, approved registries, pinned images, resource requests/limits, prohibited privileged settings, secret handling and environment-specific review approvals.

## 10. Lab 7 — Configuration drift and rollback acceptance

Simulate out-of-band drift in the disposable staging namespace:

```powershell
kubectl -n ch039-staging scale deployment/staging-web --replicas=2
kubectl -n ch039-staging get deployment staging-web
kubectl diff -k .\ch039\overlays\staging
```

**Expected:** live state differs from the overlay's desired one replica. Reconcile with the reviewed manifest:

```powershell
kubectl apply -k .\ch039\overlays\staging
kubectl -n ch039-staging rollout status deployment/staging-web --timeout=180s
kubectl -n ch039-staging get deployment staging-web
```

**Expected:** one Ready staging replica. Note that client-side apply and field ownership can affect whether a manual scale is overwritten; inspect the rendered manifest and live `managedFields` if reconciliation does not produce the expected result.

For an actual failed application update, revert the offending overlay commit in Git, render and review it, then reapply. Kubernetes `rollout undo` can restore a Deployment revision, but subsequent Kustomize/GitOps reconciliation may reintroduce the bad desired state unless the source configuration is corrected.

### Acceptance evidence

| Check | Required evidence |
|---|---|
| Base | Reusable Deployment and Service |
| Staging | One replica and staging namespace |
| Production | Three replicas and production resources |
| JSON patch | Readiness probe transformed |
| Generator | ConfigMap hash and reference rewritten |
| Safety gate | Unsafe zero-replica change detected before apply |
| Drift | Live state compared to rendered overlay |
| Recovery | Reviewed desired state reapplied |
| Security | No plaintext credentials committed |

## 11. Kustomize versus Helm

| Dimension | Kustomize | Helm |
|---|---|---|
| Primary model | Declarative YAML transforms | Chart templates and releases |
| Configuration | Bases, overlays, patches | values.yaml and Go templates |
| Render | kubectl kustomize | helm template |
| Apply | kubectl apply -k | helm install/upgrade |
| Release history | No built-in release object | Helm revisions |
| Rollback | Revert desired state / rollout controls | helm rollback |
| Generated config | ConfigMap/Secret generators | Templates or external integrations |
| Common fit | Environment overlays and GitOps | Packaging and versioned applications |

Both tools can coexist. For example, Kustomize can manage environment resources while Helm manages a third-party application chart. Establish one clear ownership and reconciliation path for each resource.

## 12. Production troubleshooting runbook

1. **Identify the environment:** confirm kubectl context, namespace, Git revision and intended overlay.
2. **Render first:** `kubectl kustomize` and inspect image, replicas, namespace, labels, resource requests and ConfigMap references.
3. **Validate:** check YAML, API schemas, admission policies and policy-as-code results.
4. **Compare:** use `kubectl diff -k` and examine unexpected deletions or immutable-field changes.
5. **Apply deliberately:** use reviewed Git revision and approved rollout window.
6. **Verify:** Deployment readiness, Pod events, Service selectors, configuration values and application SLIs.
7. **Recover:** revert faulty source change, rerender and reapply; assess any data or external side effects separately.
8. **Close:** capture timeline, rendered diff, owner, contributing factors and prevention.

### Troubleshooting matrix

| Symptom | Likely cause | First checks |
|---|---|---|
| Build fails | Bad YAML, missing base, patch target mismatch | kubectl kustomize output |
| Wrong namespace | Overlay namespace transform missing | Rendered metadata |
| Deployment selector invalid | Label transformer changed selectors | Rendered selector and Pod labels |
| Wrong image | Image transformer/patch precedence | Rendered container image |
| ConfigMap not found | Generator name/reference mismatch | Rendered ConfigMap and Pod ref |
| Pods stale | Config not projected/restarted | Generated hash, rollout status |
| Drift persists | Multiple controllers/field ownership | managedFields, GitOps owner |
| Rollback reverts unexpectedly | GitOps source still wrong | Git revision and reconciler status |

## 13. Production best practices

- Keep bases minimal and overlays explicit; avoid duplicating complete manifests.
- Use pinned container digests for production where feasible.
- Validate every environment's rendered output in CI, not only the base.
- Protect production overlays with code review and change approval.
- Keep Secret values out of generators and Git unless using an approved encrypted-secrets workflow; `secretGenerator` does not encrypt plaintext input.
- Be careful with commonLabels and immutable Deployment selectors.
- Use generator hash changes intentionally and monitor retained old ConfigMaps.
- Use one source of truth and prevent Helm, kubectl and GitOps from fighting over the same fields.
- Record tool versions because embedded kubectl Kustomize features may differ from standalone Kustomize.
- Establish rollback and cleanup rules before adopting automatic pruning.

## 14. Cleanup

Only in the disposable lab:

```powershell
kubectl -n ch039-staging get deployment,service,configmap
kubectl -n ch039-production get deployment,service,configmap
kubectl delete namespace ch039-staging
kubectl delete namespace ch039-production
```

Do not delete shared namespaces or run unscoped pruning. Local `ch039` manifests may be retained for reproducibility; do not commit actual secrets.

## 15. Acceptance checklist

- [ ] Base renders correctly.
- [ ] Staging overlay renders and deploys.
- [ ] Production overlay renders and deploys.
- [ ] Strategic merge patch verified.
- [ ] JSON 6902 patch verified.
- [ ] ConfigMap generator hash and name reference verified.
- [ ] Unsafe overlay change detected before deployment.
- [ ] Drift investigated and reconciled.
- [ ] Rollback and GitOps ownership documented.
- [ ] Runtime evidence and independent review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 16. References

- [Kubernetes Declarative Management with Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/references/kustomize/)
- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [kubectl diff](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_diff/)

**Next:** Chapter 040 — Configuration Management and Rollback Lab (Part 08 capstone).
