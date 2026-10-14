# Chapter 063 — Kubernetes Admission Policies, OPA Gatekeeper and Kyverno for GitOps Security

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 13:** Secrets, Policy and Workload Identity  
**Chapter:** 063 / 100  
**Audience:** Platform Engineers, SREs, Kubernetes Administrators, Security Engineers and DevSecOps

> **Safety:** All policy examples and failure injection belong in disposable staging namespaces. Admission policies can block deployments, recovery and system workloads. Start with audit or warning behavior, verify scope and exemptions, then enforce with approved rollback controls.

## 1. Learning objectives

By completing this chapter you will:

1. Explain Kubernetes admission control and its place in the GitOps lifecycle.
2. Compare ValidatingAdmissionPolicy, OPA Gatekeeper and Kyverno.
3. Write and test policy-as-code rules for workload security.
4. Enforce approved image registries, immutable digests and safe Pod settings.
5. Integrate policies with GitLab validation and Argo CD reconciliation.
6. Design controlled policy rollout, exceptions and break-glass procedures.
7. Monitor webhook availability, denials, latency and audit violations.
8. Troubleshoot policy conflicts and recover from accidental enforcement outages.

## 2. Architecture

~~~text
Developer -> GitLab CI policy checks -> protected GitOps MR
                                        |
                                      Argo CD
                                        |
                                 Kubernetes API server
                                        |
                              Admission evaluation
                             /          |           \
                  Native VAP       Gatekeeper      Kyverno
                             \          |           /
                           allow / deny / warn / audit
                                        |
                                   etcd persistence
                                        |
                               controllers schedule Pods
~~~

CI checks catch problems early; admission is the runtime enforcement boundary. Argo CD cannot override a denied Kubernetes admission request by simply retrying sync.

## 3. Kubernetes admission sequence

1. Authenticate the API request.
2. Authorize the actor through RBAC or another authorization mechanism.
3. Run mutating admission, where configured.
4. Run validating admission and applicable policies.
5. Persist the object if accepted.
6. Controllers reconcile downstream resources.

Admission policies do not replace image signing verification, workload runtime protection, network policy, RBAC or cloud IAM. A policy may also miss already-existing objects until they are updated or separately audited.

## 4. Policy engine comparison

| Capability | Native ValidatingAdmissionPolicy | OPA Gatekeeper | Kyverno |
| --- | --- | --- | --- |
| Language | CEL | Rego via ConstraintTemplates | Kubernetes-style policy rules |
| External webhook required for validation | No, native API feature | Yes | Yes for admission features |
| Mutation | Not via ValidatingAdmissionPolicy | Separate mutation features | Supported policy mutation |
| Background/audit reporting | Native audit annotations and binding actions | Constraint audit | Background scans/reports |
| Image verification | Requires additional design | Custom policy/integration | Dedicated verifyImages capabilities |
| Operational footprint | Low relative to webhook engines | Controller, webhook and audit | Controller/webhook/reporting |
| Best fit | Focused native validation | Rego-heavy enterprise governance | Kubernetes-native policy workflows |

Exact API versions and feature support depend on Kubernetes and policy-engine versions. Validate compatibility before deployment.

## 5. Policy hierarchy

Define organization-wide controls, environment controls and application-specific exceptions:

~~~text
Organization baseline
  -> Cluster baseline
    -> Namespace security profile
      -> Application-specific constraints
        -> Time-bound approved exception
~~~

Examples: deny privileged containers, restrict host namespaces, require resource requests, enforce approved registries, reject latest tags, require labels, block hostPath, restrict service-account token mounting and enforce Pod Security Standards.

Avoid blanket rules that break kube-system, CNI, CSI, metrics agents, operators or disaster-recovery tooling.

## 6. Native ValidatingAdmissionPolicy example

This policy requires a non-empty owner label on newly created or updated Deployments in bound namespaces.

~~~yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-deployment-owner
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: "has(object.metadata.labels) && 'platform.example/owner' in object.metadata.labels && object.metadata.labels['platform.example/owner'] != ''"
      message: "Deployment requires non-empty platform.example/owner label"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-deployment-owner-staging
spec:
  policyName: require-deployment-owner
  validationActions:
    - Deny
  matchResources:
    namespaceSelector:
      matchLabels:
        platform.example/policy-profile: restricted-staging
