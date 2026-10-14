# Chapter 059 — Feature Flags, Experimentation and Progressive Release Observability

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 12:** Progressive Delivery and Advanced Deployment Strategies  
**Chapter:** 059 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Application Engineers and Release Managers

> **Lab safety:** Use disposable staging systems and synthetic identities. Never run uncontrolled experiments on real users, place secrets in flags, or assume disabling a feature reverses database writes or other side effects.

## 1. Learning objectives

By completing this chapter you will:

1. Distinguish deployment, release, feature exposure and experiment assignment.
2. Design safe feature flags, kill switches, prerequisites and expiry policies.
3. Implement deterministic cohort assignment and audit targeting decisions.
4. Connect GitLab, GitOps and Argo Rollouts to application feature exposure.
5. Define experiment guardrails, telemetry, SLOs and decision criteria.
6. Prevent sample-ratio mismatch, metric contamination and sticky-assignment failures.
7. Practice progressive activation, emergency disable and rollback.
8. Create release evidence and production-ready runbooks.

## 2. Progressive delivery control planes

~~~text
Source MR -> GitLab build/test/scan -> immutable digest
                      |
               protected GitOps MR
                      |
                   Argo CD
                      |
                 Argo Rollouts
                 /          \
          stable version  candidate version
                      |
            application feature SDK
                      |
        flag service / local fallback
                      |
       deterministic cohort assignment
                      |
       telemetry + experiment analysis
                      |
        continue / hold / kill switch
~~~

**Important distinction:** Argo Rollouts controls deployment revision and traffic exposure; a feature flag controls behavior *inside* an application version. A 10% canary plus a 10% feature flag does not necessarily yield exactly 1% of users, because targeting and routing populations may be correlated or sticky.

## 3. Deployment versus feature release

| Control | Typical owner | Changes | Rollback behavior |
| --- | --- | --- | --- |
| GitLab build | CI platform | Artifact | Rebuild or select previous digest |
| GitOps promotion | Release/platform | Desired revision | Reviewed Git revert |
| Argo Rollouts | Progressive delivery controller | Replica/traffic exposure | Abort candidate, restore stable |
| Feature flag | Application/product with governance | Runtime feature behavior | Disable flag or restore targeting |
| Experiment | Product/data/SRE | Cohort assignment and analysis | Stop experiment, preserve results |

A feature flag kill switch is often faster than a deployment rollback, but cannot undo already committed writes, emails, charges or other external effects.

## 4. Feature flag taxonomy and ownership

| Flag type | Example | Expected lifecycle |
| --- | --- | --- |
| Release flag | New search UI | Temporary, remove after rollout |
| Operational kill switch | Disable expensive enrichment | Retained with periodic tests |
| Experiment flag | Variant A/B | Time-boxed with analysis plan |
| Permission flag | Enable capability for approved tenant | Governed authorization boundary |
| Migration flag | Switch read path to new store | Explicit dual-read/write compatibility plan |

**Security:** flags must never be the only authorization mechanism for protected actions. Server-side authorization, IAM, RBAC and data-access checks remain mandatory.

Document each flag with owner, purpose, environment, creation/expiry date, default, failure mode, allowed cohorts, audit sensitivity, cleanup issue and rollback instructions.

## 5. Flag evaluation contract

A safe feature evaluation has:

- **Stable identity:** pseudonymous user or tenant identifier appropriate for the use case.
- **Deterministic assignment:** the same identity stays in the same cohort during an experiment.
- **Versioned configuration:** auditable flag revision and rule changes.
- **Fail-safe fallback:** deliberate behavior when the flag service is unavailable.
- **Exposure event:** emitted only when the user actually encounters the decision.
- **Telemetry:** errors, latency, saturation and business outcomes by variant.
- **Privacy controls:** avoid raw personal identifiers in logs or metrics labels.

Do not use Python's built-in hash() for cross-process assignment: its hash randomization can change bucket placement between processes.

## 6. Runnable deterministic cohort assignment

The following Python example uses a keyed SHA-256 digest for stable buckets. The salt is a configuration secret, not an API credential; protect it and keep it stable for the duration of the experiment.

