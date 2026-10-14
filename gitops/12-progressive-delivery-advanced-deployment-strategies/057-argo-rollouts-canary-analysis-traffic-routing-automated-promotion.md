# Chapter 057 — Argo Rollouts Canary Analysis, Traffic Routing and Automated Promotion

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 12:** Progressive Delivery and Advanced Deployment Strategies  
**Chapter:** 057 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Release Managers

> **Safety:** All manifests and fault-injection labs target a disposable staging cluster. Example image digests, hostnames and metrics must be replaced and validated. Never use a canary experiment to send faulty responses to real customers.

## 1. Objectives

By the end of this chapter, you can:

1. Design a traffic-weighted canary using Argo Rollouts and a supported ingress or service mesh.
2. Separate stable and canary Services and understand controller ownership.
3. Implement Prometheus-backed AnalysisTemplates and AnalysisRuns.
4. Use success, failure, inconclusive and error outcomes to control rollout progression.
5. Apply minimum-sample, metric freshness, SLO and latency checks.
6. Integrate promotion with GitLab CI/CD, GitOps and Argo CD.
7. Test abort, recovery and stable-digest restoration safely.
8. Produce release evidence and operate troubleshooting runbooks.

## 2. Architecture

~~~text
GitLab source pipeline
   -> build, test, scan, sign immutable digest
   -> protected GitOps promotion MR
   -> Argo CD reconciles Rollout manifest
   -> Argo Rollouts controller
      -> stable ReplicaSet + stable Service
      -> canary ReplicaSet + canary Service
      -> supported ingress/service-mesh weighted routing
      -> Prometheus AnalysisRun
         -> success: next step / promote
         -> failure: abort and return traffic to stable
         -> inconclusive: pause / operator investigation
   -> observed digest + SLO + audit evidence
~~~

**Separation of concerns:** Argo CD reconciles desired state from Git. Argo Rollouts orchestrates ReplicaSets, traffic routing and analysis. The routing provider handles request distribution. Prometheus supplies metric observations. A GitLab job that succeeds is not proof of successful traffic migration.

## 3. Key distinctions

| Concept | Meaning | Operational caution |
| --- | --- | --- |
| setWeight | Desired canary exposure | Exact HTTP split requires supported router |
| setCanaryScale | Explicit canary replica scaling with supported traffic routing | Insufficient replicas can overload candidate |
| pause | Human or timed progression boundary | Indefinite pause requires an owner |
| AnalysisTemplate | Reusable metric definition | Validate query semantics and freshness |
| AnalysisRun | Actual metric evaluation execution | Retain outcome and diagnostic detail |
| failureLimit | Allowed failed measurements before failure | Does not override error/inconclusive handling |
| consecutiveSuccessLimit | Consecutive passing measurements required | Version support and interaction with count must be verified |
| abort | Stop failed rollout and restore stable traffic | Git desired image must still be repaired |

An AnalysisRun may become Successful, Failed, Inconclusive, Error or Running. Treat missing data and provider errors as potentially unsafe, not as implicit success.

## 4. Prerequisites

- Disposable staging Kubernetes cluster with a healthy Argo Rollouts controller and CRDs.
- Matching kubectl Argo Rollouts plugin.
- Argo CD staging Application with appropriately restricted AppProject.
- Prometheus accessible from the Rollouts controller.
- An instrumented test HTTP service exposing request count and latency metrics.
- Two signed/verified immutable image digests: known-good and candidate.
- Optional Istio control plane for the traffic-weighted lab.
- Sufficient capacity for stable and canary ReplicaSets concurrently.

~~~bash
kubectl config current-context
kubectl -n argo-rollouts get deploy,pods
kubectl get crd rollouts.argoproj.io analysistemplates.argoproj.io
kubectl -n demo-staging get rollouts,svc
kubectl -n monitoring get svc | grep prometheus
kubectl argo rollouts version
~~~

