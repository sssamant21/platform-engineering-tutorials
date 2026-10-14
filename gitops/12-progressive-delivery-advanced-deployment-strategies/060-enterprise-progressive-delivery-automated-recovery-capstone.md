# Chapter 060 — Enterprise Progressive Delivery and Automated Recovery Capstone

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 12:** Progressive Delivery and Advanced Deployment Strategies  
**Chapter:** 060 / 100 — Part 12 Capstone  
**Audience:** Platform Engineers, SREs, DevSecOps, Release Managers and Application Engineers

> **Safety:** All executable labs use isolated staging or production-simulation systems, synthetic traffic and disposable data. Do not run failure injection or uncontrolled traffic cutovers against customer workloads. A deployment rollback cannot undo database writes or external side effects.

## 1. Mission and learning objectives

Build and validate a governed progressive-delivery platform that can:

1. Build, scan, sign and promote a single immutable application artifact.
2. Deploy through Argo CD while Argo Rollouts controls release exposure.
3. Run traffic-weighted canaries with candidate-specific Prometheus analysis.
4. Execute blue-green preview validation and authorized cutover.
5. Control runtime feature exposure with deterministic cohorts and kill switches.
6. Detect unhealthy releases and abort without blindly reverting stateful changes.
7. Restore GitOps desired state and verify actual running digests.
8. Produce auditable evidence, SLO measurements and recovery acceptance results.

**Chapters integrated:** 056 fundamentals, 057 traffic routing and analysis, 058 blue-green cutover, 059 feature flags and experimentation.

## 2. Architecture

~~~text
Source MR -> GitLab CI test/scan/sign -> OCI immutable digest
                         |
                 GitOps promotion MR
                         |
               Protected branch + approvals
                         |
                       Argo CD
                         |
                  Argo Rollouts
                  /           \
             stable RS      candidate RS
                  \           /
                Istio traffic routing
                         |
              Synthetic / test requests
                         |
              Prometheus + AnalysisRun
                         |
             +-----------+------------+
             |                        |
         pass/approve             fail/inconclusive
             |                        |
         promote                 hold / abort
             |                        |
        feature flag ramp       GitOps revert or
             |                  approved roll-forward
         SLO validation                |
             +-----------+------------+
                         |
                   evidence archive
~~~

Argo CD reconciles Git; Argo Rollouts manages progressive exposure and controller-owned routing; the flag provider governs runtime behavior; monitoring verifies actual user-facing outcomes. Do not give multiple controllers write ownership over the same Service selector or traffic weights.

## 3. Capstone prerequisites

| Component | Minimum staging requirement |
| --- | --- |
| Kubernetes | Disposable cluster/namespaces, adequate headroom |
| Argo Rollouts | Healthy controller, CRDs and matching kubectl plugin |
| Argo CD | Test Application and scoped AppProject |
| GitLab | Protected GitOps branch, reviewers, CI runners |
| Registry | Two or more verifiable immutable image digests |
| Istio | Supported traffic-routing installation for canary exercise |
| Prometheus | Candidate/stable error, latency and volume metrics |
| Feature flags | Staging provider or test adapter with audit and kill switch |
| Observability | Logs, events, dashboards, synthetic smoke tests |
| Data safety | Stateless demo plus database migration tabletop |

~~~bash
kubectl config current-context
kubectl -n argo-rollouts get deploy,pods
kubectl get crd rollouts.argoproj.io analysistemplates.argoproj.io
kubectl -n demo-staging get rollouts,svc,analysisruns
argocd app list
kubectl argo rollouts version
~~~

**Stop** if context, cluster identity or target namespace is uncertain. Record all tool versions and supported integration combinations.

## 4. Repository design