~~~python
import hashlib
import hmac

def assigned_percent(identifier: str, experiment: str, salt: bytes) -> int:
    if not identifier or not experiment or not salt:
        raise ValueError("identifier, experiment and salt are required")
    payload = f"{experiment}:{identifier}".encode("utf-8")
    digest = hmac.new(salt, payload, hashlib.sha256).digest()
    return int.from_bytes(digest[:8], "big") % 10000

def enabled(identifier: str, experiment: str, salt: bytes, percent: float) -> bool:
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return assigned_percent(identifier, experiment, salt) < round(percent * 100)

assert enabled("synthetic-123", "new-search", b"lab-only-salt", 0) is False
assert enabled("synthetic-123", "new-search", b"lab-only-salt", 100) is True
assert assigned_percent("synthetic-123", "new-search", b"lab-only-salt") == assigned_percent(
    "synthetic-123", "new-search", b"lab-only-salt"
)
~~~

This is a lab implementation, **not a full feature-management service**. For mutually exclusive A/B experiments, assign each identity once to a fixed variant and preserve the assignment across exposure changes. Avoid rebucketing existing users when adding variants or changing the salt.

## 7. Example feature configuration

~~~yaml
apiVersion: platform.example/v1
kind: FeatureFlag
metadata:
  name: new-search
spec:
  environment: staging
  owner: search-platform
  defaultEnabled: false
  enabledPercent: 10
  cohortKey: pseudonymous-user-id
  saltReference: secret-manager://staging/feature-assignment-salt
  prerequisites:
    - search-v2-api-healthy
  guardrails:
    maxFiveXXRate: 0.01
    maxP95LatencyMs: 500
  expiresAt: "2026-11-30T00:00:00Z"
  killSwitchEnabled: false
~~~

This is a **logical data contract**, not a Kubernetes built-in resource or a supported CRD unless you implement one. Validate it with a schema and integrate it with a real feature flag provider. Do not apply it with kubectl.

## 8. Feature service availability and fail-safe defaults

Choose behavior explicitly:

| Failure | Possible fallback | Decision |
| --- | --- | --- |
| Flag provider unreachable | Cached last-known-good value | Only when cache age and safety are acceptable |
| Flag config malformed | Disable risky feature | Alert and investigate |
| Unknown user/tenant | Conservative default | Avoid unauthorized exposure |
| Missing prerequisite | Disable dependent flag | Preserve application compatibility |
| Emergency kill switch | Force feature off | Verify propagation and active sessions |
| Provider stale | Bounded cache TTL and audit | Avoid indefinite outdated targeting |

For critical operations, a fail-closed default may be appropriate. For availability-sensitive but low-risk features, a bounded last-known-good cache may be better. Document the tradeoff.

## 9. Instrumentation and experiment telemetry

Use low-cardinality dimensions:

~~~text
feature_evaluations_total{flag="new-search",variant="treatment",result="enabled"}
http_requests_total{service="search-api",variant="treatment",status="200"}
http_request_duration_seconds_bucket{service="search-api",variant="control",le="0.5"}
feature_exposure_total{experiment="new-search",variant="treatment"}
~~~

Avoid raw user IDs, email addresses or high-cardinality tenant IDs as Prometheus labels. Detailed exposure events belong in a privacy-reviewed analytics store with appropriate access and retention controls.

**Assignment is not exposure.** A user assigned treatment but never seeing the feature should not be counted as exposed when interpreting feature-exposure metrics.

## 10. Core PromQL guardrails

### Treatment 5xx rate

~~~promql
sum(rate(http_requests_total{service="search-api",variant="treatment",status=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{service="search-api",variant="treatment"}[5m])),0.001)
~~~

### Treatment P95 latency

~~~promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(http_request_duration_seconds_bucket{
      service="search-api",variant="treatment"
    }[5m])
  )
)
~~~

### Exposure distribution

~~~promql
sum by (variant) (increase(feature_exposure_total{experiment="new-search"}[30m]))
~~~

