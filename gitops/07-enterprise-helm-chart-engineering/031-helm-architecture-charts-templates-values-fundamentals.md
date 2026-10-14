# Chapter 031 — Helm Architecture, Charts, Templates and Values Fundamentals

**Part 07 — Enterprise Helm Chart Engineering** | **Chapter 031 / 100**  
**Audience:** Platform engineers, SREs, Kubernetes administrators and GitOps practitioners  
**Toolchain:** Helm 3, Kubernetes, GitLab CI and Argo CD  
**Architecture:** Dev, Test, Staging and Production are separate namespaces in the **same Kubernetes cluster**. Each environment uses the same Helm chart, environment-specific values and a separate Argo CD Application.

> **Safety:** Use only generic sample names and disposable resources. Do not store credentials in values files. This chapter builds and tests a chart locally first; cluster installation is optional and requires authorization. Pin real application image digests before deployment.

## 1. Learning objectives

By the end, you will be able to:

1. Explain Helm charts, templates, values, releases and revision history.
2. Describe how Helm fits into GitLab CI and Argo CD GitOps.
3. Build a reusable chart for a non-root Kubernetes HTTP service.
4. Use helpers, labels, selectors, configuration and health probes consistently.
5. Apply environment-specific values without copying the chart.
6. Validate charts using \`helm lint\`, \`helm template\` and Kubernetes API dry runs.
7. Understand values merge precedence and type pitfalls.
8. Manage safe chart upgrades, rollback and GitOps ownership.
9. Identify chart-security risks and common operational failures.

## 2. Enterprise reference architecture

\`\`\`text
GitLab application repository
   |
   +--> tests / scans / SBOM / signing
   +--> build once -> OCI image@sha256:DIGEST
   |
   v
GitOps repository
   |
   +--> charts/demo-app/              (one reusable chart)
   +--> environments/dev/values.yaml
   +--> environments/test/values.yaml
   +--> environments/staging/values.yaml
   +--> environments/prod/values.yaml
   |
   v
Argo CD Applications (one per namespace)
   |
   +--> demo-dev
   +--> demo-test
   +--> demo-staging
   +--> demo-prod
            |
       Kubernetes API
\`\`\`

The image digest is promoted unchanged between environments; only approved configuration and release policy differ. Argo CD renders Helm templates and manages desired-state reconciliation. **Do not simultaneously manage the same resources with independent \`helm upgrade\` and Argo CD workflows.**

## 3. Helm terminology

| Term | Meaning | SRE relevance |
| --- | --- | --- |
| Chart | Versioned package of Kubernetes templates and metadata | Reuse and review |
| Template | Go-template source that produces Kubernetes YAML | Rendering correctness |
| Values | Input data used during rendering | Environment configuration |
| Release | Helm-managed chart installation in a namespace | Upgrade and rollback history |
| Chart version | Version of chart package | Packaging compatibility |
| App version | Informational application version | Not an immutable artifact reference |
| Repository | HTTP chart repo or OCI registry | Distribution and access |
| Dependency | Referenced subchart/library chart | Supply-chain governance |
| \`helm lint\` | Static chart checks | Fast CI feedback |
| \`helm template\` | Render without installing | GitOps/CI validation |

Argo CD's Helm integration normally uses Helm as a **templating engine**; Argo CD, not Helm's release-state storage, tracks the deployed Application. Therefore, \`helm rollback\` is not the standard rollback method for an Argo CD-managed chart.

## 4. Helm chart anatomy

\`\`\`text
charts/demo-app/
├── Chart.yaml
├── values.yaml
├── values.schema.json
├── .helmignore
└── templates/
    ├── _helpers.tpl
    ├── configmap.yaml
    ├── deployment.yaml
    ├── service.yaml
    └── serviceaccount.yaml
\`\`\`

\`Chart.yaml\` describes the chart. \`values.yaml\` supplies defaults. Files in \`templates/\` render Kubernetes resources. Helper templates reduce duplication. A JSON schema validates expected value types and required fields.

## 5. Lab prerequisites

- Helm 3 and \`kubectl\` installed.
- An authorized Kubernetes context if performing optional installation.
- A real, previously verified \`demo-app\` image digest from Chapters 021–030.
- A sample application serving \`GET /healthz\` on port 8080 and optionally \`GET /config\`.
- A terminal supporting directory creation and text editing.

Verify:

\`\`\`bash
helm version
kubectl version --client
kubectl config current-context
\`\`\`

**Windows PowerShell:** \`New-Item -ItemType Directory -Force charts/demo-app/templates\` creates the chart folder. The YAML below is cross-platform.

## 6. Create the chart metadata

\`charts/demo-app/Chart.yaml\`:

\`\`\`yaml
apiVersion: v2
name: demo-app
description: Reusable, restricted Kubernetes application chart for GitOps labs
type: application
version: 0.1.0
appVersion: "1.0.0"
\`\`\`

Chart version and application version are not substitutes for a verified image digest.

\`charts/demo-app/.helmignore\`:

\`\`\`text
.git/
*.tmp
*.bak
.DS_Store
\`\`\`

## 7. Define chart defaults

\`charts/demo-app/values.yaml\`:

\`\`\`yaml
replicaCount: 2

image:
  repository: registry.example.com/training/demo-app
  digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  pullPolicy: IfNotPresent

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  name: ""

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

config:
  appEnv: dev
  featureEnabled: false
  logLevel: info

resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi

deployment:
  maxSurge: 1
  maxUnavailable: 0
  minReadySeconds: 5
  progressDeadlineSeconds: 180

probes:
  startup:
    failureThreshold: 12
    periodSeconds: 5
  readiness:
    periodSeconds: 5
    timeoutSeconds: 2
  liveness:
    periodSeconds: 10
    timeoutSeconds: 2

securityContext:
  runAsUser: 65532
  runAsGroup: 65532
\`\`\`

The digest above is **synthetic** for offline chart rendering only. Replace it with an actual approved digest before any cluster installation. Never infer a real registry digest from a Docker tag.

## 8. Helpers for names and labels

\`charts/demo-app/templates/_helpers.tpl\`:

\`\`\`gotemplate
{{- define "demo-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "demo-app.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "demo-app.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "demo-app.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "demo-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "demo-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "demo-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "demo-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "demo-app.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
\`\`\`

Use stable selector labels; changing selectors on an existing Deployment can require recreation because \`spec.selector\` is immutable.

## 9. ServiceAccount template

\`charts/demo-app/templates/serviceaccount.yaml\`:

\`\`\`gotemplate
{{- if .Values.serviceAccount.create }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "demo-app.serviceAccountName" . }}
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
automountServiceAccountToken: false
{{- end }}
\`\`\`

If \`serviceAccount.create: false\`, ensure the referenced ServiceAccount exists and has the intended least-privilege permissions. Workload identity integrations may require explicitly configured projected tokens.

## 10. ConfigMap template

\`charts/demo-app/templates/configmap.yaml\`:

\`\`\`gotemplate
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "demo-app.fullname" . }}-config
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
data:
  APP_ENV: {{ .Values.config.appEnv | quote }}
  FEATURE_ENABLED: {{ .Values.config.featureEnabled | toString | quote }}
  LOG_LEVEL: {{ .Values.config.logLevel | quote }}
\`\`\`

ConfigMaps are for **nonsecret** values. Never template real credentials into them.

## 11. Deployment template

\`charts/demo-app/templates/deployment.yaml\`:

\`\`\`gotemplate
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "demo-app.fullname" . }}
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  revisionHistoryLimit: 5
  minReadySeconds: {{ .Values.deployment.minReadySeconds }}
  progressDeadlineSeconds: {{ .Values.deployment.progressDeadlineSeconds }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: {{ .Values.deployment.maxSurge }}
      maxUnavailable: {{ .Values.deployment.maxUnavailable }}
  selector:
    matchLabels:
      {{- include "demo-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "demo-app.selectorLabels" . | nindent 8 }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
    spec:
      serviceAccountName: {{ include "demo-app.serviceAccountName" . }}
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: {{ .Values.securityContext.runAsUser }}
        runAsGroup: {{ .Values.securityContext.runAsGroup }}
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: demo-app
          image: {{ printf "%s@%s" .Values.image.repository .Values.image.digest | quote }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
          envFrom:
            - configMapRef:
                name: {{ include "demo-app.fullname" . }}-config
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            failureThreshold: {{ .Values.probes.startup.failureThreshold }}
            periodSeconds: {{ .Values.probes.startup.periodSeconds }}
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
            timeoutSeconds: {{ .Values.probes.readiness.timeoutSeconds }}
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
            timeoutSeconds: {{ .Values.probes.liveness.timeoutSeconds }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
\`\`\`

The \`checksum/config\` annotation changes when the rendered ConfigMap changes, causing a new Deployment revision. This is important because environment variables do not refresh in existing Pods when a ConfigMap changes.

**HPA caveat:** Later chapters will update this template to avoid independent \`spec.replicas\` management when HPA is enabled.

## 12. Service template

\`charts/demo-app/templates/service.yaml\`:

\`\`\`gotemplate
apiVersion: v1
kind: Service
metadata:
  name: {{ include "demo-app.fullname" . }}
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    {{- include "demo-app.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
\`\`\`

The Service selects the same labels as the Deployment Pod template. A mismatch yields no ready backends.

## 13. Environment-specific values

Create:

\`\`\`text
environments/
├── dev/values.yaml
├── test/values.yaml
├── staging/values.yaml
└── prod/values.yaml
\`\`\`

\`environments/dev/values.yaml\`:

\`\`\`yaml
replicaCount: 2
config:
  appEnv: dev
  featureEnabled: true
  logLevel: debug
\`\`\`

\`environments/test/values.yaml\`:

\`\`\`yaml
replicaCount: 2
config:
  appEnv: test
  featureEnabled: false
  logLevel: info
\`\`\`

\`environments/staging/values.yaml\`:

\`\`\`yaml
replicaCount: 3
config:
  appEnv: staging
  featureEnabled: false
  logLevel: info
\`\`\`

\`environments/prod/values.yaml\`:

\`\`\`yaml
replicaCount: 3
config:
  appEnv: prod
  featureEnabled: false
  logLevel: warn
\`\`\`

These overlays do not override the synthetic default digest. **Before deploying**, set \`image.digest\` to the same actual verified digest in the approved values for each promoted environment. Never store secret values in overlays.

## 14. Validate the chart locally

From the repository root:

\`\`\`bash
helm lint charts/demo-app
helm template demo-app charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/values.yaml > rendered-dev.yaml
helm template demo-app charts/demo-app \
  --namespace demo-test \
  -f environments/test/values.yaml > rendered-test.yaml
helm template demo-app charts/demo-app \
  --namespace demo-staging \
  -f environments/staging/values.yaml > rendered-staging.yaml
helm template demo-app charts/demo-app \
  --namespace demo-prod \
  -f environments/prod/values.yaml > rendered-prod.yaml
\`\`\`

Check the generated manifests for:

- Correct Deployment/Service selector alignment.
- Non-root security context and resource budgets.
- ConfigMap checksum annotation.
- Correct environment configuration.
- Digest-based image reference.
- Absence of plaintext secrets.

**Important:** \`helm template --namespace\` sets the Helm release namespace, but Kubernetes resource YAML may not contain \`metadata.namespace\` unless templates explicitly emit it. Argo CD destinations and/or the apply namespace determine where namespaced objects are created. Do not assume rendered manifests automatically carry a namespace field.

## 15. Values precedence and type behavior

Helm merges chart defaults and supplied values. A typical CLI precedence order is:

1. \`values.yaml\` chart defaults.
2. Values files supplied with \`-f\`, in order; later files take precedence.
3. \`--set\`/\`--set-string\` overrides, with later overrides taking precedence.

For example:

\`\`\`bash
helm template demo-app charts/demo-app \
  -f environments/dev/values.yaml \
  --set replicaCount=1
\`\`\`

Avoid unreviewed command-line overrides in GitOps because they make the release harder to audit. Prefer explicit values files committed to Git.

## 16. JSON schema validation

\`charts/demo-app/values.schema.json\`:

\`\`\`json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "replicaCount", "service", "config"],
  "properties": {
    "replicaCount": {"type": "integer", "minimum": 1, "maximum": 20},
    "image": {
      "type": "object",
      "required": ["repository", "digest"],
      "properties": {
        "repository": {"type": "string", "minLength": 1},
        "digest": {
          "type": "string",
          "pattern": "^sha256:[a-f0-9]{64}$"
        }
      }
    },
    "service": {
      "type": "object",
      "properties": {
        "type": {"enum": ["ClusterIP"]},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "targetPort": {"type": "integer", "minimum": 1, "maximum": 65535}
      }
    },
    "config": {
      "type": "object",
      "properties": {
        "appEnv": {"type": "string"},
        "featureEnabled": {"type": "boolean"},
        "logLevel": {"enum": ["debug", "info", "warn", "error"]}
      }
    }
  }
}
\`\`\`

This schema validates digest **syntax**, not existence, registry authenticity or signer trust. Production validation must verify the actual OCI artifact and supply-chain evidence.

## 17. Optional Helm installation lab

Only if you have explicit authorization and have replaced the synthetic digest with a real one:

\`\`\`bash
kubectl config current-context
kubectl auth can-i create deployments -n demo-dev
helm upgrade --install demo-app charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/values.yaml \
  --wait --timeout 5m
kubectl get deployments,services,pods -n demo-dev
helm status demo-app -n demo-dev
helm history demo-app -n demo-dev
\`\`\`

**Do not run this** if Argo CD already owns the same resources. This optional lab is for a separate disposable Helm-managed release.

For a Helm-managed release only, \`helm rollback demo-app <REVISION> -n demo-dev\` can restore a previous Helm revision. For an Argo CD-managed Application, revert the desired-state Git commit instead.

## 18. GitLab CI validation

Example \`.gitlab-ci.yml\` job:

\`\`\`yaml
helm_lint_and_render:
  stage: validate
  image: registry.example.com/platform/helm@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - helm lint charts/demo-app
    - helm template demo-app charts/demo-app --namespace demo-dev -f environments/dev/values.yaml > rendered-dev.yaml
    - helm template demo-app charts/demo-app --namespace demo-test -f environments/test/values.yaml > rendered-test.yaml
    - helm template demo-app charts/demo-app --namespace demo-staging -f environments/staging/values.yaml > rendered-staging.yaml
    - helm template demo-app charts/demo-app --namespace demo-prod -f environments/prod/values.yaml > rendered-prod.yaml
  artifacts:
    paths:
      - rendered-*.yaml
    expire_in: 1 day
\`\`\`

This is a **template**: replace the tool image placeholder with an approved real digest and configure an appropriate GitLab runner. Rendering alone does not validate Kubernetes admission, registry availability, application health or policy compliance.

## 19. Failure-injection exercises

Perform these locally first:

| Test | Fault | Expected result | Recovery |
| --- | --- | --- | --- |
| A | Invalid image digest format | Schema validation failure | Restore valid digest syntax |
| B | Invalid replica count | Schema validation failure | Restore supported count |
| C | Unsupported Service type | Schema validation failure | Use ClusterIP |
| D | Wrong selector labels | Service endpoints missing in live lab | Restore helper consistency |
| E | Missing ConfigMap | Pod config error in live lab | Restore ConfigMap |
| F | ConfigMap changed | Deployment checksum changes | Validate rendered Pod template |
| G | Bad template indentation | Helm render/lint error | Fix template structure |
| H | Secret in values file | Security policy failure | Remove and rotate exposed secret |
| I | Two managers own resources | Drift/overwrite risk | Select Helm or Argo CD ownership |
| J | Unavailable image digest | Image pull failure in live lab | Restore approved digest |

Do not deliberately commit real secrets or inject failures into shared workloads.

## 20. Troubleshooting runbook

| Symptom | Likely cause | Check |
| --- | --- | --- |
| \`helm lint\` fails | Chart metadata, schema or templates | Lint output |
| \`helm template\` fails | Missing values or Go-template error | Render with \`--debug\` |
| Wrong environment setting | Values precedence/overlay | Rendered ConfigMap |
| No Service endpoints | Selector mismatch or unready Pods | EndpointSlices and Pod labels |
| ConfigMap changed but app stale | No Pod-template revision | Check checksum annotation |
| ImagePullBackOff | Invalid/unavailable digest or registry auth | Pod events and registry |
| Helm upgrade times out | Probes, scheduling or quota | Deployment conditions/events |
| Argo CD OutOfSync | Git desired/live drift | Application diff |
| Release history confusing | Mixed Helm and Argo CD ownership | Identify authoritative controller |
| Schema passes but image fails | Syntax validation is not registry verification | Verify digest/signature |

## 21. SRE rollback and recovery

For a **Helm-managed disposable release**:

1. Inspect \`helm history\`.
2. Confirm the previous chart revision and digest are retained.
3. Perform an authorized \`helm rollback\`.
4. Verify Pods, Service endpoints and user-facing SLIs.

For an **Argo CD-managed environment**:

1. Identify the last known-good Git commit and image digest.
2. Open a reviewed revert or approved emergency GitOps change.
3. Allow Argo CD to reconcile the chart output.
4. Verify Application sync/health, Deployment availability and SLIs.
5. Record incident timeline and follow-up actions.

Avoid manual changes that Argo CD will overwrite.

## 22. Operational metrics

Track chart rendering failures, Helm/Argo CD reconciliation errors, rollout duration, available replicas, image pull failures, config-driven restarts, Service endpoint readiness, error rate and p95/p99 latency. Set alerts from measured service objectives and real baselines.

## 23. Cleanup

For an independently Helm-managed disposable release:

\`\`\`bash
helm uninstall demo-app -n demo-dev
\`\`\`

Only uninstall if you created and own that release. For Argo CD-managed resources, remove or update desired state through reviewed GitOps changes. Do not delete shared namespaces.

## 24. Acceptance checklist

- [ ] Chart metadata, defaults, helpers and templates created.
- [ ] Deployment, Service, ConfigMap and ServiceAccount render correctly.
- [ ] Image reference uses digest syntax.
- [ ] Values schema rejects malformed inputs.
- [ ] Dev/Test/Staging/Prod overlays render from one chart.
- [ ] ConfigMap changes alter the Pod-template checksum.
- [ ] Non-root runtime, probes and resources are present.
- [ ] No plaintext secrets are stored in chart values.
- [ ] GitLab CI lint/render validation designed.
- [ ] Helm vs Argo CD ownership and rollback explained.
- [ ] Optional installation used only a real verified digest.
- [ ] Failure-injection results and recovery documented.

## 25. Evidence worksheet

\`\`\`text
CHAPTER 031 — HELM CHART FUNDAMENTALS
Date:
Repository / source commit:
Helm version:
Chart name / version:
Approved image digest:
helm lint result:
Dev render result:
Test render result:
Staging render result:
Production render result:
Values schema negative tests:
ConfigMap checksum before/after:
Deployment selector / Service selector:
Security context and resources:
Optional Helm release / namespace:
GitOps ownership decision:
Rollback plan:
Reviewer:
Open risks and owners:
\`\`\`

## 26. Knowledge checks

1. What is the difference between a chart and a Helm release?
2. Why does Argo CD typically not use Helm release history?
3. Why must image digest pinning be enforced separately from chart versioning?
4. How does Helm values precedence work?
5. Why can a ConfigMap change require a Deployment revision?
6. Why should selector labels remain stable?
7. What does a values schema validate, and what does it not validate?
8. Why should a single chart serve four environment namespaces?

## 27. Completion

**Pass:** You can render and validate one reusable, secure Helm chart for four namespaces, demonstrate schema and configuration-rollout behavior, and document GitLab CI and Argo CD ownership boundaries.

**Next: Chapter 032 — Advanced Helm Templates, Functions, Helpers and Values Schema Design.**