~~~text
capstone/
  source/
    app/
    tests/
    Dockerfile
    .gitlab-ci.yml
  gitops/
    apps/demo-web/
      canary/
        rollout.yaml
        stable-canary-services.yaml
        virtualservice.yaml
        analysis-template.yaml
      bluegreen/
        rollout.yaml
        active-preview-services.yaml
        analysis-preview.yaml
      overlays/staging/
      overlays/prod-sim/
    argocd/
    policies/
    changes/
  flags/
    staging.json
    experiment-plan.md
  ci/
    verify-digest.sh
    validate-manifests.sh
    propose-promotion.sh
  runbooks/
    canary-abort.md
    bluegreen-recovery.md
    feature-kill-switch.md
  evidence/
    capstone-template.md
~~~

Use **separate staging namespaces or separate Rollout names** for canary and blue-green exercises. Never apply two Rollout definitions with the same name expecting both strategies to run concurrently.

## 5. Artifact and change-control contract

Record:

~~~text
Release ID:
Source SHA and GitLab pipeline:
Immutable OCI image digest:
Signature/provenance/SBOM reference:
GitOps MR and approvers:
Approved environment and change window:
Argo CD Application and target revision:
Stable and candidate digest:
Release strategy:
Rollback owner:
Database compatibility:
SLO thresholds and sample-size policy:
Evidence retention location:
~~~

A mutable image tag is not acceptable proof of artifact identity. The GitOps MR must change the approved digest, not rebuild a different artifact for each environment.

Protected Git merge and Argo CD sync authorization are distinct boundaries. A GitLab manual job does not automatically prevent Argo CD auto-sync after merge.

## 6. GitLab CI/CD skeleton

This example is an integration skeleton. Internal build/sign/verification scripts and approved pinned CI images must be supplied.

~~~yaml
stages: [test, build, verify, propose]

unit_tests:
  stage: test
  image: python:3.12-slim
  script:
    - python -m pip install -r requirements.txt
    - python -m pytest -q

build_image:
  stage: build
  image: registry.example.internal/ci/secure-builder:PINNED_VERSION
  script:
    - ./ci/build-image.sh
  artifacts:
    paths: [release.env]
    reports:
      dotenv: release.env
    expire_in: 7 days

verify_release:
  stage: verify
  image: registry.example.internal/ci/security-tools:PINNED_VERSION
  needs:
    - job: build_image
      artifacts: true
  script:
    - ./ci/verify-digest.sh
    - ./ci/validate-manifests.sh

propose_staging:
  stage: propose
  image: registry.example.internal/ci/gitlab-client:PINNED_VERSION
  resource_group: staging-promotion
  needs:
    - job: build_image
      artifacts: true
    - job: verify_release
  script:
    - ./ci/propose-promotion.sh staging
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

The dotenv artifact must contain only non-secret metadata. Never export registry passwords, GitLab tokens, signing keys or kubeconfigs as artifacts. Resource groups serialize jobs within their scope, but do not replace cross-project promotion ordering and stale-revision checks.

## 7. Release safety controls

| Control | Enforcement point | Validation |
| --- | --- | --- |
| Artifact signature/digest | CI verification and admission | Reject unknown digest |
| Protected production overlay | GitLab branch/MR rules | Unauthorized merge denied |
| AppProject destination | Argo CD | Unauthorized cluster/namespace denied |
| Traffic route ownership | Rollouts controller and RBAC | Manual mutation denied |
| Metrics gate | AnalysisRun and release policy | Bad candidate aborts |
| Flag activation | Feature provider RBAC | Unauthorized targeting denied |
| Emergency change | Approved release exception | Time-bound, audited |
| Data compatibility | DBRE/application review | Unsafe rollback prohibited |

A successful CI job or Argo CD Healthy status alone does not prove an application is safe for customers.

## 8. Canary Rollout reference

Assumes an Istio VirtualService named demo-web with route primary and two Services demo-stable and demo-canary, all in the staging namespace.

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-canary
  namespace: demo-staging
