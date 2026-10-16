# Chapter 051 — Jenkins Helm-Based Kubernetes Deployments and Release Automation

**Part 11 — Helm, Kubernetes Deployment and GitOps**  
**Audience:** Jenkins SRE, Kubernetes platform engineers, release engineering and DevSecOps  
**Prerequisites:** Chapters 046–050; nonproduction Kubernetes cluster, Helm 3, kubectl, Jenkins Kubernetes plugin and immutable image digest from Chapters 043–045.

## Objectives

Design a secure Jenkins → Helm deployment workflow using reviewed charts, immutable image digests, scoped release identity, environment-specific values, validation, approval, health checks, rollback, audit evidence and GitOps boundaries.

## 1. Release architecture

```text
Protected Git revision
    ↓
CI: build → test → scan → SBOM → sign immutable OCI digest
    ↓
Trusted release job (separate identity + approval)
    ├─ helm lint/template
    ├─ policy/admission validation
    ├─ helm upgrade --install --atomic --wait
    ├─ rollout + SLO verification
    └─ release evidence
    ↓
Kubernetes staging namespace
    ↓
Controlled promotion or GitOps reconciliation
```

A release tag is not a substitute for a registry manifest digest. Helm controls desired Kubernetes resources; Jenkins must not silently compete with Argo CD or Flux over the same managed objects.

## 2. Release prerequisites and trust boundaries

| Control | Purpose |
|---|---|
| Protected main/release branch | Reviewed pipeline and chart |
| Approved chart version/digest | Prevent chart substitution |
| Immutable image digest | Reproducible deployment |
| Namespaced Kubernetes RBAC | Prevent cluster-wide modification |
| Scoped workload identity | Avoid admin kubeconfig/static credentials |
| Separate CI and release agents | Protect deployment credentials |
| Environment approval | Production change control |
| Secret externalization | Keep secrets out of Helm values and logs |
| Evidence and rollback | Audit and incident recovery |

Use the Kubernetes service account projected token only in trusted release Pods when needed. Untrusted PR Pods must not inherit release permissions.

## 3. Repository layout

```text
repo/
├── Jenkinsfile.release
├── charts/
│   └── sample-app/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values.schema.json
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           └── _helpers.tpl
└── environments/
    ├── staging-values.yaml
    └── production-values.yaml
```

Pin chart dependencies in `Chart.lock` and use trusted repositories/OCI registries. Avoid remote dependency updates during a production deployment without review.

## 4. Minimal chart

`charts/sample-app/Chart.yaml`:

```yaml
apiVersion: v2
name: sample-app
description: Jenkins Helm release lab
type: application
version: 0.1.0
appVersion: "1.0.0"
```

`charts/sample-app/values.yaml`:

```yaml
replicaCount: 2
image:
  repository: registry.example.test/training/sample-app
  digest: sha256:REPLACE_WITH_REAL_DIGEST
service:
  port: 8080
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

`charts/sample-app/templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app.kubernetes.io/instance: {{ .Release.Name }}
    spec:
      automountServiceAccountToken: false
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          ports:
            - containerPort: {{ .Values.service.port }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          readinessProbe:
            httpGet:
              path: /healthz
              port: {{ .Values.service.port }}
            initialDelaySeconds: 2
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: {{ .Values.service.port }}
            initialDelaySeconds: 10
            periodSeconds: 10
```

`charts/sample-app/templates/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
spec:
  selector:
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.port }}
```

The image must actually serve `/healthz` on port 8080 as nonroot. The placeholder digest is deliberately invalid; replace it with an approved pushed digest before deployment. Harden further with PodDisruptionBudget, NetworkPolicy, image signature admission, topology spread and a read-only filesystem if supported.

## 5. Chart validation and dry-run

```sh
set -eu
helm lint charts/sample-app -f environments/staging-values.yaml
helm template sample-app charts/sample-app \
  --namespace jenkins-staging \
  -f environments/staging-values.yaml > rendered.yaml
