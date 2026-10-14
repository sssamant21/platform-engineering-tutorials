# Chapter 040 — Argo CD Installation, Application Operations and Recovery Capstone

**Part 08 — Argo CD Fundamentals and Installation: Final Capstone**  
**Chapter 040 of 100** | **Audience:** SRE, infrastructure and platform operations engineers  
**Prerequisites:** Chapters 036–039, Helm Chapters 031–035 and GitLab CI/CD foundations.

> **Safety boundary:** This chapter is designed for an authorized disposable Kubernetes environment. The reference topology uses **one cluster** and four namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`. Argo CD runs in \`argocd\`. Do not install cluster-scoped CRDs, modify SSO/RBAC, delete resources, inject failures or enable automated pruning in a shared production cluster without approved change control. Never place real credentials in Git or evidence logs.

## 1. Mission

You are the platform on-call engineer assigned to certify an Argo CD deployment and GitLab-to-Kubernetes GitOps delivery process. The application is a generic HTTP service packaged as a reusable Helm chart. The platform must support reviewed changes, least-privilege access, drift detection, recovery and reliable release evidence.

The capstone integrates:

- **036:** Architecture, controllers, repo-server, Application/AppProject and reconciliation.
- **037:** Installation, namespace/RBAC design, SSO and bootstrap configuration.
- **038:** CLI/UI operations, GitLab repository credentials, TLS and connectivity.
- **039:** Application creation, sync, health, drift and GitOps rollback.

**Exit standard:** 85/100 or higher, no failed critical controls, and a complete evidence worksheet. Mark unperformed exercises **Not Tested**; do not claim live validation from an offline render.

## 2. Reference architecture

\`\`\`text
        GitLab source repository
        build/test/scan/sign ONCE
                  |
     OCI image@sha256:<verified digest>
                  |
        Reviewed GitOps repository
                  |
       +----------+-----------+
       | Argo CD control plane|
       | namespace: argocd    |
       | server + repo-server |
       | application controller
       | Redis + ApplicationSet
       +----------+-----------+
                  |
             Kubernetes API
                  |
           ONE training cluster
        +---------+---------+----------+
        |         |         |          |
     demo-dev  demo-test demo-staging demo-prod
        |         |         |          |
       Application per namespace + Helm values
\`\`\`

Argo CD is the authoritative controller for these workloads. **Do not independently use \`helm upgrade\`, \`helm rollback\` or \`kubectl rollout undo\` to manage an Argo CD-owned application.** Recovery is through reviewed GitOps desired-state changes.

## 3. Deliverables

Create a working lab repository or copy:

\`\`\`text
argocd-capstone/
├── charts/demo-app/
│   ├── Chart.yaml
│   ├── Chart.lock
│   ├── values.yaml
│   ├── values.schema.json
│   ├── templates/
│   └── env/
│       ├── dev-values.yaml
│       ├── test-values.yaml
│       ├── staging-values.yaml
│       └── prod-values.yaml
├── argocd/
│   ├── projects/demo-platform.yaml
│   └── applications/
│       ├── demo-app-dev.yaml
│       ├── demo-app-test.yaml
│       ├── demo-app-staging.yaml
│       └── demo-app-prod.yaml
├── tests/
│   └── preflight.sh
└── docs/
    ├── CHANGE-RECORD.md
    ├── SECURITY-REVIEW.md
    ├── INCIDENT-RUNBOOK.md
    └── EVIDENCE.md
\`\`\`

Reuse the validated chart from Part 07; do not substitute a minimal chart that omits probes, security contexts, resource requests, configuration checksum or image digest pinning.

## 4. Phase 1 — Preflight and approval

Run read-only:

\`\`\`bash
kubectl config current-context
kubectl cluster-info
kubectl version
kubectl get namespaces
kubectl get crd applications.argoproj.io
kubectl get crd appprojects.argoproj.io
kubectl get crd applicationsets.argoproj.io
kubectl get deployments,statefulsets,services -n argocd
argocd version --client
\`\`\`

If Argo CD is not installed, do not install it without approved cluster-scoped change authorization. Follow Chapter 037 using a pinned, reviewed artifact and compatibility matrix.

Record:

\`\`\`text
Cluster/context:
Change ID and approver:
Approved Argo CD version:
Kubernetes version:
Argo CD namespace:
GitLab repository:
Helm chart version:
Chart package/OCI digest:
Verified image digest:
Approved destination namespaces:
SSO/RBAC owner:
Backup/rollback owner:
Application SLO baseline:
\`\`\`

## 5. Phase 2 — Validate the control plane

\`\`\`bash
kubectl get pods -n argocd -o wide
kubectl get deployments,statefulsets -n argocd
kubectl get services -n argocd
kubectl get events -n argocd --sort-by=.lastTimestamp
\`\`\`

Verify the installed topology rather than assuming component workload kinds. Required roles typically include the API server, repository server and application controller, plus cache and optional controllers.

Inspect capacity, restarts, Pod readiness and availability. Check that Kubernetes API and GitLab connectivity are available. A healthy Argo CD API server alone does not prove reconciliation works.

## 6. Phase 3 — Security and authorization audit

Inspect the approved RBAC configuration without disclosing secrets:

\`\`\`bash
kubectl get configmap argocd-rbac-cm -n argocd -o yaml
kubectl get serviceaccounts,roles,rolebindings -n argocd
kubectl get clusterroles,clusterrolebindings
kubectl get appprojects.argoproj.io -n argocd
\`\`\`

Audit:

| Control | Required outcome |
| --- | --- |
| Identity | SSO/OIDC and MFA for human operators |
| Default Argo CD RBAC | Least privilege; no routine shared admin |
| Project restrictions | Approved repos, namespaces and resource kinds |
| Kubernetes RBAC | Controller privileges reviewed independently |
| GitLab access | Read-only scoped repo credentials |
| Secrets | External secret management; no plaintext Git |
| TLS/SSH | Trusted GitLab CA and host keys |
| Registry | Verified immutable image digests |
| CI governance | Protected branches and MR approval |
| Emergency access | Audited, tested break-glass procedure |

**Critical:** An AppProject restriction is not the same as Kubernetes RBAC. A Project cannot remove privileges already held by the controller ServiceAccount.

## 7. Phase 4 — Validate GitLab and Helm rendering

Verify repository source and paths:

\`\`\`text
repoURL: https://gitlab.example.com/platform/demo-gitops.git
path: charts/demo-app
valueFiles:
  - env/dev-values.yaml
\`\`\`

Run from a trusted Git checkout:

\`\`\`bash
helm dependency build charts/demo-app
helm lint charts/demo-app
helm template demo-app charts/demo-app \
  --namespace demo-dev \
  -f charts/demo-app/env/dev-values.yaml > rendered-dev.yaml
helm template demo-app charts/demo-app \
  --namespace demo-test \
  -f charts/demo-app/env/test-values.yaml > rendered-test.yaml
helm template demo-app charts/demo-app \
  --namespace demo-staging \
  -f charts/demo-app/env/staging-values.yaml > rendered-staging.yaml
helm template demo-app charts/demo-app \
  --namespace demo-prod \
  -f charts/demo-app/env/prod-values.yaml > rendered-prod.yaml
\`\`\`

Inspect image digests, selectors, ServiceAccounts, security contexts, probes, resources and optional HPA/PDB/NetworkPolicy.

**Offline rendering does not prove** admission, registry access, Kubernetes health or user-facing SLOs.

## 8. Phase 5 — Restricted AppProject

\`argocd/projects/demo-platform.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  description: Approved demo application destinations
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
  namespaceResourceBlacklist:
    - group: rbac.authorization.k8s.io
      kind: Role
    - group: rbac.authorization.k8s.io
      kind: RoleBinding
\`\`\`

The Project is illustrative. Confirm the actual chart does not require disallowed resources. Protect Project modifications with platform-team ownership.

In an authorized lab:

\`\`\`bash
kubectl apply --dry-run=client -f argocd/projects/demo-platform.yaml
kubectl apply -f argocd/projects/demo-platform.yaml
kubectl get appproject demo-platform -n argocd
\`\`\`

## 9. Phase 6 — Define four Applications

Dev Application:

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

Repeat the pattern with the following substitutions:

| Application name | Destination | Chart-local values |
| --- | --- | --- |
| \`demo-app-dev\` | \`demo-dev\` | \`env/dev-values.yaml\` |
| \`demo-app-test\` | \`demo-test\` | \`env/test-values.yaml\` |
| \`demo-app-staging\` | \`demo-staging\` | \`env/staging-values.yaml\` |
| \`demo-app-prod\` | \`demo-prod\` | \`env/prod-values.yaml\` |

These are **four Applications targeting one cluster**, not four clusters. Keep manual sync and pruning disabled until operational approval. Production change approval must be enforced in both GitLab and Argo CD access controls.

## 10. Phase 7 — Manual Dev sync and runtime checks

Only on an approved disposable Dev application:

\`\`\`bash
kubectl apply --dry-run=client -f argocd/applications/demo-app-dev.yaml
kubectl apply -f argocd/applications/demo-app-dev.yaml
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

Review every change, including resource deletion candidates. After approval:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
kubectl get deployment,pods,svc -n demo-dev
kubectl get endpointslices -n demo-dev
kubectl get events -n demo-dev --sort-by=.lastTimestamp
\`\`\`

Record \`Synced\` and \`Healthy\` separately. Verify the application's actual health endpoint and measured error rate/latency.

## 11. Phase 8 — Reviewed GitOps promotion

1. GitLab CI builds, scans and signs the application image once.
2. Record the verified \`image@sha256\` digest.
3. Update Dev values through an approved GitOps MR.
4. Review Argo CD diff, sync Dev and validate readiness/SLIs.
5. Promote the **same digest** to Test, then Staging, then Production.
6. At each gate, capture source commit, chart version, image digest and approval.
7. Halt promotion on an unresolved comparison, sync, health or SLO failure.

Do not rebuild per environment. During a promotion wave, environments may temporarily run different previously approved digests.

## 12. Phase 9 — Safe drift demonstration

Use a disposable Argo CD-managed Dev Deployment only, with self-heal disabled. First inspect the actual Deployment name:

\`\`\`bash
kubectl get deployments -n demo-dev
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

If approved, make a benign temporary change to a tracked field (such as a test annotation explicitly present in desired state), then observe whether Argo CD detects the difference. Some fields are ignored or normalized by Argo CD comparison settings, so verify that the chosen field is tracked.

Restore through authorized synchronization to Git desired state. Do not mutate production resources or rely on a live patch as a lasting change.

## 13. Phase 10 — Failure injection matrix

Complete at least four approved failure tests in a disposable scope:

| Test | Fault | Expected signal | Recovery |
| --- | --- | --- | --- |
| GitLab URL | Invalid source URL | Repository connection failure | Restore reviewed URL |
| Helm values | Missing chart-local values file | Manifest generation error | Fix reviewed path |
| Project boundary | Unauthorized namespace | AppProject destination denial | Restore approved namespace |
| Image digest | Unavailable test image digest | ImagePullBackOff / Degraded | Revert to verified digest |
| Readiness | Bad probe path | Synced but Degraded | Git revert and sync |
| SSO/RBAC | Unauthorized sync attempt | Access denied | Keep least privilege |
| Controller capacity | Simulated queue backlog | Slow reconciliation | Capacity/metrics review |
| Prune policy | Dry-run deletion candidate | Destructive diff | Halt and review |

Never inject faults into shared Argo CD controllers or production workloads.

## 14. Phase 11 — GitOps rollback exercise

Scenario: a reviewed Dev change updates the readiness probe to an invalid path and causes a failed rollout.

1. Capture last-known-good GitOps commit and image digest.
2. Observe \`Synced\` versus \`Degraded\` (or a failed sync operation) and Kubernetes events.
3. Stop promotion to Test/Staging/Production.
4. Open a GitLab revert MR restoring the last-known-good chart/values configuration.
5. Obtain the required approval and merge.
6. Synchronize the Application if manual sync is configured.
7. Verify healthy Pods, Service EndpointSlices and application SLIs.
8. Record detection, recovery duration and preventive controls.

**Do not use \`helm rollback\` on an Argo CD-managed Helm chart.** Argo CD usually renders Helm manifests without creating a Helm CLI release. GitOps desired-state history is the release authority.

## 15. Operational diagnostic decision tree

\`\`\`text
Argo CD API unavailable?
  -> server Pods, TLS, SSO, ingress/port-forward
Application comparison fails?
  -> GitLab URL, credentials, DNS, repo-server, Helm path
Application sync fails?
  -> AppProject, Kubernetes RBAC, admission, hooks
Application Synced but Degraded?
  -> Pods, probes, image pull, Service, runtime dependencies
Application OutOfSync unexpectedly?
  -> Git commit, live drift, HPA, mutating webhooks
Application Healthy but user impact?
  -> HTTP errors, latency, dependencies, traffic routing
\`\`\`

Do not resolve authorization failures by granting cluster-admin or bypassing security admission.

## 16. Security and reliability acceptance gates

| Gate | Required evidence |
| --- | --- |
| GitLab MR approval | Approved commit/change record |
| Artifact immutability | Verified image digest and chart version |
| GitLab credentials | Scoped read-only repo access |
| Argo CD RBAC | Authorized and denied-action tests |
| AppProject | Approved repo/destination restrictions |
| Manifest rendering | Helm lint/template results |
| Kubernetes readiness | Deployment/Pods/Service endpoints |
| Application health | Sync and health independently recorded |
| User-facing SLO | HTTP errors/latency baseline comparison |
| Recovery | Tested Git revert and restored SLIs |
| Control-plane readiness | Components/metrics/backup owner |
| Auditability | Logs, approvers, timestamps and runbook |

## 17. Observability

Monitor:

- Argo CD server, controller and repo-server availability.
- Repository connection and manifest generation failures.
- Application OutOfSync and Degraded duration.
- Reconciliation duration and controller queue/backlog.
- Sync operation failures, unexpected prune candidates and resource deletions.
- Kubernetes Pod restarts, readiness, OOMKills and EndpointSlices.
- Application HTTP 5xx, p95/p99 latency and SLO burn.
- GitLab token/SSO certificate expiration and audit events.

Set thresholds based on measured workloads. A successful sync is not proof of user-facing reliability.

## 18. Backup, HA and recovery readiness

Document owners and tested procedures for:

- Backup/restore of Applications, AppProjects and Argo CD configuration.
- Secure recovery of repository credentials and SSO integration.
- Compatible Argo CD/Kubernetes/CRD versions.
- HA server, controller, repo-server and cache topology.
- GitLab and registry availability dependencies.
- Reconciliation backlog and API throttling.
- Disaster recovery without unintentional pruning.
- Rollback limits for CRD upgrades and data migrations.

An Argo CD outage can delay reconciliation while existing application Pods continue serving. Avoid emergency changes that turn a control-plane outage into an application outage.

## 19. SRE incident runbook

**Incident:** Production Application is Synced but Degraded after a GitOps promotion.

\`\`\`text
1. Confirm cluster/context, Application, namespace and owner.
2. Stop subsequent promotions.
3. Capture GitOps commit, chart version and image digest.
4. Inspect Argo CD sync/health, resource tree and events.
5. Inspect Kubernetes Deployment, Pods, Service endpoints and logs.
6. Compare HTTP error rate/latency to pre-release baseline.
7. Determine whether the release caused the regression.
8. Revert the reviewed GitOps change when appropriate.
9. Reconcile; validate readiness and SLO recovery.
10. Record impact, root cause, detection/recovery times and action items.
\`\`\`

Protect secret contents and sensitive logs when collecting evidence.

## 20. Scored assessment

| Category | Points |
| --- | ---: |
| Argo CD architecture and component inventory | 10 |
| Secure installation and compatibility review | 10 |
| SSO/RBAC, AppProject and GitLab access | 15 |
| Helm chart/values and immutable artifact verification | 10 |
| Four-namespace Application design | 10 |
| Manual sync, diff and runtime verification | 10 |
| Drift, prune and self-heal risk management | 10 |
| Failure injection and GitOps rollback | 15 |
| Observability, backup and incident runbook | 5 |
| Evidence and sign-off | 5 |
| **Total** | **100** |

**Critical controls:** Correct cluster context; no plaintext secrets; no unapproved privileged changes; no unauthorized pruning; verified immutable image; single deployment owner; tested GitOps recovery path; required production approval.

**Decision:** 85+ with all critical controls passing = PASS. Any failed critical control = NOT READY. Missing required live tests = INCOMPLETE until tested or formally waived.

## 21. Evidence worksheet

Create \`docs/EVIDENCE.md\`:

\`\`\`markdown
# Chapter 040 — Argo CD Capstone Evidence

Date:
Reviewer:
Change ID:
Cluster/context:
Argo CD version:
Control-plane namespace:
Component readiness:
CRD/RBAC review:
SSO group mapping:
Denied-action test:
GitLab repository:
Repository authentication method (no secrets):
AppProject:
Dev/Test/Staging/Prod Application names:
Destination namespaces:
Helm chart version:
Chart digest:
Verified image digest:
Offline render results:
GitOps source commit:
Diff review:
Manual sync result:
Sync/health status:
Runtime Pod/Service verification:
SLO baseline and post-change:
Drift exercise:
Failure tests (at least four):
Rollback Git commit:
Recovery duration:
Backup/HA owner:
Open risks:
Score / 100:
Critical controls PASS/FAIL:
Final decision:
\`\`\`

## 22. Acceptance checklist

- [ ] Correct cluster and namespace inventory verified.
- [ ] Argo CD installation version, integrity and topology reviewed.
- [ ] CRDs, Kubernetes RBAC and Argo CD RBAC audited.
- [ ] SSO and least-privilege access tested.
- [ ] GitLab repo connectivity and TLS trust verified.
- [ ] AppProject source/destination boundaries reviewed.
- [ ] All four Application definitions match one-cluster design.
- [ ] Helm chart renders for all environment overlays.
- [ ] Image digest verified and promotion chain documented.
- [ ] Manual sync and application runtime checks completed.
- [ ] Sync/health differences explained and recorded.
- [ ] Drift test safely performed or explicitly marked untested.
- [ ] At least four fault scenarios validated or simulated with evidence.
- [ ] GitOps revert and SLO recovery validated.
- [ ] Prune/self-heal safeguards documented.
- [ ] Monitoring, backup and incident runbook completed.
- [ ] Acceptance score and reviewer sign-off recorded.

## 23. Cleanup

For disposable lab Applications only, use an approved GitOps change and controlled deletion process. **Do not delete shared namespaces, Argo CD CRDs, the control plane or production Applications.** Understand Application finalizers and cascade deletion behavior before removing any Application. Preserve evidence and change records.

## 24. Knowledge assessment

1. What are the distinct responsibilities of the API server, repo-server and application controller?
2. Why are AppProject permissions insufficient without Kubernetes RBAC review?
3. Why does Argo CD not normally create a Helm CLI release?
4. How can an Application be Synced and Degraded simultaneously?
5. What is the operational difference between Git change and live drift?
6. Why is self-heal risky for emergency live changes?
7. What are the consequences of enabling automated prune?
8. Why must GitLab repository credentials be read-only and scoped?
9. Why is Git revert preferred for application rollback?
10. Which SLO signals must pass before production promotion?
11. How can an Argo CD outage affect reconciliation without stopping existing Pods?
12. What evidence proves a safe production release?

## 25. Part 08 completion

Part 08 is now complete:

- **036:** Argo CD Architecture, GitOps Reconciliation and Core Components.
- **037:** Argo CD Installation, Namespaces, RBAC and Initial Configuration.
- **038:** Argo CD CLI, UI, Authentication and Repository Connectivity.
- **039:** Argo CD Application Creation, Synchronization, Health and Drift Detection.
- **040:** Argo CD Installation, Application Operations and Recovery Capstone.

**Next: Chapter 041 — Argo CD Application Architecture, Sources, Destinations and Multi-Environment Design**, beginning Part 09 — Argo CD Applications and ApplicationSets.
