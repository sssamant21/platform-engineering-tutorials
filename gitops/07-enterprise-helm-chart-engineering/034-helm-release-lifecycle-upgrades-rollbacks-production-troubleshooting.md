# Chapter 034 — Helm Release Lifecycle, Upgrades, Rollbacks and Production Troubleshooting

**Part 07 — Enterprise Helm Chart Engineering** | **Chapter 034 of 100**  
**Audience:** SREs, Kubernetes administrators, platform engineers and release operators  
**Prerequisites:** Chapters 031–033, Helm 3, kubectl, an approved disposable namespace  
**Architecture:** One Kubernetes cluster with \`demo-dev\`, \`demo-test\`, \`demo-staging\` and \`demo-prod\` namespaces. GitLab CI validates and packages artifacts; Argo CD owns GitOps deployments.

> **Critical ownership rule:** Helm CLI release management and Argo CD Helm rendering are different operational modes. Never run \`helm upgrade\` or \`helm rollback\` against resources owned by an Argo CD Application unless an explicitly approved emergency procedure accounts for reconciliation. All live Helm labs below use an **independent disposable release** in \`demo-dev\`, not an Argo CD-managed Application.

## 1. Learning outcomes

By completing this chapter, you will:

1. Explain Helm release storage, revisions, statuses and deployment history.
2. Operate \`helm install\`, \`upgrade\`, \`history\`, \`status\`, \`get\`, \`diff\` alternatives, \`rollback\` and \`uninstall\`.
3. Distinguish \`--wait\`, \`--wait-for-jobs\`, \`--timeout\`, \`--atomic\`, \`--cleanup-on-fail\` and \`--history-max\` behavior.
4. Plan safe rolling releases with immutable image digests and verified chart versions.
5. Diagnose pending, failed, stuck and partially healthy upgrades.
6. Recover from bad probes, unavailable images, immutable-field changes and resource exhaustion.
7. Explain CRD, hook, database migration and secret rotation rollback limitations.
8. Create GitLab CI validation and production release governance.
9. Perform evidence-based release acceptance using Kubernetes and application SLIs.
10. Write a repeatable Helm incident response runbook.

## 2. Helm release lifecycle architecture

\`\`\`text
Chart source + Chart.lock + values
                 |
           helm template
                 |
        lint / policy / review
                 |
           helm install
                 |
          Release revision 1
                 |
       helm upgrade (new values/chart)
                 |
          Release revision 2
                 |
       success / failure / rollback
                 |
       Helm release history metadata
                 |
          Kubernetes resources
                 |
       Pods / Service / user SLIs
\`\`\`

Helm stores release information in the target namespace, normally using Kubernetes Secrets. Release metadata can include rendered manifests and values, so **do not embed credentials** in charts or values. Protect access to release storage using RBAC and secret-management controls.

Argo CD typically uses Helm only to render manifests and stores reconciliation state in Argo CD resources rather than Helm CLI release history.

## 3. Command reference

| Command | Use | SRE caution |
| --- | --- | --- |
| \`helm install\` | Create release | Confirm target namespace and ownership |
| \`helm upgrade\` | Apply new chart/values | Confirm immutable image and migration compatibility |
| \`helm upgrade --install\` | Install if absent, otherwise upgrade | Avoid accidental installation in wrong namespace |
| \`helm status\` | Inspect current release | Not proof of application SLO health |
| \`helm list -a\` | List releases including nondeployed statuses | RBAC limits visibility |
| \`helm history\` | Inspect revisions | History can be pruned |
| \`helm get values\` | View release values | Output may be sensitive |
| \`helm get manifest\` | View deployed manifest | Output may be sensitive |
| \`helm rollback\` | Restore earlier Helm revision | Does not reverse external data changes |
| \`helm uninstall\` | Remove release resources | Persistent data and CRDs may remain |
| \`helm template\` | Render locally | Does not execute admission/runtime checks |
| \`helm lint\` | Static chart checks | Not comprehensive policy validation |

Use \`helm get\` output only in authorized channels. Avoid storing secrets or sensitive manifests in CI artifacts.

## 4. Lab topology and safeguards

Use the Chapter 032 chart \`charts/demo-app\` with a **real approved image digest**. The app must listen on port 8080 and expose \`/healthz\`.

Prerequisites:

\`\`\`bash
helm version
kubectl version --client
kubectl config current-context
kubectl get namespace demo-dev
kubectl auth can-i create deployments -n demo-dev
kubectl auth can-i create secrets -n demo-dev
\`\`\`

Use release name \`demo-app-helm-lab\`, ensuring no existing Argo CD Application or other operator owns matching resources. Check:

\`\`\`bash
helm list -n demo-dev -a
kubectl get deployment -n demo-dev
\`\`\`

**Do not run the live lab** if ownership is unclear. You can complete offline rendering, policy checks and runbook exercises without cluster write access.

## 5. Prepare release artifacts

Record the approved inputs:

\`\`\`text
Source commit:         <approved-git-sha>
Chart version:         0.1.0
Chart source/package:  <approved-chart-reference>
Image digest:          sha256:<real-verified-digest>
Target namespace:      demo-dev
Release name:          demo-app-helm-lab
\`\`\`

For this lab, create \`environments/dev/helm-lab-values.yaml\`:

\`\`\`yaml
fullnameOverride: demo-app-helm-lab
replicaCount: 2
config:
  appEnv: dev
  featureEnabled: false
  logLevel: info
autoscaling:
  enabled: false
podDisruptionBudget:
  enabled: false
networkPolicy:
  enabled: false
\`\`\`

Set the approved image digest in a separate reviewed values overlay or replace the synthetic digest in your disposable chart copy. Do not commit an environment-specific secret. Confirm \`helm template\` renders the real digest before installing.

## 6. Lab A — Preflight and dry-run validation

Run:

\`\`\`bash
helm dependency build charts/demo-app
helm lint charts/demo-app
helm template demo-app-helm-lab charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/helm-lab-values.yaml > rendered-helm-lab.yaml
\`\`\`

Review the rendered YAML:

- Deployment and Service selectors match.
- Image uses the approved \`repository@sha256:<digest>\` reference.
- ConfigMap and Pod-template checksum agree.
- Resource requests, limits, probes and security context are present.
- No cluster-scoped resources, privileged containers or plaintext secrets appear unexpectedly.
- No conflicting object name exists in \`demo-dev\`.

If authorized, a server-side dry run can check API admission on rendered manifests:

\`\`\`bash
kubectl apply --dry-run=server -n demo-dev -f rendered-helm-lab.yaml
\`\`\`

This can still be limited by RBAC or admission configuration and is **not** equivalent to a successful installation.

## 7. Lab B — Install and inspect a release

Only in the approved disposable namespace:

\`\`\`bash
helm install demo-app-helm-lab charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/helm-lab-values.yaml \
  --wait --timeout 5m

helm status demo-app-helm-lab -n demo-dev
helm history demo-app-helm-lab -n demo-dev
helm list -n demo-dev
kubectl rollout status deployment/demo-app-helm-lab -n demo-dev --timeout=240s
kubectl get deployment,pods,svc -n demo-dev -l app.kubernetes.io/instance=demo-app-helm-lab
\`\`\`

Expected: revision 1 is deployed, Pods become ready and the Service has ready EndpointSlices.

\`--wait\` waits for supported Kubernetes readiness conditions; it does not prove that application latency, error rate or all business functions meet SLOs.

## 8. Lab C — Release metadata and history

Inspect:

\`\`\`bash
helm history demo-app-helm-lab -n demo-dev
helm status demo-app-helm-lab -n demo-dev
helm get values demo-app-helm-lab -n demo-dev
helm get manifest demo-app-helm-lab -n demo-dev
kubectl get secrets -n demo-dev -l owner=helm,name=demo-app-helm-lab
\`\`\`

**Security:** Helm release Secrets are sensitive metadata. Do not dump raw release Secret contents into tickets or public CI logs.

Document revision, status, chart version, image digest and configuration checksum. Compare with the approved Git source.

## 9. Lab D — Safe configuration upgrade

Create \`environments/dev/helm-lab-upgrade.yaml\`:

\`\`\`yaml
config:
  featureEnabled: true
  logLevel: debug
\`\`\`

Upgrade using **both** the base lab values and upgrade overlay:

\`\`\`bash
helm upgrade demo-app-helm-lab charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/helm-lab-values.yaml \
  -f environments/dev/helm-lab-upgrade.yaml \
  --wait --timeout 5m

helm history demo-app-helm-lab -n demo-dev
kubectl rollout status deployment/demo-app-helm-lab -n demo-dev --timeout=240s
\`\`\`

The chart's ConfigMap checksum annotation should trigger a new Pod-template revision. Check the actual application configuration through a controlled port-forward:

\`\`\`bash
kubectl port-forward -n demo-dev service/demo-app-helm-lab 8080:80
\`\`\`

In a second terminal:

\`\`\`bash
curl --fail --silent http://127.0.0.1:8080/healthz
curl --fail --silent http://127.0.0.1:8080/config
\`\`\`

Stop port-forward with Ctrl+C. Record revision 2, rollout duration, ready replicas and configuration result.

## 10. Understand Helm upgrade flags

| Flag | Meaning | Caution |
| --- | --- | --- |
| \`--wait\` | Wait for supported resources to become ready | Does not enforce application SLOs |
| \`--timeout 5m\` | Bound wait time for individual operations | Must reflect real startup time |
| \`--atomic\` | On failed upgrade, attempt rollback; automatically enables wait | Does not undo database or external side effects |
| \`--cleanup-on-fail\` | Delete certain newly created resources on upgrade failure | Not a general transactional rollback |
| \`--wait-for-jobs\` | Include Jobs in wait checks when wait is enabled | Hook/job semantics need review |
| \`--history-max\` | Bound retained revisions | Pruned revisions cannot be selected later |
| \`--reuse-values\` | Reuse existing release values | Can preserve stale/unexpected settings |
| \`--reset-values\` | Start from chart defaults before overrides | Can drop required prior customizations |
| \`--force\` | Replace resources when necessary | Can be disruptive; avoid routine use |

Review the installed Helm version's help for exact supported flags and semantics:

\`\`\`bash
helm upgrade --help
helm rollback --help
\`\`\`

Prefer explicit, reviewed values files over \`--reuse-values\` in production workflows.

## 11. Lab E — Failure injection: broken readiness

Only in the disposable Helm lab, modify a copy of the chart's Deployment readiness path to \`/not-ready\`. Do not change the canonical chart or an Argo CD-managed Application.

Run an upgrade **without** \`--atomic\` to observe the failed state:

\`\`\`bash
helm upgrade demo-app-helm-lab charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/helm-lab-values.yaml \
  -f environments/dev/helm-lab-upgrade.yaml \
  --wait --timeout 90s
\`\`\`

Expected: the new Pods do not become ready, and Helm may mark the upgrade failed after timeout. With \`maxUnavailable: 0\`, previous ready replicas may continue serving, provided the old revision remains healthy and capacity permits.

Investigate:

\`\`\`bash
helm history demo-app-helm-lab -n demo-dev
kubectl describe deployment demo-app-helm-lab -n demo-dev
kubectl get pods -n demo-dev -l app.kubernetes.io/instance=demo-app-helm-lab
kubectl get events -n demo-dev --sort-by=.lastTimestamp
\`\`\`

Restore the correct readiness path before the next exercise.

## 12. Lab F — Manual Helm rollback

For the standalone Helm-managed lab only, identify a known-good revision:

\`\`\`bash
helm history demo-app-helm-lab -n demo-dev
\`\`\`

Then replace \`<KNOWN_GOOD_REVISION>\` with the verified revision number:

\`\`\`bash
helm rollback demo-app-helm-lab <KNOWN_GOOD_REVISION> \
  --namespace demo-dev --wait --timeout 5m

helm history demo-app-helm-lab -n demo-dev
kubectl rollout status deployment/demo-app-helm-lab -n demo-dev --timeout=240s
\`\`\`

Rollback creates another Helm release revision representing restored state. Verify Service connectivity and application SLIs; do not assume command success proves user impact has ended.

**PowerShell note:** Use the same command with an actual numeric revision; angle-bracket placeholders are documentation only.

## 13. Lab G — Automatic rollback with atomic upgrade

With the corrected chart and a known-good release in place, inject an invalid readiness path again in a disposable copy and run:

\`\`\`bash
helm upgrade demo-app-helm-lab charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/helm-lab-values.yaml \
  --atomic --timeout 90s
\`\`\`

Expected: Helm attempts rollback if the upgrade fails. Inspect \`helm history\`, Deployment readiness and actual application responses.

**Important:** \`--atomic\` is not a database transaction and cannot guarantee restoration of external state, PersistentVolume contents, schema migrations or downstream side effects. Record both the upgrade failure and rollback result.

## 14. Release state and failure modes

Helm release statuses can include \`deployed\`, \`failed\`, \`pending-install\`, \`pending-upgrade\`, \`pending-rollback\`, \`uninstalled\` and others depending on lifecycle and retained history.

A pending state can result from interrupted operations, long-running hooks or timeouts. **Do not manually delete Helm release Secrets** to clear a stuck status without an approved recovery plan; this can destroy history and complicate ownership.

Investigate the cause and preserve metadata before taking action.

## 15. Production rollback limitations

| Change | Helm rollback restores? | Additional recovery |
| --- | --- | --- |
| Deployment image and spec | Usually attempts to restore prior manifest | Verify old image retained |
| ConfigMap template | Usually | Restart/reconcile dependent workloads |
| External database schema | No | Backward-compatible migrations / recovery plan |
| Data written after release | No | Application/data reconciliation |
| CRD definition changes | Not reliably as normal resources | Dedicated CRD lifecycle plan |
| PVC contents | No | Backup/restore or application-level recovery |
| External DNS/CDN | Not necessarily | Separate traffic rollback |
| Rotated secret in external vault | No | Approved secret version recovery |
| Irreversible hook side effects | No | Explicit compensating actions |

A safe release requires backward-compatible schema changes, retained artifacts and tested recovery procedures.

## 16. Kubernetes rollout vs Helm release rollback

\`kubectl rollout undo deployment/...\` restores a Deployment revision but does not necessarily restore the matching ConfigMap, Service, PDB or other chart resources. Helm rollback targets a Helm release revision. Argo CD GitOps rollback restores reviewed desired state from Git.

Choose recovery at the **correct ownership boundary**. Mixing these mechanisms can create drift and partial recovery.

## 17. GitOps-specific release lifecycle

For Argo CD-managed Helm charts:

1. GitLab CI builds, scans and verifies the application image.
2. Chart and image references are pinned and reviewed.
3. An approved GitOps MR updates environment-specific values or chart version.
4. Argo CD renders and reconciles resources.
5. SRE monitors Deployment health, sync status and user-facing SLIs.
6. On regression, revert the GitOps change to the last known-good chart/image configuration.
7. Verify Argo CD convergence and restored SLIs.

Do not use \`helm history\` as the source of truth for an Argo CD Helm-rendered Application.

## 18. GitLab CI release checks

Illustrative validation stage:

\`\`\`yaml
helm_release_preflight:
  stage: validate
  image: registry.example.com/platform/helm@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - helm dependency build charts/demo-app
    - helm lint charts/demo-app
    - helm template demo-app charts/demo-app --namespace demo-dev -f environments/dev/values.yaml > dev.yaml
    - helm template demo-app charts/demo-app --namespace demo-test -f environments/test/values.yaml > test.yaml
    - helm template demo-app charts/demo-app --namespace demo-staging -f environments/staging/values.yaml > staging.yaml
    - helm template demo-app charts/demo-app --namespace demo-prod -f environments/prod/values.yaml > prod.yaml
  artifacts:
    paths: [dev.yaml, test.yaml, staging.yaml, prod.yaml]
    expire_in: 1 day
\`\`\`

Replace the tool image placeholder with a real approved digest. Add schema checks, policy-as-code, secret scanning, signature/provenance verification and controlled approvals. A passing lint/render stage is **not** sufficient for production promotion.

## 19. Release readiness checklist

Before any production release:

- Approved source, chart version and immutable image digest are recorded.
- Security and policy checks pass.
- Chart dependencies and provenance are trusted.
- Resource quota, surge capacity and PDB compatibility are reviewed.
- Probes, Service selectors and configuration checksums are validated.
- Database and API backward compatibility are documented.
- Previous chart and image artifacts remain retrievable.
- Release window, owner, rollback authority and communications are assigned.
- Application SLIs and alert baselines are available.
- A rollback rehearsal or documented recovery procedure exists.

## 20. Troubleshooting matrix

| Symptom | Likely cause | Diagnostic action |
| --- | --- | --- |
| Helm upgrade times out | Unready Pods, hook or scheduling issue | \`helm status\`, events, rollout |
| \`ImagePullBackOff\` | Digest, registry auth or network | Pod events and registry evidence |
| \`CrashLoopBackOff\` | Application crash or liveness failures | Previous logs and probe config |
| No Service endpoints | Selector mismatch or unready Pods | EndpointSlices, Pod labels |
| HPA not scaling | Metrics missing or resource requests absent | \`kubectl describe hpa\` |
| Release pending-upgrade | Interrupted/stuck operation | History, hooks and events |
| Immutable field error | Changed Deployment selector or other immutable field | Compare manifests |
| Atomic rollback fails | Previous revision unavailable or cluster problem | History, events and artifacts |
| Release deployed but users fail | SLO regression or external dependency | Application telemetry |
| Argo CD reverts manual fix | Git desired state differs | Revert/approve GitOps state |

## 21. SRE incident runbook — Failed release

**Scenario:** A chart upgrade is marked failed, new Pods are unready and user-facing error rates increase.

1. Confirm cluster context, namespace, release ownership and current revision.
2. Stop further promotion and identify the incident commander/change owner.
3. Capture \`helm status\`, \`helm history\`, Kubernetes events and application SLIs.
4. Check image digest, probe paths, Service endpoints, quotas and dependencies.
5. Determine whether an old healthy ReplicaSet is still serving traffic.
6. Choose rollback according to ownership: Helm revision for standalone release; Git revert for Argo CD.
7. Execute the approved rollback; watch Pods and Service endpoints.
8. Verify 5xx/error-rate and latency recovery against baselines.
9. Preserve release evidence and record root cause, timeline and follow-ups.

Do not clear failures by deleting Helm release Secrets or bypassing admission policy.

## 22. Observability and SLO validation

Monitor:

- Helm release status and revision changes.
- Upgrade duration and failed upgrade count.
- Deployment desired/available replicas.
- Pod readiness, restarts, OOMKills and scheduling failures.
- Service EndpointSlices and ingress/backend health.
- HPA metrics and resource pressure.
- HTTP error rate, p95/p99 latency and throughput.
- Argo CD sync/health and drift for GitOps workloads.

Set thresholds using measured application SLOs; a successful Helm command is not sufficient evidence of a successful user-facing release.

## 23. Optional cleanup

Only for the disposable, independently Helm-managed release:

\`\`\`bash
helm uninstall demo-app-helm-lab -n demo-dev
helm list -n demo-dev -a
\`\`\`

Verify cleanup does not affect shared resources. PersistentVolumes, CRDs and external resources may remain and require separate authorized lifecycle procedures. For GitOps-managed workloads, remove or update the Git source of truth instead.

## 24. Acceptance checklist

- [ ] Ownership verified: standalone Helm vs Argo CD.
- [ ] Chart lint/render and image digest verification completed.
- [ ] Disposable Helm release installed and inspected.
- [ ] Release history and values reviewed securely.
- [ ] Configuration upgrade created a new revision.
- [ ] Application endpoints and SLOs validated after upgrade.
- [ ] Failed readiness upgrade reproduced and diagnosed.
- [ ] Manual rollback restored a known-good revision.
- [ ] Atomic rollback behavior tested or limitation recorded.
- [ ] External data/CRD/hook rollback limitations documented.
- [ ] GitLab CI and GitOps promotion boundaries reviewed.
- [ ] Incident runbook and cleanup completed.

## 25. Evidence worksheet

\`\`\`text
CHAPTER 034 — HELM RELEASE LIFECYCLE
Date:
Reviewer:
Cluster / context / namespace:
Helm version:
Release name:
Chart version:
Source Git commit:
Verified image digest:
Initial Helm revision/status:
Upgrade Helm revision/status:
Upgrade start/end and duration:
Pod ready/desired:
Service EndpointSlices:
HTTP health/config response:
Failure injection:
Failed revision/status:
Manual rollback revision/result:
Atomic rollback test/result:
Error-rate / p99 before and after:
GitOps ownership decision:
Rollback limitations:
Final score / pass:
Open risks and owners:
\`\`\`

## 26. Knowledge checks

1. How is a Helm release revision different from a GitOps commit?
2. Why does \`helm upgrade --atomic\` not guarantee database recovery?
3. Why is \`helm status deployed\` insufficient to prove release success?
4. What are the operational risks of \`--reuse-values\`?
5. Why should Helm release Secrets be access-controlled?
6. How do \`helm rollback\`, \`kubectl rollout undo\` and Git revert differ?
7. Why are retained chart and image artifacts essential for recovery?
8. What would you investigate first for a \`pending-upgrade\` release?

## 27. Completion

**Pass:** You demonstrate an authorized standalone Helm release installation, upgrade, failure investigation, manual rollback, and documented atomic rollback behavior while maintaining clear Argo CD ownership boundaries.

**Next: Chapter 035 — Enterprise Helm Chart Engineering, Security and Release Operations Capstone**, completing Part 07.
