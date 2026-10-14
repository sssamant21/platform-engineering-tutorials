# Chapter 045 — Argo CD Applications and ApplicationSets Production Operations Capstone

**Part 09 — Argo CD Applications and ApplicationSets: Final Capstone**  
**Chapter 045 of 100** | **Audience:** SRE, infrastructure, platform engineering and security operations  
**Prerequisites:** Chapters 036–044, GitLab CI/CD fundamentals and enterprise Helm chart engineering  
**Reference topology:** ONE Kubernetes cluster, four namespaces (\`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`), Argo CD control plane in \`argocd\`.

> **Safety boundary:** All changes and fault injection require an approved disposable environment and change record. Production is represented by a lab namespace, not permission to operate a real production workload. Keep Application sync manual, automated pruning and self-heal disabled. Never delete ApplicationSets, Applications, namespaces, CRDs, PVCs or shared controllers as a cleanup shortcut. Do not expose credentials in Git or logs.

## 1. Mission and operational scenario

Your platform team must certify a GitLab-driven Argo CD deployment model that can generate, govern, deploy and recover a sample service across four environments **inside one cluster**. The service is packaged as a versioned Helm chart; configuration is stored in a separately governed GitLab values repository. An ApplicationSet creates the four Applications, while individual environment promotion requires an approved change and explicit sync.

You must prove:

- The chart, values Git revision and image digest are reproducible.
- The ApplicationSet generates exactly four expected Applications.
- AppProject and Kubernetes RBAC prevent unauthorized sources and destinations.
- Only the approved environment is synchronized at each promotion gate.
- Runtime readiness and application SLOs are validated independently of Argo CD sync.
- Git and Helm source errors are detected and recovered without destructive workarounds.
- Unexpected generated Applications, shared resources and deletion risks are contained.
- A GitOps revert restores last-known-good desired state and user-facing service.

**Exit standard:** Score at least 85/100, pass all critical controls, attach evidence, and obtain reviewer sign-off. Mark unperformed live tests **NOT TESTED** rather than claiming completion.

## 2. Integrated architecture

\`\`\`text
   GitLab application repository
      build/test/scan/sign once
                |
      image@sha256:<digest>
                |
        Approved Helm chart
     chart repo / OCI registry
                |
                v
         Argo CD repo-server <------ GitLab values repo
                |                    env/{dev,test,staging,prod}
                |                    protected branch + MR
                |
      ApplicationSet controller <--- approved inventory
          | generates 4 Applications
          v
       Application controller
          | render / compare / manual sync
          v
          Kubernetes API
                |
        ONE Kubernetes cluster
   +------------+------------+-------------+-----------+
   | demo-dev   | demo-test  | demo-staging| demo-prod |
   +------------+------------+-------------+-----------+
\`\`\`

Argo CD renders Helm templates and manages Kubernetes resources. It normally does **not** create a Helm CLI release for an Argo CD-managed Helm source; do not use \`helm rollback\` as the operational recovery path.

## 3. Required artifacts and lab time

Budget 3–5 hours plus any approved change windows. Produce:

\`\`\`text
demo-gitops-values/
├── environments/
│   ├── dev/demo-app-values.yaml
│   ├── test/demo-app-values.yaml
│   ├── staging/demo-app-values.yaml
│   └── prod/demo-app-values.yaml
├── argocd/
│   ├── projects/demo-platform.yaml
│   └── applicationsets/demo-multisource.yaml
├── tools/
│   └── validate-inventory.py
└── docs/
    ├── change-record.md
    ├── architecture-and-ownership.md
    ├── security-review.md
    ├── promotion-evidence.md
    ├── incident-runbook.md
    └── capstone-evidence.md
\`\`\`

Maintain the versioned Helm chart in its approved chart source. Avoid applying duplicate manually managed Applications while ApplicationSet owns those names.

## 4. Phase 1 — Read-only preflight

\`\`\`bash
kubectl config current-context
kubectl cluster-info
kubectl get namespaces
kubectl get crd applications.argoproj.io appprojects.argoproj.io applicationsets.argoproj.io
kubectl get deployments,statefulsets,pods -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl get applicationsets.argoproj.io -n argocd
kubectl get appprojects.argoproj.io -n argocd
argocd version --client
argocd repo list
\`\`\`

Record Argo CD version, controller readiness, cluster context, approved repo endpoints, chart version, Git commit, image digest, available namespaces, quota and baseline application SLOs. Do not display Secret data or token values.

**Stop conditions:** Unexpected cluster context, existing ownership collision, missing approvals, insecure repository credentials, unreviewed chart source or inability to identify a recovery owner.

## 5. Phase 2 — Validate GitLab inventory

The four approved environment records are:

| Environment | Destination | Values path | Application |
| --- | --- | --- | --- |
| Dev | \`demo-dev\` | \`environments/dev/demo-app-values.yaml\` | \`demo-app-dev\` |
| Test | \`demo-test\` | \`environments/test/demo-app-values.yaml\` | \`demo-app-test\` |
| Staging | \`demo-staging\` | \`environments/staging/demo-app-values.yaml\` | \`demo-app-staging\` |
| Production | \`demo-prod\` | \`environments/prod/demo-app-values.yaml\` | \`demo-app-prod\` |

A simple policy validator can reject unexpected environments:

\`\`\`python
from pathlib import Path
root = Path(__file__).resolve().parents[1]
expected = {
    "dev": "demo-dev",
    "test": "demo-test",
    "staging": "demo-staging",
    "prod": "demo-prod",
}
actual = {
    path.parent.name
    for path in (root / "environments").glob("*/demo-app-values.yaml")
}
assert actual == set(expected), f"Unexpected environments: {actual}"
for name in expected:
    assert (root / "environments" / name / "demo-app-values.yaml").is_file()
print("PASS: four approved values overlays")
\`\`\`

Run:

\`\`\`bash
python tools/validate-inventory.py
\`\`\`

Windows PowerShell:

\`\`\`powershell
py .\tools\validate-inventory.py
\`\`\`

This validates directory inventory only; additionally validate Helm schema, namespace mapping and digest policy in CI.

## 6. Phase 3 — AppProject security policy

\`argocd/projects/demo-platform.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: demo-platform
  namespace: argocd
spec:
  sourceRepos:
    - https://charts.example.com
    - https://gitlab.example.com/platform/demo-gitops-values.git
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

AppProject policy is necessary but not sufficient. Validate the Argo CD controller ServiceAccount's Kubernetes RBAC and admission restrictions separately. Protect Project edits with platform security ownership.

## 7. Phase 4 — Multi-source ApplicationSet

\`argocd/applicationsets/demo-multisource.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-multisource
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
    - missingkey=error
  generators:
    - list:
        elements:
          - name: dev
            namespace: demo-dev
          - name: test
            namespace: demo-test
          - name: staging
            namespace: demo-staging
          - name: prod
            namespace: demo-prod
  template:
    metadata:
      name: 'demo-app-{{.name}}'
    spec:
      project: demo-platform
      sources:
        - repoURL: https://charts.example.com
          chart: demo-app
          targetRevision: 1.2.3
          helm:
            releaseName: demo-app
            valueFiles:
              - '$values/environments/{{.name}}/demo-app-values.yaml'
        - repoURL: https://gitlab.example.com/platform/demo-gitops-values.git
          targetRevision: main
          ref: values
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{.namespace}}'
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
  syncPolicy:
    applicationsSync: create-update
\`\`\`

The \`$values\` prefix resolves against the root of the Git source with \`ref: values\`. The chart version is pinned; record the resolved Git values commit at each release gate. The example uses manual Application sync.

**Important:** \`applicationsSync: create-update\` limits routine deletion by the ApplicationSet controller but does not universally protect Applications/workloads after ApplicationSet deletion, Kubernetes garbage collection or finalizer behavior.

## 8. Phase 5 — Helm chart and values validation

Using trusted local checkouts of the chart and values repositories:

\`\`\`bash
helm dependency build ./demo-app
helm lint ./demo-app
helm template demo-app ./demo-app --namespace demo-dev \
  -f ./demo-gitops-values/environments/dev/demo-app-values.yaml > rendered-dev.yaml
helm template demo-app ./demo-app --namespace demo-test \
  -f ./demo-gitops-values/environments/test/demo-app-values.yaml > rendered-test.yaml
helm template demo-app ./demo-app --namespace demo-staging \
  -f ./demo-gitops-values/environments/staging/demo-app-values.yaml > rendered-staging.yaml
helm template demo-app ./demo-app --namespace demo-prod \
  -f ./demo-gitops-values/environments/prod/demo-app-values.yaml > rendered-prod.yaml
\`\`\`

Adjust checkout paths to your actual workspace. Inspect:

- Verified \`image@sha256\` digest, not a mutable image tag.
- Namespace, Deployment/Service names and selectors.
- Probes, resource requests/limits and Pod security settings.
- Chart dependencies and version provenance.
- No plaintext Secrets or unexpected cluster-scoped resources.
- No duplicate resource identity across generated Applications.

Offline Helm rendering does not validate live cluster admission or runtime health.

## 9. Phase 6 — Dry-run and ownership review

\`\`\`bash
kubectl apply --dry-run=client -f argocd/projects/demo-platform.yaml
kubectl apply --dry-run=client -f argocd/applicationsets/demo-multisource.yaml
kubectl get applications.argoproj.io -n argocd
kubectl get applicationsets.argoproj.io -n argocd
\`\`\`

If authorized and CRDs are installed:

\`\`\`bash
kubectl apply --dry-run=server -f argocd/applicationsets/demo-multisource.yaml
\`\`\`

**Dry-run does not evaluate generators.** Before applying, confirm no explicit Application already owns the four target Application names and no other Application manages the same Kubernetes resources.

## 10. Phase 7 — Generate four Applications

On an approved disposable cluster only:

\`\`\`bash
kubectl apply -f argocd/projects/demo-platform.yaml
kubectl apply -f argocd/applicationsets/demo-multisource.yaml
kubectl get applicationset demo-multisource -n argocd
kubectl describe applicationset demo-multisource -n argocd
kubectl get applications.argoproj.io -n argocd
\`\`\`

Expected: exactly four generated Applications with approved destinations. Inspect each \`spec.sources\`, AppProject, sync policy and owner references. If count or destinations differ, stop before synchronization.

## 11. Phase 8 — Manual Dev deployment

\`\`\`bash
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

Review desired changes and any deletion candidates. After approval:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
kubectl get deployments,pods,services -n demo-dev
kubectl get endpointslices -n demo-dev
kubectl get events -n demo-dev --sort-by=.lastTimestamp
\`\`\`

Verify the actual HTTP health endpoint and application SLOs. \`Synced\` and \`Healthy\` are distinct states. A successful sync does not prove acceptable error rate or latency.

## 12. Phase 9 — Promotion gates

GitLab CI builds, scans, signs and verifies the image **once**. Promote its same immutable digest through the four environments:

| Gate | Required evidence | Approver |
| --- | --- | --- |
| Dev | Helm render, manual sync, readiness and SLIs | Dev/platform owner |
| Test | Functional/regression checks and unchanged digest | Test owner |
| Staging | Load/security/reliability evidence | Release owner |
| Production | Change approval, SLO baseline and rollback plan | Authorized production owner |

For each environment, update the protected values repository through a reviewed GitLab MR, capture its resolved commit, inspect Argo CD diff, synchronize after approval, and validate Pods/Service endpoints plus HTTP error rate and latency.

Do not bypass an environment merely because the ApplicationSet already created its Application object.

## 13. Phase 10 — Failure injection matrix

Use disposable Dev only; production-related tests must be tabletop unless separately approved.

| Drill | Injected condition | Expected signal | Safe recovery |
| --- | --- | --- | --- |
| A | Wrong \`$values\` ref | Manifest generation error | Restore matching \`ref\` |
| B | Missing values path | Repo-server/Helm render error | Revert path |
| C | Unapproved chart repo | AppProject source denial | Restore approved source |
| D | Invalid chart version | Chart fetch/render failure | Restore pinned version |
| E | Unauthorized destination | AppProject destination denial | Restore approved namespace |
| F | Invalid image digest | ImagePullBackOff / Degraded | Git revert digest |
| G | Broken readiness probe | Synced but Degraded | Git revert probe |
| H | Unexpected generator element | Fifth Application generated | Reject/revert generator change |
| I | Duplicate resource identity | Shared-resource or repeated-resource warning | Remove collision |
| J | Controller outage (tabletop) | Delayed reconciliation | Restore control plane, verify backlog |

For each drill record the fault, expected and actual status, logs/events, recovery, elapsed time and residual risk. Do not disable RBAC, TLS or admission to force success.

## 14. Phase 11 — Controlled GitOps recovery

**Scenario:** A reviewed Dev values change deploys an unavailable image digest.

1. Stop promotion and identify the affected Application.
2. Capture Application source revisions, chart version, image digest and change record.
3. Inspect Argo CD sync/health and Kubernetes Pod events.
4. Confirm the image digest cannot be pulled; distinguish registry outage from wrong digest.
5. Open a GitLab revert MR to restore the last-known-good values.
6. Obtain required approval, merge and let Argo CD compare new desired state.
7. Manually sync Dev; wait for sync and health.
8. Verify Deployment image digest, ready replicas, Service endpoints and HTTP SLIs.
9. Record detection time, recovery time, root cause and preventive checks.

Do not use \`helm rollback\` or untracked \`kubectl rollout undo\` as the standard recovery path for Argo CD-owned resources.

## 15. Phase 12 — Unexpected Application generation

**Scenario:** An ApplicationSet inventory change creates a fifth Application.

1. Identify the ApplicationSet and resolved Git commit.
2. Compare expected and actual generated Application names/destinations.
3. Confirm auto-sync remains disabled.
4. Verify AppProject and Kubernetes RBAC prevent unauthorized deployment.
5. Stop promotion; revert the generator/inventory change via approved GitLab MR.
6. Inspect owner references, deletion policy and finalizers **before** deleting anything.
7. Verify the intended four Applications remain and no unauthorized resources were created.
8. Add CI allowlist checks and an alert on generated Application count.

Never delete the entire ApplicationSet as a quick fix. Generator and Application deletion behavior can be destructive.

## 16. Troubleshooting decision tree

\`\`\`text
Unexpected generated Application count?
  -> ApplicationSet generator, template, Git inventory, ownership
Application source comparison failed?
  -> Chart URL/version, Git ref, $values path, credentials, TLS
Application destination denied?
  -> AppProject and Kubernetes RBAC
Application OutOfSync but Healthy?
  -> Pending manual sync, live drift, ignored differences
Application Synced but Degraded?
  -> Image, probes, Pods, Service endpoints, runtime dependencies
Application Healthy but user impact?
  -> HTTP errors, latency, traffic path, dependencies, SLO
Unexpected delete/prune candidate?
  -> STOP: source changes, finalizers, ownership, PVC retention
\`\`\`

Avoid force sync, disabling security controls or unapproved production patches.

## 17. Operational observability

| Metric or event | Why it matters |
| --- | --- |
| ApplicationSet controller availability | Generated Application lifecycle |
| Expected vs actual generated Application count | Inventory integrity |
| GitLab source fetch errors | Repository access failures |
| Helm chart fetch/render duration | Repo-server bottlenecks |
| Application comparison errors | Desired-state resolution failures |
| Application OutOfSync duration | Pending sync or drift |
| Application Degraded duration | Runtime reliability |
| AppProject denials | Policy enforcement |
| Unexpected resource deletion | Destructive change detection |
| Kubernetes Pod/endpoint health | Workload availability |
| HTTP error rate/p95/p99 | User-facing SLO |
| GitLab MR and Argo CD audit events | Change accountability |

Set thresholds from measured baselines. Pending manual sync is not automatically an incident.

## 18. Reliability, HA and capacity review

Check Argo CD controller and repo-server CPU/memory, reconciliation queues, GitLab API load, registry availability, network egress, DNS/TLS trust and Kubernetes API throttling. Validate backup/recovery of Applications, AppProjects, ApplicationSets and controller configuration. Secrets must be recoverable through the approved external secret store.

An Argo CD control-plane outage can stop reconciliation while existing Pods continue serving. Avoid emergency changes that create an application outage.

## 19. Security review

**Critical controls:**

- Protected GitLab branches and CODEOWNERS for ApplicationSet/Project files.
- Read-only, scoped GitLab/Helm repository credentials.
- Trusted TLS/SSH endpoints and restricted egress.
- Approved chart versions and immutable image digests.
- AppProject source and destination allowlists.
- Kubernetes RBAC/admission enforced independently.
- Manual production sync and reviewed change approvals.
- No unauthorized ApplicationSet generators or cluster registrations.
- No shared-resource ownership collisions.
- No automated pruning/self-heal without risk approval.
- No plaintext secrets in Git, Helm values or evidence.

Failure of any critical control means **NOT READY**, regardless of numeric score.

## 20. EKS, AKS and GKE alignment

The ApplicationSet and multi-source design is cloud-independent. Run this same one-cluster/four-namespace lab on EKS, AKS or GKE. Cloud-specific implementation differs for workload identity, private network access, registries, DNS, secrets and admission.

| Concern | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Identity | Pod Identity / IRSA | Entra Workload ID | Workload Identity Federation |
| Registry | ECR | ACR | Artifact Registry |
| Secrets | AWS Secrets Manager | Azure Key Vault | Secret Manager |
| Cluster connectivity | VPC/IAM/Kubernetes RBAC | VNet/Entra/Kubernetes RBAC | VPC/IAM/Kubernetes RBAC |

Do not interpret Dev/Test/Staging/Prod as separate clusters. Fleet deployment and cross-cluster governance are covered later.

## 21. Scored SRE assessment

| Category | Points |
| --- | ---: |
| Architecture and ownership boundaries | 10 |
| GitLab source, chart version and image integrity | 10 |
| AppProject, RBAC and repository security | 15 |
| ApplicationSet generator correctness | 15 |
| Multi-source Helm values and rendering | 10 |
| Four-environment promotion governance | 10 |
| Sync, health, runtime and SLO validation | 10 |
| Failure injection and GitOps recovery | 10 |
| Observability, HA and runbook | 5 |
| Evidence and reviewer sign-off | 5 |
| **Total** | **100** |

**PASS:** 85 or more points, all critical controls pass, required live tests performed, and reviewer sign-off recorded.  
**NOT READY:** Any critical control fails.  
**INCOMPLETE:** Required live tests or evidence missing; do not infer success from example manifests.

## 22. Evidence worksheet

Create \`docs/capstone-evidence.md\`:

\`\`\`markdown
# Chapter 045 — Application Operations Capstone Evidence

Date:
Operator:
Reviewer:
Change ID:
Cluster/context:
Argo CD version:
AppProject:
ApplicationSet:
Generator type:
Expected Application count:
Actual Application count:
Generated Application names:
Destination namespaces:
Helm chart source and version:
Chart package digest/provenance:
GitLab values source and resolved commit:
Verified image digest:
Repo credentials/TLS review:
AppProject/Kubernetes RBAC review:
Offline Helm render:
Source collision check:
Dev diff review:
Dev sync status:
Dev health status:
Deployment/Service endpoints:
Application HTTP SLO:
Test/Staging/Prod promotion gates:
Failure tests completed:
GitOps revert commit:
Recovery duration:
ApplicationSet deletion/finalizer review:
Monitoring and backup owners:
Open risks:
Score / 100:
Critical controls PASS/FAIL:
Decision: PASS / NOT READY / INCOMPLETE
\`\`\`

## 23. Acceptance checklist

- [ ] Correct cluster context and four-namespace topology verified.
- [ ] Argo CD and ApplicationSet controllers healthy.
- [ ] Approved Helm chart and GitLab values sources accessible.
- [ ] Chart version, Git commit and image digest captured.
- [ ] AppProject and Kubernetes RBAC reviewed.
- [ ] Exactly four Applications generated without ownership collisions.
- [ ] ApplicationSet deletion/finalizer risks documented.
- [ ] Four Helm values overlays render and validate.
- [ ] Dev sync/health/runtime SLOs tested.
- [ ] Promotion gates require independent approvals.
- [ ] No automated prune/self-heal without explicit approval.
- [ ] At least four failure drills performed or explicitly marked not tested.
- [ ] GitOps revert restores last-known-good runtime state.
- [ ] Monitoring, HA, backup and recovery owners assigned.
- [ ] Reviewer records score and final decision.

## 24. Cleanup and handoff

Preserve evidence, GitLab MRs, audit logs and runbooks. For disposable resources, use an approved cleanup plan that checks ApplicationSet ownership, Application finalizers, cascade behavior, PVC retention and shared-resource dependencies. **Never delete the Argo CD namespace, CRDs or production resources as routine lab cleanup.**

Handoff to the on-call team must include repository owners, chart/version locking policy, generator inventory validation, AppProject boundaries, alerts, escalation contacts and tested GitOps recovery steps.

## 25. Knowledge assessment

1. What is the distinction between ApplicationSet generation and Application reconciliation?
2. Why is one cluster with four namespaces not equivalent to four independent clusters?
3. How does \`$values\` resolve across sources?
4. Why must chart version and values Git commit be recorded together?
5. What security risks arise from a Git file or Cluster generator?
6. Why must AppProject controls be backed by Kubernetes RBAC?
7. Why can an Application be Synced and Degraded?
8. What happens when multiple sources render the same resource?
9. Why does \`applicationsSync: create-update\` not guarantee deletion safety?
10. How do you stop an unauthorized fifth Application from reaching production?
11. Why should Argo CD-owned Helm applications recover through Git revert?
12. What evidence proves a production promotion meets its SLO?

## 26. Part 09 completion

Part 09 — Argo CD Applications and ApplicationSets:

- **041:** Application Architecture, Sources, Destinations and Multi-Environment Design.
- **042:** ApplicationSets, Generators, Templates and Automated Application Provisioning.
- **043:** ApplicationSet Git and Cluster Generators for Multi-Environment Operations.
- **044:** Multi-Source Applications, Helm Values Repositories and ApplicationSet Governance.
- **045:** Applications and ApplicationSets Production Operations Capstone.

**Next: Chapter 046 — Argo CD Enterprise RBAC, SSO, AppProject Security and Multi-Tenancy**, beginning Part 10 — Argo CD Security, Multi-Tenancy and High Availability.