kubectl apply --dry-run=client -f rendered.yaml
```

Client dry-run does not execute admission webhooks or guarantee server compatibility. Use `kubectl apply --dry-run=server` only with appropriate namespace/RBAC and understand it can invoke admission. Add policy-as-code checks and manifest schema validation before release.

## 6. Trusted Helm deployment

```sh
set -eu
helm upgrade --install sample-app charts/sample-app \
  --namespace jenkins-staging --create-namespace \
  --values environments/staging-values.yaml \
  --set-string image.digest="$IMAGE_DIGEST" \
  --atomic --wait --timeout 10m \
  --history-max 10
kubectl rollout status deployment/sample-app \
  --namespace jenkins-staging --timeout=5m
helm status sample-app --namespace jenkins-staging
helm history sample-app --namespace jenkins-staging
```

Use a **precreated namespace** in production and remove `--create-namespace` when release identity lacks cluster-scoped namespace permissions. `--atomic` attempts rollback on failure; it does not replace application data migration rollback, backups or SLO checks. Ensure the Helm version supports the flags used.

## 7. Jenkins release Pipeline

The following sample assumes a **trusted** Kubernetes release agent with `helm` and `kubectl`, a namespaced Kubernetes identity, a reviewed chart and an externally supplied validated digest.

```groovy
pipeline {
    agent { label 'trusted-helm-release' }
    parameters {
        string(name: 'IMAGE_DIGEST', defaultValue: '', description: 'Approved sha256 manifest digest')
    }
    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    environment {
        RELEASE_NAMESPACE = 'jenkins-staging'
        RELEASE_NAME = 'sample-app'
    }
    stages {
        stage('Validate input') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    printf '%s' "$IMAGE_DIGEST" | grep -Eq '^sha256:[a-f0-9]{64}$'
                '''
            }
        }
        stage('Validate chart') {
            steps {
                sh 'helm lint charts/sample-app -f environments/staging-values.yaml'
                sh 'helm template sample-app charts/sample-app -n "$RELEASE_NAMESPACE" -f environments/staging-values.yaml --set-string image.digest="$IMAGE_DIGEST" > rendered.yaml'
                archiveArtifacts artifacts: 'rendered.yaml', fingerprint: true
            }
        }
        stage('Approval') {
            steps {
                input message: 'Deploy reviewed digest to staging?', ok: 'Deploy'
            }
        }
        stage('Deploy') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    helm upgrade --install "$RELEASE_NAME" charts/sample-app \
                      -n "$RELEASE_NAMESPACE" \
                      -f environments/staging-values.yaml \
                      --set-string image.digest="$IMAGE_DIGEST" \
                      --atomic --wait --timeout 10m --history-max 10
                '''
            }
        }
        stage('Verify') {
            steps {
                sh 'kubectl rollout status deployment/"$RELEASE_NAME" -n "$RELEASE_NAMESPACE" --timeout=5m'
                sh 'helm status "$RELEASE_NAME" -n "$RELEASE_NAMESPACE"'
            }
        }
    }
}
```

**Production gaps to close:** Protect the job from untrusted branch changes; verify image signature and provenance before deployment; pin Helm/kubectl and chart versions; use noninteractive environment approval and change records; check external health/SLOs; archive Helm history and audit metadata; handle migrations separately. Do not pass secrets with `--set`, `--debug` or artifact archives.

## 8. Rollback and release history

```sh
helm history sample-app -n jenkins-staging
helm rollback sample-app <KNOWN_GOOD_REVISION> \
  -n jenkins-staging --wait --timeout 10m
kubectl rollout status deployment/sample-app \
  -n jenkins-staging --timeout=5m
