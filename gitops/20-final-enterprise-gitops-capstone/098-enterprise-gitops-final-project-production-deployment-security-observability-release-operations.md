# Chapter 098 — Enterprise GitOps Final Project: Production Deployment, Security, Observability and Release Operations

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 20:** Final Enterprise GitOps Capstone  
**Chapter:** 098 / 100  
**Audience:** SRE, Platform Engineering, Security, Release Engineering and On-Call Operations

> **Safety:** “Production” in the chapter title describes production-grade practices, not permission to modify a live environment. All exercises use approved disposable staging workloads. Promotion, secrets changes and incident simulations require explicit change control.

## 1. Learning objectives

Operate the Chapter 097 platform through a secure release lifecycle: signed image provenance, GitLab protected CI gates, Argo CD policy, Kubernetes least privilege, network/secret security, Helm validation, progressive delivery, service-level monitoring, incident response and reversible rollback.

## 2. End-to-end release control plane

```text
Protected source commit
       |
 CI tests + security scans + SBOM
       |
 signed immutable OCI digest
       |
 GitOps config promotion PR + approvers
       |
 Argo CD AppProject / sync policy
       |
 staging canary -> SLO gates -> staged promotion
       |
 application + database compatibility
       |
 independent telemetry / paging / rollback
```

**Never** allow a generic CI runner to bypass protected GitOps state by applying directly to production. Separate application developers, release approvers, Argo CD controller identities and incident responders.

## 3. Production readiness gates

| Gate | Evidence | Hard stop |
|---|---|---|
| G1 Source integrity | Protected commit, approved PR | Unreviewed code |
| G2 Artifact provenance | Signed immutable digest and SBOM | Signature or policy failure |
| G3 CI quality | Unit/integration/security tests | Required check failed |
| G4 Cluster policy | AppProject, RBAC, PodSecurity, network isolation | Privilege or destination violation |
| G5 Secrets | Workload identity, External Secrets and KMS | Missing or leaked credential |
| G6 Reliability | SLO baseline, canary and synthetic transactions | Burn-rate or user journey failure |
| G7 Observability | Metrics, logs, traces, paging | Blind release |
| G8 Rollback | Compatible prior digest, Git revert and owner | No safe recovery path |

A release cannot pass with a high numeric score if a hard-stop gate fails.

## 4. Security reference manifests

### Restricted workload security context

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: synthetic-api
  namespace: enterprise-gitops-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: synthetic-api}
  template:
    metadata:
      labels: {app: synthetic-api}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: api
          image: registry.example.invalid/lab/synthetic-api@sha256:REPLACE_WITH_VERIFIED_DIGEST
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: ["ALL"]}
          ports: [{containerPort: 8080}]
          readinessProbe:
            httpGet: {path: /ready, port: 8080}
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: /health, port: 8080}
            periodSeconds: 10
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {memory: 256Mi}
```

The referenced image must support non-root execution and read-only filesystem (mount a writable temporary volume if needed). The digest is intentionally a placeholder and must be replaced with a verified immutable value.

### Default-deny policy (staging-only)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: enterprise-gitops-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

A default deny blocks DNS, ingress and observability until explicit allow rules exist. Never apply it without reviewing CNI enforcement, namespace scope and allowlist dependencies.

## 5. SLO and canary decision model

Define SLIs for successful user transactions, availability, p95/p99 latency, request error rate, saturation and data correctness. Establish burn-rate alerts and a clear canary gate. For illustration, if the approved SLO is 99.9% successful requests over 30 days, the error budget is 0.1% of eligible requests; calculate actual remaining budget from observed traffic rather than assuming a fixed number of errors.

| Phase | Required observation | Action |
|---|---|---|
| Pre-release | Stable baseline and green alerts | Approve canary |
| Small canary | Synthetic success and no material SLO regression | Hold or expand |
| Wider rollout | Sustained latency/error/capacity stability | Continue |
| Full release | Health, tracing, audit and rollback readiness | Close change |
| Failure | Budget burn or user transaction failure | Stop and roll back |

## 6. GitLab protected promotion pattern

```yaml
stages: [validate, verify, promote]
verify_release:
  stage: verify
  image: registry.example.invalid/ci/security-toolchain@sha256:REPLACE_WITH_VERIFIED_DIGEST
  script:
    - echo "Verify protected commit, SBOM, signature, tests and immutable digest"
promote_staging:
  stage: promote
  image: registry.example.invalid/ci/security-toolchain@sha256:REPLACE_WITH_VERIFIED_DIGEST
  environment:
    name: staging
  when: manual
  allow_failure: false
  script:
    - echo "Open protected GitOps promotion MR; do not kubectl apply directly"
  rules:
    - if: '$CI_COMMIT_REF_PROTECTED == "true"'
