# Chapter 044 — Argo CD Multi-Source Applications, Helm Values Repositories and ApplicationSet Governance

**Part 09 — Argo CD Applications and ApplicationSets** | **Chapter 044 of 100**  
**Audience:** SRE, infrastructure, security and platform operations engineers  
**Prerequisites:** Chapters 036–043, Helm chart engineering and approved GitLab CI/CD practices  
**Reference topology:** ONE Kubernetes cluster with \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\` namespaces; Argo CD control plane in \`argocd\`.

> **Safety:** Multi-source Applications combine trust from more than one repository. Only use approved chart and values repositories, protected branches, read-only credentials and narrowly scoped AppProjects. Default to manual sync without automated prune or self-heal. Run writes and failure injection only in an authorized disposable environment.

## 1. Objectives

After completing this chapter, you can:

1. Explain the operational purpose of Argo CD \`spec.sources\`.
2. Separate an approved Helm chart source from environment values stored in GitLab.
3. Use \`$values\` references correctly and diagnose broken source paths.
4. Distinguish Git \`targetRevision\` from Helm chart version pinning.
5. Apply source repository allowlists, least-privilege credentials and provenance checks.
6. Generate multi-source Applications with a controlled ApplicationSet List generator.
7. Understand repeated-resource warnings and source precedence.
8. Prevent source drift, unexpected privilege changes and deletion risks.
9. Troubleshoot manifest generation, repo-server failures and source mismatches.
10. Execute a safe GitOps recovery and produce SRE acceptance evidence.

## 2. Why multi-source Applications?

A platform team may publish a versioned, signed Helm chart in an approved registry while application teams maintain environment-specific values in a protected GitLab repository. Argo CD can combine those sources at manifest generation time.

\`\`\`text
          Approved Helm chart source
           chart: demo-app / version 1.2.3
                       |
                       v
                 Argo CD repo-server
                       ^
                       |
        GitLab environment values repo
       environments/dev/demo-app-values.yaml
       environments/test/demo-app-values.yaml
       environments/staging/demo-app-values.yaml
       environments/prod/demo-app-values.yaml
                       |
            rendered Kubernetes manifests
                       |
              Application controller
                       |
              Kubernetes API
                       |
                 ONE cluster
         dev / test / staging / prod
\`\`\`

The chart and values sources are independent inputs. Their versions must be recorded together for reproducibility. The Application controller still manages the deployed Kubernetes resources; Helm CLI does not become a second deployment owner.

## 3. Source types and revision semantics

| Source | Typical \`repoURL\` | \`targetRevision\` | Additional field |
| --- | --- | --- | --- |
| Git-hosted chart | GitLab repository URL | Git branch, tag or commit | \`path\` |
| Helm chart repository | Helm repository URL | Exact chart version | \`chart\` |
| OCI Helm chart | OCI-supported registry repository | Chart version supported by registry/Argo CD | \`chart\` |
| Git values repository | GitLab repository URL | Git commit or reviewed branch | \`ref\` |
| Kustomize directory | GitLab repository URL | Git commit or reviewed branch | \`path\` |

For production, prefer immutable chart artifacts and capture the exact Git values commit. A mutable branch like \`main\` can be appropriate for reviewed GitOps reconciliation, but it is not an immutable release identifier.

## 4. Repository layout

Two independently governed repositories:

\`\`\`text
platform-helm-charts/
└── demo-app/
    ├── Chart.yaml
    ├── Chart.lock
    ├── values.yaml
    ├── values.schema.json
    └── templates/
\`\`\`

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
    ├── source-lock-record.md
    ├── change-policy.md
    └── recovery-runbook.md
\`\`\`

The chart may be published to an OCI or HTTPS Helm repository. The values repository should not contain plaintext secrets.

## 5. Single-source versus multi-source

A single-source Git-hosted chart uses chart-relative values:

\`\`\`yaml
source:
  repoURL: https://gitlab.example.com/platform/demo-gitops.git
  targetRevision: main
  path: charts/demo-app
  helm:
    valueFiles:
      - env/dev-values.yaml
\`\`\`

A multi-source Application can load a chart from a Helm repository and values from a separate Git repository:

\`\`\`yaml
sources:
  - repoURL: https://charts.example.com
    chart: demo-app
    targetRevision: 1.2.3
    helm:
      valueFiles:
        - $values/environments/dev/demo-app-values.yaml
  - repoURL: https://gitlab.example.com/platform/demo-gitops-values.git
    targetRevision: main
    ref: values
\`\`\`

The \`$values\` prefix refers to the source with \`ref: values\`. The remainder of the path is resolved relative to that Git repository's root. Do not specify \`chart\` on a values-only source.

## 6. Full Dev Application example

\`argocd/applications/demo-app-dev.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app-dev
  namespace: argocd
spec:
  project: demo-platform
  sources:
    - repoURL: https://charts.example.com
      chart: demo-app
      targetRevision: 1.2.3
      helm:
        releaseName: demo-app
        valueFiles:
          - $values/environments/dev/demo-app-values.yaml
    - repoURL: https://gitlab.example.com/platform/demo-gitops-values.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-dev
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
\`\`\`

This example assumes a real approved Helm chart repository, chart version and GitLab values repository exist. It does not enable automated sync, pruning or self-heal. Use \`sources\`, not \`source\`, for this multi-source design.

## 7. Values overlay and image digest

Example \`environments/dev/demo-app-values.yaml\`:

\`\`\`yaml
environment: dev
replicaCount: 1
image:
  repository: registry.example.com/platform/demo-app
  digest: sha256:REPLACE_WITH_VERIFIED_64_HEX_DIGEST
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    memory: 512Mi
\`\`\`

The digest is a placeholder, not a deployable value. Your Helm template must render the image as \`repository@digest\`. The chart's schema or CI policy should reject missing/invalid digests. GitLab CI builds, scans and signs once; the same verified digest is promoted through Dev, Test, Staging and Production with approvals.

## 8. AppProject restrictions for both sources

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
\`\`\`

AppProjects restrict allowed source repositories and destinations but do not replace Kubernetes RBAC or admission. Protect Project changes separately from application values changes.

## 9. Lab A — Preflight and repository inspection

Read-only:

\`\`\`bash
kubectl config current-context
kubectl get pods,deployments -n argocd
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
argocd version --client
argocd repo list
\`\`\`

Record:

- Argo CD server/CLI version and multi-source compatibility.
- Approved chart repository URL, chart name and exact version.
- Approved GitLab values repository URL and resolved commit.
- Chart signing/provenance and image digest verification.
- AppProject source allowlist.
- TLS certificate trust and scoped repository credentials.

Do not print Kubernetes Secret data or use inline password flags.

## 10. Lab B — Validate the Helm chart and values offline

In an authorized local checkout of the chart source and values repository:

\`\`\`bash
helm dependency build ./demo-app
helm lint ./demo-app
helm template demo-app ./demo-app \
  --namespace demo-dev \
  -f ../demo-gitops-values/environments/dev/demo-app-values.yaml \
  > rendered-dev.yaml
\`\`\`

Repeat for Test, Staging and Production values. Verify:

1. Helm chart version and dependencies match the approved release.
2. Every values file exists at the expected Git revision.
3. The chart schema accepts the values.
4. Image digest is immutable and verified.
5. Security context, resource requests/limits and probes render correctly.
6. Namespace and Service selectors are correct.
7. No unintended cluster-scoped resources or plaintext secrets appear.

This local test does not prove Argo CD repo-server connectivity or Kubernetes admission.

## 11. Lab C — Validate multi-source Application

With an authorized Argo CD installation:

\`\`\`bash
kubectl apply --dry-run=client -f argocd/applications/demo-app-dev.yaml
kubectl apply --dry-run=server -f argocd/applications/demo-app-dev.yaml
\`\`\`

Server dry-run requires CRDs and permissions. It validates schema/admission, **not** Git/Helm fetches or \`$values\` path resolution.

In a disposable environment, after approval:

\`\`\`bash
kubectl apply -f argocd/applications/demo-app-dev.yaml
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

Review the Application's resolved sources, desired manifests and resource tree. If comparison fails, investigate repo-server logs and source paths before syncing.

## 12. Lab D — Manual Dev sync

Only after an approved diff:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
kubectl get deployments,pods,services -n demo-dev
kubectl get endpointslices -n demo-dev
\`\`\`

Record the exact chart version, values Git commit, image digest, sync/health statuses and application HTTP SLIs. A \`Synced\` Application can still be \`Degraded\`; an \`OutOfSync\` Application can still be \`Healthy\`.

## 13. Four-environment source mapping

| Application | Destination | Values repository path | Promotion |
| --- | --- | --- | --- |
| \`demo-app-dev\` | \`demo-dev\` | \`environments/dev/demo-app-values.yaml\` | First |
| \`demo-app-test\` | \`demo-test\` | \`environments/test/demo-app-values.yaml\` | After Dev |
| \`demo-app-staging\` | \`demo-staging\` | \`environments/staging/demo-app-values.yaml\` | After Test |
| \`demo-app-prod\` | \`demo-prod\` | \`environments/prod/demo-app-values.yaml\` | After Staging |

All four Applications target **one cluster**. Promotion changes approved GitOps values to reference the same verified image digest; do not rebuild a different image for each environment.

## 14. ApplicationSet for multi-source Applications

For a fixed approved inventory, a List generator can create four multi-source Applications:

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

This ApplicationSet manages Application objects; the Application controller manages Kubernetes resources. Generated Applications remain manual-sync. \`applicationsSync: create-update\` restricts routine ApplicationSet deletion behavior but is **not a universal guarantee** of retention after deleting the ApplicationSet or interacting with finalizers/garbage collection.

**Do not apply** while manually managed Applications with the same names already exist. Plan adoption/ownership explicitly.

## 15. Lab E — Preview generated Application inventory

Read-only preflight:

\`\`\`bash
kubectl get applicationsets.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl apply --dry-run=client -f argocd/applicationsets/demo-multisource.yaml
\`\`\`

In an approved disposable cluster without conflicting Applications:

\`\`\`bash
kubectl apply -f argocd/applicationsets/demo-multisource.yaml
kubectl describe applicationset demo-multisource -n argocd
kubectl get applications.argoproj.io -n argocd
\`\`\`

Expected: exactly four generated Applications targeting \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`. Check \`ownerReferences\`, \`spec.sources\`, AppProject, sync policy and generated names.

## 16. Source precedence and repeated resources

Argo CD combines rendered manifests from multiple sources. If multiple sources produce the same resource identity (group, kind, name, namespace), the later source can take precedence and Argo CD may emit a repeated-resource warning.

**Operational risk:** Source ordering becomes behavior. A seemingly harmless values-repository change that adds Kubernetes manifests could override a chart resource.

Controls:

- Use the values repository as values-only where possible.
- Review each source's generated manifests.
- Treat repeated-resource warnings as release-blocking unless explicitly approved.
- Record source order and revision.
- Do not use multi-source Applications as a general-purpose Application grouping mechanism; use ApplicationSets for grouping many Applications.

## 17. Source revision locking and release evidence

A reproducible release record must include:

\`\`\`text
Application:
Destination namespace:
Helm repository URL:
Chart name/version:
Chart package digest/provenance:
GitLab values repository URL:
Resolved values Git commit:
Image repository@sha256 digest:
AppProject:
Approver and change ID:
Argo CD sync revision(s):
Runtime health/SLO evidence:
\`\`\`

Multi-source Applications can have more than one resolved source revision. Capture all of them; a single branch name or chart version is insufficient to reproduce the full desired state.

## 18. Secrets, credentials and trust

- Use read-only repository/registry credentials scoped to each source.
- Store credentials in approved external secret management.
- Verify GitLab HTTPS CA or SSH host keys.
- Restrict repo-server egress and DNS resolution to approved endpoints.
- Protect Helm repository access and chart provenance.
- Rotate credentials with tested recovery.
- Avoid broad repository credential templates that match unintended URLs.
- Audit who can edit Application \`sources\`, AppProjects and ApplicationSets.

Never use \`--insecure-skip-server-verification\` as a normal production workaround.

## 19. Common failure modes

| Symptom | Likely cause | Diagnostic action |
| --- | --- | --- |
| \`$values\` path not found | Wrong \`ref\` or path | Check ref name and Git root path |
| Chart fetch fails | Helm repo URL, auth or TLS | Repo-server logs, registry trust |
| Values repo fetch fails | GitLab auth/DNS/proxy | Repository connection and token scope |
| Helm render fails | Schema, values or dependencies | Offline lint/template |
| AppProject denies source | Chart or values repo not allowlisted | Review \`sourceRepos\` |
| Unexpected repeated resource | Two sources render same object | Compare source output and order |
| ApplicationSet creates extras | Generator/template mistake | Inventory count and Git diff |
| Sync succeeds but app Degraded | Probe, image, capacity or dependency | Pods/events/SLIs |
| Drift persists | Manual change or compare rule | Diff, resource tracking, HPA |
| Unexpected prune candidate | Desired state removed | Halt sync, inspect finalizers/PVC |

Do not grant cluster-admin, bypass TLS or force sync to conceal a comparison failure.

## 20. Failure injection lab (disposable only)

| Test | Injection | Expected signal | Recovery |
| --- | --- | --- | --- |
| 1 | Wrong \`$values\` ref | Manifest-generation error | Restore matching \`ref\` |
| 2 | Missing values file | Helm render error | Restore reviewed path |
| 3 | Wrong chart version | Chart unavailable/incompatible | Restore pinned approved version |
| 4 | Invalid Git revision | Values fetch failure | Restore valid commit/branch |
| 5 | Unauthorized chart source | AppProject source denial | Restore approved repository |
| 6 | Duplicate resource output | Repeated-resource warning | Remove collision |
| 7 | Missing generator parameter | Template failure | Restore validated inventory |
| 8 | Bad image digest | Image pull/health failure | Git revert to verified digest |

Do not inject faults into production or shared repositories. Record what was actually tested versus tabletop-simulated.

## 21. SRE incident runbook — Multi-source manifest generation failure

**Scenario:** A GitLab values repository ref was renamed; all four Applications report comparison errors.

1. Confirm affected Applications, chart version, values source URL and Git revision.
2. Stop promotion and prevent unreviewed synchronization.
3. Inspect Application \`spec.sources\`, ApplicationSet template and repo-server errors.
4. Verify GitLab branch/commit exists and credentials/TLS remain valid.
5. Confirm \`ref: values\` matches the \`$values\` prefix.
6. Validate values paths and Helm rendering offline.
7. Revert the offending GitOps change or restore the approved revision.
8. Reconcile ApplicationSet and Application comparisons.
9. Verify generated Application count, sync/health and runtime SLIs.
10. Record detection, blast radius, recovery duration and preventive checks.

Existing Kubernetes Pods may continue running while Argo CD cannot generate new manifests. Avoid emergency actions that destabilize healthy workloads.

## 22. Observability

Monitor:

| Signal | Operational value |
| --- | --- |
| Repo-server fetch/render failures by source | Identify chart versus values outages |
| Manifest-generation duration | Detect dependency latency |
| Application comparison errors | Reconciliation health |
| ApplicationSet expected/actual count | Inventory drift |
| Repeated-resource warnings | Ownership/source collision |
| AppProject source denial | Security enforcement |
| Sync failures | API/admission/hook issues |
| Application Degraded duration | Runtime availability |
| GitLab token/CA expiration | Preventable outages |
| HTTP error rate, p95/p99 latency | User-facing SLO |

Set alerts using actual baselines; an intentionally pending manual sync is not necessarily an incident.

## 23. EKS, AKS and GKE notes

The Argo CD multi-source model is cloud-independent. EKS, AKS and GKE differ in registry authentication, workload identity, private DNS/egress and admission policy. This lab remains one cluster with four namespaces; multi-cluster deployment is covered in later parts.

## 24. Acceptance checklist

- [ ] Argo CD release supports multi-source Applications.
- [ ] Chart and values repositories are approved and independently governed.
- [ ] AppProject allowlists both source URLs.
- [ ] Chart version and values Git commit captured.
- [ ] \`$values\` prefix and \`ref\` resolve correctly.
- [ ] Chart and four values overlays render offline.
- [ ] Immutable image digest verified.
- [ ] Dev Application manually synced in approved lab.
- [ ] Four generated Applications have unique names and destinations.
- [ ] ApplicationSet ownership and deletion behavior reviewed.
- [ ] Repeated-resource warnings investigated.
- [ ] GitLab MR/CODEOWNERS and secrets controls verified.
- [ ] At least three failure scenarios tested or marked not tested.
- [ ] GitOps revert and SLO recovery documented.

## 25. Evidence worksheet

\`\`\`text
CHAPTER 044 — MULTI-SOURCE APPLICATIONS
Date:
Operator/reviewer:
Cluster/context:
Argo CD version:
Application/AppProject:
Helm repository URL:
Chart name/version:
Chart package digest/provenance:
Values repository URL:
Resolved values Git commit:
$values ref and file path:
Image@sha256:
Manual sync policy:
ApplicationSet expected/actual count:
Source collision review:
Offline render:
Dev sync/health:
Deployment/Service endpoints:
HTTP SLO baseline/after:
Failure tests:
Recovery Git commit:
Open risks:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 26. Knowledge checks

1. Why use multi-source Applications instead of copying values into a chart repository?
2. How is \`targetRevision\` interpreted for a Helm chart versus a Git source?
3. What does \`$values\` reference and where is its path rooted?
4. Why should a values-only source have \`ref\` but no \`chart\`?
5. What happens if two sources render the same Kubernetes object?
6. Why must AppProjects allowlist both chart and values repositories?
7. Why are chart version and values Git commit both required for reproducibility?
8. Why should generated Applications remain manual-sync during initial rollout?
9. What does ApplicationSet \`create-update\` not protect against?
10. How does an SRE recover from a broken values repository revision?

## 27. Completion

**Pass:** You can securely combine approved Helm charts and GitLab values, generate four controlled Applications, troubleshoot multi-source failures, and recover through GitOps with SLO evidence.

**Next: Chapter 045 — Argo CD Applications and ApplicationSets Production Operations Capstone**, completing Part 09.