These queries require real instrumentation and representative traffic. For classic histogram buckets use histogram_quantile as shown; native histograms require different queries. Always validate missing series, scrape gaps, sampling and denominator size before trusting a rollout decision.

## 11. Experiment design

Before an experiment starts, document:

1. Hypothesis and primary success metric.
2. Guardrail metrics and stop conditions.
3. Randomization unit (user, tenant, session or cluster).
4. Assignment persistence and mutually exclusive cohorts.
5. Eligibility, exclusions and privacy/consent requirements.
6. Minimum detectable effect, sample-size estimate and analysis duration.
7. Sample-ratio mismatch detection.
8. Sequential testing or peeking policy.
9. Decision owner and retrospective documentation.

Do not declare statistical significance based on repeatedly checking a conventional p-value without a valid sequential-testing plan. Small cohorts, highly correlated tenant populations and uneven traffic can invalidate simple comparisons.

## 12. Feature flags and Argo Rollouts

A release may follow:

~~~text
1. Deploy candidate code with feature disabled.
2. Verify canary/blue-green health.
3. Promote application revision to stable.
4. Enable feature for internal synthetic identities.
5. Increase feature cohort: 1% -> 5% -> 10% -> 25% -> 50% -> 100%.
6. At each step evaluate error, latency, business and data-integrity guardrails.
7. Disable flag immediately on regression; decide whether code rollback is also needed.
8. Remove temporary flag after stabilization.
~~~

Do not assume the percentages translate directly into request shares. Feature targeting may be per user or tenant, while Rollouts routes per request or connection. If the new feature changes database schema or writes, evaluate compatibility before both flag rollback and deployment rollback.

## 13. GitLab CI/CD policy checks

Example CI job to validate a JSON flag definition with a repository script:

~~~yaml
stages: [validate, test, promote]

validate_flags:
  stage: validate
  image: python:3.12-slim
  script:
    - python3 ci/validate_flags.py flags/staging.json

test_feature_off:
  stage: test
  image: python:3.12-slim
  script:
    - python3 -m pytest tests/test_feature_disabled.py -q

test_feature_on:
  stage: test
  image: python:3.12-slim
  script:
    - python3 -m pytest tests/test_feature_enabled.py -q

propose_promotion:
  stage: promote
  image: registry.example.internal/ci/gitlab-client:PINNED_VERSION
  script:
    - ./ci/propose_flag_change.sh
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

The validation and promotion scripts are **interfaces to implement**. A pipeline passing does not itself enforce production approvals, and changing a flag in a remote SaaS provider may bypass GitOps if permissions are too broad. Apply provider RBAC, change logs and approval policy at the actual flag mutation boundary.

## 14. Flag lifecycle governance

Each release flag must have an expiry and owner. Review stale flags monthly or on the team's approved cadence. Remove unused code branches, tests, configuration and targeting rules after a successful rollout.

Operational kill switches may be long-lived but require periodic exercises. A disabled flag can still incur technical debt or unintended side effects if code paths diverge over time.

## 15. Lab A — Deterministic cohort assignment

1. Save the Python example as ci/cohort.py.
2. Create 10,000 synthetic identifiers.
3. Assign a 10% treatment cohort using a fixed experiment and salt.
4. Repeat the assignment in another process and compare results.
5. Change the rollout percentage to 25% without changing the salt.
6. Verify that existing treatment users remain in treatment when using monotonic threshold allocation.

**Pass:** stable identities receive consistent assignments, and actual sample proportion is near the configured target within expected random variation.

## 16. Lab B — Feature-off and feature-on tests

1. Deploy a test application with the new feature disabled by default.
2. Verify legacy functionality, error rates and authorization.
3. Enable the feature for a synthetic allowlist.
4. Exercise both variants with integration tests.
5. Confirm the exposure event is emitted only on real feature evaluation.
6. Confirm no sensitive user identifiers appear in Prometheus labels.

**Pass:** both paths work, and unauthorized access is denied regardless of flag state.

## 17. Lab C — Progressive cohort activation

