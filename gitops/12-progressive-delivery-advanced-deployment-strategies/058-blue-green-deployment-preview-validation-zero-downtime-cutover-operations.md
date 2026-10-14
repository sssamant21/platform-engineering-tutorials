# Chapter 058 — Blue-Green Deployment, Preview Validation and Zero-Downtime Cutover Operations

**Part 12 — Progressive Delivery and Advanced Deployment Strategies | Chapter 058 / 100**

> All commands are for disposable staging environments. Zero downtime is an objective, not a guarantee. Cutover can disrupt connections, sessions, database compatibility, and external side effects.

## Objectives

Implement Argo Rollouts blue-green delivery with active and preview Services, manual promotion, pre/post-promotion analysis, GitOps change control, connection draining, failure simulation, evidence collection, and recovery runbooks.

## Architecture

~~~text
GitLab build -> immutable image digest -> reviewed GitOps MR
  -> Argo CD -> Argo Rollouts
       |               |
   stable ReplicaSet  candidate ReplicaSet
       |               |
   active Service     preview Service
       |               |
  customer traffic    pre-release validation
                     /
          approved promotion
                |
       active Service cutover
                |
       SLO checks + audit evidence
~~~

Argo CD reconciles Git; Argo Rollouts manages ReplicaSets and Service selectors. Avoid competing writers for controller-managed fields.

## Strategy comparison

| Dimension | Blue-green | Canary |
| --- | --- | --- |
| Exposure | Preview endpoint before cutover | Gradual traffic share |
| Promotion | Switch active Service | Increase canary weight |
| Capacity | Often two overlapping stacks | Depends on scale and router |
| Validation | Preview tests and post-cutover SLO | Candidate metrics at partial exposure |
| Rollback | Restore known-good active revision | Abort candidate and restore stable |

Preview tests cannot fully reproduce real customer load, sessions or state mutations.

## Prerequisites and validation

Use a staging cluster with Argo Rollouts controller, matching CRDs/plugin, Argo CD Application, two real immutable image digests, functioning readiness endpoints, Prometheus for analysis, and enough CPU/memory for overlapping stacks.

~~~bash
kubectl config current-context
kubectl -n argo-rollouts get deploy,pods
kubectl get crd rollouts.argoproj.io analysistemplates.argoproj.io
kubectl -n demo-staging get rollout,svc,pods
kubectl argo rollouts version
~~~

Replace all placeholders. Verify installed versions and controller ownership before applying resources.

## Repository layout

~~~text
gitops/apps/demo-web/base/
  rollout.yaml
  services.yaml
  analysis-preview.yaml
  kustomization.yaml
gitops/apps/demo-web/overlays/staging/
gitops/apps/demo-web/overlays/prod-sim/
gitops/runbooks/blue-green-release.md
gitops/runbooks/blue-green-rollback.md
gitops/evidence/release-template.md
~~~

Protect Rollout strategies, AnalysisTemplates, Services and production overlays with independent review.

## Active and preview Services

~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-active
  namespace: demo-staging
spec:
  selector:
    app: demo-web
  ports:
    - name: http
      port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: demo-preview
  namespace: demo-staging
spec:
  selector:
    app: demo-web
  ports:
    - name: http
      port: 80
      targetPort: 8080
~~~

The initial selectors are bootstrap values. Argo Rollouts updates them to select stable and preview ReplicaSets. Do not commit ReplicaSet hashes or continually overwrite controller-managed selectors.

## Blue-green Rollout

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  replicas: 3
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - name: http
              containerPort: 8080
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 2
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
  strategy:
    blueGreen:
      activeService: demo-active
      previewService: demo-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 120
      scaleDownDelayRevisionLimit: 2
~~~

A first deployment establishes the stable revision. To exercise blue-green promotion, update the image digest to a second reviewed version. The delay helps routing propagation but does not guarantee zero dropped connections.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging apply --dry-run=server -f services.yaml
kubectl --context STAGING_CONTEXT -n demo-staging apply --dry-run=server -f rollout.yaml
kubectl --context STAGING_CONTEXT -n demo-staging get svc,endpointslices
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web --watch
~~~

## Preview analysis and health gates

Pre-promotion tests must call the preview Service, verify candidate version/digest, test dependencies, and collect enough synthetic requests for meaningful metrics.

~~~bash
curl --fail --show-error --max-time 5 http://demo-preview.demo-staging.svc.cluster.local/healthz
curl --fail --show-error --max-time 5 http://demo-preview.demo-staging.svc.cluster.local/readyz
curl --fail --show-error --max-time 10 http://demo-preview.demo-staging.svc.cluster.local/api/version
~~~

Run from a test Pod with cluster DNS access. Endpoints are examples and must exist in the application.

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: demo-preview-analysis
  namespace: demo-staging
