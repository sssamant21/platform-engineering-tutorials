# Chapter 038 — Helm Installation, Charts and Releases

**Track:** Kubernetes Administration · **Part 08 — Configuration Management**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 011–020 and 036–037; kubectl, Helm 3 or compatible Helm 4 client, Windows PowerShell, isolated Kubernetes cluster

## 1. Production scenario

A team deploys an application through Helm. A new values file changes the container image to a nonexistent tag, and the rollout fails. Operators need to inspect rendered resources, release revisions and Kubernetes events, then restore service while preserving state and avoiding leaked credentials.

Helm is a package manager and release-management tool for Kubernetes. A **chart** packages templates and defaults; a **release** is a particular installed chart instance in a namespace.

### Learning objectives

1. Install and verify Helm client and cluster access.
2. Explain chart directories, templates, values, helpers and release metadata.
3. Render manifests and lint charts before deployment.
4. Install, inspect and upgrade a release.
5. Diagnose failed upgrades using Helm history and Kubernetes evidence.
6. Perform safe rollback and understand rollback limitations.
7. Complete seven labs and a production release acceptance project.

## 2. Helm architecture

```text
Chart (Chart.yaml + values.yaml + templates/)
          |
     helm template / lint
          |
     helm install / upgrade
          |
  Kubernetes API objects
          |
    Release metadata
   (namespace-scoped Secrets by default)
          |
 helm status / history / rollback / uninstall
```

Helm 3 uses a client-oriented architecture without Tiller. Helm stores release metadata in Kubernetes, typically as namespace-scoped Secrets. This metadata may contain rendered manifests and values: **do not place plaintext production credentials into Helm values or commit them to Git**. Helm release history is not a secret manager.

## 3. Helm installation and prerequisites

On Windows, install Helm through an approved package manager or the official Helm release archive. Validate installation:

```powershell
helm version
helm env
kubectl config current-context
kubectl get nodes
kubectl create namespace ch038
```

The labs require permission to create Deployments, Services and Helm release metadata in the disposable `ch038` namespace. If Helm is unavailable, stop and install a version compatible with your organization's supported chart ecosystem. Do not modify production contexts.

## 4. Chart structure and design

```text
ch038-web/
  Chart.yaml
  values.yaml
  templates/
    _helpers.tpl
    deployment.yaml
    service.yaml
```

Create a chart scaffold:

```powershell
helm create ch038-web
Get-ChildItem .\ch038-web -Recurse
```

The scaffold includes extra resources such as tests, service account, ingress and HPA depending on Helm version. For a reproducible lab, remove the scaffold's `templates` directory and create the minimal files below:

```powershell
Remove-Item .\ch038-web\templates -Recurse -Force
New-Item -ItemType Directory .\ch038-web\templates
```

**Only run this in the newly generated lab chart folder**, not an existing application chart.

Replace `ch038-web/Chart.yaml`:

```yaml
apiVersion: v2
name: ch038-web
description: Minimal Helm release lifecycle lab
type: application
version: 0.1.0
appVersion: "1.0"
```

Replace `ch038-web/values.yaml`:

```yaml
replicaCount: 2
image:
  repository: nginx
  tag: "1.27"
  pullPolicy: IfNotPresent
service:
  port: 80
resources:
  requests:
    cpu: 25m
    memory: 32Mi
  limits:
    cpu: 200m
    memory: 128Mi
```

Save `ch038-web/templates/_helpers.tpl`:

```gotemplate
{{- define "ch038-web.name" -}}
{{- .Chart.Name -}}
{{- end -}}
{{- define "ch038-web.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
```