1. Start with internal synthetic users.
2. Raise treatment eligibility to 1%, then 5%, then 10%.
3. Generate representative test traffic.
4. Verify assignment persistence and expected exposure counts.
5. Compare control/treatment latency, 5xx and business success.
6. Record approval and metric evidence at each step.

**Pass:** each step has an auditable decision; no automatic progression on missing telemetry.

## 18. Lab D — Kill switch and failure recovery

1. Introduce a deliberately faulty staging-only feature variant.
2. Observe elevated treatment error rate.
3. Activate the emergency kill switch using an authorized identity.
4. Verify propagation delay and that new evaluations return disabled.
5. Check in-flight sessions and external side effects.
6. Decide whether a code rollback is additionally required.
7. Preserve evidence and restore a safe baseline.

**Pass:** feature exposure stops within the agreed objective and customer-like test behavior recovers. Existing writes are evaluated separately.

## 19. Lab E — Provider outage and stale cache

1. Confirm the application's documented default.
2. Simulate temporary provider unavailability in a disposable staging environment.
3. Observe bounded last-known-good cache behavior or fail-closed behavior.
4. Verify alerts on stale config and failed evaluations.
5. Restore provider access.
6. Confirm eventual convergence to the approved flag revision.

**Pass:** the failure mode is predictable, observable and does not bypass authorization.

## 20. Lab F — Sample-ratio mismatch

1. Assign synthetic identities 50/50 to control and treatment.
2. Intentionally drop a portion of treatment exposure events.
3. Compare observed variant counts with expected assignment ratio.
4. Flag the sample-ratio mismatch.
5. Repair instrumentation and rerun the test.
6. Document why results from the contaminated experiment should not drive rollout.

**Pass:** a biased sample is detected rather than accepted as a successful experiment.

## 21. Lab G — Deploy rollback versus flag disable

1. Deploy candidate code with the feature disabled.
2. Enable the feature for a synthetic cohort.
3. Simulate a feature-only defect.
4. Disable the flag and verify immediate behavior.
5. Simulate a code-level defect unrelated to the flag.
6. Abort the staging Rollout and revert the GitOps digest.
7. Compare recovery time and data compatibility.

**Pass:** operators select the correct recovery control for each failure type.

## 22. Lab H — Experiment evidence and cleanup

Collect release ID, experiment hypothesis, assigned population, actual exposure, primary/guardrail metrics, assignment method, configuration revision, approval, decisions, stop reason and follow-up owner.

Then remove temporary release flags and test-only code paths after the retention period and review.

**Pass:** the experiment can be audited and repeated without leaking identifiers.

## 23. Production runbook — controlled feature activation

**Preflight:** confirm immutable application digest, flag owner, change window, baseline SLOs, cohort eligibility, assignment stability, minimum sample, privacy review and kill-switch owner.

**Activate:** enable only approved synthetic/internal cohorts first. Verify flag revision and actual exposure.

**Ramp:** increase eligibility in approved increments. At every step compare control/treatment errors, latency, saturation and business metrics.

**Hold/stop:** halt on missing telemetry, sample-ratio mismatch, significant guardrail regression, unauthorized targeting or stale configuration.

**Close:** record final rollout decision, metrics, approvals, config revision, cleanup issue and evidence archive.

## 24. Production runbook — emergency kill switch

1. Declare the incident and record affected feature, version and cohorts.
2. Stop additional activation.
3. Activate the authorized kill switch or approved fallback.
4. Verify propagation to application instances and new evaluations.
5. Check sessions, in-flight work, queues and persistent side effects.
6. Decide whether GitOps application rollback or data recovery is also required.
7. Preserve redacted flag-provider audit logs, application metrics and release evidence.
8. Restore only after a tested fix and independent approval.

Do not assume disabling the flag reverses already executed database writes, charges, messages or external API calls.