~~~

**Scope caution:** Namespace labels are trusted policy inputs; restrict who may change them. Use Audit and/or Warn for rollout rehearsal before Deny. Validate CEL expression and policy binding with server-side dry-run in a supported cluster.

## 7. Gatekeeper ConstraintTemplate example

Gatekeeper uses a ConstraintTemplate plus a Constraint instance. This simplified template denies Deployment objects without the required owner label.

~~~yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredowner
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredOwner
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredowner
        violation[{"msg": msg}] {
          not input.review.object.metadata.labels["platform.example/owner"]
          msg := "Deployment must include platform.example/owner label"
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredOwner
metadata:
  name: require-owner-staging
spec:
  enforcementAction: dryrun
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
    namespaces:
      - demo-staging
~~~

**Important:** Apply the ConstraintTemplate first, wait for its generated CRD to become established, then apply the Constraint. Rego and template API compatibility must be validated against the installed Gatekeeper version. The example starts in dryrun mode.

## 8. Kyverno ClusterPolicy example

The following Kyverno policy checks the owner label for Deployments in a disposable namespace.

~~~yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-owner-staging
spec:
  validationFailureAction: Audit
  background: true
  rules:
    - name: deployment-owner
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - demo-staging
      validate:
        message: "Deployment requires platform.example/owner label"
        pattern:
          metadata:
            labels:
              platform.example/owner: "?*"
~~~

Kyverno enforcement configuration and policy API shape can change between major releases. Validate this example against the pinned Kyverno version and CRD. Start with Audit and promote to Enforce only after evaluating policy reports and false positives.

## 9. Compare equivalent outcomes

| Input | Native VAP | Gatekeeper | Kyverno |
| --- | --- | --- | --- |
| Deployment with owner label | Allow | No violation | Pass |
| Deployment without owner | Deny when bound | Violation in dryrun | Audit finding |
| Namespace outside scope | Not bound | Not matched | Not matched |
| Policy engine unavailable | Native evaluation | Depends on webhook failurePolicy | Depends on webhook failurePolicy |

Do not assume the three examples have identical enforcement modes: native VAP is shown with Deny, Gatekeeper dryrun and Kyverno Audit specifically to demonstrate rollout safety.

## 10. Container image policy design

For production applications, consider:

- Approved registries and namespaces.
- Immutable digest references instead of mutable latest tags.
- Verified image signatures and provenance.
- Minimum vulnerability and SBOM policy.
- Non-root execution and dropped Linux capabilities.
- Restricted privilege escalation and host access.
- Read-only root filesystem where compatible.
- Required CPU/memory requests and limits.
- Approved ServiceAccounts and token automount.
- Required labels for owner, cost center and environment.

A digest alone proves content identity, not publisher trust. Combine digest pinning with signature/provenance verification where supported.

## 11. Pod Security Admission and policy engines

Kubernetes Pod Security Admission provides baseline/restricted controls through namespace labels. Gatekeeper, Kyverno and VAP can enforce additional organization-specific rules.

~~~bash
kubectl get namespace demo-staging --show-labels
kubectl label namespace demo-staging   pod-security.kubernetes.io/warn=restricted   pod-security.kubernetes.io/audit=restricted   --overwrite
~~~

Apply enforcement labels only after confirming application and system compatibility. Namespace labels and admission exceptions must be access-controlled.

## 12. Policy-as-code repository

~~~text
gitops/
  policies/
    native/
      require-owner.yaml
    gatekeeper/
      templates/
      constraints/
    kyverno/
      clusterpolicies/
    tests/
      compliant-deployment.yaml
      missing-owner-deployment.yaml
      privileged-pod.yaml
    exceptions/
      staging-exception-register.yaml
    runbooks/
      policy-denial.md
      webhook-outage.md
  apps/
    demo-web/
      overlays/staging/
      overlays/prod/
~~~

Protect policy files and exception registers with CODEOWNERS or equivalent mandatory review.

## 13. GitLab CI policy-validation pipeline

~~~yaml
stages: [render, validate, policy]

render_manifests:
  stage: render
  image: registry.example.internal/ci/kustomize:PINNED_VERSION
  script:
    - kustomize build gitops/apps/demo-web/overlays/staging > rendered.yaml
  artifacts:
    paths: [rendered.yaml]
    expire_in: 1 day

validate_schema:
  stage: validate
  image: registry.example.internal/ci/kubeconform:PINNED_VERSION
  needs: [render_manifests]
  script:
    - kubeconform -strict -summary rendered.yaml

policy_test:
  stage: policy
  image: registry.example.internal/ci/policy-tools:PINNED_VERSION
  needs: [render_manifests]
  script:
    - ./ci/test-admission-policies.sh rendered.yaml
~~~

The custom image and script are interfaces to implement, not built-in tools. CRDs need approved schemas. Run engine-specific tests (for example Gatekeeper Rego tests or Kyverno CLI tests) against both allowed and denied manifests.

## 14. Argo CD policy deployment ordering

Recommended GitOps bootstrap sequence:

~~~text
1. Install policy engine controller and CRDs.
2. Validate webhook certificates and availability.
3. Deploy policy definitions in Audit/dryrun.
4. Inspect existing resources and false positives.
5. Deploy policy tests and namespace scope.
6. Approve change and switch selected policies to Enforce/Deny.
7. Monitor denials, webhook latency and rollout health.
~~~

Argo CD sync waves can order manifests but cannot guarantee a webhook is healthy merely because its Deployment resource exists. Include health checks and explicit rollout readiness.

## 15. Webhook availability and failurePolicy

Validating webhook configurations may use failurePolicy Fail or Ignore. Fail protects enforcement integrity but can block operations during webhook outages; Ignore preserves availability but can bypass policy when the webhook fails.

Document which workloads and operations are critical, how system namespaces are protected, and how emergency recovery is authorized. Do not broadly switch to Ignore in production without security approval.

Native VAP is evaluated by the API server and does not depend on an external policy webhook, but CEL validation errors and policy configuration still require testing.

## 16. Exception governance

Every exception should include:

~~~yaml
exceptionId: SEC-EXCEPTION-123
environment: staging
namespace: demo-staging
policy: require-owner-staging
resource: demo-legacy
reason: legacy migration with approved remediation
approver: security-reviewer
owner: application-team
expiresAt: "2026-11-01T00:00:00Z"
ticket: CHANGE-123
compensatingControls:
  - restricted namespace
  - temporary read-only access
~~~

This is a **documentation schema**, not a native Kubernetes exception resource. Actual Gatekeeper/Kyverno/VAP exceptions must use supported engine mechanisms and must not grant unintended cross-namespace bypass. Expired exceptions must be reviewed and removed.

## 17. Observability

Track:

- Admission allow/deny counts by policy and namespace.
- Policy engine controller and webhook availability.
- Admission webhook latency and API-server timeout events.
- Constraint violations and Kyverno policy reports.
- Native VAP audit annotations and denied requests.
- Argo CD sync failures caused by admission.
- Policy revision, exception count and exception age.
- Unauthorized policy changes and break-glass actions.

Metric names differ by version and engine. Discover actual Prometheus series before building alerts.

## 18. Lab A — Native VAP audit to deny

1. Create a disposable namespace with policy-profile label.
2. Apply a VAP and binding with Audit/Warn rather than Deny.
3. Apply a compliant Deployment with owner label.
4. Dry-run a noncompliant Deployment.
5. Review warnings/audit evidence.
6. Switch the binding to Deny after approval.
7. Confirm the noncompliant Deployment is rejected.

~~~bash
kubectl --context STAGING_CONTEXT apply --dry-run=server -f compliant-deployment.yaml
kubectl --context STAGING_CONTEXT apply --dry-run=server -f missing-owner-deployment.yaml
~~~

**Pass:** compliant workload accepted, noncompliant workload denied only after enforcement approval.

## 19. Lab B — Gatekeeper ConstraintTemplate and Constraint

1. Install a pinned Gatekeeper release in staging.
2. Apply the ConstraintTemplate.
3. Wait for the generated CRD.
4. Apply Constraint with enforcementAction dryrun.
5. Create a noncompliant test Deployment.
6. Inspect violations.
7. Switch to deny only after validation.

~~~bash
kubectl get constrainttemplates
kubectl get k8srequiredowner
kubectl describe k8srequiredowner require-owner-staging
~~~

**Pass:** audit detects violations and enforcement blocks the intended resources without affecting system namespaces.

## 20. Lab C — Kyverno policy reporting

1. Install a pinned Kyverno release.
2. Apply the ClusterPolicy in Audit mode.
3. Deploy compliant and noncompliant synthetic resources.
4. Inspect PolicyReports or ClusterPolicyReports as supported by the installed version.
5. Change to Enforce in staging after approval.
6. Verify the noncompliant resource is denied.

~~~bash
kubectl get clusterpolicy require-owner-staging
kubectl get policyreports -A
kubectl get clusterpolicyreports
~~~

**Pass:** reports identify violations and enforcement behaves as documented.

## 21. Lab D — Image registry and digest controls

1. Define approved test registry prefixes.
2. Validate an immutable digest reference.
3. Test a mutable latest tag.
4. Test an image from an unauthorized registry.
5. Verify signature checks where supported.
6. Record denial messages and remediation steps.

**Pass:** unauthorized or mutable images are rejected, while approved signed digests pass.

## 22. Lab E — Privileged Pod and host access denial

1. Use Pod Security Admission warn/audit restricted labels in staging.
2. Test a compliant non-root Pod.
3. Dry-run a privileged Pod.
4. Test hostPath or hostNetwork usage.
5. Confirm warnings or denials and review exemptions.
6. Do not modify kube-system or production infrastructure workloads.

**Pass:** risky workload configurations are detected without breaking essential platform components.

## 23. Lab F — GitLab policy checks

1. Render staging manifests.
2. Validate Kubernetes and CRD schemas.
3. Run policy tests against compliant and noncompliant fixtures.
4. Verify a failing policy blocks the merge pipeline.
5. Confirm policy exception changes require security review.
6. Archive non-sensitive test evidence.

**Pass:** policy violations fail before reaching Argo CD.

## 24. Lab G — Argo CD admission rejection

1. Commit a deliberately noncompliant staging Deployment.
2. Observe Argo CD sync failure.
3. Inspect Kubernetes admission denial details.
4. Correct the manifest in Git.
5. Reconcile and confirm healthy state.
6. Verify no manual policy bypass was needed.

**Pass:** GitOps recovery occurs through reviewed desired-state correction.

## 25. Lab H — Webhook outage tabletop

1. Select a disposable staging policy engine.
2. Record webhook failurePolicy and availability.
3. Simulate controller/webhook unavailability in staging.
4. Attempt a safe dry-run admission request.
5. Observe fail-closed or fail-open behavior.
6. Restore controller and validate certificates/endpoints.
7. Document recovery and security tradeoffs.

**Pass:** operators understand actual outage behavior and can recover without globally disabling production policy.

## 26. Lab I — Time-bound exception

1. Submit an exception request with scope, reason and expiry.
2. Obtain independent security approval.
3. Apply the smallest supported engine-specific exception.
4. Verify only the intended test resource bypasses the rule.
5. Test a second resource and confirm it remains denied.
6. Remove the exception at expiry.

**Pass:** exception scope is narrow, audited and temporary.

## 27. Lab J — Policy rollback and disaster recovery

1. Simulate an overly strict staging policy.
2. Record blocked workloads and policy revision.
3. Revert the policy GitOps commit through emergency approval.
4. Restore admission health and application reconciliation.
5. Validate audit and exception records.
6. Record recovery time and prevention actions.

**Pass:** rollback is controlled and restores service without a lasting enforcement gap.

## 28. Troubleshooting — fourteen scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | Argo CD sync denied | Admission policy violation | Inspect message and fix Git |
| 2 | VAP rule never applies | Binding/namespace selector mismatch | Verify binding scope |
| 3 | VAP rejects compliant object | CEL expression error | Test expression and object shape |
| 4 | Gatekeeper Constraint unknown | Template CRD not established | Wait for template registration |
| 5 | Gatekeeper violations not reported | Audit disabled/match mismatch | Inspect controller and Constraint |
| 6 | Kyverno reports empty | Background scan/scope issue | Check policy version and reports |
| 7 | Policy denies system Pods | Missing exemptions | Scope policies safely |
| 8 | Image digest policy bypassed | Wrong container path handling | Cover init/ephemeral containers |
| 9 | Webhook timeout blocks API | FailurePolicy Fail and outage | Restore webhook and endpoints |
| 10 | Webhook outage bypasses rule | FailurePolicy Ignore | Review security risk and recovery |
| 11 | Exception grants broad bypass | Namespace wildcard | Narrow scope and audit |
| 12 | CI passes, admission denies | Different policy revisions | Pin and compare policy versions |
| 13 | Mutation causes Argo CD drift | Controller-managed fields | Align diff and ownership |
| 14 | Policy rollback does not recover | GitOps re-enforces bad revision | Revert desired policy and reconcile |

## 29. Production runbook — new policy rollout

**Preflight:** identify rule owner, affected resources, namespaces, system dependencies, engine version, false-positive risks, monitoring and rollback.

**Audit:** deploy in dryrun/Audit/Warn mode and collect violations over representative workload cycles.

**Approve:** review exceptions, CI test results and policy diff.

**Enforce:** apply scoped Deny/Enforce to staging first, then approved production targets.

**Observe:** monitor admission denials, API latency, Argo CD sync and platform health.

**Close:** record policy revision, owners, exceptions and rollback plan.

## 30. Production runbook — admission outage

1. Declare impact and identify policy engine/webhook and failurePolicy.
2. Check controller Pods, Services, endpoints, certificates and API-server events.
3. Preserve policy and webhook configuration evidence.
4. Restore controller from approved pinned version.
5. Test admission against safe synthetic resources.
6. Avoid broad policy bypass unless explicitly approved through emergency change.
7. Verify Argo CD recovery and workload health.
8. Record outage duration, security impact and follow-up actions.

## 31. Production runbook — false-positive enforcement

1. Freeze policy changes and capture the denial message.
2. Identify exact policy, namespace, resource and Git revision.
3. Confirm whether the resource is truly noncompliant.
4. If false positive, revert or narrowly exempt through approved workflow.
5. Verify unrelated controls remain enforced.
6. Reconcile affected Argo CD Applications.
7. Add regression fixtures and update the policy test suite.

## 32. Evidence template

~~~text
Change / incident ID:
Cluster and namespace:
Policy engine and version:
Policy name and GitOps revision:
Admission operation and resource:
Expected outcome:
Actual allow/deny/audit outcome:
CI policy test result:
Argo CD sync result:
Webhook health and latency:
Exception scope, approver and expiry:
Rollback commit and recovery duration:
Security review:
Evidence archive reference:
~~~

## 33. Acceptance checklist

- [ ] Native VAP, Gatekeeper and Kyverno responsibilities understood.
- [ ] Admission policies tested before enforcement.
- [ ] System namespace and platform component impact reviewed.
- [ ] Image and Pod security rules cover relevant workload variants.
- [ ] GitLab CI rejects noncompliant rendered manifests.
- [ ] Argo CD admission failures are diagnosable.
- [ ] Webhook failurePolicy behavior is documented and tested.
- [ ] Policy exceptions are scoped, approved and time-bound.
- [ ] Monitoring covers denials, latency and webhook availability.
- [ ] Unauthorized policy changes are denied.
- [ ] Ten hands-on labs have evidence.
- [ ] Production rollback and outage runbooks are validated.

## 34. Knowledge check

1. How does admission differ from GitLab CI policy validation?
2. Why does a healthy Argo CD Application not override an admission denial?
3. Which engine uses CEL, Rego and Kubernetes-style policy rules?
4. Why should enforcement begin in Audit/Warn/dryrun mode?
5. What are the availability/security tradeoffs of failurePolicy Fail and Ignore?
6. Why is an image digest insufficient proof of publisher trust?
7. Why do exceptions need expiry and scope?
8. What is the risk of a broad ClusterPolicy affecting kube-system?
9. Why can mutation cause GitOps drift?
10. How should an admission-controller outage be recovered?

## 35. References

- [Kubernetes Admission Controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Kubernetes Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/)
- [Kyverno Documentation](https://kyverno.io/docs/)
- [Argo CD Sync Phases and Waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 063 complete.** Next: **Chapter 064 — Policy-as-Code Supply Chain Security, Image Signing and Provenance Enforcement**.