Save `ch038-web/templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "ch038-web.fullname" . }}
  labels:
    app.kubernetes.io/name: {{ include "ch038-web.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/instance: {{ .Release.Name }}
      app.kubernetes.io/name: {{ include "ch038-web.name" . }}
  template:
    metadata:
      labels:
        app.kubernetes.io/instance: {{ .Release.Name }}
        app.kubernetes.io/name: {{ include "ch038-web.name" . }}
    spec:
      containers:
        - name: nginx
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 2
            periodSeconds: 5
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

Save `ch038-web/templates/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "ch038-web.fullname" . }}
spec:
  selector:
    app.kubernetes.io/name: {{ include "ch038-web.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
  type: ClusterIP
```

The helper and selector labels must remain stable across upgrades; changing a Deployment selector is generally forbidden.

## 5. Lab 1 — Lint and render without changing the cluster

```powershell
helm lint .\ch038-web
helm template demo .\ch038-web --namespace ch038
helm template demo .\ch038-web --namespace ch038 --set replicaCount=3
```

**Expected:** lint succeeds; rendered Deployment and Service contain no template delimiters; `replicas` changes from 2 to 3 in the overridden render. Rendering does not prove admission, image availability or runtime readiness.

Use `helm template --debug` for template troubleshooting, but never enable verbose output with real secrets embedded in values.

## 6. Lab 2 — Install and inspect a release

```powershell
helm install demo .\ch038-web --namespace ch038 --wait --timeout 3m
helm list -n ch038
helm status demo -n ch038
helm get values demo -n ch038
helm get manifest demo -n ch038
kubectl -n ch038 get deployment,pods,service -o wide
kubectl -n ch038 rollout status deployment/demo-ch038-web --timeout=180s
```

**Expected:** release `deployed`, two Ready nginx replicas and ClusterIP Service. `helm get manifest` shows rendered Kubernetes YAML. Do not run `helm get values --all` or `helm get manifest` into shared logs for real charts that embed secrets.

## 7. Lab 3 — Values override and controlled upgrade

Save `ch038-prod-like-values.yaml`:

```yaml
replicaCount: 3
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 250m
    memory: 128Mi
```

```powershell
helm upgrade demo .\ch038-web -n ch038 -f .\ch038-prod-like-values.yaml --wait --timeout 3m
helm status demo -n ch038
helm history demo -n ch038
kubectl -n ch038 get deployment demo-ch038-web
kubectl -n ch038 rollout status deployment/demo-ch038-web --timeout=180s
```

**Expected:** three Ready replicas and a new release revision. Understand values precedence: chart defaults, `-f` files in order, then `--set` overrides. Use explicit values files and version-controlled non-secret configuration for reproducibility.

## 8. Lab 4 — Inject a failed upgrade safely

The lab uses a nonexistent nginx tag to simulate a bad release. **Do not use this fault injection in production.**

```powershell
helm upgrade demo .\ch038-web -n ch038 -f .\ch038-prod-like-values.yaml --set image.tag=ch038-tag-does-not-exist --wait --timeout 90s
```

**Expected:** command fails due to Pods unable to pull the image; existing healthy replicas may remain serving traffic depending on Deployment rollout behavior. Inspect:

```powershell
helm status demo -n ch038
helm history demo -n ch038
kubectl -n ch038 get deployment,replicaset,pods -o wide
kubectl -n ch038 get events --sort-by=.lastTimestamp
kubectl -n ch038 describe deployment demo-ch038-web
```

Look for `ErrImagePull`, `ImagePullBackOff`, progress deadline and failed Helm revision. `--wait` checks readiness and times out; it does not automatically roll back unless an appropriate atomic/rollback flag is used. Avoid interpreting Helm's failed status as proof that all application traffic stopped.

## 9. Lab 5 — Recover using Helm rollback

Identify the last known-good revision from `helm history`. If revision 2 is the latest successful revision in this lab:

```powershell
helm rollback demo 2 -n ch038 --wait --timeout 3m
helm history demo -n ch038
helm status demo -n ch038
kubectl -n ch038 rollout status deployment/demo-ch038-web --timeout=180s
kubectl -n ch038 get pods -o wide
```

**Expected:** deployment returns to healthy nginx tag and three Ready replicas. A rollback creates another Helm revision. Confirm actual revision numbers from your cluster before running commands; never blindly assume revision 2 in an environment with prior attempts.

**Important:** Helm rollback re-applies earlier Kubernetes release manifests. It does not reverse database schema changes, external API calls, PV data mutations, CRD migrations or all Helm hook side effects. Plan application/data rollback separately.

## 10. Lab 6 — Inspect history, metadata and release drift

```powershell
helm list -n ch038 --all
helm history demo -n ch038
helm get metadata demo -n ch038
helm get values demo -n ch038
helm get manifest demo -n ch038
kubectl -n ch038 get deployment demo-ch038-web -o yaml
```

If your Helm version lacks `helm get metadata`, use `helm status` and `helm history`.

Drift exercise: compare Helm-rendered desired replicas with the live Deployment. Manual `kubectl scale` can introduce drift:

```powershell
kubectl -n ch038 scale deployment/demo-ch038-web --replicas=1
kubectl -n ch038 get deployment demo-ch038-web
helm get values demo -n ch038
```

**Expected:** live replica count differs from the values that produced the release. Reconcile deliberately with a Helm upgrade using the known-good values:

```powershell
helm upgrade demo .\ch038-web -n ch038 -f .\ch038-prod-like-values.yaml --wait --timeout 3m
kubectl -n ch038 get deployment demo-ch038-web
```

**Expected:** three Ready replicas. A Helm upgrade may not overwrite every out-of-band field change because Helm uses patch/merge behavior; for production drift, inspect actual desired/live resources and GitOps ownership before choosing remediation.

## 11. Lab 7 — Release incident acceptance exercise

Scenario: after a chart upgrade, Pods are not Ready and the on-call team considers uninstalling the release.

Required investigation:

```powershell
helm list -n ch038 --all
helm status demo -n ch038
helm history demo -n ch038
kubectl -n ch038 get deployment,replicaset,pods,service -o wide
kubectl -n ch038 describe deployment demo-ch038-web
kubectl -n ch038 get events --sort-by=.lastTimestamp
```

Document:
1. Which revision introduced the failure?
2. Did Helm render valid manifests?
3. Did the Kubernetes API accept resources?
4. Did the image pull, schedule and readiness checks succeed?
5. What is the last verified healthy revision?
6. What does rollback **not** restore?
7. Which SLIs and acceptance tests demonstrate recovery?

### Acceptance matrix

| Check | Evidence |
|---|---|
| Chart structure | Chart.yaml, values.yaml, templates |
| Render/lint | Successful lint and expected manifests |
| Install | Deployed release, Ready replicas |
| Upgrade | Values change and new revision |
| Failure | Failed image pull, events and Helm history |
| Rollback | Last good revision restored |
| Drift | Live state compared to Helm release |
| Security | No real credentials in values or release history |
| Cleanup | Only lab release and namespace removed |

## 12. Helm operations and production safeguards

- Pin chart versions and container image digests; avoid unreviewed `latest` tags.
- Run `helm lint`, `helm template`, schema validation and policy checks in CI.
- Use `--wait`, `--timeout` and deliberate rollback/atomic behavior where supported.
- Understand `--atomic` behavior for your Helm version; failed upgrades may roll back automatically, but external side effects remain.
- Review CRDs and hooks separately: CRDs under `crds/` have special install/upgrade/delete semantics.
- Avoid `helm uninstall` as an incident recovery shortcut; it removes managed resources and may affect availability or persistent data.
- Avoid passing production secrets with `--set` or plaintext values files stored in Git.
- Restrict access to Helm release metadata Secrets.
- Record release owner, chart version, app version, values source, change ticket and rollback plan.
- Coordinate Helm with GitOps tools; competing reconcilers can undo manual changes.

## 13. Troubleshooting matrix

| Symptom | Likely cause | First checks |
|---|---|---|
| Template error | Invalid Go template or values type | helm lint/template --debug |
| Install forbidden | RBAC/admission/quota | Helm output, API events |
| Release pending-install | Incomplete operation or timeout | helm status/history, cluster resources |
| Failed upgrade | Image, probes, quota, scheduling | Pods, ReplicaSets, events |
| Rollback fails | Invalid old manifest, immutable fields | Helm history, API error |
| Release exists but app unhealthy | Readiness, Service selector, config | Deployment, Pod and Service checks |
| Drift after kubectl edit | Out-of-band mutation | helm get manifest vs live YAML |
| Uninstall leaves data | PVC retention or resource keep policy | PVC/PV, reclaim policy |

### Production recovery runbook

1. Freeze conflicting deployment automation under approved change control.
2. Capture Helm revision history, values provenance and Kubernetes events.
3. Classify render, admission, scheduling, image, probe, config or external dependency failure.
4. Identify last known-good revision and check data migration compatibility.
5. Choose forward fix or rollback; evaluate hooks, CRDs and persistent state.
6. Execute with availability and timeout safeguards.
7. Validate service endpoints, error rates, latency, readiness and business transactions.
8. Document incident timeline, root cause, corrective action and prevention.

## 14. Cleanup

Only in the disposable lab:

```powershell
helm list -n ch038
helm uninstall demo -n ch038 --wait
kubectl -n ch038 get all
kubectl delete namespace ch038
```

Helm uninstall may leave CRDs, PVs/PVCs, resources annotated to keep, or external cloud assets in other charts. This minimal chart creates only a Deployment and Service; verify before deleting anything else.

## 15. Acceptance checklist

- [ ] Helm version and cluster context verified.
- [ ] Chart structure created and explained.
- [ ] Lint and template rendering completed.
- [ ] Release installed and verified.
- [ ] Values override upgraded successfully.
- [ ] Broken image upgrade reproduced and diagnosed.
- [ ] Last healthy revision restored and verified.
- [ ] Helm release history and live drift inspected.
- [ ] Rollback limits and secret exposure risks documented.
- [ ] Cleanup and independent review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 16. References

- [Helm Documentation](https://helm.sh/docs/)
- [Helm Charts](https://helm.sh/docs/topics/charts/)
- [Helm Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Helm Upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Helm Rollback](https://helm.sh/docs/helm/helm_rollback/)

**Next:** Chapter 039 — Kustomize and Environment Overlays.