The Prometheus Service name and namespace vary by installation. Confirm actual endpoints rather than assuming the example address exists.

## 5. Safe repository structure

~~~text
gitops/
  apps/demo-web/
    base/
      rollout.yaml
      services.yaml
      analysis-template.yaml
      virtualservice.yaml
      destinationrule.yaml
    overlays/
      staging/kustomization.yaml
      prod/kustomization.yaml
  policies/
    progressive-delivery.rego
  runbooks/
    canary-abort.md
    telemetry-failure.md
  evidence/
    canary-release-template.md
~~~

Protect traffic-routing manifests, AnalysisTemplates, Argo CD Applications and rollout parameters with required review. Do not allow a release bot to modify both policy and release digest without independent approval.

## 6. Instrumentation contract

Use candidate-specific labels such as:

~~~text
http_requests_total{
  app="demo-web",
  revision="candidate",
  status="200"
}
http_request_duration_seconds_bucket{
  app="demo-web",
  revision="candidate",
  le="0.5"
}
~~~

The above are **illustrative metric names/labels**. Production instrumentation might use service-mesh destination workload labels, application version labels or other counters. Validate actual label values in Prometheus.

Avoid aggregating stable and candidate traffic together: a healthy stable population can mask a failing canary.

## 7. Canary traffic routing with Istio

This example assumes Istio is installed, sidecar or ambient traffic interception is correctly configured, and the Rollouts controller has permissions to modify the referenced VirtualService.

### Stable and canary Services

~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-stable
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
  name: demo-canary
  namespace: demo-staging
spec:
  selector:
    app: demo-web
  ports:
    - name: http
      port: 80
      targetPort: 8080
~~~

The Rollouts controller adjusts Service selectors to stable and canary ReplicaSets. Do not hard-code ReplicaSet hashes or independently mutate controller-managed selectors.

### Istio VirtualService

~~~yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  hosts:
    - demo-web.example.test
  gateways:
    - demo-gateway
  http:
    - name: primary
      route:
        - destination:
            host: demo-stable.demo-staging.svc.cluster.local
          weight: 100
        - destination:
            host: demo-canary.demo-staging.svc.cluster.local
          weight: 0
~~~

The referenced Gateway must exist and the host must resolve through the test ingress. The controller manages weights for the named route. Verify the precise VirtualService schema against the installed Istio version.

## 8. Canary Rollout manifest

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
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_VALID_64_HEX_DIGEST
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
      stableService: demo-stable
      canaryService: demo-canary
      trafficRouting:
        istio:
          virtualService:
            name: demo-web
            routes:
              - primary
      maxSurge: 1
      maxUnavailable: 0
      steps:
        - setWeight: 5
        - pause:
            duration: 2m
        - setWeight: 20
        - analysis:
            templates:
              - templateName: demo-canary-success
        - setWeight: 50
        - pause: {}
        - setWeight: 100
~~~

**Important:** This is a version-sensitive example, not a ready-to-apply production bundle. Replace the digest, configure Istio Gateway/routing, create the AnalysisTemplate below, and validate the manifest against your installed CRDs. A Rollout's initial deployment establishes a stable revision; a subsequent image change triggers canary steps.

The routing percentage is a target split, not a guarantee of exact request distribution over small samples.

## 9. Prometheus AnalysisTemplate

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: demo-canary-success
  namespace: demo-staging
spec:
  metrics:
    - name: candidate-success-rate
      interval: 30s
      count: 5
      failureLimit: 1
      successCondition: len(result) > 0 && result[0] >= 0.99
      failureCondition: len(result) > 0 && result[0] < 0.99
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc.cluster.local:9090
          query: |
            sum(rate(http_requests_total{
              app="demo-web",revision="candidate",status!~"5.."
            }[2m]))
            /
            clamp_min(
              sum(rate(http_requests_total{
                app="demo-web",revision="candidate"
              }[2m])),
              0.001
            )