spec:
  metrics:
    - name: preview-success-rate
      interval: 30s
      count: 5
      failureLimit: 1
      successCondition: len(result) > 0 && result[0] >= 0.99
      failureCondition: len(result) > 0 && result[0] < 0.99
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc.cluster.local:9090
          query: |
            sum(rate(http_requests_total{app="demo-web",traffic="preview",status!~"5.."}[2m]))
            /
            clamp_min(sum(rate(http_requests_total{app="demo-web",traffic="preview"}[2m])),0.001)
~~~

This assumes the application or test instrumentation really exports a preview-specific traffic label. Argo Rollouts does not create that metric automatically. Production policies also need sample-size, freshness and missing-data safeguards.

Attach under the blueGreen strategy:

~~~yaml
prePromotionAnalysis:
  templates:
    - templateName: demo-preview-analysis
~~~

Inspect analysis outcomes:

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
kubectl --context STAGING_CONTEXT -n demo-staging describe analysisrun ANALYSIS_RUN_NAME
~~~

**Pre-promotion:** candidate readiness, preview smoke tests, integration checks, metrics and approvals. **Post-promotion:** active traffic error rate, P95/P99 latency, sessions, business transactions and observed image digest.

## Cutover, draining and capacity

Changing the active Service selector does not instantly close existing TCP connections. Kubernetes EndpointSlice propagation, ingress caches, keep-alive/HTTP2, WebSockets, terminationGracePeriodSeconds and application SIGTERM handling all matter.

Recommended safeguards:

- Accurate readiness/startup probes.
- Graceful shutdown that stops accepting new work before exit.
- A scale-down delay and termination grace period matched to measured drain time.
- Ingress and load-balancer drain settings aligned with application behavior.
- Explicit handling of sticky sessions, WebSockets and background consumers.
- Sufficient node headroom for both revisions.

Example capacity: 6 stable + 6 preview Pods at 500m CPU and 1Gi memory each require **6 vCPU and 12Gi memory** of application requests, before sidecars, system reservations and headroom.

## GitLab and Argo CD integration

1. Build, test, scan and sign one immutable image.
2. Open a protected GitOps promotion MR changing the Rollout digest.
3. Validate rendered manifests, policy, approvals and change window.
4. Merge only at the effective deployment boundary.
5. Argo CD reconciles the approved candidate revision.
6. Argo Rollouts exposes the preview Service and runs analysis.
7. Authorized operator promotes the Rollout after validation.
8. Verify the active Service and post-cutover SLOs.
9. Archive release evidence and retain rollback digest.

A GitLab manual deployment job **does not automatically gate Argo CD auto-sync** after the GitOps MR is merged.

## Seven hands-on labs

### Lab A — Establish a stable active revision

Deploy a verified healthy digest and both Services in a disposable staging namespace. Verify active Service endpoints, Pod readiness and version endpoint. Record the stable digest and Git revision.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging apply -f services.yaml
kubectl --context STAGING_CONTEXT -n demo-staging apply -f rollout.yaml
kubectl --context STAGING_CONTEXT -n demo-staging get svc,endpointslices,pods
~~~

**Pass:** the active Service routes to the known-good revision.

### Lab B — Preview candidate without customer cutover

Promote a second immutable digest through a staging GitOps MR. Verify preview endpoints, candidate readiness, smoke tests and active Service unchanged.

~~~bash
argocd app get demo-staging --refresh
kubectl --context STAGING_CONTEXT -n demo-staging get svc demo-active demo-preview -o yaml
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web
~~~

**Pass:** candidate validated in preview; stable still active.

### Lab C — Authorized manual promotion

Verify analysis and independent staging approval, then:

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts promote demo-web
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web --watch
kubectl --context STAGING_CONTEXT -n demo-staging get svc demo-active -o yaml
~~~

**Pass:** active Service selects approved candidate; observed digest and application smoke tests pass.

### Lab D — Failed preview

Promote an intentionally unhealthy disposable candidate. Confirm readiness or analysis fails, active remains stable, abort candidate, and revert the GitOps desired digest.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts abort demo-web
kubectl --context STAGING_CONTEXT -n demo-staging get rollout,analysisruns,pods
~~~

**Pass:** unhealthy candidate never becomes active.

### Lab E — Post-cutover regression

Use a staging candidate that passes preview but fails synthetic load. Measure error/latency regression, assess stateful compatibility, and recover via reviewed GitOps revert or roll-forward.

**Pass:** actual running digest and business tests prove recovery; RTO measured.

### Lab F — Long-lived connections

Generate sustained requests and long-lived connections across cutover. Measure resets, latency and drain duration. Adjust app shutdown and delay settings and retest.

**Pass:** interruption rate is measured; zero downtime is not claimed without evidence.

