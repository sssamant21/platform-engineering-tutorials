# Chapter 027 — Kubernetes Configuration Management, Secrets and Environment Isolation for GitOps

**Part 06 — Kubernetes Deployment Fundamentals** | **Chapter 027 / 100**  
**Audience:** SRE, infrastructure and platform engineers  
**Tools:** Kubernetes, kubectl, GitLab CI, Helm (preview), Argo CD (preview), External Secrets Operator (optional)  
**Reference:** One shared cluster with four namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.

> **Safety:** This lab uses only generic names and a disposable \`demo-dev\` namespace. Never commit live credentials to Git, print secret values in CI logs, or assume a namespace alone is a strong security boundary. Use a separately governed production cluster when workload risk warrants it.

## 1. Learning objectives

By the end, you can:

1. Distinguish ConfigMaps, Kubernetes Secrets, external secret managers and environment variables.
2. Separate nonsecret configuration from sensitive data in GitOps repositories.
3. Manage configuration per environment without rebuilding application images.
4. Apply least-privilege RBAC, resource quotas, Pod Security Admission and NetworkPolicy.
5. Understand secret encryption at rest, RBAC exposure and the limits of base64 encoding.
6. Safely roll out ConfigMap and Secret changes with predictable Pod behavior.
7. Use External Secrets Operator (ESO) as an example of external secret reconciliation.
8. Diagnose missing configuration, denied access, stale values and cross-namespace exposure.
9. Design an auditable GitLab → GitOps → Argo CD promotion model.

## 2. Configuration architecture

\`\`\`text
GitLab CI
  |
  +--> build and scan image once -> registry@sha256:...
  |
  v
GitOps repository (reviewed)
  |
  +--> charts/demo-app/
  +--> environments/dev/values.yaml
  +--> environments/test/values.yaml
  +--> environments/staging/values.yaml
  +--> environments/prod/values.yaml
  |
  +--> nonsecret ConfigMaps / policy manifests
  +--> ExternalSecret references (NOT secret values)
  |
  v
Argo CD per-environment Application
  |
  +--> demo-dev
  +--> demo-test
  +--> demo-staging
  +--> demo-prod
           |
     External Secrets Operator
           |
    approved secret provider
\`\`\`

**Core distinction:** A GitOps repository should describe desired configuration and secret *references*. Sensitive values should be stored in a dedicated secret manager and made available using an approved mechanism.

## 3. Configuration mechanisms and tradeoffs

| Mechanism | Suitable for | Limitations |
| --- | --- | --- |
| ConfigMap | Feature flags, log level, nonsecret endpoints | Not confidential |
| Secret | Kubernetes API object containing sensitive values | Base64 is not encryption; RBAC and etcd encryption required |
| Environment variables | Simple process configuration | Changes require Pod restart; process visibility risks |
| Mounted ConfigMap volume | Files and dynamic nonsecret config | Updates eventually propagate; app must reload |
| Mounted Secret volume | Secret files | Rotation propagation and application reload must be handled |
| External Secrets Operator | Sync from cloud/vault secret manager | Adds controller, IAM and availability dependencies |
| CSI Secrets Store | Provider-backed mounted secrets | Driver/provider support and rotation behavior vary |
| Helm values | Environment-specific template inputs | Do not put plaintext secrets in Git |

A Kubernetes Secret object can still be read by authorized API clients and, depending on access, by workloads and nodes. Encryption at rest does not replace least-privilege access.

## 4. Hands-on lab prerequisites

- An authorized disposable Kubernetes cluster or \`demo-dev\` namespace.
- \`kubectl\` access to create ConfigMaps, Deployments and Services.
- A verified immutable \`demo-app\` image digest from Chapter 026.
- Permission to inspect namespace policies.
- No production secrets.

Validate context and permissions:

\`\`\`bash
kubectl config current-context
kubectl auth can-i create configmaps -n demo-dev
kubectl auth can-i create deployments -n demo-dev
kubectl auth can-i get secrets -n demo-dev
\`\`\`

The last command is a permission **check**, not an instruction to grant secret access. Lack of secret read permission is expected for many operators.

## 5. Lab A — ConfigMap-driven application configuration

For a fully executable configuration lab, use a small Python application that reads nonsecret environment variables.

Create \`src/server.py\`:

\`\`\`python
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


def config():
    return {
        "environment": os.getenv("APP_ENV", "unknown"),
        "feature_enabled": os.getenv("FEATURE_ENABLED", "false").lower() == "true",
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            code, body = 200, {"status": "ok"}
        elif self.path == "/config":
            code, body = 200, config()
        else:
            code, body = 404, {"error": "not found"}
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
\`\`\`

Create empty \`src/__init__.py\`. Build and publish this training image using the secure build procedure from Chapter 021. **Record its real digest.** Do not use the Chapter 026 image if it lacks the \`/config\` endpoint.

### ConfigMap

\`k8s/configmap.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-app-config
  namespace: demo-dev
data:
  APP_ENV: dev
  FEATURE_ENABLED: "false"
  LOG_LEVEL: info
\`\`\`

Apply:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/configmap.yaml
kubectl apply -f k8s/configmap.yaml
kubectl describe configmap demo-app-config -n demo-dev
\`\`\`

**Do not place secrets in this ConfigMap.**

### Deployment

\`k8s/deployment.yaml\`:

\`\`\`yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-app
  template:
    metadata:
      labels:
        app: demo-app
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: demo-app
          image: registry.example.com/training/demo-app@sha256:REPLACE_WITH_REAL_DIGEST
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          envFrom:
            - configMapRef:
                name: demo-app-config
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 256Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
\`\`\`

Replace the image placeholder with the **real digest** from your authorized registry.

\`k8s/service.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  selector:
    app: demo-app
  ports:
    - name: http
      port: 80
      targetPort: http
  type: ClusterIP
\`\`\`

Apply and verify:

\`\`\`bash
kubectl apply --dry-run=server -f k8s/deployment.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/demo-app -n demo-dev --timeout=180s
kubectl port-forward -n demo-dev service/demo-app 8080:80
\`\`\`

In a second terminal:

\`\`\`bash
curl --fail --silent http://127.0.0.1:8080/config
\`\`\`

Expected:

\`\`\`json
{"environment": "dev", "feature_enabled": false}
\`\`\`

Stop port-forward when finished.

## 6. Lab B — Configuration change and restart semantics

Change \`FEATURE_ENABLED\` to \`"true"\` in \`k8s/configmap.yaml\`:

\`\`\`bash
kubectl apply -f k8s/configmap.yaml
\`\`\`

**Important:** Existing Pods do **not** automatically refresh environment variables sourced from a ConfigMap. Restart the Deployment in this manual lab:

\`\`\`bash
kubectl rollout restart deployment/demo-app -n demo-dev
kubectl rollout status deployment/demo-app -n demo-dev --timeout=180s
\`\`\`

Recheck \`/config\`; expected \`feature_enabled: true\`.

For GitOps, avoid ad hoc restarts as the steady-state release mechanism. Prefer versioned ConfigMap names or a reviewed checksum annotation in the Pod template so configuration changes produce a new Deployment revision. Argo CD will otherwise reconcile the ConfigMap but may leave existing environment-variable values unchanged.

## 7. Secrets: safe handling and limitations

Kubernetes Secrets are **not** encrypted merely because their \`data\` fields are base64 encoded. Require:

- Encryption at rest for Kubernetes API storage.
- Least-privilege RBAC for read/list/watch.
- Restricted access to Pods, nodes and backup data.
- External secret manager and workload identity where possible.
- Rotation, revocation, audit logging and secret-scanning policies.
- No secret values in Git, Helm values, CI artifacts or command history.

### Disposable Secret example — illustration only

\`\`\`yaml
apiVersion: v1
kind: Secret
metadata:
  name: demo-placeholder
  namespace: demo-dev
type: Opaque
stringData:
  EXAMPLE_TOKEN: "not-a-real-secret"
\`\`\`

**Do not commit actual secrets.** This object uses a harmless placeholder solely to illustrate the API schema. For real environments, prefer an external secret provider and approved synchronization mechanism.

Avoid \`kubectl get secret -o yaml\` in incident notes or CI logs, because encoded secret material can be exposed.

## 8. External Secrets Operator architecture

ESO typically reconciles an \`ExternalSecret\` resource, reads a secret through a configured \`SecretStore\` or \`ClusterSecretStore\`, and creates/updates a Kubernetes Secret.

\`\`\`text
ExternalSecret (namespace)
       |
       v
SecretStore / ClusterSecretStore
       |
       v
Cloud IAM / workload identity
       |
       v
AWS Secrets Manager / Azure Key Vault / Google Secret Manager / Vault
       |
       v
Kubernetes Secret -> Pod consumption
\`\`\`

Illustrative \`ExternalSecret\` (requires ESO CRDs, a configured \`SecretStore\` and an existing authorized provider key):

\`\`\`yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: demo-app-credentials
  namespace: demo-dev
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: SecretStore
    name: demo-secret-store
  target:
    name: demo-app-credentials
    creationPolicy: Owner
  data:
    - secretKey: API_TOKEN
      remoteRef:
        key: training/demo-app
        property: token
\`\`\`

**Not directly runnable:** ESO API versions, provider authentication and secret-store schema depend on installed operator version. Validate against the cluster CRDs before applying. Never point a disposable lab at production secret paths.

Check status without printing secret values:

\`\`\`bash
kubectl get externalsecret -n demo-dev
kubectl describe externalsecret demo-app-credentials -n demo-dev
kubectl get secret demo-app-credentials -n demo-dev \
  -o jsonpath='{.metadata.name}'
\`\`\`

The last command requires secret metadata read permission and should be skipped if not authorized.

## 9. Workload identity and least privilege

Prefer cloud workload identity over long-lived static cloud credentials:

| Platform | Typical identity approach |
| --- | --- |
| Amazon EKS | IRSA or EKS Pod Identity where supported |
| Azure AKS | Microsoft Entra Workload ID |
| Google GKE | Workload Identity Federation for GKE |

An identity should be bound to the specific namespace/service account and only the permitted secret paths or cloud resources. Cloud identity does not replace Kubernetes RBAC, and an application should not automatically receive Kubernetes API access.

### Dedicated ServiceAccount

\`\`\`yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-app
  namespace: demo-dev
automountServiceAccountToken: false
\`\`\`

If the application needs no Kubernetes API access, use \`automountServiceAccountToken: false\`. If a cloud workload identity integration requires a projected service-account token, configure that specific flow and audience explicitly; do not disable required identity token projection without testing the provider integration.

## 10. Environment isolation controls

Namespaces alone do not isolate nodes, the Kubernetes control plane, cluster-scoped CRDs, privileged workloads or all network traffic.

Recommended controls:

| Control | Why it matters |
| --- | --- |
| Namespace RBAC | Prevent unauthorized cross-environment API access |
| Pod Security Admission | Reject privileged workload configurations |
| NetworkPolicy | Restrict pod ingress and egress where CNI supports it |
| ResourceQuota / LimitRange | Prevent one namespace from consuming excessive resources |
| Dedicated node pools | Reduce noisy-neighbor effects; not a full trust boundary |
| Separate service accounts | Distinct workload and cloud identities |
| Secret-store scoping | Prevent cross-environment secret reads |
| GitOps AppProjects | Limit allowed repositories, destinations and resources |
| Admission policy | Enforce signed images, digest pinning and security context |
| Separate clusters | Stronger isolation for critical production risk |

### Example default-deny ingress and egress

\`k8s/networkpolicy.yaml\`:

\`\`\`yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: demo-dev
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
\`\`\`

**Warning:** Applying this policy may immediately break DNS, registry access, telemetry and application dependencies. Do **not** apply it until explicit allow policies for required flows are designed and tested. NetworkPolicy enforcement depends on the installed CNI. A default-deny policy is not a complete egress firewall.

## 11. GitOps repository layout

\`\`\`text
gitops/
├── charts/demo-app/
├── environments/
│   ├── dev/values.yaml
│   ├── test/values.yaml
│   ├── staging/values.yaml
│   └── prod/values.yaml
├── policies/
│   ├── namespaces/
│   ├── rbac/
│   └── network/
└── argocd/
    ├── demo-dev.yaml
    ├── demo-test.yaml
    ├── demo-staging.yaml
    └── demo-prod.yaml
\`\`\`

Example nonsecret values:

\`\`\`yaml
image:
  repository: registry.example.com/training/demo-app
  digest: sha256:REPLACE_WITH_REAL_DIGEST
config:
  appEnv: dev
  featureEnabled: false
  logLevel: info
externalSecret:
  storeName: demo-secret-store
  remoteKey: training/demo-app
\`\`\`

Do not include actual \`API_TOKEN\` values in GitOps values files.

## 12. GitLab CI configuration checks

GitLab CI should validate:

1. Environment values files exist and are syntactically valid.
2. The image reference uses an approved immutable digest.
3. Secret values are absent from committed manifests.
4. Helm renders the expected namespace and ConfigMap.
5. Security context, resource limits and probes are present.
6. RBAC, quota and network policies meet organization requirements.
7. A reviewed promotion MR changes only approved environment configuration.

**Example GitLab job (template):**

\`\`\`yaml
config_policy_check:
  stage: validate
  image: registry.example.com/platform/helm@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - helm lint charts/demo-app
    - helm template demo-app charts/demo-app -f environments/dev/values.yaml > rendered.yaml
\`\`\`

Replace the tool image with an actual approved digest and ensure the chart exists. This validates rendering only; use a separate policy engine and cluster admission tests to verify security requirements. Do not give MR validation jobs production cluster credentials.

## 13. Failure-injection lab

Perform only in the disposable namespace.

### Test A — Missing ConfigMap

Temporarily change \`configMapRef.name\` to a nonexistent ConfigMap.

**Expected:** Pod startup fails with a configuration error (for a required reference). Inspect events:

\`\`\`bash
kubectl describe pods -n demo-dev -l app=demo-app
kubectl get events -n demo-dev --sort-by=.lastTimestamp
\`\`\`

**Recovery:** Restore the correct ConfigMap name.

### Test B — Stale environment-variable value

Change ConfigMap data without restarting the Deployment.

**Expected:** Existing Pods continue using old environment-variable values.

**Recovery:** Trigger a reviewed Pod-template change or an authorized rollout restart.

### Test C — Invalid image digest

Use a nonexistent digest in a disposable manifest.

**Expected:** Image pull failure.

**Recovery:** Restore the approved digest and validate registry permissions.

### Test D — Secret store unavailable

In a disposable ESO test, use a nonexistent provider key.

**Expected:** \`ExternalSecret\` reports a synchronization failure; no valid new secret value is obtained.

**Recovery:** Restore the authorized key reference and verify controller status. Never paste secret values into logs.

### Test E — Cross-namespace access denied

Use \`kubectl auth can-i\` with an authorized test identity to check secret access in another environment.

**Expected:** Least-privilege identities cannot read unrelated environment secrets. Do not impersonate identities without authorization.

### Test F — Network isolation

Review the default-deny policy in dry run and plan DNS/egress exceptions. Apply only in an isolated namespace after allow rules are ready.

**Expected:** Required connectivity remains available while unauthorized paths are denied, as proven by connectivity tests—not merely by the presence of a NetworkPolicy object.

## 14. Troubleshooting runbook

| Symptom | Likely cause | Investigation |
| --- | --- | --- |
| \`CreateContainerConfigError\` | Missing ConfigMap/Secret key or reference | Pod events and references |
| App sees stale config | Env var snapshot | Pod revision and rollout |
| Secret sync fails | ESO provider auth/key/permissions | ExternalSecret status and controller logs |
| Unexpected secret access | Excessive RBAC or workload identity | RoleBindings and audit logs |
| Pod rejected | Restricted PSA or admission policy | Admission error and security context |
| Service cannot reach dependency | NetworkPolicy/DNS/egress | CNI and DNS flow tests |
| Config change not deployed | GitOps drift or missing template checksum | Argo CD diff and Pod template |
| ImagePullBackOff | Digest, registry auth or architecture | Pod events and registry |
| Namespace quota exceeded | Resource requests/limits | \`kubectl describe quota\` |
| Wrong environment configuration | Values overlay or Application destination | Rendered manifests and Argo CD spec |

## 15. Incident response and recovery

1. Identify affected namespace, Deployment, image digest and configuration revision.
2. Determine whether the incident is a configuration, secret, RBAC, network or image issue.
3. Stop unsafe promotions and preserve nonsecret audit evidence.
4. If credentials may be exposed, revoke and rotate through the authorized secret manager.
5. Revert incorrect GitOps configuration or restore an approved secret reference.
6. Confirm ESO sync status where applicable.
7. Verify Deployment rollout, ready endpoints, application health and SLOs.
8. Document root cause, time to recovery and preventive controls.

Do not store secret values in incident tickets, CI artifacts or screenshots.

## 16. Operational monitoring

Track:

- ConfigMap/Secret reference failures and Pod startup errors.
- ExternalSecret synchronization success, age and provider errors.
- Secret rotation completion and application reload behavior.
- RBAC denial/audit events and unexpected cross-namespace access.
- NetworkPolicy connectivity failures and DNS availability.
- Namespace quota utilization and Pod admission failures.
- Argo CD OutOfSync/Degraded states and config drift.
- Application error rate and latency after configuration changes.

Use observed baselines before setting alert thresholds.

## 17. Cleanup

For resources created solely for this lab:

\`\`\`bash
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
kubectl delete -f k8s/configmap.yaml --ignore-not-found
\`\`\`

Delete an ExternalSecret, Secret, NetworkPolicy or namespace only if you created it in an isolated lab and are explicitly authorized. If Argo CD owns the resources, clean up through a reviewed GitOps change.

## 18. Acceptance checklist

- [ ] Correct cluster context and namespace verified.
- [ ] Nonsecret ConfigMap deployed successfully.
- [ ] Application reads expected environment configuration.
- [ ] ConfigMap update and restart semantics demonstrated.
- [ ] Secret values kept out of Git and CI logs.
- [ ] Kubernetes Secret base64/encryption distinction understood.
- [ ] External secret architecture and identity requirements reviewed.
- [ ] Namespace RBAC, PSA, quotas and NetworkPolicy risks reviewed.
- [ ] Missing ConfigMap failure diagnosed and recovered.
- [ ] Environment-specific GitOps values design documented.
- [ ] No unauthorized production or cross-namespace changes made.

## 19. Evidence worksheet

\`\`\`text
CHAPTER 027 — CONFIGURATION, SECRETS AND ENVIRONMENT ISOLATION
Date:
Cluster context:
Namespace:
Application image digest:
ConfigMap name and revision:
Initial /config result:
Updated /config result:
Rollout/reload method:
Secret manager and store design:
ESO API version / sync status (if tested):
Workload identity and namespace scope:
RBAC access review:
Pod Security Admission labels:
ResourceQuota / LimitRange:
NetworkPolicy and required flows:
Negative test results:
Recovery validation:
GitOps values review:
Reviewer:
Open risks and owners:
\`\`\`

## 20. Knowledge checks

1. Why is a Kubernetes Secret not secure merely because it uses base64 encoding?
2. When do environment variables sourced from ConfigMaps update?
3. How do mounted ConfigMap/Secret volumes differ from environment variables?
4. What is the role of External Secrets Operator?
5. Why is workload identity preferable to static cloud keys?
6. What isolation is and is not provided by namespaces?
7. Why can a default-deny NetworkPolicy disrupt DNS and dependencies?
8. How should GitLab CI and Argo CD divide configuration responsibilities?

## 21. Completion

**Pass:** You deploy nonsecret environment configuration, validate configuration updates and restart behavior, diagnose missing references, and document least-privilege secret management and namespace isolation controls.

**Next: Chapter 028 — Kubernetes Services, Ingress, DNS and Application Connectivity for GitOps.**