## 25. Twelve troubleshooting scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | Same user changes variant | Unstable identity/salt | Restore deterministic assignment |
| 2 | Treatment traffic differs from target | Sticky sessions or targeting rules | Verify actual eligible cohort |
| 3 | Experiment counts mismatch | Exposure instrumentation loss | Stop analysis and repair |
| 4 | Feature enabled for wrong tenant | Broad targeting policy | Kill switch, audit and restrict |
| 5 | Flag service unavailable | Provider outage | Apply tested fallback and alert |
| 6 | Stale flag after disable | SDK cache/stream delay | Check propagation and TTL |
| 7 | Prometheus query returns no series | Missing variant labels | Repair instrumentation |
| 8 | Stable traffic masks failures | Metrics aggregated across variants | Use treatment-specific metrics |
| 9 | Good p-value, bad business outcome | Invalid metric or repeated peeking | Review experiment design |
| 10 | Flag off but errors continue | Code defect or persistent side effect | Roll back code/repair data |
| 11 | Flag changes bypass GitLab approval | Direct provider write access | Enforce provider RBAC/audit |
| 12 | Too many stale flags | Missing ownership/expiry | Remove with tested cleanup |

## 26. Observability dashboard requirements

A production dashboard should display:

- Application digest and Argo CD GitOps revision.
- Argo Rollouts stable/candidate status.
- Feature configuration revision and active cohort percentage.
- Assignment count versus actual exposure count.
- Variant-specific request volume, 5xx and P95/P99 latency.
- Business outcome metrics by control/treatment.
- Flag provider availability and stale-cache age.
- Kill-switch state and last mutation actor.
- Release change ID, approvals and experiment decision.

Avoid high-cardinality personal identifiers and raw customer data in dashboard labels.

## 27. Evidence template

~~~text
Release / change ID:
Application source commit:
Immutable image digest:
GitOps MR and Argo CD revision:
Argo Rollouts revision:
Feature flag and owner:
Flag configuration revision:
Experiment hypothesis:
Randomization unit and assignment salt reference:
Eligibility and exclusions:
Expected versus actual sample ratio:
Actual exposure count:
Primary metric and guardrail results:
Flag activation history:
Kill switch tested and propagation time:
Decision and approver:
Database/external side-effect assessment:
Audit archive reference:
Cleanup owner and due date:
~~~

## 28. Acceptance criteria

- [ ] Deployment, feature exposure and experiment assignment are independently governed.
- [ ] Stable deterministic assignment and sticky cohorts validated.
- [ ] Feature flags are not used as sole authorization controls.
- [ ] Safe provider-outage behavior and bounded cache staleness tested.
- [ ] Control/treatment telemetry is available without sensitive labels.
- [ ] Experiment sample ratio and minimum exposure are checked.
- [ ] Progressive activation pauses on missing or invalid metrics.
- [ ] Emergency kill switch stops new exposure within measured objective.
- [ ] Rollback decisions consider persistent side effects.
- [ ] GitLab, GitOps, Argo CD and Rollouts release revisions are traceable.
- [ ] Eight labs have results and owners.
- [ ] Temporary flags have expiry and cleanup tasks.
- [ ] Runbooks and audit evidence are reviewed.

## 29. Knowledge check

1. How does feature release differ from code deployment?
2. Why is a stable cohort identifier important?
3. What is the difference between assignment and exposure?
4. Why should Prometheus labels exclude raw user IDs?
5. What is sample-ratio mismatch and why does it matter?
6. Why might a feature kill switch not fully recover a service?
7. How do flag-provider failures influence fail-open versus fail-closed choices?
8. Why can a canary traffic percentage differ from feature eligibility percentage?
9. When should an experiment stop without a winner?
10. How are temporary flags retired safely?

## 30. References

- [OpenFeature Specification](https://openfeature.dev/specification/)
- [OpenFeature Concepts](https://openfeature.dev/docs/reference/concepts/)
- [Argo Rollouts Canary](https://argo-rollouts.readthedocs.io/en/stable/features/canary/)
- [Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Prometheus Querying](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [GitLab Protected Branches](https://docs.gitlab.com/user/project/repository/branches/protected/)

---

**Chapter 059 complete.** Next: **Chapter 060 — Enterprise Progressive Delivery and Automated Recovery Capstone**, completing Part 12.