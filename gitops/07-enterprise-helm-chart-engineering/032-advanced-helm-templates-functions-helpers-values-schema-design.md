# Chapter 032 — Advanced Helm Templates, Functions, Helpers and Values Schema Design

**Part 07 — Enterprise Helm Chart Engineering** | **Chapter 032 / 100**  
**Audience:** Platform engineers, Kubernetes administrators and SREs  
**Prerequisite:** Chapter 031's reusable \`charts/demo-app\` Helm chart  
**Operating model:** GitLab CI validates; Argo CD reconciles. Dev, Test, Staging and Production are separate namespaces within the same Kubernetes cluster.

> **Lab safety:** Use generic names, synthetic nonsecret configuration and an approved disposable namespace. Rendering is offline. Never store credentials in Helm values, and never install the sample image placeholder. Pin and verify real image digests for cluster testing.

## 1. Objectives

After this chapter, you can:

1. Explain Helm Go-template context, scopes, pipelines, functions and whitespace control.
2. Build reusable named helpers for stable labels, names and ServiceAccounts.
3. Use \`include\`, \`required\`, \`default\`, \`quote\`, \`toYaml\`, \`nindent\`, \`dict\`, \`list\`, \`range\` and \`with\` safely.
4. Understand values merge precedence, maps vs lists, \`null\` and type coercion.
5. Enforce value contracts with \`values.schema.json\` and template-level guards.
6. Add optional HPA, PDB and NetworkPolicy templates without unsafe defaults.
7. Validate four environment overlays and detect selector/configuration drift.
8. Test negative cases and document release troubleshooting and recovery.

## 2. Helm rendering pipeline

\`\`\`text
Chart.yaml + values.yaml + values.schema.json
                |
      -f environment overlay
                |
        CLI / Argo CD parameters
                |
       Go templates + Sprig
                |
         Kubernetes YAML
                |
   lint / schema / policy / API validation
                |
     GitOps-reviewed deployment
\`\`\`

Helm template functions generate text, not validated Kubernetes objects. A chart that renders successfully can still violate admission policy or fail at runtime.

## 3. Lab directory

Extend Chapter 031's chart:

\`\`\`text
charts/demo-app/
├── Chart.yaml
├── values.yaml
├── values.schema.json
└── templates/
    ├── _helpers.tpl
    ├── configmap.yaml
    ├── deployment.yaml
    ├── service.yaml
    ├── serviceaccount.yaml
    ├── hpa.yaml
    ├── pdb.yaml
    └── networkpolicy.yaml
environments/
├── dev/values.yaml
├── test/values.yaml
├── staging/values.yaml
└── prod/values.yaml
tests/
└── negative-values/
    ├── invalid-replicas.yaml
    ├── invalid-image.yaml
    └── invalid-network.yaml
\`\`\`

Use the Chapter 031 chart as the starting point; the changes below are complete replacement blocks for the files explicitly named.

## 4. Understand template context and scope

Helm supplies \`.Values\`, \`.Chart\`, \`.Release\`, \`.Capabilities\`, \`.Files\` and \`.Template\`. Inside \`range\` and \`with\`, the meaning of \`.\` changes. Use \`$\` for the root context.

Example:

\`\`\`gotemplate
{{- range $name, $value := .Values.extraLabels }}
{{ $name }}: {{ $value | quote }}
{{- end }}
\`\`\`

Inside nested scopes:

\`\`\`gotemplate
{{- with .Values.config }}
APP_ENV: {{ .appEnv | quote }}
RELEASE_NAME: {{ $.Release.Name | quote }}
{{- end }}
\`\`\`

Do not use untrusted values as arbitrary template source with \`tpl\` unless your security design explicitly permits template execution. Treat chart inputs as code-adjacent.

## 5. Reusable helper templates

Replace \`charts/demo-app/templates/_helpers.tpl\`:

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

{{- define "demo-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "demo-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "demo-app.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
{{- include "demo-app.selectorLabels" . }}
{{- end -}}

{{- define "demo-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "demo-app.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- required "serviceAccount.name must be set when create=false" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "demo-app.image" -}}
{{- printf "%s@%s" (required "image.repository is required" .Values.image.repository) (required "image.digest is required" .Values.image.digest) -}}
{{- end -}}

{{- define "demo-app.configChecksum" -}}
{{- include (print $.Template.BasePath "/configmap.yaml") . | sha256sum -}}
{{- end -}}
\`\`\`

**SRE design:** Selector labels must be stable between revisions; labels such as chart version belong in metadata but **not** immutable Deployment selectors. Reuse a single helper for Service selectors and Pod labels.

## 6. Expanded values defaults

Merge these fields into \`charts/demo-app/values.yaml\` from Chapter 031, preserving existing \`image\`, \`service\`, \`config\`, \`resources\`, \`probes\`, \`deployment\`, \`securityContext\` and \`serviceAccount\` values:

\`\`\`yaml
extraLabels: {}

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
  scaleDownStabilizationSeconds: 300

podDisruptionBudget:
  enabled: false
  minAvailable: 1

networkPolicy:
  enabled: false
  allowSameNamespaceIngress: true
\`\`\`

Keep \`image.digest\` as a synthetic 64-character lowercase hex digest only for offline rendering; replace with a real verified digest before installation.

## 7. ConfigMap and controlled rollout

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

The ConfigMap contains **nonsecret** values only. The Deployment's checksum annotation must be computed from the rendered ConfigMap to trigger a new Pod template when environment-variable values change.

## 8. Deployment template with HPA-aware replicas

Replace \`charts/demo-app/templates/deployment.yaml\`:

\`\`\`gotemplate
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "demo-app.fullname" . }}
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
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
        {{- with .Values.extraLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      annotations:
        checksum/config: {{ include "demo-app.configChecksum" . }}
    spec:
      serviceAccountName: {{ include "demo-app.serviceAccountName" . }}
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: {{ .Values.securityContext.runAsUser }}
        runAsGroup: {{ .Values.securityContext.runAsGroup }}
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: demo-app
          image: {{ include "demo-app.image" . | quote }}
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

When HPA is enabled, \`spec.replicas\` is omitted to reduce competing ownership. On an existing Deployment, changing field ownership requires care: omitting the field does not automatically prove that all prior field managers relinquished it. Inspect server-side apply/Argo CD behavior before production adoption.

**Guardrail:** \`extraLabels\` must not override \`app.kubernetes.io/name\` or \`app.kubernetes.io/instance\`; add policy/schema checks for this in later chapters.

## 9. Optional HPA template

\`charts/demo-app/templates/hpa.yaml\`:

\`\`\`gotemplate
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "demo-app.fullname" . }}
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "demo-app.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: {{ .Values.autoscaling.scaleDownStabilizationSeconds }}
{{- end }}
\`\`\`

HPA requires the metrics API and meaningful CPU requests. A successful Helm render does not establish that HPA can scale.

## 10. Optional PDB template

\`charts/demo-app/templates/pdb.yaml\`:

\`\`\`gotemplate
{{- if .Values.podDisruptionBudget.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "demo-app.fullname" . }}
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.podDisruptionBudget.minAvailable }}
  selector:
    matchLabels:
      {{- include "demo-app.selectorLabels" . | nindent 6 }}
{{- end }}
\`\`\`

Choose \`minAvailable\` based on minimum healthy capacity and maintenance behavior. PDBs govern voluntary evictions, not involuntary node loss.

## 11. Optional NetworkPolicy template

\`charts/demo-app/templates/networkpolicy.yaml\`:

\`\`\`gotemplate
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "demo-app.fullname" . }}-ingress
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "demo-app.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
  ingress:
    {{- if .Values.networkPolicy.allowSameNamespaceIngress }}
    - from:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: {{ .Values.service.targetPort }}
    {{- else }}
    []
    {{- end }}
{{- end }}
\`\`\`

This optional policy is deliberately **off by default**. When enabled, it allows only same-namespace Pod ingress (or no ingress when disabled by its subsetting). It can block ingress controllers and monitoring Pods in other namespaces. NetworkPolicy enforcement depends on the CNI. Plan and test real traffic flows before enabling.

## 12. Strengthen values.schema.json

Replace \`charts/demo-app/values.schema.json\` with:

\`\`\`json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "replicaCount", "service", "config", "autoscaling", "podDisruptionBudget", "networkPolicy"],
  "properties": {
    "replicaCount": {"type": "integer", "minimum": 1, "maximum": 20},
    "image": {
      "type": "object",
      "required": ["repository", "digest"],
      "properties": {
        "repository": {"type": "string", "minLength": 1},
        "digest": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"}
      }
    },
    "service": {
      "type": "object",
      "required": ["type", "port", "targetPort"],
      "properties": {
        "type": {"enum": ["ClusterIP"]},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "targetPort": {"type": "integer", "minimum": 1, "maximum": 65535}
      }
    },
    "config": {
      "type": "object",
      "required": ["appEnv", "featureEnabled", "logLevel"],
      "properties": {
        "appEnv": {"enum": ["dev", "test", "staging", "prod"]},
        "featureEnabled": {"type": "boolean"},
        "logLevel": {"enum": ["debug", "info", "warn", "error"]}
      }
    },
    "autoscaling": {
      "type": "object",
      "required": ["enabled", "minReplicas", "maxReplicas", "targetCPUUtilizationPercentage"],
      "properties": {
        "enabled": {"type": "boolean"},
        "minReplicas": {"type": "integer", "minimum": 1, "maximum": 20},
        "maxReplicas": {"type": "integer", "minimum": 1, "maximum": 50},
        "targetCPUUtilizationPercentage": {"type": "integer", "minimum": 1, "maximum": 100},
        "scaleDownStabilizationSeconds": {"type": "integer", "minimum": 0, "maximum": 3600}
      }
    },
    "podDisruptionBudget": {
      "type": "object",
      "required": ["enabled", "minAvailable"],
      "properties": {
        "enabled": {"type": "boolean"},
        "minAvailable": {"type": "integer", "minimum": 0, "maximum": 20}
      }
    },
    "networkPolicy": {
      "type": "object",
      "required": ["enabled", "allowSameNamespaceIngress"],
      "properties": {
        "enabled": {"type": "boolean"},
        "allowSameNamespaceIngress": {"type": "boolean"}
      }
    },
    "extraLabels": {"type": "object", "additionalProperties": {"type": "string"}}
  }
}
\`\`\`

**Limitations:** JSON Schema checks individual types and ranges but does not automatically enforce cross-field invariants such as \`minReplicas <= maxReplicas\` or prevent reserved selector label overrides. Add explicit policy tests for those.

## 13. Cross-field validation guards

Add to the **top** of \`charts/demo-app/templates/deployment.yaml\`, before \`apiVersion\`:

\`\`\`gotemplate
{{- if and .Values.autoscaling.enabled (gt (int .Values.autoscaling.minReplicas) (int .Values.autoscaling.maxReplicas)) -}}
{{- fail "autoscaling.minReplicas must be <= autoscaling.maxReplicas" -}}
{{- end -}}
{{- if and .Values.podDisruptionBudget.enabled (not .Values.autoscaling.enabled) (gt (int .Values.podDisruptionBudget.minAvailable) (int .Values.replicaCount)) -}}
{{- fail "PDB minAvailable cannot exceed replicaCount when autoscaling is disabled" -}}
{{- end -}}
{{- range $key, $_ := .Values.extraLabels -}}
{{- if or (eq $key "app.kubernetes.io/name") (eq $key "app.kubernetes.io/instance") -}}
{{- fail (printf "extraLabels cannot override reserved selector label %s" $key) -}}
{{- end -}}
{{- end -}}
\`\`\`

The HPA-enabled case still requires a capacity/PDB compatibility review. Helm template guards are a supplement to, not a replacement for, policy-as-code and admission controls.

## 14. Environment overlays

\`environments/dev/values.yaml\`:

\`\`\`yaml
replicaCount: 2
config:
  appEnv: dev
  featureEnabled: true
  logLevel: debug
autoscaling:
  enabled: false
podDisruptionBudget:
  enabled: false
networkPolicy:
  enabled: false
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
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 6
podDisruptionBudget:
  enabled: true
  minAvailable: 2
\`\`\`

\`environments/prod/values.yaml\`:

\`\`\`yaml
replicaCount: 3
config:
  appEnv: prod
  featureEnabled: false
  logLevel: warn
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 8
podDisruptionBudget:
  enabled: true
  minAvailable: 2
\`\`\`

These are examples for **offline rendering**. Do not treat the shared-cluster production namespace as a sufficient isolation boundary for critical workloads.

## 15. Render and inspect all environments

\`\`\`bash
helm lint charts/demo-app
helm template demo-app charts/demo-app --namespace demo-dev \
  -f environments/dev/values.yaml > rendered-dev.yaml
helm template demo-app charts/demo-app --namespace demo-test \
  -f environments/test/values.yaml > rendered-test.yaml
helm template demo-app charts/demo-app --namespace demo-staging \
  -f environments/staging/values.yaml > rendered-staging.yaml
helm template demo-app charts/demo-app --namespace demo-prod \
  -f environments/prod/values.yaml > rendered-prod.yaml
\`\`\`

Expected: Dev/Test render Deployment, ConfigMap, Service and ServiceAccount; Staging/Prod additionally render HPA and PDB. NetworkPolicy is absent until explicitly enabled.

Inspect the rendered YAML for:
- Identical selector labels across Deployment/Service/PDB.
- Non-root security context, requests, limits and probes.
- No \`spec.replicas\` when HPA is enabled.
- Correct environment configuration.
- Digest-based image reference.
- ConfigMap checksum annotation.
- No plaintext secrets.

## 16. Negative tests

Create \`tests/negative-values/invalid-replicas.yaml\`:

\`\`\`yaml
replicaCount: 0
\`\`\`

Create \`tests/negative-values/invalid-image.yaml\`:

\`\`\`yaml
image:
  digest: latest
\`\`\`

Create \`tests/negative-values/invalid-network.yaml\`:

\`\`\`yaml
networkPolicy:
  enabled: "yes"
\`\`\`

Run each against the defaults and expect **nonzero exit status**:

\`\`\`bash
helm template demo-app charts/demo-app -f tests/negative-values/invalid-replicas.yaml
helm template demo-app charts/demo-app -f tests/negative-values/invalid-image.yaml
helm template demo-app charts/demo-app -f tests/negative-values/invalid-network.yaml
\`\`\`

A negative test **passes** when Helm rejects the invalid values. For automated tests, capture the exit status and assert it is nonzero; do not count a printed error as success without checking exit status.

Additional tests:

\`\`\`bash
helm template demo-app charts/demo-app \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=8 \
  --set autoscaling.maxReplicas=2

helm template demo-app charts/demo-app \
  --set extraLabels.app\\.kubernetes\\.io/name=overridden
\`\`\`

The second CLI command illustrates why escaping dotted keys is error-prone; for reliable testing, prefer a small YAML override file containing the literal key. A rejected render is expected when the reserved selector label is overridden.

## 17. Helm values precedence pitfalls

Typical precedence: chart defaults, \`-f\` files in supplied order, then CLI overrides. Later files/overrides win.

- Maps are merged by key; lists are generally replaced rather than merged item-by-item.
- YAML \`true\` and \`"true"\` have different types.
- \`--set\` may infer numbers/booleans; use \`--set-string\` when strings are required.
- A \`null\` value can remove an inherited key and break a template.
- \`default\` treats some values, including \`false\` and \`0\`, as empty; use explicit conditionals when those are meaningful.

Avoid production-only \`--set\` overrides outside version-controlled GitOps state.

## 18. GitLab CI validation workflow

Illustrative \`.gitlab-ci.yml\` job:

\`\`\`yaml
helm_advanced_validation:
  stage: validate
  image: registry.example.com/platform/helm@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - helm lint charts/demo-app
    - helm template demo-app charts/demo-app --namespace demo-dev -f environments/dev/values.yaml > dev.yaml
    - helm template demo-app charts/demo-app --namespace demo-test -f environments/test/values.yaml > test.yaml
    - helm template demo-app charts/demo-app --namespace demo-staging -f environments/staging/values.yaml > staging.yaml
    - helm template demo-app charts/demo-app --namespace demo-prod -f environments/prod/values.yaml > prod.yaml
  artifacts:
    paths:
      - dev.yaml
      - test.yaml
      - staging.yaml
      - prod.yaml
    expire_in: 1 day
\`\`\`

Replace the tool-image placeholder with an approved real digest. Add policy-as-code and schema validation to the production pipeline; rendering alone is not enough. Ensure artifacts contain **no secrets**.

## 19. GitOps integration and field ownership

Argo CD renders the chart from reviewed Git state. It normally does not create Helm's release history, so use a **Git revert** for durable rollback.

When HPA is enabled:
- Omit Deployment \`spec.replicas\` from the chart output.
- Review server-side apply ownership and Argo CD diff behavior.
- Verify HPA is not fighting another controller.
- Check resource quota and surge capacity.

Use separate Argo CD Applications and namespaces for Dev/Test/Staging/Prod. Promote one verified image digest; do not rebuild independently for each environment.

## 20. Troubleshooting runbook

| Symptom | Likely cause | SRE response |
| --- | --- | --- |
| Template parse error | Bad Go-template delimiters or whitespace | \`helm template --debug\` |
| YAML indentation error | Incorrect \`nindent\`/trim markers | Inspect rendered YAML |
| Missing key | Wrong scope inside \`with\`/\`range\` | Use \`$\` root or pass context |
| Schema failure | Invalid type/range | Correct values file |
| HPA render missing | \`autoscaling.enabled=false\` | Inspect overlay |
| PDB blocks maintenance | \`minAvailable\` too strict | Review replica count and policy |
| Service no endpoints | Selector mismatch | Compare helper outputs |
| ConfigMap update stale | Missing checksum or rollout | Inspect Pod template revision |
| Network outage after policy | Incorrect allowed flows | Revert policy, validate CNI |
| Argo CD drift | Competing managers or manual changes | Restore Git ownership |
| Image pull failure | Invalid digest/registry permissions | Verify OCI artifact and events |

## 21. Operational recovery

1. Identify the changed chart version, values file and GitOps commit.
2. Render the last known-good configuration.
3. Compare Deployment selectors, image digests, resources and policies.
4. Stop further promotion.
5. Revert the approved GitOps commit and allow Argo CD to reconcile.
6. Verify ready Pods, EndpointSlices, application SLOs and HPA/PDB state.
7. Record incident evidence and preventive checks.

For a standalone disposable Helm release (not Argo CD-managed), \`helm history\` and \`helm rollback\` may be used. Never mix independent managers for the same Kubernetes objects.

## 22. Acceptance checklist

- [ ] Reusable helper templates render stable names and labels.
- [ ] ConfigMap checksum changes on configuration update.
- [ ] HPA template is conditional and omits Deployment replicas.
- [ ] PDB and NetworkPolicy are disabled unless configured.
- [ ] JSON schema rejects invalid digest, replica count and types.
- [ ] Cross-field guards reject HPA min/max mismatch.
- [ ] Reserved selector labels cannot be overridden.
- [ ] All four environment overlays render correctly.
- [ ] No secret values are committed or rendered.
- [ ] GitLab CI validation design is documented.
- [ ] Argo CD field ownership and rollback behavior understood.
- [ ] Negative tests and recovery results recorded.

## 23. Evidence worksheet

\`\`\`text
CHAPTER 032 — ADVANCED HELM TEMPLATES AND SCHEMA
Date:
Chart version:
Helm version:
Source commit:
Rendered Dev/Test/Staging/Prod:
Selector label consistency:
ConfigMap checksum before/after:
HPA enabled/replicas ownership:
PDB minAvailable review:
NetworkPolicy ingress-flow review:
JSON schema negative tests:
Cross-field guard negative tests:
Image digest verification status:
CI validation results:
GitOps rollback commit:
Reviewer:
Open risks and owners:
\`\`\`

## 24. Knowledge checks

1. What is the difference between \`include\` and a direct template definition?
2. Why is \`$\` useful inside \`range\` and \`with\`?
3. Why must selector labels remain stable across releases?
4. What problem does a ConfigMap checksum solve?
5. Why should HPA-enabled Deployments avoid independent replica management?
6. Which invariants cannot be enforced by the provided JSON schema alone?
7. Why is \`default\` risky for boolean false and numeric zero?
8. Why must a NetworkPolicy template be disabled until required traffic flows are tested?

## 25. Completion

**Pass:** You render and validate a reusable enterprise chart with optional autoscaling and disruption controls, schema-enforced values, negative tests and GitOps-compatible ownership.

**Next: Chapter 033 — Helm Dependencies, OCI Registries, Chart Packaging and Supply-Chain Security.**