```

Replace the revision placeholder with an actual verified prior revision. Verify previous image digest/signature and database schema compatibility. Helm rollback can restore Kubernetes manifests, but cannot automatically reverse irreversible data migrations or external side effects.

## 9. Helm versus GitOps ownership

**Direct Helm from Jenkins:** Jenkins invokes `helm upgrade` and is responsible for release state, approval and rollback.

**GitOps:** Jenkins builds/scans/signs image and proposes a reviewed Git change to the desired digest; Argo CD or Flux reconciles it. Avoid Jenkins `helm upgrade` against the same objects GitOps owns. GitOps promotion, drift detection and rollback will be covered in Chapters 052–055.

## 10. Observability and SLOs

Measure release success rate, lead time, approval latency, Helm upgrade duration, rollback frequency, Deployment rollout duration, readiness failures, unavailable replicas, admission failures and post-deploy error budget burn. Correlate Jenkins build ID, Git SHA, chart version, image digest, Kubernetes events and change ticket.

## 11. Troubleshooting matrix

| Failure | Diagnostic | Recovery |
|---|---|---|
| Helm lint failure | Chart templates/values | Fix chart |
| Template renders invalid YAML | `helm template` | Correct indentation/schema |
| Release SA forbidden | Kubernetes RBAC | Scope Role/Binding |
| Namespace missing | `kubectl get ns` | Precreate with admin |
| ImagePullBackOff | Registry credentials/digest | Fix pull access |
| Admission rejected | Pod Security/policy | Harden manifest |
| Readiness probe fails | Pod logs/events | Fix app/port |
| Deployment timeout | Rollout conditions | Restore capacity/config |
| Helm release locked | Pending operation history | Investigate/recover safely |
| Atomic rollback fails | Helm history/resources | Manual approved recovery |
| Wrong image digest | Effective Deployment | Reconcile approved digest |
| Secret exposed in values | Release history | Revoke/rotate/redesign |
| CRD upgrade issue | API compatibility | Plan CRD lifecycle |
| PVC/StatefulSet immutable field | API error | Migration plan |
| Chart dependency unavailable | OCI/repo access | Restore pinned artifact |
| GitOps fights Helm | Drift/reconciliation logs | Establish one owner |

## 12. Production runbooks

### A. New Helm release onboarding
1. Review chart and image provenance, namespace and RBAC.
2. Validate values/schema, `helm lint` and template rendering.
3. Test admission, secrets handling and readiness probes.
4. Deploy signed digest to nonproduction namespace.
5. Verify rollout, SLOs, evidence and rollback.
6. Obtain change approval before production.

### B. Helm deployment failure
1. Capture Jenkins build, Git SHA, digest, Helm revision and Kubernetes events.
2. Distinguish RBAC, admission, image pull, probes, resources and chart errors.
3. Avoid uncontrolled repeated upgrades.
4. Recover via atomic rollback or approved prior revision.
5. Verify service health and record incident.

### C. Bad image or signature mismatch
1. Halt release and quarantine untrusted digest.
2. Verify registry manifest, signature identity and provenance.
3. Restore previous signed digest via approved release process.
4. Investigate source/build/signing chain.
5. Update policy and audit records.

### D. Secret leak
1. Stop deployment, revoke/rotate secret and restrict access.
2. Inspect Helm release history, values, logs and artifacts.
3. Remove sensitive values from chart workflow; use secret manager.
4. Revalidate least privilege and audit access.
5. Document security incident.

### E. Drift and ownership conflict
1. Determine whether Helm or GitOps owns the resource.
2. Capture desired and live manifests.
3. Pause only approved reconciler during remediation.
4. Establish one source of truth and reconcile.
5. Verify no recurring drift.

## 13. Acceptance criteria

- [ ] Chart lint, template and schema validation pass.
- [ ] Image is pinned to reviewed registry digest.
- [ ] Release identity is namespace-scoped.
- [ ] Deployment approval and audit evidence captured.
- [ ] Rollout/readiness and SLO checks pass.
- [ ] Helm revision and rollback tested.
- [ ] Secrets never enter rendered artifacts/logs.
- [ ] Helm/GitOps ownership boundary documented.

**Companion:** [Chapter 051 hands-on lab](labs/051-jenkins-helm-kubernetes-deployments-release-automation-check.md).  
**Next:** Chapter 052 — Jenkins Kubernetes Deployment Strategies: Rolling, Blue-Green and Canary.
