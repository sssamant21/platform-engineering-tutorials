# Chapter 056 — Progressive Delivery Fundamentals: Canary, Blue-Green and Release Risk

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 12:** Progressive Delivery and Advanced Deployment Strategies  
**Chapter:** 056 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Kubernetes Administrators and Release Managers

> **Safety:** Execute rollout experiments only in disposable development or staging environments. Traffic routing, analysis, rollback and resource deletion must be reviewed for your controller, service mesh and ingress versions. Never run failure injection against customer-serving workloads.

## 1. Learning objectives

After completing this chapter, you can:

1. Compare rolling, recreate, canary and blue-green deployment strategies.
2. Explain progressive delivery as a risk-reduction process rather than merely a Kubernetes rollout mechanism.
3. Describe Argo Rollouts architecture, controller ownership and integration with Argo CD.
4. Configure a basic staged canary rollout with manual approval and analysis.
5. Implement blue-green Services, promotion and preview validation.
6. Distinguish replica-weighted canaries from true traffic-weighted canaries.
7. Define release metrics, abort thresholds, rollback and post-release evidence.
8. Troubleshoot common rollout failures using Kubernetes and Argo Rollouts tooling.

## 2. Why progressive delivery matters

A conventional Deployment updates Pods according to a rollout strategy. Progressive delivery adds deliberate **exposure management** and **automated verification**: release a candidate to a controlled subset of users or traffic, observe health and business metrics, and only then increase exposure.

~~~text
Build + scan + sign -> immutable image digest
                           |
                     GitOps promotion MR
                           |
                       Argo CD sync
                           |
                     Argo Rollouts
                           |
              +------------+------------+
              |                         |
         stable version            candidate version
              |                         |
           baseline             canary / preview
              +------------+------------+
                           |
                   metrics + analysis
                           |
                   promote or abort
~~~

Argo CD is the GitOps reconciliation controller; Argo Rollouts is a separate Kubernetes controller that manages Rollout resources and related ReplicaSets/Services. They are complementary, not interchangeable.

## 3. Strategy comparison

| Strategy | Release exposure | Primary advantage | Main risk |
| --- | --- | --- | --- |
| Recreate | Old Pods stop before new Pods start | Simple state transition | Downtime likely |
| RollingUpdate | Pods replaced gradually | Built into Deployments | Limited traffic/metric control |
| Canary | Small fraction of replicas or routed traffic receives candidate | Limits blast radius and enables analysis | Routing and metric complexity |
| Blue-green | Stable and preview stacks; Service cutover | Fast switch and pre-cutover testing | Double capacity and session/state risks |
| Feature flags | Feature enabled for selected users | Decouples deploy from feature release | Flag governance and inconsistent behavior |

**Important:** A basic Argo Rollouts canary without a traffic router approximates a requested weight by replica proportions. It cannot guarantee an exact percentage of user requests, particularly with sticky sessions or uneven load. Accurate traffic-weighted canaries require a supported ingress controller, service mesh or other traffic router.

## 4. Prerequisites and version checks

- A disposable Kubernetes staging cluster and namespace.
- Argo Rollouts controller installed from a version-pinned, supported manifest or Helm chart.
- The matching Argo Rollouts kubectl plugin, if using its plugin commands.
- Argo CD Application and restrictive AppProject, if testing GitOps reconciliation.
- Two real, tested immutable image digests: stable and candidate.
- An HTTP demo app exposing a working readiness endpoint.
- Metrics backend for automated analysis (Prometheus or supported provider).
- Enough capacity to run stable and candidate replicas simultaneously.

~~~bash
kubectl config current-context
kubectl get ns
kubectl -n argo-rollouts get deploy,pods
kubectl get crd rollouts.argoproj.io
kubectl argo rollouts version
kubectl -n demo-staging get rollouts,deploy,svc
~~~

If the kubectl plugin is unavailable, use standard kubectl inspection until the matching plugin is installed. Verify the controller/CRD/plugin versions against the pinned release documentation.

## 5. Recommended GitOps repository layout

~~~text
gitops/
  apps/demo-web/
    base/
      rollout.yaml
      service.yaml
      kustomization.yaml
    overlays/
      staging/
        kustomization.yaml
      prod/
        kustomization.yaml
  analysis/
    http-success-rate.yaml
  argocd/
    demo-staging.yaml
  runbooks/
    canary-abort.md
    blue-green-rollback.md
  evidence/
    release-template.md
~~~

Treat traffic-routing resources and AnalysisTemplates as privileged release controls. Protect their Git paths with CODEOWNERS, policy validation and independent review.

## 6. Argo Rollouts objects and controller responsibilities

