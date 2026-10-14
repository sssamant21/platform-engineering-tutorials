# Chapter 039 — Argo CD Application Creation, Synchronization, Health and Drift Detection

**Part 08 — Argo CD Fundamentals and Installation** | **Chapter 039 of 100**  
**Audience:** SREs, platform engineers and Kubernetes administrators  
**Prerequisites:** Chapters 036–038; a reviewed Helm chart from Part 07; authorized access to an existing Argo CD instance  
**Reference architecture:** One Kubernetes cluster, Argo CD control plane in \`argocd\`, and four application namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.

> **Safety:** Start with manual sync, pruning disabled and self-heal disabled. Do not create or modify production Applications as part of the lab. All write exercises require an approved disposable application and namespace. Git is the desired-state authority for Argo CD-managed workloads; do not use independent \`helm upgrade\` or \`kubectl rollout undo\` as routine recovery methods.

## 1. Learning outcomes

You will be able to:

1. Define an Argo CD Application with a Git source, Helm rendering and Kubernetes destination.
2. Explain Application, AppProject and namespace authorization boundaries.
3. Compare manual and automated synchronization.
4. Interpret \`Synced\`, \`OutOfSync\`, \`Unknown\`, \`Healthy\`, \`Progressing\`, \`Degraded\` and \`Missing\`.
5. Inspect resource trees, revision history, diff and sync operations.
6. Detect live drift and distinguish it from an intentional Git change.
7. Understand self-heal, prune, sync waves, hooks and ownership risks.
8. Diagnose render, authorization, admission and runtime failures.
9. Recover through an approved GitOps revert.
10. Capture operational evidence and SLO-based acceptance.

## 2. Architecture: desired state versus live state

\`\`\`text
GitLab CI: build, test, scan, sign
              |
    Approved image@sha256:<digest>
              |
       GitLab GitOps MR
              |
       Reviewed Git commit
              |
      Argo CD repo-server
       Helm template render
              |
      Application controller
          compare/diff
              |
      Kubernetes live state
              |
       Sync if authorized
              |
       Pods / Services / SLIs
\`\`\`

An Argo CD Application declares **what should run**. The application controller continuously compares rendered desired manifests with live Kubernetes resources and, depending on policy, can reconcile differences.

**Critical distinction:** \`Synced\` means desired/live state agrees under Argo CD comparison rules. \`Healthy\` means resource health assessments pass. Neither independently guarantees user-facing latency or error-rate objectives.

## 3. One cluster, four Applications

| Application | Namespace | Values overlay | Promotion gate |
| --- | --- | --- | --- |
| \`demo-app-dev\` | \`demo-dev\` | \`env/dev-values.yaml\` | Reviewed change and smoke test |
| \`demo-app-test\` | \`demo-test\` | \`env/test-values.yaml\` | Integration tests |
| \`demo-app-staging\` | \`demo-staging\` | \`env/staging-values.yaml\` | SLO and operational checks |
| \`demo-app-prod\` | \`demo-prod\` | \`env/prod-values.yaml\` | Protected approval and change record |

Each Application has its own source configuration and destination namespace. All four run in the **same training cluster**. For high-criticality production, namespace separation may be insufficient; use independent clusters if required by risk assessment.

The application image digest is immutable. A single promotion wave advances the same verified digest through the environments; different environments can temporarily remain at different approved revisions while gates are pending.

## 4. Repository layout

For a first single-source Helm lab, keep environment values under the chart path:

\`\`\`text
demo-gitops/
├── charts/demo-app/
│   ├── Chart.yaml
│   ├── Chart.lock
│   ├── values.yaml
│   ├── values.schema.json
│   ├── env/
│   │   ├── dev-values.yaml
│   │   ├── test-values.yaml
│   │   ├── staging-values.yaml
│   │   └── prod-values.yaml
│   └── templates/
└── argocd/
    ├── projects/demo-platform.yaml
    └── applications/
        ├── demo-app-dev.yaml
        ├── demo-app-test.yaml
        ├── demo-app-staging.yaml
        └── demo-app-prod.yaml
\`\`\`

The Helm values paths below are relative to \`charts/demo-app\`. Do not use an out-of-chart relative path unless the Argo CD version and configured source mechanism explicitly support it.

## 5. AppProject: policy boundary

Before defining an Application, verify the approved Project:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  sourceRepos:
    - https://gitlab.example.com/platform/demo-gitops.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: demo-dev
    - server: https://kubernetes.default.svc
      namespace: demo-test
    - server: https://kubernetes.default.svc
      namespace: demo-staging
    - server: https://kubernetes.default.svc
      namespace: demo-prod
  clusterResourceWhitelist: []
\`\`\`

**Security:** AppProjects are an Argo CD authorization boundary, not a substitute for Kubernetes RBAC, admission policy or cluster isolation. Protect who can modify Projects and the controller's underlying Kubernetes permissions.

## 6. Define a Dev Application

\`argocd/applications/demo-app-dev.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app-dev
  namespace: argocd
spec:
  project: demo-platform
  source:
    repoURL: https://gitlab.example.com/platform/demo-gitops.git
    targetRevision: main
    path: charts/demo-app
    helm:
      releaseName: demo-app
      valueFiles:
        - env/dev-values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-dev
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
\`\`\`

This is a **manual-sync** Application. It does not set \`automated\`, \`prune\` or \`selfHeal\`. Confirm the repository, chart and values files exist before using it.

**Helm ownership:** Argo CD renders the Helm chart but does not normally create Helm CLI release history. Use Argo CD and Git revision history, not \`helm rollback\`, to manage this application.

## 7. Lab A — Preflight and offline validation

Read-only:

\`\`\`bash
kubectl config current-context
kubectl get namespace argocd demo-dev
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
argocd version --client
\`\`\`

In the Git checkout:

\`\`\`bash
helm dependency build charts/demo-app
helm lint charts/demo-app
helm template demo-app charts/demo-app \
  --namespace demo-dev \
  -f charts/demo-app/env/dev-values.yaml > rendered-dev.yaml
\`\`\`

Review selectors, resources, probes, Service endpoints, ConfigMap checksum and verified image digest. If Helm rendering fails offline, correct chart/values before diagnosing Argo CD.

## 8. Lab B — Create the Application safely

Only with approved write access to the disposable Dev Application:

\`\`\`bash
kubectl apply --dry-run=client -f argocd/applications/demo-app-dev.yaml
kubectl apply -f argocd/applications/demo-app-dev.yaml
kubectl get application demo-app-dev -n argocd -o yaml
argocd app get demo-app-dev
\`\`\`

**Expected before first sync:** The Application exists and can generate manifests. It may be \`OutOfSync\` because the desired resources have not yet been created. A \`Missing\` resource is not necessarily a controller failure before first deployment.

Record the Git revision, Project, destination and initial sync/health statuses.

## 9. Lab C — Review the desired/live diff

\`\`\`bash
argocd app get demo-app-dev
argocd app diff demo-app-dev
argocd app manifests demo-app-dev
argocd app resources demo-app-dev
\`\`\`

The diff may return a nonzero exit code when differences exist; this can be expected behavior rather than a CLI failure. Check your installed CLI's documented exit codes.

Review:

- Resources to be created, changed or deleted.
- Deployment image digest and chart version.
- Service selectors, labels and ConfigMap references.
- Resource kinds outside the intended namespace.
- Unexpected namespace, CRD, RBAC or Secret changes.

Do not sync if the diff contains unauthorized or destructive changes.

## 10. Lab D — Manual synchronization

Only after an approved diff and change authorization:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
argocd app get demo-app-dev
\`\`\`

The wait command may fail or time out even if some resources are running. Investigate before retrying.

Kubernetes checks:

\`\`\`bash
kubectl get deployment,pods,svc -n demo-dev
kubectl get endpointslices -n demo-dev
kubectl get events -n demo-dev --sort-by=.lastTimestamp
\`\`\`

Verify the application health endpoint using an approved internal route or port-forward. Check actual error rate, latency and readiness—not just the Argo CD status.

## 11. Understanding sync status

| Status | Meaning | SRE action |
| --- | --- | --- |
| \`Synced\` | Desired/live resources agree | Still check health and SLOs |
| \`OutOfSync\` | Desired/live difference detected | Review diff and source revision |
| \`Unknown\` | Comparison unavailable or inconclusive | Investigate repo/controller/API errors |

Sync status is a **comparison result**, not an approval, deployment or business-health guarantee.

## 12. Understanding health status

| Health | Typical interpretation | Investigation |
| --- | --- | --- |
| \`Healthy\` | Supported resource health checks pass | Validate application SLIs |
| \`Progressing\` | Rollout or reconciliation in progress | Pods, rollout and timeout |
| \`Degraded\` | Resource health assessment failed | Logs, probes, events, dependencies |
| \`Missing\` | Desired resource absent | Initial sync, deletion or ownership |
| \`Unknown\` | Health cannot be determined | Controller/resource health checks |
| \`Suspended\` | Resource intentionally suspended where supported | Confirm expected maintenance state |

An Application can be **Synced + Degraded** when the desired Deployment exists but Pods cannot become ready. An Application can be **OutOfSync + Healthy** when a live manual change still serves traffic.

## 13. Lab E — Observe a reviewed Git change

Create a GitLab MR that changes only a safe, nonsecret Dev setting (for example, an application feature flag), with the chart's ConfigMap checksum triggering a new Pod template.

1. Capture current Git commit, Argo CD status and Deployment image digest.
2. Open and approve the GitLab MR.
3. Merge it to the GitOps branch.
4. Observe Argo CD detecting the new desired revision.
5. Review the diff and perform authorized manual sync.
6. Confirm the new Deployment revision and updated application configuration.
7. Record SLOs and the change timeline.

Do **not** rebuild the application image merely to promote the configuration change.

## 14. Drift detection

Drift occurs when live Kubernetes resources differ from GitOps desired state. Causes include:

- Direct \`kubectl edit\` or \`kubectl scale\`.
- Admission controller mutation.
- HPA adjusting replicas.
- Another controller updating managed fields.
- Manual emergency hotfix.
- A resource deleted outside GitOps.
- A newly merged Git commit awaiting sync.

Some differences are expected and should be handled with narrowly scoped comparison rules, such as known HPA-managed fields. Avoid broad ignore rules that conceal real security or configuration drift.

## 15. Lab F — Simulate safe drift (disposable Dev only)

**Only if explicitly authorized:** Use a benign annotation on a disposable, Argo CD-owned Deployment. Confirm the Application is manual-sync and self-heal is disabled.

\`\`\`bash
kubectl annotate deployment demo-app -n demo-dev \
  sre-lab.example.com/drift=observed --overwrite
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

The Deployment name may differ based on Helm naming helpers; inspect it before running the command. Argo CD may ignore or normalize some annotations depending on compare options, so select an annotation that is actually part of tracked desired state and verify the diff. If no drift is reported, document the comparison behavior rather than forcing an unsafe mutation.

**Recovery:** Reconcile through an authorized Argo CD sync or restore the Git-desired state. Do not make untracked edits to production.

## 16. Manual sync versus automated sync

Manual sync requires an operator to initiate reconciliation after reviewing desired-state changes.

Automated sync example:

\`\`\`yaml
syncPolicy:
  automated:
    prune: false
    selfHeal: false
\`\`\`

With automated sync enabled, Argo CD can synchronize eligible OutOfSync Applications when source revisions change. \`selfHeal: true\` also allows automatic correction of certain live drift. \`prune: true\` permits deletion of resources removed from desired state.

**Do not enable auto-prune in this lab.** In production, review deletion blast radius, namespace ownership, PVC retention, finalizers, change windows and break-glass procedures.

## 17. Sync options, hooks and ordering

Argo CD supports sync options and resource ordering mechanisms such as sync phases, hooks and waves. Operational concerns:

- PreSync hooks can block deployments.
- Hook Jobs may require cleanup policies.
- Sync waves determine ordering, not application business readiness by themselves.
- Namespace and CRD prerequisites must be established before dependent resources.
- A failing hook can leave the Application operation failed even when some workloads run.
- Repeated hooks can have non-idempotent side effects.

Avoid introducing complex hooks without tested retry, cleanup and rollback behavior. Detailed orchestration is covered in later chapters.

## 18. History, revisions and rollback

Inspect:

\`\`\`bash
argocd app history demo-app-dev
argocd app get demo-app-dev
\`\`\`

**Preferred GitOps recovery:** Revert the reviewed GitOps commit that introduced the regression, then synchronize to the restored desired state and verify application SLIs.

Do not treat \`argocd app rollback\` as a substitute for Git revert in a managed promotion workflow: application history rollback has restrictions and may conflict with automated synchronization or subsequent Git reconciliation. Record the last-known-good chart version and immutable image digest.

## 19. Troubleshooting matrix

| Symptom | Layer | First action |
| --- | --- | --- |
| \`ComparisonError\` | Git/Helm manifest generation | Repo-server logs, path, values |
| \`OutOfSync\` after merge | Desired/live diff | Review Git revision and diff |
| \`SyncFailed\` | API/admission/hook | Application operation, events |
| \`Synced + Degraded\` | Kubernetes/runtime | Pods, probes, image and Service |
| \`Progressing\` indefinitely | Rollout or controller | Deployment conditions, events |
| \`Missing\` resource | Initial deploy, prune or deletion | Desired manifest and resource tree |
| HPA replica drift | Controller-managed field | Review ignoreDifferences carefully |
| Manual hotfix reverted | Self-heal enabled | Restore Git desired state |
| Unexpected deletion candidate | Prune policy | Stop sync and inspect diff |
| Permission denied | Project/Kubernetes RBAC | Project and ServiceAccount permissions |

Do not resolve errors by granting cluster-admin or disabling admission controls.

## 20. SRE incident runbook — Synced but Degraded

**Scenario:** A reviewed Dev promotion reports \`Synced\` but \`Degraded\`, with increased HTTP 5xx.

1. Confirm the Application, cluster context, namespace and Git revision.
2. Stop promotion to Test, Staging and Production.
3. Inspect Application resource tree, health and operation history.
4. Inspect Pods, Deployment conditions, events, logs and EndpointSlices.
5. Check image digest, registry access, probes, resource pressure and dependencies.
6. Compare 5xx, p95/p99 latency and traffic to pre-change baselines.
7. Revert the faulty GitOps change if the release is responsible.
8. Reconcile and verify both \`Synced\` and \`Healthy\`.
9. Confirm user-facing SLIs recover and record recovery time.
10. Create a follow-up to strengthen CI/policy/health gates.

**Key rule:** A successful Argo CD sync does not prove a successful release.

## 21. Observability and alerting

Monitor:

| Signal | Why |
| --- | --- |
| Application OutOfSync duration | Unexpected drift or stalled promotion |
| Application Degraded duration | Runtime release failure |
| Reconciliation errors | Controller/repo problems |
| Manifest-generation failures | Helm/path/dependency issues |
| Sync failures and retries | API/admission/hooks |
| Unexpected prune candidates | Destructive change risk |
| Deployment available replicas | Workload availability |
| Pod restarts/OOMKills | Runtime instability |
| Service EndpointSlices | Backend readiness |
| HTTP error rate and p95/p99 | User-facing SLO |

Alert on persistent or meaningful conditions using real service baselines; brief OutOfSync during a manual approval gate can be expected.

## 22. Cloud considerations

| Concern | Amazon EKS | Azure AKS | Google GKE |
| --- | --- | --- | --- |
| Identity | EKS Pod Identity/IRSA | Entra Workload ID | Workload Identity Federation |
| Image registry | ECR | ACR | Artifact Registry |
| Network | VPC/CNI/ingress | VNet/CNI/ingress | VPC/CNI/ingress |
| Audit | CloudTrail/Kubernetes | Azure Monitor/Kubernetes | Cloud Audit/Kubernetes |

The Argo CD Application model remains consistent, but network, registry authentication, admission and workload identity are cloud-specific.

## 23. Acceptance checklist

- [ ] Application source and destination are approved.
- [ ] AppProject restricts source repositories and namespaces.
- [ ] Chart renders with correct environment values.
- [ ] Immutable verified image digest is present.
- [ ] Manual-sync Application created in approved Dev scope.
- [ ] Desired/live diff reviewed before synchronization.
- [ ] Sync status and health status recorded independently.
- [ ] Runtime Pods, Service and SLOs verified after sync.
- [ ] Reviewed Git change detected and synchronized.
- [ ] Drift scenario observed or documented safely.
- [ ] Auto-prune and self-heal risk assessed.
- [ ] Git revert rollback procedure documented.
- [ ] Incident runbook and evidence completed.

## 24. Evidence worksheet

\`\`\`text
CHAPTER 039 — APPLICATION SYNC, HEALTH AND DRIFT
Date:
Reviewer:
Cluster/context:
Application/Project:
GitLab repository:
Source commit:
Helm chart/version:
Values file:
Verified image digest:
Destination namespace:
Initial sync/health:
Reviewed diff:
Manual sync result:
Deployment availability:
Service EndpointSlices:
HTTP health response:
SLO baseline/after:
Git change revision:
Drift test and diff:
Automated sync/prune/self-heal policy:
Rollback Git commit:
Recovery evidence:
Open risks:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 25. Knowledge checks

1. What is the difference between \`Synced\` and \`Healthy\`?
2. Why can an Application be Synced but Degraded?
3. What is the role of the AppProject?
4. Why are Helm CLI release commands not authoritative for Argo CD-managed resources?
5. What causes live drift?
6. When might HPA create an expected difference?
7. What is the risk of enabling prune?
8. How does self-heal affect emergency live changes?
9. Why is Git revert the preferred release recovery path?
10. What runtime signals must pass after a successful sync?

## 26. Completion

**Pass:** You can create and inspect a manually synchronized Application, review desired/live differences, diagnose sync versus health failures, observe drift safely, and recover through GitOps with SLO evidence.

**Next: Chapter 040 — Argo CD Installation, Application Operations and Recovery Capstone**, completing Part 08.
