# Chapter 026 — Kubernetes Deployment Fundamentals for GitLab CI/CD and GitOps

**Part 06 — Kubernetes Deployment Fundamentals** | **Chapter 026 / 100**  
**Audience:** Kubernetes administrators, SREs, infrastructure/platform engineers  
**Toolchain:** kubectl, GitLab CI, Helm (later chapters), Argo CD (later chapters)  
**Reference architecture:** One Kubernetes cluster with four namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.

> **Scope and safety:** All resources are generic training examples. Run commands in a disposable cluster or explicitly approved \`demo-dev\` namespace. Do not apply to production. Namespaces provide logical isolation, not a separate control plane or complete security boundary. For critical production workloads, evaluate separate clusters and cloud-account boundaries.

## 1. Learning objectives

After this chapter, you can:

1. Describe Kubernetes desired state, API server, controllers and reconciliation.
2. Explain Pods, Deployments, ReplicaSets, Services, ConfigMaps, Secrets and namespaces.
3. Deploy a non-root sample workload using an **immutable image digest**.
4. Inspect rollouts, health probes, events, logs, resource requests and limits.
5. Distinguish \`kubectl apply\`, Helm release management and Argo CD GitOps reconciliation.
6. Design GitLab CI as the artifact producer, not an uncontrolled production deployer.
7. Troubleshoot image pulls, scheduling, crash loops, readiness and service connectivity.
8. Recover through a reviewed GitOps revert and validate application SLOs.

## 2. Platform architecture

\`\`\`text
GitLab source repo
    |
    +--> merge request validation
    +--> protected build pipeline
    +--> scan / SBOM / signature / provenance
    |
    v
OCI registry: demo-app@sha256:<verified-digest>
    |
    v
GitOps repository (desired Kubernetes state)
    |
    +--> demo-dev
    +--> demo-test
    +--> demo-staging
    +--> demo-prod
    |
    v
Argo CD Applications -> Kubernetes API
    |
    +--> Deployment controller -> ReplicaSets -> Pods
    +--> Service -> stable virtual endpoint
    +--> ConfigMaps / external secret references
    +--> NetworkPolicy / quotas / RBAC
\`\`\`

**Separation of duties:** GitLab CI builds and validates a single immutable artifact. Approved GitOps changes promote the same digest. Argo CD reconciles the desired state. A green CI job is not itself production release authorization.

## 3. Core objects and operational roles

| Object | Responsibility | SRE checks |
| --- | --- | --- |
| Namespace | Groups resources and policies | Quotas, RBAC, isolation |
| Pod | Smallest scheduled workload unit | Phase, restarts, probes |
| Deployment | Manages stateless replicas and rolling updates | Available replicas, conditions |
| ReplicaSet | Maintains Pod count for Deployment revision | Desired/current/ready |
| Service | Stable access to matching Pods | Selectors, EndpointSlices |
| ConfigMap | Nonsecret configuration | Correct keys and rollout strategy |
| Secret | Sensitive values stored via Kubernetes API | RBAC, encryption, external management |
| ServiceAccount | Workload API identity | Least privilege |
| NetworkPolicy | Pod network traffic rules | CNI enforcement and required flows |
| ResourceQuota | Namespace resource budget | Usage, hard limits |
| LimitRange | Default/min/max per-object resources | Admission and scheduling |

A Service does not create Pods. It selects eligible endpoints; readiness determines whether Pods should receive normal Service traffic.

## 4. Reconciliation and deployment lifecycle

1. A manifest is submitted to the Kubernetes API.
2. Admission authenticates, authorizes and validates the request.
3. The Deployment controller creates or updates ReplicaSets.
4. The scheduler selects nodes for pending Pods.
5. The kubelet pulls the image and starts containers.
6. Startup/readiness/liveness probes influence lifecycle and traffic.
7. EndpointSlices reflect ready Service backends.
8. Controllers continue reconciling actual state toward desired state.

A Pod in \`Running\` phase is not necessarily \`Ready\`. A rollout is successful only when desired replicas are available and service health is validated.

## 5. Hands-on lab prerequisites

- Kubernetes cluster with authorized access to create resources in a disposable namespace.
- \`kubectl\` configured with the **correct** context.
- An OCI image from Chapter 021/025 with an actual digest, reachable by the cluster.
- The sample image listens on port 8080 and responds to \`GET /healthz\`.
- Namespace policies permitting the chosen workload.
- A terminal with Bash; PowerShell alternatives are provided where practical.

Verify:

\`\`\`bash
kubectl config current-context
kubectl cluster-info
kubectl auth can-i create deployments -n demo-dev
kubectl auth can-i create services -n demo-dev
\`\`\`

Do not assume you can create namespaces; ask a cluster administrator to provision \`demo-dev\` with approved controls when necessary.

## 6. Namespace and guardrails

The following is a **reference** manifest for an authorized administrator. Do not apply it without permission:

\`k8s/namespace.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo-dev
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
\`\`\`

If authorized:

\`\`\`bash
kubectl apply -f k8s/namespace.yaml
kubectl get namespace demo-dev --show-labels
\`\`\`

\`k8s/quota.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: demo-dev-quota
  namespace: demo-dev
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 2Gi
    limits.cpu: "4"
    limits.memory: 4Gi
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: demo-dev-defaults
  namespace: demo-dev
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 100m
        memory: 64Mi
      default:
        cpu: 500m
        memory: 256Mi
\`\`\`

Apply only if authorized:

\`\`\`bash
kubectl apply -f k8s/quota.yaml
kubectl describe quota -n demo-dev
kubectl describe limitrange -n demo-dev
\`\`\`

The quota values are lab examples; size them from measured workload and node capacity.

## 7. Deployment manifest

Create \`k8s/deployment.yaml\`:

\`\`\`yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: demo-dev
  labels:
    app.kubernetes.io/name: demo-app
spec:
  replicas: 2
  revisionHistoryLimit: 5
  progressDeadlineSeconds: 180
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: demo-app
  template:
    metadata:
      labels:
        app.kubernetes.io/name: demo-app
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
          image: registry.example.com/training/demo-app@sha256:REPLACE_WITH_ACTUAL_DIGEST
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            failureThreshold: 12
            periodSeconds: 5
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 5
            timeoutSeconds: 2
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
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
              drop:
                - ALL
\`\`\`

**Before applying:** Replace \`registry.example.com/training/demo-app@sha256:REPLACE_WITH_ACTUAL_DIGEST\` with your **actual verified** registry image reference. The placeholder is deliberately invalid. If the registry is private, configure an authorized read-only image pull identity. Confirm the image supports your node architecture.

### Why these settings?

- Two replicas tolerate a single Pod failure, but not necessarily node/zone loss.
- \`maxUnavailable: 0\` attempts to preserve existing capacity during rollout; quota and available cluster resources must support surge Pods.
- Startup probe gives initialization time; readiness controls Service traffic; liveness restarts unhealthy containers.
- \`runAsNonRoot\`, seccomp, dropped capabilities and read-only root filesystem support restricted workload operation.
- Resource requests influence scheduling; limits constrain resource usage.
- \`automountServiceAccountToken: false\` avoids an unnecessary API token for this simple application.

## 8. Service manifest

Create \`k8s/service.yaml\`:

\`\`\`yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: demo-app
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
\`\`\`

A ClusterIP Service is internal to the cluster by default. Exposing it externally requires separately reviewed ingress or load-balancer configuration.

## 9. Apply and validate

Validate the manifests before a write:

\`\`\`bash
kubectl apply --dry-run=client -f k8s/deployment.yaml
kubectl apply --dry-run=client -f k8s/service.yaml
kubectl apply --dry-run=server -f k8s/deployment.yaml
kubectl apply --dry-run=server -f k8s/service.yaml
\`\`\`

Client-side dry run does not fully reproduce admission and server validation; prefer server-side validation when authorized and available.

Apply in the disposable namespace:

\`\`\`bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/demo-app -n demo-dev --timeout=180s
kubectl get deployments,replicasets,pods,services -n demo-dev -o wide
kubectl get endpointslices -n demo-dev \
  -l kubernetes.io/service-name=demo-app
\`\`\`

Expected: Deployment reports 2/2 available, both Pods ready, Service has ready endpoints. Actual timings depend on image pulls, node capacity and cluster policy.

### Verify from your workstation

\`\`\`bash
kubectl port-forward -n demo-dev service/demo-app 8080:80
\`\`\`

In a **second** terminal:

\`\`\`bash
curl --fail --silent http://127.0.0.1:8080/healthz
\`\`\`

Expected:

\`\`\`json
{"status":"ok"}
\`\`\`

Stop port-forward with Ctrl+C. For PowerShell, use \`Invoke-RestMethod http://127.0.0.1:8080/healthz\`.

## 10. Inspect Kubernetes operational state

\`\`\`bash
kubectl describe deployment demo-app -n demo-dev
kubectl get pods -n demo-dev -l app.kubernetes.io/name=demo-app
kubectl describe pods -n demo-dev -l app.kubernetes.io/name=demo-app
kubectl logs -n demo-dev deployment/demo-app --tail=100
kubectl get events -n demo-dev --sort-by=.lastTimestamp
kubectl rollout history deployment/demo-app -n demo-dev
kubectl top pods -n demo-dev
\`\`\`

\`kubectl top\` requires Metrics Server or a compatible metrics API. Missing metrics do not prove the workload is unhealthy.

Inspect actual deployed image references:

\`\`\`bash
kubectl get deployment demo-app -n demo-dev \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
\`\`\`

Check the reference matches the approved registry digest.

## 11. Failure injection — safe lab scenarios

Run only in \`demo-dev\`, never in production.

### Scenario A — Invalid image digest

Change the Deployment image to a nonexistent digest in your training repository. Apply the manifest and observe:

\`\`\`bash
kubectl get pods -n demo-dev -w
kubectl describe pods -n demo-dev -l app.kubernetes.io/name=demo-app
kubectl rollout status deployment/demo-app -n demo-dev --timeout=60s
\`\`\`

Expected: new Pods fail image pull and the rollout cannot complete. With \`maxUnavailable: 0\`, old ready replicas may remain available, provided capacity and policies permit.

**Recovery:** Restore the last verified digest in the manifest and apply it; confirm full rollout and health.

### Scenario B — Readiness failure

Temporarily set readiness probe path to \`/missing\`.

Expected: new Pods do not become Ready and are excluded from normal Service endpoints. Liveness still uses \`/healthz\`, so readiness failure alone should not force restarts.

**Recovery:** Restore \`/healthz\`; verify ready replicas and EndpointSlices.

### Scenario C — Resource pressure

Increase a **disposable** Deployment's CPU request beyond the available quota or schedulable capacity.

Expected: quota admission rejects the update or Pods remain Pending with scheduling events.

**Recovery:** Restore the original request; investigate quota, node allocatable resources and scheduling constraints.

### Scenario D — Service selector mismatch

Change the Service selector to a nonexistent label.

Expected: EndpointSlices have no matching ready endpoints and Service requests fail.

**Recovery:** Restore selector \`app.kubernetes.io/name: demo-app\`.

### Scenario E — Unhealthy application

Use a separately built disposable image whose \`/healthz\` returns a failure response.

Expected: startup/readiness or liveness failures depending on the image behavior and probe configuration. Do not infer root cause solely from Pod phase.

**Recovery:** Restore the previously approved image digest.

## 12. Kubernetes rollout vs GitOps reconciliation

### Imperative/manual operations

\`\`\`bash
kubectl rollout status deployment/demo-app -n demo-dev
kubectl rollout history deployment/demo-app -n demo-dev
kubectl rollout undo deployment/demo-app -n demo-dev
\`\`\`

\`kubectl rollout undo\` can be a useful emergency action when authorized, but it changes live state. If Argo CD owns the Deployment, it may subsequently reconcile back to the Git-declared version.

### GitOps-managed operations

The durable recovery procedure is:

1. Identify the last known-good image digest.
2. Open a reviewed GitOps revert/update MR.
3. Update the Helm values or manifest in the correct environment path.
4. Let Argo CD reconcile the approved desired state.
5. Verify Deployment rollout, application health and SLOs.
6. Preserve the incident timeline and audit evidence.

For emergency response, follow the organization's approved break-glass procedure; reconcile Git desired state promptly afterward.

## 13. GitLab CI/CD integration boundary

GitLab CI is responsible for:

- Linting Kubernetes manifests and Helm templates.
- Running unit, integration, policy and security checks.
- Building a trusted image once and publishing by digest.
- Producing verified SBOM, signature and provenance evidence.
- Proposing reviewed GitOps digest updates.

Argo CD is responsible for reconciling Kubernetes resources from the GitOps repository.

**Do not** place broad production \`kubectl apply\` credentials in general MR pipelines. CI runners should not hold cluster-admin credentials merely to release applications.

Illustrative GitLab validation job:

\`\`\`yaml
manifest_validation:
  stage: validate
  image: registry.example.com/platform/kubectl@sha256:<APPROVED_TOOL_IMAGE_DIGEST>
  tags: [mr-validation]
  script:
    - kubectl apply --dry-run=client -f k8s/deployment.yaml
    - kubectl apply --dry-run=client -f k8s/service.yaml
\`\`\`

This is a **template**, not directly runnable until the tool image is replaced with a real approved digest and the image placeholder in the Deployment is resolved. Client dry run does not prove the cluster will accept or successfully run the workload.

## 14. Helm and Argo CD preview

Later chapters will implement full Helm chart engineering and Argo CD Applications. The desired architecture is:

\`\`\`text
gitops/
  charts/demo-app/
  environments/dev/values.yaml
  environments/test/values.yaml
  environments/staging/values.yaml
  environments/prod/values.yaml
  argocd/demo-dev.yaml
  argocd/demo-test.yaml
  argocd/demo-staging.yaml
  argocd/demo-prod.yaml
\`\`\`

The shared Helm chart uses environment-specific values, but every approved promotion preserves the same application image digest. Each Argo CD Application targets the corresponding namespace. Namespace-specific RBAC, NetworkPolicy, quotas, admission controls and workload identities remain necessary.

## 15. Troubleshooting runbook

| Symptom | Likely cause | Safe investigation |
| --- | --- | --- |
| Deployment unavailable | Image, probe, scheduling or crash | Describe Deployment and Pods |
| \`ImagePullBackOff\` | Invalid digest, auth, DNS or architecture | Pod events, registry pull |
| \`CrashLoopBackOff\` | App exits, config or permissions | Logs, exit code, previous logs |
| \`Pending\` Pods | CPU/memory, affinity, taints, quota | Pod events, node capacity |
| \`Running\` but not Ready | Readiness probe or dependency | Probe status and endpoint data |
| Service returns no response | Selector, port, endpoints, NetworkPolicy | Service and EndpointSlices |
| 403 from Kubernetes API | RBAC or admission policy | \`kubectl auth can-i\`, events |
| OOMKilled | Memory limit or workload spike | Container last state, metrics |
| Rollout stalled | Probe failure or insufficient surge capacity | Deployment conditions/events |
| Argo CD OutOfSync | Desired/live drift or sync failure | Application conditions and Git diff |

## 16. SRE monitoring and operational readiness

Track:

- Deployment available/desired replica ratio.
- Pod restart rate and OOMKilled events.
- Rollout success/failure and duration.
- Readiness and liveness probe failure rates.
- Service error rate, latency and availability SLIs.
- CPU/memory requests, limits and actual usage.
- Image pull failures and registry latency.
- Argo CD sync/health state and reconciliation failures.
- Namespace quota utilization and cluster scheduling pressure.

Use real observation windows to define SLOs. Do not treat a green rollout as proof that the application meets user-facing availability or latency objectives.

## 17. Cleanup and rollback

Only clean up resources **you created** in the disposable namespace:

\`\`\`bash
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
\`\`\`

Delete quota, LimitRange or namespace **only if** you created them for an isolated lab and have explicit authorization. Never delete a shared environment namespace or another team's resources.

If Argo CD manages these resources, remove them through the approved GitOps change rather than repeatedly deleting live objects.

## 18. Acceptance checklist

- [ ] Correct cluster context and namespace verified.
- [ ] Namespace security and quota controls reviewed.
- [ ] Deployment image pinned to an actual verified digest.
- [ ] Non-root runtime and restricted security context validated.
- [ ] Two replicas become available.
- [ ] Startup, readiness and liveness probes function.
- [ ] Service routes to ready endpoints.
- [ ] Resource requests and limits are present.
- [ ] Invalid digest failure is diagnosed and recovered.
- [ ] Readiness failure is diagnosed and recovered.
- [ ] Service selector failure is diagnosed and recovered.
- [ ] GitLab CI vs Argo CD responsibilities explained.
- [ ] GitOps rollback path documented.
- [ ] No production namespace or credentials changed.

## 19. Evidence worksheet

\`\`\`text
CHAPTER 026 — KUBERNETES DEPLOYMENT FUNDAMENTALS
Date:
Cluster/context:
Namespace:
Approved image repository and digest:
Deployment replicas desired/available:
Pod UID / node placement:
Runtime UID and security controls:
Startup/readiness/liveness status:
Service and EndpointSlices:
Health endpoint response:
Resource requests and limits:
Quota utilization:
Rollout duration:
Failure injection A / recovery:
Failure injection B / recovery:
Failure injection C / recovery:
Failure injection D / recovery:
GitOps desired-state review:
Reviewer:
Open risks and owners:
\`\`\`

## 20. Knowledge checks

1. What is the difference between a Pod, ReplicaSet and Deployment?
2. Why can a Pod be Running but not Ready?
3. How does a Service determine which Pods receive traffic?
4. Why does an immutable image digest matter for GitOps rollback?
5. What does \`maxUnavailable: 0\` require from cluster capacity?
6. Why can manual \`kubectl rollout undo\` conflict with Argo CD reconciliation?
7. Why do four namespaces in one cluster share important failure domains?
8. What should GitLab CI do before proposing a GitOps promotion?

## 21. Completion

**Pass:** An approved disposable workload is deployed by digest, is healthy behind a ClusterIP Service, and the operator demonstrates safe diagnosis and recovery from image, readiness, scheduling and Service configuration failures.

**Next: Chapter 027 — Kubernetes Configuration Management, Secrets and Environment Isolation for GitOps.**