| Object | Role |
| --- | --- |
| Rollout | Defines canary or blue-green strategy and manages ReplicaSets |
| AnalysisTemplate | Reusable metric-based verification policy |
| AnalysisRun | Concrete execution and result of an analysis |
| Experiment | Runs controlled comparative tests |
| Service | Routes stable/active or canary/preview traffic |
| Ingress/service mesh | Optional true weighted traffic routing |
| Argo CD Application | Tracks desired manifests in Git and reconciles them |

The Rollouts controller manages rollout-specific changes such as ReplicaSets and, depending on strategy, Service selectors and routing resources. Do not add unrelated automation that fights those controller-owned fields.

## 7. Lab A — Deploy a basic canary Rollout

**Goal:** use replica-weighted staging with manual pauses and a safe abort path. Replace the image placeholder with a real digest before applying.

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  replicas: 4
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
  strategy:
    canary:
      maxSurge: 1
      maxUnavailable: 0
      steps:
        - setWeight: 25
        - pause: {}
        - setWeight: 50
        - pause:
            duration: 2m
        - setWeight: 100
~~~

Save as rollout.yaml. This is a **replica-weighted canary**: without a traffic router, the configured weight influences the proportion of candidate Pods, not an exact HTTP request percentage. Four replicas and 25% exposure correspond approximately to one candidate Pod at the first step, subject to controller rounding and availability constraints.

~~~bash
kubectl --context STAGING_CONTEXT create ns demo-staging \
  --dry-run=client -o yaml | kubectl --context STAGING_CONTEXT apply -f -
kubectl --context STAGING_CONTEXT -n demo-staging apply --dry-run=server -f rollout.yaml
kubectl --context STAGING_CONTEXT -n demo-staging apply -f rollout.yaml
kubectl --context STAGING_CONTEXT -n demo-staging get rollout demo-web
kubectl --context STAGING_CONTEXT -n demo-staging get rs,pods -l app=demo-web
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web --watch
~~~

The initial creation of a Rollout does not necessarily exercise a canary update. First establish a healthy stable revision, then change its image to a second reviewed digest and observe the steps.

### Manual promotion and abort

~~~bash
# Only after staging checks and the appropriate approval:
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts promote demo-web

# If the candidate is unhealthy:
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts abort demo-web
~~~

An abort stops the candidate rollout and returns traffic/replica allocation toward stable behavior as supported by the strategy. **It does not automatically revert the GitOps desired image.** Update Git to a known-good digest or otherwise reconcile the source of truth before expecting durable recovery.

**Pass:** a healthy stable revision exists; a new revision pauses at the intended step; promotion advances; abort leaves a recoverable state and evidence.

## 8. Lab B — Blue-green deployment

**Goal:** separate active traffic from preview traffic using two Services.

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
    - port: 80
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
    - port: 80
      targetPort: 8080
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
  strategy:
    blueGreen:
      activeService: demo-active
      previewService: demo-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 60
~~~

Use this blue-green manifest **instead of**, not alongside, the canary Rollout with the same name. Run it in a separate disposable namespace or delete/recreate the test Rollout after reviewing effects. The Rollouts controller updates Service selectors to point to the appropriate ReplicaSets.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get svc demo-active demo-preview -o yaml
kubectl --context STAGING_CONTEXT -n demo-staging get rollout demo-web
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web --watch
~~~

**Pass:** active Service remains on stable revision while preview Service points to candidate; manual promotion switches active traffic after preview validation.

**Caution:** Service selector cutover does not instantly terminate existing client connections. DNS, ingress, connection draining and stateful sessions may affect observed behavior. Size the cluster for overlapping stacks.

## 9. Lab C — Add an automated analysis gate

An AnalysisTemplate evaluates metrics during rollout. The following **illustrative** Prometheus query assumes a metric that actually exists in your test environment; adapt metric names and labels to your instrumentation.

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: demo-success-rate
  namespace: demo-staging
spec:
  metrics:
    - name: success-rate
      interval: 30s
      count: 5
      successCondition: result[0] >= 0.99
      failureLimit: 1
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc.cluster.local:9090
          query: |
            sum(rate(http_requests_total{app="demo-web",status!~"5.."}[2m]))
            /
            clamp_min(sum(rate(http_requests_total{app="demo-web"}[2m])), 0.001)
~~~

Before using this as an automated release gate, validate metric freshness, query cardinality, low-traffic behavior, baseline comparison and whether the query actually isolates the **candidate** revision. As written, it is a service-wide signal; a production canary analysis should use candidate-specific labels or traffic-router telemetry to avoid hiding canary errors in stable traffic.

To reference the template from a canary strategy, add:

~~~yaml
steps:
  - setWeight: 25
  - analysis:
      templates:
        - templateName: demo-success-rate
  - pause: {}
  - setWeight: 50
  - pause:
      duration: 2m