~~~

**Caveat:** This example assumes a genuine \`revision="candidate"\` label is present on the observed requests. Argo Rollouts does not automatically add that label to your application metrics. If the query returns no series, the analysis may become Inconclusive or Error depending on provider behavior and expression evaluation. Explicitly define missing-data handling and test it before enabling automated promotion.

This success-rate expression counts all non-5xx statuses as success. If 4xx responses indicate failures for your API, change the query accordingly. A real production gate should also require sufficient request volume, representative cohorts, fresh telemetry and baseline comparison.

## 10. Metric design: volume, errors and latency

### Minimum candidate traffic

A 99% success rate from 10 requests is not statistically persuasive. Gate on a minimum sample size, for example a team-approved number of candidate requests during the analysis interval. Select thresholds using expected traffic and SLO/error-budget requirements rather than arbitrary universal defaults.

### Candidate error ratio

~~~promql
sum(rate(http_requests_total{app="demo-web",revision="candidate",status=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{app="demo-web",revision="candidate"}[5m])), 0.001)
~~~

### Candidate P95 latency

~~~promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(http_request_duration_seconds_bucket{
      app="demo-web",revision="candidate"
    }[5m])
  )
)
~~~

Validate the histogram bucket units and labels. The query assumes a classic histogram; native histograms use different PromQL. Compare candidate to stable where appropriate, and account for changes in request mix.

## 11. AnalysisRun outcomes and safety policy

| Result | Meaning | Release action |
| --- | --- | --- |
| Successful | Required metric conditions satisfied | Proceed to next step |
| Failed | Metric failure threshold reached | Abort candidate rollout |
| Inconclusive | No definitive outcome | Pause for operator decision |
| Error | Provider/query/controller error | Hold or abort according to policy |
| Running | Analysis not finished | Wait; do not promote early |

Set timeouts and escalation owners. Never treat Prometheus unavailability as a reason to silently skip an SLO gate.

## 12. Lab A — Verify controller, CRDs and metrics

1. Confirm Rollouts controller and CRDs are healthy.
2. Confirm test service produces request/latency metrics.
3. Execute the candidate-specific PromQL in Prometheus.
4. Verify expected time series and sample volume.
5. Confirm metrics disappear or become insufficient when no candidate receives traffic.
6. Record the chosen missing-data behavior.

~~~bash
kubectl -n argo-rollouts get deploy,pods
kubectl -n demo-staging get analysistemplates
kubectl -n demo-staging get rollouts
kubectl -n demo-staging get analysisruns
~~~

**Pass:** metric queries are grounded in real series and failure/missing-data behavior is documented.

## 13. Lab B — Traffic-weighted canary

1. Install/validate Istio in the disposable staging environment.
2. Create stable/canary Services and the VirtualService.
3. Deploy a healthy stable Rollout revision.
4. Update the GitOps image digest to a new reviewed candidate.
5. Confirm Argo Rollouts changes the VirtualService weights.
6. Generate enough synthetic test traffic to compare observed routing.
7. Observe pauses, AnalysisRuns and promotion decisions.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get virtualservice demo-web -o yaml
kubectl --context STAGING_CONTEXT -n demo-staging get svc demo-stable demo-canary -o yaml
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web --watch
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
~~~

**Pass:** requested routing weights change as expected and test traffic is distributed approximately according to policy. Measure actual exposure instead of assuming a perfect split.

## 14. Lab C — Automated failure and abort

1. Establish a healthy stable image.
2. Promote a deliberately faulty staging candidate.
3. Generate enough candidate traffic for the error metric to evaluate.
4. Observe AnalysisRun failure.
5. Verify the Rollout aborts and stable routing is restored.
6. Revert the GitOps image digest to the known-good revision.
7. Validate the running image and smoke tests.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
kubectl --context STAGING_CONTEXT -n demo-staging describe analysisrun ANALYSIS_RUN_NAME
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web
kubectl --context STAGING_CONTEXT -n demo-staging get virtualservice demo-web -o yaml
~~~

**Pass:** failure is detected, candidate exposure stops, and GitOps desired state is corrected. Record detection time and recovery time.

## 15. Lab D — Missing telemetry / inconclusive analysis

1. Use a disposable metrics query with a deliberately nonexistent candidate label.
2. Start a test analysis against the missing series.
3. Observe whether the AnalysisRun becomes Inconclusive, Error or another status.
4. Confirm the release does not automatically promote on missing evidence.
5. Restore the real metric query and re-run analysis.

**Pass:** the release is held safely, operators can diagnose the missing telemetry, and no silent fail-open path exists.

## 16. Lab E — Manual promotion and approval boundary

1. Create a GitOps promotion MR with a new immutable digest.
2. Obtain staging review and merge.
3. Pause the canary at the configured manual step.
4. Confirm approval and release evidence are complete.
5. Promote the Rollout only with the authorized staging operator identity.
6. Confirm final stable revision, observed image digest and SLOs.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts promote demo-web
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-web
~~~

**Pass:** manual promotion is denied for unauthorized actors and succeeds only after approved evidence is available.

## 17. Lab F — Capacity and overload testing

In a disposable environment:

1. Record baseline stable Pod CPU/memory and response time.
2. Start a 5% canary with one candidate replica.
3. Generate representative synthetic traffic.
4. Observe whether candidate saturation differs from stable.
5. Adjust replica count or setCanaryScale under reviewed configuration.
6. Repeat the test and record candidate-specific latency and errors.

**Pass:** the team understands that low traffic weight does not guarantee low per-Pod load if the candidate has too few replicas.

## 18. GitLab CI/CD and GitOps promotion workflow

A release pipeline should:

1. Build once, test, scan, sign and publish an immutable digest.
2. Open a GitOps MR changing only the intended Rollout image digest.
3. Run manifest/schema/policy validation.
4. Require approvals and check the effective release window.
5. Merge protected GitOps state.
6. Allow Argo CD to reconcile the approved revision.
7. Observe Rollouts steps and AnalysisRuns.
8. Promote only when analysis and authorization pass.
9. Archive actual routing weights, observed digest and SLO results.
10. Revert GitOps desired state after abort when necessary.

A GitLab manual job is **not automatically** a gate for Argo CD auto-sync. Enforce authorization at the protected Git merge or another true deployment boundary.

## 19. Production release evidence

~~~text
Change ID:
Source commit:
Image digest:
GitOps MR and approvers:
GitOps commit:
Argo CD Application and revision:
Rollout name:
Stable/canary ReplicaSet hashes:
Traffic router and VirtualService route:
Requested and observed canary exposure:
AnalysisTemplate version:
AnalysisRun ID and result:
Candidate request count:
Candidate 5xx rate:
Candidate P95 latency:
Stable baseline:
Promotion/abort actor and time:
Observed final image digest:
Rollback Git commit:
Recovery duration:
Audit archive reference:
~~~

Retain redacted evidence in an approved, access-controlled archive. Do not store service-mesh credentials, API tokens or customer payloads.

## 20. Production runbook — canary release

**Preflight:** confirm stable baseline, candidate digest, controller health, route ownership, Prometheus query validity, sample volume, capacity and rollback plan.

**Execute:** merge the approved GitOps MR and confirm Argo CD sync. Watch the candidate ReplicaSet and traffic route.

**Analyze:** evaluate candidate-specific errors, P95/P99 latency, saturation, business transaction success and AnalysisRun outcome.

**Promote:** advance only when analysis succeeds and approval policy is satisfied.

**Close:** confirm final revision, observed image, service health and evidence retention.

## 21. Production runbook — failed analysis

1. Stop additional promotions.
2. Record current traffic weights, candidate digest and AnalysisRun status.
3. Distinguish actual application failure from missing/bad telemetry.
4. Abort the Rollout if candidate impact is unacceptable.
5. Revert the GitOps desired digest to a reviewed known-good version.
6. Confirm stable traffic routing, application health and observed digest.
7. Preserve metrics, controller logs, GitLab and Argo CD evidence.
8. Correct the underlying metric or application defect before retry.

## 22. Troubleshooting — twelve scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | VirtualService weight never changes | Router integration or RBAC | Verify Rollout trafficRouting and controller permissions |
| 2 | Canary receives no requests | Gateway/host/routing mismatch | Trace ingress and Service endpoints |
| 3 | Observed traffic differs from weight | Low sample size/sticky sessions | Measure sufficient requests and cohorts |
| 4 | AnalysisRun Error | Prometheus unreachable/query invalid | Repair provider and hold release |
| 5 | AnalysisRun Inconclusive | Missing series/insufficient samples | Fix instrumentation and retry |
| 6 | Canary failures hidden | Stable+canary metrics combined | Add candidate-specific selectors |
| 7 | Candidate P95 spikes | Too few replicas/CPU throttling | Inspect capacity and scale |
| 8 | Rollout stuck at pause | Manual approval or analysis pending | Review policy and ownership |
| 9 | Rollout repeatedly fails after abort | Git desired digest unchanged | Revert GitOps and reconcile |
| 10 | Argo CD OutOfSync during rollout | Controller-managed fields/drift | Review integration and diff configuration |
| 11 | Promotion occurred during freeze | Gate not at effective boundary | Enforce protected merge/sync |
| 12 | Analysis succeeds on stale metrics | Query freshness/traffic labels | Add freshness and minimum-volume checks |

## 23. Rollback and cleanup

Aborting an Argo Rollouts canary is an immediate mitigation, not a permanent GitOps revert. Restore the approved stable digest in Git, merge through the correct workflow, reconcile, and verify actual running image and application health.

Delete only disposable staging resources. Inspect Services, VirtualServices, finalizers and controller ownership before cleanup. Do not remove shared Istio gateways or Prometheus installations.

## 24. Acceptance criteria

- [ ] Argo Rollouts, Istio and Prometheus compatibility verified.
- [ ] Stable and canary Services route to correct ReplicaSets.
- [ ] Traffic weights are controlled by Argo Rollouts.
- [ ] Candidate-specific metrics exist and are validated.
- [ ] Minimum traffic/sample and metric freshness policies defined.
- [ ] Successful analysis advances a healthy canary.
- [ ] Failed analysis aborts a faulty canary.
- [ ] Missing telemetry cannot silently approve promotion.
- [ ] Manual approval boundary is tested with unauthorized identity.
- [ ] GitOps desired state is restored after abort.
- [ ] Capacity testing identifies candidate saturation risk.
- [ ] Release evidence includes routing, analysis and actual digest.
- [ ] Runbooks have an owner and measurable recovery objective.

## 25. Knowledge check

1. Why can replica weighting differ from HTTP traffic weighting?
2. Which component changes Istio VirtualService weights?
3. What happens when candidate-specific Prometheus labels do not exist?
4. Why must a success-rate gate also consider minimum request volume?
5. What distinguishes Failed from Inconclusive analysis?
6. Why does abort not guarantee a durable rollback?
7. How can a small canary percentage still overload the candidate?
8. What evidence is needed before promoting a canary to 100%?

## 26. References

- [Argo Rollouts Canary Strategy](https://argo-rollouts.readthedocs.io/en/stable/features/canary/)
- [Argo Rollouts Traffic Management](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/)
- [Argo Rollouts Istio Integration](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Argo Rollouts AnalysisTemplate](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Prometheus Querying](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Istio Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)

---

**Chapter 057 complete.** Next: **Chapter 058 — Blue-Green Deployment, Preview Validation and Zero-Downtime Cutover Operations**.