spec:
  replicas: 4
  selector:
    matchLabels:
      app: demo-canary
  template:
    metadata:
      labels:
        app: demo-canary
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
              - templateName: demo-canary-analysis
        - setWeight: 50
        - pause: {}
        - setWeight: 100
~~~

Service selectors must match app: demo-canary as bootstrap labels; the Rollouts controller then manages stable/canary ReplicaSet selection. Configure the actual Istio Gateway, VirtualService and host before deploying. Exact traffic weights require a supported routing provider and adequate request samples.

## 9. Candidate-specific Prometheus analysis

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: demo-canary-analysis
  namespace: demo-staging
spec:
  metrics:
    - name: candidate-error-rate
      interval: 30s
      count: 5
      failureLimit: 1
      successCondition: len(result) > 0 && result[0] <= 0.01
      failureCondition: len(result) > 0 && result[0] > 0.01
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc.cluster.local:9090
          query: |
            sum(rate(http_requests_total{app="demo-web",revision="candidate",status=~"5.."}[2m]))
            /
            clamp_min(sum(rate(http_requests_total{app="demo-web",revision="candidate"}[2m])),0.001)
~~~

This is a **demonstration**, not a complete production analysis. The application or service mesh must really export revision=candidate. Verify the actual query returns the expected series. Add minimum sample volume, telemetry freshness, missing-data handling, business SLOs and baseline comparison before enabling unattended promotion.

AnalysisRun states include Running, Successful, Failed, Inconclusive and Error. Missing or invalid metrics must not silently count as success.

## 10. Blue-green reference

Use a separate Rollout named demo-bluegreen and Services demo-active and demo-preview.

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-bluegreen
  namespace: demo-staging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: demo-bluegreen
  template:
    metadata:
      labels:
        app: demo-bluegreen
    spec:
      terminationGracePeriodSeconds: 60
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
      scaleDownDelaySeconds: 120
      prePromotionAnalysis:
        templates:
          - templateName: demo-preview-analysis
~~~

Create matching Services and a real preview-specific AnalysisTemplate before applying. The initial Rollout establishes stable state; a second digest triggers preview and promotion. Active Service cutover is not a guarantee that all TCP sessions survive.

## 11. Feature-flag contract

Use a provider-backed configuration or staging adapter, not an unimplemented Kubernetes CRD.

~~~json
{
  "flag": "new-search",
  "environment": "staging",
  "owner": "search-platform",
  "defaultEnabled": false,
  "targetPercent": 5,
  "assignmentKey": "pseudonymous-user-id",
  "killSwitch": false,
  "expiresAt": "2026-11-30T00:00:00Z"
}
~~~

Use deterministic assignment with stable identity and salt. Do not expose raw user identifiers in Prometheus labels. A feature flag is not an authorization mechanism. A kill switch stops future feature evaluation but does not reverse writes, messages, charges or other side effects.

## 12. Observability and SLO gates

| Metric | Canary | Blue-green | Feature flag |
| --- | --- | --- | --- |
| Observed digest | Stable/candidate | Active/preview | Application revision |
| 5xx rate | Candidate-specific | Preview then active | Control/treatment |
| P95/P99 | Candidate versus stable | Preview then active | Variant-specific |
| Request volume | Minimum sample | Preview test and active load | Exposure count |
| Readiness | Candidate ReplicaSet | Active/preview Pods | Dependency health |
| Business metric | Canary transactions | Post-cutover success | Experiment outcome |
| Missing data | Hold/abort | Deny promotion | Pause ramp |
| Rollback action | Abort + Git revert | Cutover recovery + Git revert | Kill switch; possibly code rollback |

Record metric labels, units, time windows, expected baseline and owners. Low-traffic experiments need explicit inconclusive handling.

## 13. Lab A — Platform readiness and baseline

1. Verify Argo CD, Rollouts, Istio, Prometheus and registry connectivity.
2. Deploy a healthy stable digest to staging.
3. Run synthetic requests and capture errors, P95/P99 and capacity.
4. Verify controller and CRD versions are compatible.
5. Confirm unauthorized users cannot mutate routing resources.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get rollouts,svc,pods
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
argocd app get demo-staging --refresh
~~~