~~~

The snippet replaces the steps field in the Lab A canary Rollout; it is not a standalone resource.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get analysistemplates
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
kubectl --context STAGING_CONTEXT -n demo-staging describe analysisrun ANALYSIS_RUN_NAME
~~~

**Pass:** an AnalysisRun executes and returns a traceable success/failure decision. Do not allow missing or stale metrics to silently count as healthy.

## 10. Traffic-weighted canaries

For precise HTTP traffic splits, integrate Argo Rollouts with a supported traffic router such as Istio, NGINX Ingress or another documented integration. The controller may manage weighted routing while stable and canary ReplicaSet sizes are controlled independently.

~~~text
Client -> ingress/service mesh
                |
           weighted route
             /       \
          stable     canary
          90%         10%
~~~

**Do not assume** an arbitrary Ingress controller supports the same traffic-routing configuration. Validate the exact Rollouts version, ingress/service-mesh version, Service names, route resources and RBAC before deploying.

When evaluating a canary, consider request count, user cohorts, geographic concentration, sticky sessions, retry amplification and the possibility that a low-traffic candidate cannot produce statistically meaningful metrics.

## 11. Release risk and guardrails

| Guardrail | Why it matters |
| --- | --- |
| Small initial exposure | Limits blast radius |
| Manual pause | Allows human inspection |
| Candidate-specific metrics | Prevents stable traffic masking failures |
| Minimum sample size | Avoids false confidence from sparse data |
| Timeout/failure policy | Prevents indefinite stuck rollouts |
| Immutable image digest | Guarantees tested artifact identity |
| GitOps revert plan | Ensures durable desired-state recovery |
| Database compatibility | Avoids unsafe application rollback |
| Capacity reserve | Supports stable and candidate replicas |
| Change-window approval | Aligns release with operational governance |

## 12. Lab D — Simulate canary failure and abort

1. Deploy a known-good stable revision.
2. Promote a deliberately unhealthy **staging** image digest.
3. Observe readiness failures and rollout status.
4. Inspect AnalysisRun outcome if configured.
5. Abort the rollout using the plugin.
6. Revert the GitOps overlay to the last known-good digest.
7. Reconcile and verify workload health and observed digest.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web
kubectl --context STAGING_CONTEXT -n demo-staging get pods -l app=demo-web
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts abort demo-web
~~~

**Pass:** stable service remains healthy within the agreed objective, candidate exposure is stopped, and GitOps desired state is restored to an approved digest.

## 13. Lab E — Compare rolling, canary and blue-green

Using separate disposable namespaces, run the same demo application under:

- A standard Kubernetes RollingUpdate Deployment.
- An Argo Rollouts canary with manual pauses.
- An Argo Rollouts blue-green with active/preview Services.

Measure:

| Metric | Rolling | Canary | Blue-green |
| --- | --- | --- | --- |
| Additional peak Pods | Record | Record | Record |
| Time to first candidate exposure | Record | Record | Record |
| Ability to preview before full cutover | Limited | Yes | Yes |
| Manual promotion point | Optional workflow | Yes | Yes |
| Recovery duration | Record | Record | Record |
| Application error rate | Record | Record | Record |

**Pass:** comparison is based on actual observations, not claims of universal zero downtime.

## 14. GitLab and Argo CD integration

A recommended flow is:

1. GitLab builds, scans and publishes an immutable image.
2. A protected GitOps MR changes the Rollout image digest.
3. CI renders and validates the Rollout and analysis resources.
4. Reviewers approve the release and change window.
5. Argo CD syncs the approved Git revision.
6. Argo Rollouts controls canary/blue-green progression.
7. Metrics and health checks determine promotion or abort.
8. Release evidence captures actual digest, analysis and outcomes.

**Ownership rule:** Do not simultaneously let multiple controllers or CI jobs mutate the same Rollout strategy/Service selector fields. Protect Argo Rollouts controller-managed fields from accidental GitOps drift loops by following the documented Argo CD/Rollouts integration guidance for your versions.

## 15. Monitoring and release evidence

Capture:

~~~text
Release ID and change ticket:
Source commit and CI pipeline:
Image digest:
GitOps promotion MR and approvers:
Argo CD Application and sync revision:
Rollout name and strategy:
Stable/candidate ReplicaSet revisions:
Canary step or blue-green cutover time:
Traffic-router configuration (if used):
AnalysisTemplate/AnalysisRun result:
Candidate request count and error rate:
Application latency and smoke tests:
Abort/promotion actor and timestamp:
Recovery time and observed stable digest:
Rollback Git commit:
Evidence location (redacted):
~~~

## 16. Production runbook — canary release

**Preflight:** confirm digest, rollout strategy, controller health, capacity, metrics quality, approved change window and rollback owner.