```

This is a **policy scaffold**, not a complete security implementation. Replace echo checks with pinned verification tools and enforce GitLab protected environments, merge request approvals, runner trust, branch protection and credential scoping.

## 7. Lab preflight

```bash
export LAB_NS=enterprise-gitops-lab
export LAB_HEALTH_URL=https://lab.example.invalid/health
export APPROVED_CONTEXT=replace-with-approved-staging-context
test "$(kubectl config current-context)" = "$APPROVED_CONTEXT"
kubectl -n "$LAB_NS" get deploy,pods,svc -o wide
kubectl -n argocd get applications -o wide
```

## 8. Eighteen hands-on release and operations labs

Each lab requires approved staging scope, baseline, expected result, abort threshold, rollback owner and UTC evidence.

### Lab 01 — Deployment readiness review

**Exercise:** Verify approved staging environment, release owner, rollback and signed artifact digest.

```bash
kubectl config current-context
kubectl -n "$LAB_NS" get deployments,pods,svc -o wide
```

**Acceptance:** Signed go/no-go decision. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 02 — Baseline SLIs

**Exercise:** Capture user-journey success, latency, saturation, error budget and alert coverage.

```bash
kubectl -n "$LAB_NS" top pods
kubectl -n "$LAB_NS" get hpa,pdb
```

**Acceptance:** Baseline and alert owners. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 03 — Supply-chain attestation

**Exercise:** Review image provenance, SBOM, signatures and immutable GitOps revision.

```bash
git rev-parse HEAD
kubectl -n "$LAB_NS" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[*].image}{"\n"}{end}'
```

**Acceptance:** Trusted release digest. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 04 — Argo CD project policy

**Exercise:** Inspect source repo and namespace restrictions, cluster-resource allowlist and sync controls.

```bash
kubectl -n argocd get appprojects -o yaml
```

**Acceptance:** Least-privilege sync. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 05 — Kubernetes RBAC audit

**Exercise:** Test service account permissions and deny unintended cluster-scoped writes.

```bash
kubectl auth can-i create clusterroles --as=system:serviceaccount:"$LAB_NS":synthetic-api
kubectl -n "$LAB_NS" get serviceaccounts
```

**Acceptance:** RBAC negative tests pass. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 06 — Pod security posture

**Exercise:** Inspect security context, capabilities, service accounts and image pull policies.

```bash
kubectl -n "$LAB_NS" get deploy synthetic-api -o yaml
```

**Acceptance:** Non-root, least privilege. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 07 — NetworkPolicy enforcement

**Exercise:** Review ingress/egress policy and DNS/telemetry exceptions in staging.

```bash
kubectl -n "$LAB_NS" get networkpolicies -o yaml
```

**Acceptance:** Isolation and necessary traffic. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 08 — Secret rotation rehearsal

**Exercise:** Use disposable credentials in isolated provider and validate rotation without plaintext logging.

```bash
kubectl -n "$LAB_NS" get externalsecret
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -10
```

**Acceptance:** Secret sync and rollback. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 09 — TLS and ingress validation

**Exercise:** Check TLS chain, routing and synthetic health on staging endpoint.

```bash
curl --fail --silent --show-error --max-time 5 "$LAB_HEALTH_URL"
kubectl -n "$LAB_NS" get ingress,svc
```

**Acceptance:** Healthy authenticated endpoint. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 10 — Helm pre-release validation

**Exercise:** Lint, render and server-side dry run reviewed staging manifests.

```bash
helm lint applications/synthetic-api/chart
helm template synthetic-api applications/synthetic-api/chart -f environments/staging/values.yaml > /tmp/ch098-rendered.yaml
kubectl apply --dry-run=server -n "$LAB_NS" -f /tmp/ch098-rendered.yaml
```

**Acceptance:** Valid and policy-compliant manifests. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 11 — GitLab release pipeline

**Exercise:** Review protected branch pipeline gates, manual approvals, artifact retention and environment protection.

```bash
git log -3 --oneline
git diff --check
```

**Acceptance:** Traceable approval chain. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 12 — Canary release rehearsal

**Exercise:** Roll out only disposable staging canary and compare request error/latency before expansion.

```bash
kubectl -n "$LAB_NS" rollout status deploy/synthetic-api --timeout=120s
kubectl -n "$LAB_NS" get pods -o wide
```

**Acceptance:** No SLO regression. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 13 — Progressive delivery abort

**Exercise:** Inject a synthetic failing health condition and validate automatic or manual rollback decision.

```bash
kubectl -n "$LAB_NS" describe deployment synthetic-api
kubectl -n "$LAB_NS" get events --sort-by=.lastTimestamp | tail -15
```

**Acceptance:** Bad canary blocked. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 14 — Argo CD drift review

**Exercise:** Compare Git desired state with live resources and inspect reconciliation before manual changes.

```bash
kubectl -n argocd get applications -o wide
kubectl -n "$LAB_NS" get deploy synthetic-api -o yaml
```

**Acceptance:** Drift detected without destructive sync. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 15 — Metrics/logs/traces

**Exercise:** Correlate synthetic transaction with workload logs, Prometheus metrics and tracing.

```bash
kubectl -n "$LAB_NS" logs deploy/synthetic-api --tail=40
kubectl -n "$LAB_NS" get servicemonitor
```

**Acceptance:** Signal coverage and retention. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 16 — Alert routing and escalation

**Exercise:** Test staging alert with owner, severity, deduplication and recovery notice.

```bash
kubectl -n "$LAB_NS" get pods,deploy
kubectl -n argocd get applications -o wide
```

**Acceptance:** Actionable paging and runbook. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 17 — Rollback and recovery

**Exercise:** Rehearse reverting GitOps desired state to approved image digest; validate DB compatibility.

```bash
git log -5 --oneline
kubectl -n "$LAB_NS" rollout history deployment/synthetic-api
```

**Acceptance:** Safe restored user transaction. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

### Lab 18 — Release acceptance and handoff

**Exercise:** Complete security, SLO, canary, audit and operational signoff with incident escalation.

```bash
date -u +%FT%TZ
kubectl -n "$LAB_NS" get deploy,pods,svc,ingress -o wide
```

**Acceptance:** Approved evidence packet. **Abort/rollback:** stop on unexpected environment, data authority ambiguity, failed SLO or missing observability. Revert only explicitly approved disposable changes.

## 9. Twenty troubleshooting scenarios

| # | Failure | Investigation | Recovery verification |
|---|---|---|---|
| 1 | Release approval absent | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 2 | Protected branch bypass | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 3 | Unsigned image digest | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 4 | SBOM policy violation | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 5 | Argo CD repo authentication | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 6 | AppProject destination denied | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 7 | RBAC privilege escalation | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 8 | PodSecurity admission denial | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 9 | NetworkPolicy DNS blocked | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 10 | ExternalSecret sync failed | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 11 | TLS certificate invalid | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 12 | Ingress route misconfigured | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 13 | Helm chart rendering failure | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 14 | Canary error-rate spike | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 15 | Readiness probe misconfigured | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 16 | Argo CD drift loop | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 17 | Metrics missing | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 18 | Alert storm or missing page | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 19 | Rollback DB incompatibility | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |
| 20 | Production capacity insufficient | Inspect protected CI evidence, Argo CD diff, Kubernetes events, policy and service SLIs | Contain blast radius, fix root cause, validate synthetic transaction and audit trail |

## 10. Eight operational runbooks

### RB-01 Release go/no-go

**Trigger and actions:** Confirm protected commit, signed digest, pipeline tests, change approval, SLO baseline, rollback and on-call staffing; block on failed gate.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-02 Security incident containment

**Trigger and actions:** Freeze release, revoke compromised CI identity, quarantine artifacts, preserve logs and verify provenance before restoring deployment.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-03 Argo CD reconciliation recovery

**Trigger and actions:** Inspect repo-server, controller, AppProject, sync windows and diff; resolve policy or source errors without force-pruning.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-04 Canary rollback

**Trigger and actions:** Stop promotion on burn-rate, error, latency or transaction failure; revert approved GitOps commit and validate data migration compatibility.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-05 Secret and identity outage

**Trigger and actions:** Inspect workload identity, KMS and External Secrets conditions; rotate only through approved vault, never expose plaintext.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-06 Observability outage

**Trigger and actions:** Use independent synthetic probes, restore metrics/log pipelines, verify alert routing and avoid declaring release success while blind.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-07 Kubernetes workload degradation

**Trigger and actions:** Inspect events, probes, quotas, PDB, autoscaling, node capacity and network policy; mitigate and prove user-journey recovery.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

### RB-08 Release closeout

**Trigger and actions:** Archive approvals, revisions, SBOM/signature, SLO results, incident notes, rollback and operational owner handoff.

**Closeout:** incident/change ID, owner, UTC timeline, source revision, image digest, user transaction, SLO impact, rollback status and approved evidence.

## 11. Release acceptance scorecard (100 points)

| Category | Points |
|---|---:|
| GitLab change control and pipeline quality | 15 |
| Image provenance and supply-chain security | 15 |
| Argo CD/Kubernetes authorization and policy | 15 |
| Secrets, workload identity and network isolation | 15 |
| Canary, rollback and release safety | 15 |
| Observability, SLOs and incident response | 15 |
| Audit, documentation and on-call handoff | 10 |
| **Total** | **100** |

**Pass:** at least 90/100 and all hard-stop gates G1–G8, including a successful synthetic business transaction and verified rollback.

## 12. Release evidence template

```text
Release ID / environment / change ticket:
Approver and on-call owner:
Git commit / GitOps revision:
Signed OCI digest / SBOM / vulnerability exceptions:
Helm chart version and rendered diff:
AppProject / RBAC / NetworkPolicy checks:
Secret provider and workload identity status:
Baseline SLI / canary metrics / error budget:
Synthetic transaction:
Rollback target and DB migration compatibility:
Alerts / incident escalation:
Go/no-go decision and UTC timestamps:
Final score / risks / corrective actions:
```

## 13. Definition of done

The release is ready only when a protected GitOps change produces a verified immutable workload in an isolated staging environment, security gates hold, the canary stays within SLO, telemetry and paging are actionable, rollback is safe and operational evidence is signed. A completed tutorial is not a production deployment claim.

**Next:** Chapter 099 — Enterprise GitOps Final Project: Failure Simulation, Disaster Recovery and Production Reliability Validation.