**Pass:** baseline is healthy and the exact stable digest is recorded.

## 14. Lab B — Traffic-weighted canary

1. Validate stable/canary Services and Istio VirtualService.
2. Promote a new reviewed digest through a staging GitOps MR.
3. Observe 5%, 20% and 50% traffic steps.
4. Generate sufficient synthetic traffic and compare actual distribution.
5. Verify candidate-specific metrics and AnalysisRun outcome.
6. Promote after authorized approval.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-canary --watch
kubectl --context STAGING_CONTEXT -n demo-staging get virtualservice demo-web -o yaml
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
~~~

**Pass:** routing follows reviewed steps, analysis is grounded in actual candidate metrics and final digest is verified.

## 15. Lab C — Faulty canary and automated abort

1. Establish known-good stable revision.
2. Introduce a deliberately failing candidate digest.
3. Generate synthetic traffic until analysis has sufficient samples.
4. Verify the candidate error threshold is exceeded.
5. Observe failed AnalysisRun and aborted Rollout.
6. Revert GitOps to the approved stable digest.
7. Confirm stable routing and service recovery.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get analysisruns
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-canary
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts abort demo-canary
~~~

**Pass:** faulty candidate exposure stops, desired GitOps state is repaired and recovery time is measured.

## 16. Lab D — Blue-green preview and manual cutover

1. Deploy a separate blue-green Rollout with healthy stable image.
2. Update to a second immutable candidate digest.
3. Confirm preview Service routes to candidate while active stays stable.
4. Run preview smoke tests and pre-promotion analysis.
5. Require independent staging approval.
6. Promote and observe active Service selector.
7. Verify running digest, latency and business tests.

~~~bash
kubectl --context STAGING_CONTEXT -n demo-staging get svc demo-active demo-preview -o yaml
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts get rollout demo-bluegreen
kubectl --context STAGING_CONTEXT -n demo-staging argo rollouts promote demo-bluegreen
~~~

**Pass:** active traffic changes only after authorization and preview validation.

## 17. Lab E — Connection-draining regression

1. Generate long-lived synthetic connections and steady request load.
2. Record connection resets and response latency.
3. Perform an authorized blue-green cutover.
4. Observe EndpointSlice updates and old ReplicaSet lifetime.
5. Compare drain settings with termination grace period.
6. Tune and retest.

**Pass:** cutover interruption rate is measured and documented; zero downtime is not asserted without evidence.

## 18. Lab F — Progressive feature activation

1. Deploy application code with feature disabled.
2. Enable for synthetic allowlist only.
3. Increase eligible cohorts to 1%, 5%, then 10%.
4. Verify stable deterministic assignment.
5. Compare control/treatment errors, latency and business success.
6. Record approval and actual exposure at every step.

**Pass:** each ramp is evidence-based, and missing telemetry pauses the rollout.

## 19. Lab G — Kill switch versus deployment rollback

1. Inject a staging-only feature defect.
2. Detect treatment error regression.
3. Activate authorized kill switch and measure propagation.
4. Confirm new evaluations are disabled.
5. Separately simulate a code defect not controlled by the flag.
6. Abort the Rollout and revert GitOps digest.
7. Evaluate whether any stateful side effects require separate recovery.

**Pass:** operators select the appropriate mitigation for each defect class.

## 20. Lab H — Missing telemetry and inconclusive analysis

1. Intentionally use a nonexistent candidate metric label in a disposable AnalysisTemplate.
2. Start a candidate rollout and observe the AnalysisRun.
3. Verify the release does not promote on absent data.
4. Repair instrumentation and re-run the test.
5. Record timeout and escalation policy.

**Pass:** the system fails safely and surfaces missing telemetry.

## 21. Lab I — Stateful rollback tabletop