**Start:** merge approved GitOps MR and sync via authorized workflow. Verify candidate revision, traffic exposure and readiness.

**Observe:** monitor candidate-specific 5xx, P95/P99, saturation, application transactions and AnalysisRun status. Do not promote on missing telemetry.

**Promote:** advance only when minimum sample size, health and approval conditions pass.

**Close:** confirm stable/candidate transition, final digest, desired revision, SLOs and audit evidence.

## 17. Production runbook — failed canary or blue-green cutover

1. Declare incident and freeze further promotions.
2. Record actual candidate digest, traffic weight and error metrics.
3. Abort the Rollout or restore the stable active Service through supported controls.
4. Revert the GitOps image digest/configuration to the approved stable state.
5. Verify application health, observed digest, connections and business transactions.
6. Check database/schema compatibility before rollback of stateful applications.
7. Preserve AnalysisRun, controller logs and GitLab/Argo CD evidence.
8. Record root cause, recovery time and missing guardrail.

## 18. Troubleshooting — twelve scenarios

| # | Symptom | Diagnostic focus | Safe response |
| --- | --- | --- | --- |
| 1 | Rollout CRD not found | Controller/CRD installation | Install pinned supported release |
| 2 | kubectl plugin command unavailable | Plugin installation/version | Use matching plugin or kubectl |
| 3 | Canary stuck at pause | Manual gate or analysis pending | Review approval and metrics |
| 4 | Weight not equal to HTTP percentage | Replica-based canary | Configure supported traffic router |
| 5 | Candidate unhealthy | Image, readiness, resources | Abort and inspect Pod events |
| 6 | AnalysisRun inconclusive | Low traffic or stale metrics | Improve metric/sample policy |
| 7 | Metrics show success despite errors | Service-wide query masks canary | Add candidate-specific labels |
| 8 | Blue-green preview unreachable | Service selectors/endpoints | Inspect Services and ReplicaSets |
| 9 | Cutover causes session errors | Connection draining/state | Review ingress and app sessions |
| 10 | Abort followed by bad rollout again | GitOps desired state unchanged | Revert Git and reconcile |
| 11 | Rollout consumes too much capacity | Overlapping stable/candidate Pods | Adjust capacity and surge |
| 12 | Argo CD and Rollouts appear to fight | Controller ownership/drift | Review integration and managed fields |

## 19. Rollback and cleanup

For durable recovery, revert the approved GitOps digest and let Argo CD reconcile. A Rollouts abort is an immediate mitigation but is not a replacement for updating the Git source of truth. A blue-green cutover rollback must account for connections, migrations and any state changes after promotion.

Clean up only disposable test namespaces, Rollouts, AnalysisRuns and Services. Before deleting a Rollout, inspect finalizers, Service selector ownership and persistent dependencies. Preserve redacted evidence according to policy.

## 20. Acceptance criteria

- [ ] Differences between rolling, canary and blue-green are understood.
- [ ] Argo Rollouts controller/CRD/plugin versions are validated.
- [ ] Basic canary Rollout starts from a healthy stable revision.
- [ ] Manual pause, promote and abort are exercised.
- [ ] Blue-green active and preview Services are validated.
- [ ] AnalysisRun executes against known-good metrics.
- [ ] Candidate-specific analysis limitations are documented.
- [ ] Replica weighting is not misrepresented as precise traffic routing.
- [ ] GitLab/Argo CD approval and immutable digest traceability are enforced.
- [ ] Failed candidate is aborted and GitOps desired state reverted.
- [ ] Release evidence records actual exposure, health and recovery.
- [ ] Production runbooks and rollback owners are documented.

## 21. Knowledge check

1. What is the difference between replica-weighted and traffic-weighted canaries?
2. Why is a manual pause useful even when metrics are automated?
3. How do active and preview Services behave in blue-green deployments?
4. Why might a service-wide success-rate metric hide a bad canary?
5. Why does aborting a Rollout not guarantee a durable GitOps rollback?
6. What risks remain after switching a blue-green active Service?
7. When is automatic rollback unsafe for a database-backed application?
8. How do GitLab, Argo CD and Argo Rollouts divide responsibilities?

## 22. References

- [Argo Rollouts Documentation](https://argo-rollouts.readthedocs.io/en/stable/)
- [Argo Rollouts Canary Strategy](https://argo-rollouts.readthedocs.io/en/stable/features/canary/)
- [Argo Rollouts Blue-Green Strategy](https://argo-rollouts.readthedocs.io/en/stable/features/bluegreen/)
- [Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Argo Rollouts Traffic Management](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

---

**Chapter 056 complete.** Next: **Chapter 057 — Argo Rollouts Canary Analysis, Traffic Routing and Automated Promotion**.