### Lab G — Capacity/failure-domain drill

Measure allocatable resources, deploy overlapping stacks, verify topology spread, and test one disposable worker failure if safe.

**Pass:** active availability and capacity headroom meet the agreed objective.

## Twelve troubleshooting scenarios

| # | Symptom | Diagnosis | Response |
| --- | --- | --- | --- |
| 1 | Preview has no endpoints | Candidate readiness/selectors | Inspect Pods, ReplicaSets and Services |
| 2 | Active changes early | Auto-promotion/selector ownership | Review strategy and controller |
| 3 | Promotion blocked | Manual pause or failed analysis | Inspect AnalysisRuns and policy |
| 4 | Preview healthy, active unhealthy | Load/ingress/session differences | Compare actual traffic |
| 5 | Cutover 5xx spike | Drain/readiness mismatch | Tune shutdown and proxy |
| 6 | Old Pods exit too soon | Delay or grace period too short | Extend tested drain interval |
| 7 | Preview Pods Pending | Capacity, quota, scheduling | Reserve headroom |
| 8 | Argo CD selector drift | Competing writers | Correct field ownership |
| 9 | Inconclusive analysis | Missing series/low traffic | Repair telemetry and sample size |
| 10 | Revert breaks database | Incompatible migration | DBRE-led recovery or roll-forward |
| 11 | Unauthorized promotion | Broad RBAC | Restrict and audit actor |
| 12 | Missing release evidence | Incomplete collector | Repair archive and correlation |

## Production runbook — planned cutover

**Preflight:** verify window, approvers, stable/candidate digests, backup and data compatibility, preview tests, analysis metrics, capacity and rollback owner.

**Preview:** merge approved GitOps MR, reconcile, validate candidate endpoints and pre-promotion analysis.

**Cutover:** authorized Rollouts promotion, capture selector change and timestamp.

**Observe:** active 5xx, P95/P99, connection resets, business transactions, readiness and database writes.

**Close:** verify running digest, GitOps revision and SLOs; archive redacted evidence.

## Production runbook — failed cutover

1. Declare incident and freeze subsequent promotions.
2. Record active/preview Service selectors, ReplicaSet hashes and digests.
3. Classify routing, capacity, application, session or database failure.
4. Assess whether reverting active traffic is safe.
5. Use supported Rollouts controls and reviewed GitOps revert/forward fix.
6. Verify actual running digest, sessions, transactions and SLO recovery.
7. Preserve analysis, controller, GitLab and Argo CD evidence.

Do not blindly revert irreversible database migrations or external side effects.

## Evidence template

~~~text
Change ID and approved window:
Source commit / CI pipeline:
Immutable image digest:
GitOps MR, approvers and revision:
Rollout and stable/candidate ReplicaSet IDs:
Preview Service endpoints and smoke tests:
Pre-promotion AnalysisRun:
Promotion actor and timestamp:
Active Service selector after promotion:
Observed running digest:
Post-promotion 5xx and P95/P99:
Connection-drain test:
Database compatibility:
Rollback/forward-fix decision:
Recovery duration:
Audit archive reference:
~~~

## Acceptance checklist

- [ ] Active/preview Services correctly managed by Argo Rollouts.
- [ ] Healthy stable revision established before candidate update.
- [ ] Preview validates candidate without unintended active exposure.
- [ ] AnalysisTemplate uses real preview-specific metrics.
- [ ] Missing telemetry cannot silently authorize promotion.
- [ ] Manual promotion requires authorized identity and approval.
- [ ] Active cutover points to the approved immutable digest.
- [ ] Post-promotion smoke tests, errors and latency are validated.
- [ ] Long-lived connection draining is measured.
- [ ] Stable/preview overlapping capacity is validated.
- [ ] Failed preview cannot become active.
- [ ] Regression recovery includes database compatibility checks.
- [ ] Release evidence and production runbooks reviewed.

## Knowledge check

1. How do active and preview Services differ?
2. Why is a second revision necessary to exercise blue-green?
3. Why might preview tests pass but active traffic fail?
4. What does scaleDownDelaySeconds not guarantee?
5. Why are graceful termination and readiness both necessary?
6. How do overlapping ReplicaSets affect cluster capacity?
7. Why must an abort be followed by a GitOps source-of-truth review?
8. How can database writes make a traffic rollback unsafe?

## References

- [Argo Rollouts Blue-Green](https://argo-rollouts.readthedocs.io/en/stable/features/bluegreen/)
- [Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Argo Rollouts kubectl Plugin](https://argo-rollouts.readthedocs.io/en/stable/features/kubectl-plugin/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)

---

**Chapter 058 complete.** Next: **Chapter 059 — Feature Flags, Experimentation and Progressive Release Observability**.