**Scenario:** candidate application writes a schema incompatible with the stable version.

1. Identify the first incompatible write.
2. Determine whether traffic rollback would cause data corruption.
3. Check database backups/PITR, RPO and RTO.
4. Design expand-and-contract or compatible roll-forward.
5. Account for CDC, consumers, queues and external effects.
6. Produce a DBRE-approved recovery decision.

**Pass:** the team does not blindly revert an incompatible data change.

## 22. Lab J — Governance, recovery and evidence drill

1. Attempt unauthorized production-simulation GitOps merge.
2. Attempt unauthorized Rollouts promotion.
3. Attempt direct modification of controller-owned routing fields.
4. Verify each action is denied at its effective boundary.
5. Simulate a failed release and perform approved recovery.
6. Archive redacted metrics, revision/digest, approvals and recovery timing.

**Pass:** enforcement and evidence are independently verifiable, not merely documented.

## 23. Ten troubleshooting scenarios

| # | Symptom | Investigation | Safe recovery |
| --- | --- | --- | --- |
| 1 | Canary weight never changes | Istio route/RBAC/controller | Fix routing integration |
| 2 | Analysis says success but canary fails | Aggregated metrics | Use candidate-specific series |
| 3 | Analysis is Inconclusive | Missing data/low traffic | Hold and repair instrumentation |
| 4 | Candidate overload at 5% | Too few candidate replicas | Scale and retest |
| 5 | Blue-green preview unreachable | Service selectors/readiness | Inspect endpoints and ReplicaSets |
| 6 | 5xx spike during cutover | Connection draining | Tune shutdown and proxy behavior |
| 7 | Flag disable not propagated | SDK cache/provider outage | Verify revision and fallback |
| 8 | Rollout reintroduces bad image | Git desired state unchanged | Revert GitOps and reconcile |
| 9 | Rollback breaks database reads | Incompatible migration | DBRE-led roll-forward/recovery |
| 10 | Unauthorized release succeeds | Wrong approval boundary | Protect Git merge and runtime RBAC |

## 24. Production runbook — governed progressive release

**Preflight:** verify artifact digest/signature, protected GitOps MR, approvers, change window, metrics, sample-size policy, capacity, database compatibility and rollback owner.

**Start:** merge approved GitOps revision and reconcile Argo CD. Observe Argo Rollouts candidate, route and analysis.

**Progress:** advance canary weight or blue-green promotion only after valid analysis and authorization. Ramp feature exposure independently after deployment health is established.

**Observe:** monitor candidate/active errors, P95/P99, saturation, business transactions, sample ratios and flag provider health.

**Close:** confirm final running digest, healthy service, expected feature state, evidence archive and release-owner sign-off.

## 25. Production runbook — automated failure and recovery

1. Declare incident and freeze further promotions.
2. Record Git revision, stable/candidate digests, traffic weights and AnalysisRun.
3. Identify whether failure is code, configuration, traffic routing, telemetry, feature or stateful.
4. Abort candidate or activate feature kill switch as appropriate.
5. Assess database/schema compatibility and persistent side effects.
6. Revert GitOps to approved digest or roll forward with reviewed fix.
7. Verify observed workload digest, traffic route, smoke tests and SLO recovery.
8. Preserve evidence and document root cause and prevention work.

Do not equate an Argo Rollouts abort or a flag disable with permanent GitOps or data rollback.

## 26. Production runbook — progressive-delivery controller outage

1. Determine whether existing application traffic is healthy.
2. Inspect Argo Rollouts controller health, leader election, CRDs and permissions.
3. Preserve Rollout/AnalysisRun state and logs.
4. Avoid direct edits to managed Service selectors unless following an approved emergency runbook.
5. Restore the controller from a tested pinned version and configuration.
6. Reconcile one canary application before broad rollout resumption.
7. Confirm traffic weights, ReplicaSet health and audit events.

## 27. Evidence template

~~~text
Capstone ID and change ticket:
Source commit / CI pipeline:
Signed image digest and SBOM:
GitOps MR, reviewers and commit:
Argo CD Application and revision:
Rollout strategy and stable/candidate ReplicaSets:
Traffic router and actual weights:
AnalysisTemplate/AnalysisRun IDs and outcomes:
Candidate/active request count, errors and P95/P99:
Blue-green preview test and cutover timestamp:
Feature flag config revision and cohort exposure:
Kill switch state and actor:
Database compatibility decision:
Failure injection and mitigation:
Observed final running digest:
Recovery duration versus RTO:
Evidence archive location:
Reviewer and follow-up owner:
~~~

## 28. Scored acceptance assessment

| Domain | Points | Required evidence |
| --- | ---: | --- |
| Immutable artifact, CI and GitOps governance | 15 | Signed digest, protected promotion MR |
| Canary routing and analysis | 20 | Actual weights and candidate-specific metrics |
| Blue-green preview and cutover | 15 | Active/preview proof, drain measurements |
| Feature flags and experiment safety | 15 | Deterministic cohorts and kill switch |
| Automated failure detection and recovery | 20 | Abort, GitOps revert and measured recovery |
| Observability and audit evidence | 10 | SLO dashboard, revision/digest correlation |
| Runbooks and operational ownership | 5 | Reviewed procedures and contacts |
| **Total** | **100** | |

**Pass:** at least **85/100** plus every critical control: no unauthorized promotion, no unverified artifact, no fail-open missing telemetry, no unsafe stateful rollback, and a demonstrated known-good recovery. Numeric score cannot override a critical failure.

## 29. Final acceptance checklist

- [ ] One immutable artifact is promoted through protected GitOps.
- [ ] Argo CD and Argo Rollouts responsibilities are separated.
- [ ] Canary routing weights and actual exposure are measured.
- [ ] Candidate-specific Prometheus analysis is validated.
- [ ] Failed and inconclusive analyses do not silently promote.
- [ ] Blue-green preview and authorized cutover are exercised.
- [ ] Connection-draining impact and capacity are measured.
- [ ] Feature cohorts are deterministic and privacy-conscious.
- [ ] Kill switch is tested and propagation measured.
- [ ] Failed candidate is aborted and GitOps desired state restored.
- [ ] Stateful rollback safety and RPO/RTO are reviewed.
- [ ] Unauthorized changes are denied and audited.
- [ ] Ten labs have pass/fail results and owners.
- [ ] Release evidence and recovery runbooks are complete.
- [ ] Platform, security and release owners sign off.

## 30. Knowledge check

1. Why do Argo CD and Argo Rollouts have separate responsibilities?
2. What is the difference between replica and traffic weighting?
3. Why must analysis isolate the candidate revision?
4. Why can a blue-green preview pass while cutover fails?
5. What is the effect of sticky sessions and connection draining?
6. Why is feature assignment different from actual exposure?
7. Why does a kill switch not reverse committed data writes?
8. What is the correct recovery after an Argo Rollouts abort under GitOps?
9. Why must missing telemetry fail safely?
10. Which evidence proves that the approved digest actually ran?

## 31. References

- [Argo Rollouts Canary](https://argo-rollouts.readthedocs.io/en/stable/features/canary/)
- [Argo Rollouts Blue-Green](https://argo-rollouts.readthedocs.io/en/stable/features/bluegreen/)
- [Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Argo Rollouts Istio Integration](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [OpenFeature Specification](https://openfeature.dev/specification/)
- [Prometheus Querying](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [GitLab Protected Branches](https://docs.gitlab.com/user/project/repository/branches/protected/)

---

**Chapter 060 complete — Part 12 complete (Chapters 056–060).**

**Next:** Chapter 061 — GitOps Secrets Management, External Secrets and Workload Identity Fundamentals, beginning Part 13: Secrets, Policy and Workload Identity.