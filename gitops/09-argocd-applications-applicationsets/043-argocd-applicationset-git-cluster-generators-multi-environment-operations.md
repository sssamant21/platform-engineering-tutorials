# Chapter 043 — Argo CD ApplicationSet Git and Cluster Generators for Multi-Environment Operations

**Part 09 — Argo CD Applications and ApplicationSets** | **Chapter 043 of 100**  
**Audience:** SRE, infrastructure and platform operations engineers  
**Prerequisites:** Chapters 036–042; approved Argo CD control plane, GitLab repository and Helm chart  
**Lab topology:** ONE Kubernetes cluster, four namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`; Argo CD in \`argocd\`.

> **Operational safety:** Git and Cluster generators can change the Application inventory when files, directories, registered clusters or labels change. Keep this chapter's deployments in an authorized disposable environment. Use manual Application sync, disable prune and self-heal, protect generator configuration with GitLab approvals, and test deletion/ownership behavior before any production rollout. Never use real credentials in Git or examples.

## 1. Objectives

At completion you can:

1. Explain Git directory and Git file generator discovery.
2. Define schema-validated environment inventory in GitLab.
3. Use Go templates and fail on missing parameters.
4. Compare Git and Cluster generator trust boundaries.
5. Safely filter registered clusters using labels.
6. Design deterministic Application naming and destination policies.
7. Detect unintended Application multiplication, deletion and resource collisions.
8. Troubleshoot generator refresh, repository, RBAC and manifest generation.
9. Implement approval gates, audit evidence and recovery runbooks.
10. Demonstrate a secure four-environment GitOps lab.

## 2. Architecture

\`\`\`text
                 GitLab GitOps repository
                protected branch + MR review
                           |
          +----------------+----------------+
          |                                 |
   environments/*.json              apps/* directories
       Git file generator            Git directory generator
          |                                 |
          +-------------+-------------------+
                        |
                ApplicationSet controller
                generator -> template
                        |
           Application objects in argocd
             dev / test / staging / prod
                        |
               Application controller
                        |
                  Kubernetes API
                        |
                ONE cluster only
       demo-dev demo-test demo-staging demo-prod

  Separate future fleet use case:
  Argo CD registered cluster Secrets -> Cluster generator
  -> filtered cluster inventory -> generated Applications
\`\`\`

**Separation of responsibility:** The ApplicationSet controller generates Applications; the Application controller reconciles each Application's Kubernetes resources. A GitLab CI pipeline should update approved desired-state files, not require broad production Kubernetes credentials.

## 3. Generator comparison

| Generator | Input | Typical use | Key risk |
| --- | --- | --- | --- |
| Git directory | Directory matches in Git | One Application per app folder | New directory creates unexpected App |
| Git file | Structured JSON/YAML files in Git | Environment/application inventory | Untrusted metadata controls targets |
| Cluster | Argo CD registered cluster Secrets | Multi-cluster fleet | Label or registration changes affect targets |
| List | Explicit inline elements | Fixed four-namespace lab | Manual duplication |
| Matrix | Cartesian product | App × environment | Unexpected scale-up |
| Merge | Keyed parameter overlays | Cluster-specific configuration | Incorrect precedence |

For the one-cluster/four-namespace tutorial, prefer the **Git file generator** when you want inventory changes reviewed in GitLab. The Cluster generator is introduced as a separate, read-only fleet exercise, not as a claim that four namespaces are four clusters.

## 4. Repository layout

\`\`\`text
demo-gitops/
├── environments/
│   ├── dev.json
│   ├── test.json
│   ├── staging.json
│   └── prod.json
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
├── argocd/
│   ├── projects/demo-platform.yaml
│   └── applicationsets/demo-git-environments.yaml
├── tools/
│   └── validate-environments.py
└── docs/
    ├── change-policy.md
    ├── incident-runbook.md
    └── evidence.md
\`\`\`

Keep generator files and ApplicationSet definitions under protected CODEOWNERS review. Do not allow arbitrary unreviewed branches to drive production Applications.

## 5. Environment inventory files

Example \`environments/dev.json\`:

\`\`\`json
{
  "name": "dev",
  "namespace": "demo-dev",
  "valuesFile": "dev-values.yaml"
}
\`\`\`

Other files:

\`\`\`json
{"name":"test","namespace":"demo-test","valuesFile":"test-values.yaml"}
\`\`\`

\`\`\`json
{"name":"staging","namespace":"demo-staging","valuesFile":"staging-values.yaml"}
\`\`\`

\`\`\`json
{"name":"prod","namespace":"demo-prod","valuesFile":"prod-values.yaml"}
\`\`\`

Treat \`name\`, \`namespace\` and \`valuesFile\` as a restricted allowlist. Do not let arbitrary inventory files select \`kube-system\`, the Argo CD namespace, privileged Projects or unregistered cluster APIs.

## 6. Lab A — Validate environment inventory before merge

A simple dependency-free validator, \`tools/validate-environments.py\`:

\`\`\`python
import json
from pathlib import Path

expected = {
    "dev": ("demo-dev", "dev-values.yaml"),
    "test": ("demo-test", "test-values.yaml"),
    "staging": ("demo-staging", "staging-values.yaml"),
    "prod": ("demo-prod", "prod-values.yaml"),
}
root = Path(__file__).resolve().parents[1]
files = sorted((root / "environments").glob("*.json"))
assert len(files) == len(expected), "Unexpected environment inventory count"

seen = set()
for file in files:
    obj = json.loads(file.read_text(encoding="utf-8"))
    assert set(obj) == {"name", "namespace", "valuesFile"}, file
    name = obj["name"]
    assert name in expected and name not in seen, file
    assert (obj["namespace"], obj["valuesFile"]) == expected[name], file
    assert file.stem == name, file
    values = root / "charts" / "demo-app" / "env" / obj["valuesFile"]
    assert values.is_file(), f"Missing values file: {values}"
    seen.add(name)
assert seen == set(expected), "Missing expected environments"
print("PASS: four approved environments, namespaces and chart-local values")
\`\`\`

Run:

\`\`\`bash
python tools/validate-environments.py
\`\`\`

**Windows PowerShell:**

\`\`\`powershell
py .\tools\validate-environments.py
\`\`\`

Expected output: \`PASS: four approved environments, namespaces and chart-local values\`.

This validator intentionally **fails closed** for extra environment files. In a production platform, replace hardcoded allowlists with a reviewed policy-as-code schema and approved inventory source, not an unrestricted discovery glob.

## 7. Git file generator ApplicationSet

\`argocd/applicationsets/demo-git-environments.yaml\`:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-git-environments
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
    - missingkey=error
  generators:
    - git:
        repoURL: https://gitlab.example.com/platform/demo-gitops.git
        revision: main
        files:
          - path: environments/*.json
  template:
    metadata:
      name: 'demo-app-{{.name}}'
    spec:
      project: demo-platform
      source:
        repoURL: https://gitlab.example.com/platform/demo-gitops.git
        targetRevision: main
        path: charts/demo-app
        helm:
          releaseName: demo-app
          valueFiles:
            - 'env/{{.valuesFile}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{.namespace}}'
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
  syncPolicy:
    applicationsSync: create-update
\`\`\`

**Template detail:** \`goTemplate: true\` requires Go template expressions such as \`{{.name}}\`. Do not mix with fasttemplate syntax \`{{name}}\`. \`missingkey=error\` catches absent required fields.

**Deletion caution:** \`applicationsSync: create-update\` prevents the controller's routine deletion of generated Applications, but does not guarantee retention when the ApplicationSet itself is deleted or garbage collection/finalizers are involved. Review owner references and deletion semantics before changing generator inventory.

## 8. AppProject boundary

Use a platform-owned Project:

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

The Project enforces Argo CD source/destination policy, but Kubernetes RBAC and admission still govern actual API changes. Restrict who can modify the Project and the ApplicationSet template.

## 9. Lab B — Preflight and dry run

Read-only:

\`\`\`bash
kubectl config current-context
kubectl get crd applicationsets.argoproj.io
kubectl get pods,deployments -n argocd
kubectl get appprojects.argoproj.io -n argocd
kubectl get applications.argoproj.io -n argocd
kubectl get applicationsets.argoproj.io -n argocd
\`\`\`

Validate local manifests:

\`\`\`bash
python tools/validate-environments.py
kubectl apply --dry-run=client -f argocd/applicationsets/demo-git-environments.yaml
helm dependency build charts/demo-app
helm lint charts/demo-app
\`\`\`

Where server-side dry-run is authorized:

\`\`\`bash
kubectl apply --dry-run=server -f argocd/applicationsets/demo-git-environments.yaml
\`\`\`

Dry-run does **not** execute the generator or prove GitLab connectivity. Inspect actual generated Applications only after an authorized lab apply.

## 10. Lab C — Apply in a disposable cluster

**Precondition:** The \`demo-platform\` AppProject exists and no other ApplicationSet or manually maintained Application already owns \`demo-app-dev\`, \`demo-app-test\`, \`demo-app-staging\`, or \`demo-app-prod\`.

After approval:

\`\`\`bash
kubectl apply -f argocd/applicationsets/demo-git-environments.yaml
kubectl get applicationset demo-git-environments -n argocd
kubectl describe applicationset demo-git-environments -n argocd
kubectl get applications.argoproj.io -n argocd
\`\`\`

Expected generated Application names: exactly four, all targeting the same cluster and the approved namespaces. Generated Applications should have manual sync (no \`automated\` stanza). Review \`ownerReferences\` and ApplicationSet controller logs if names or counts are wrong.

## 11. Lab D — Manual Dev deployment

\`\`\`bash
argocd app get demo-app-dev
argocd app diff demo-app-dev
\`\`\`

Only after reviewing the desired/live diff:

\`\`\`bash
argocd app sync demo-app-dev
argocd app wait demo-app-dev --sync --health --timeout 300
kubectl get deployments,pods,services -n demo-dev
kubectl get endpointslices -n demo-dev
\`\`\`

Do not sync Test, Staging or Production without their own approvals. Record Git commit, chart version, verified immutable image digest, sync status, health status and HTTP SLIs.

## 12. Git directory generator

The directory generator discovers paths such as \`apps/*\`:

\`\`\`yaml
generators:
  - git:
      repoURL: https://gitlab.example.com/platform/demo-gitops.git
      revision: main
      directories:
        - path: apps/*
\`\`\`

Directory metadata can be used in ApplicationSet templates; verify the installed Argo CD release's parameter names and Go template structure.

**Operational risk:** A new directory may generate a new Application. Require GitLab CODEOWNERS approval for the \`apps/\` tree, validate names and destination allowlists, and alert on unexpected Application count changes.

## 13. Git file generator versus directory generator

| Criterion | Git files | Git directories |
| --- | --- | --- |
| Environment metadata | Explicit JSON/YAML fields | Derived from paths |
| Validation | Schema and allowlist | Path/name rules |
| Change review | File diff with typed fields | Directory changes |
| Best use | Approved environments and policies | Homogeneous application discovery |
| Main risk | Arbitrary parameter values | Accidental new Application |

Prefer files when destination namespace, environment or release governance must be explicit and reviewable.

## 14. Cluster generator: architecture and constraints

Cluster generators discover Argo CD-registered cluster credentials, generally from labeled cluster Secrets in the Argo CD namespace.

Illustrative selector:

\`\`\`yaml
generators:
  - clusters:
      selector:
        matchLabels:
          platform.example.com/gitops-enabled: "true"
\`\`\`

For registered clusters, templates can use generator-provided cluster parameters (such as cluster name and API server address), but exact parameters and labels depend on Argo CD version and registration mode. Verify the live generator output and cluster Secret inventory before deploying.

**Important:** The local in-cluster destination may not appear in label-selected results unless explicitly registered with a corresponding Secret. The four-namespace lab does **not** need a Cluster generator.

## 15. Read-only Cluster generator discovery lab

\`\`\`bash
argocd cluster list
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster
kubectl get applicationsets.argoproj.io -n argocd
\`\`\`

Do not print cluster Secret data. Record only approved cluster names, API endpoints, labels and registration status. Protect cluster registration, labels and Secrets because they can alter fleet deployment targets.

## 16. Future fleet example: filtered clusters

A conceptual multi-cluster ApplicationSet template can select approved cluster registrations and render one Application per cluster:

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-fleet-preview
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
    - missingkey=error
  generators:
    - clusters:
        selector:
          matchLabels:
            platform.example.com/gitops-enabled: "true"
  template:
    metadata:
      name: 'demo-fleet-{{.nameNormalized}}'
    spec:
      project: approved-fleet-project
      source:
        repoURL: https://gitlab.example.com/platform/demo-gitops.git
        targetRevision: main
        path: charts/demo-app
        helm:
          valueFiles:
            - env/dev-values.yaml
      destination:
        server: '{{.server}}'
        namespace: demo-dev
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
  syncPolicy:
    applicationsSync: create-update
\`\`\`

**Do not apply this example.** It requires separately approved cluster registrations, a fleet AppProject, destination namespaces and credential controls. Its purpose is to illustrate cluster parameter substitution, not to turn the one-cluster tutorial into a fleet deployment.

## 17. Matrix and Merge considerations

When combining Git metadata with cluster inventory:

- **Matrix** forms combinations. Three applications × four clusters = twelve generated Applications; confirm the intended cardinality.
- **Merge** overlays parameter sets by keys; document override precedence and reject duplicates.
- Use explicit environment/cluster allowlists.
- Reject empty or unexpected generator output.
- Prevent duplicate Application names.
- Review which generator parameters are trusted to influence destination and Project.

For production, require a dry-run inventory diff as part of the GitLab MR review process.

## 18. Refresh behavior and webhooks

Git generators discover changes through configured polling/reconciliation and may support webhook-triggered refresh. Do not assume instantaneous discovery. Measure:

- Time from GitLab merge to generator refresh.
- Time to Application object update.
- Time to Application comparison.
- Time to approved sync and health.
- ApplicationSet controller errors/backlog.

A Git webhook can improve responsiveness, but it does not replace source authorization or protected-branch governance.

## 19. Change control for generator inventory

Required GitLab MR checks:

1. Validate inventory JSON/YAML schema.
2. Compare expected Application names before/after.
3. Verify no new destination namespace or cluster.
4. Verify source repository and AppProject remain approved.
5. Validate chart-local values files.
6. Render Helm manifests offline.
7. Require platform CODEOWNERS approval for generator changes.
8. Require production approval for production inventory changes.
9. Record the exact merged commit and generated Application count.
10. Alert on unexpected generated Application changes.

Never treat a new generator file as a harmless documentation change; it can be an infrastructure deployment instruction.

## 20. Troubleshooting matrix

| Symptom | Likely cause | First check |
| --- | --- | --- |
| No Applications generated | Git fetch, pattern, controller error | ApplicationSet conditions and repo-server |
| Unexpected extra Application | Inventory wildcard or new file | Git diff and expected count |
| Template failure | Missing field or wrong Go syntax | \`missingkey=error\`, parameters |
| Duplicate Application names | Nonunique template output | Naming logic |
| Destination denied | AppProject restriction | Project and target namespace |
| Missing values file | Wrong chart-local path | Helm offline render |
| Cluster generator empty | Selector or local cluster registration | Cluster Secret labels |
| Applications generated but OutOfSync | Manual sync not performed | App diff and policy |
| Application Synced but Degraded | Runtime issue | Pods, probes, registry, endpoints |
| Unexpected deletion risk | Generator removal/owner references | ApplicationSet policy and finalizers |

Do not bypass TLS, grant cluster-admin or delete an ApplicationSet as a first response.

## 21. Failure injection lab (disposable only)

| Scenario | Injection | Expected result | Recovery |
| --- | --- | --- | --- |
| Missing key | Remove \`valuesFile\` from disposable JSON | Template/validation failure | Restore field |
| Invalid namespace | Set \`namespace\` to \`kube-system\` | CI allowlist failure; Project denies sync | Restore approved namespace |
| Extra environment | Add \`qa.json\` | CI rejects unexpected inventory | Remove unapproved file |
| Wrong chart path | Point to nonexistent values | Manifest generation error | Correct path |
| Invalid Git revision | Use nonexistent branch | Repository comparison error | Restore approved revision |
| Wrong cluster selector | Use unmatched label | No matching registered clusters | Fix approved selector |
| Duplicate names | Reuse environment \`name\` | Validator rejects duplicate | Correct unique name |

Prefer CI validation and tabletop simulation to destructive live tests. Do not remove production generator entries to test deletion.

## 22. Incident runbook — Unexpected Application inventory

**Scenario:** After a GitLab MR merges, the ApplicationSet produces an unauthorized fifth Application.

1. Confirm Argo CD context and affected ApplicationSet.
2. Capture Git commit, MR approver and generator inputs.
3. Compare actual versus approved Application count.
4. Check whether generated Applications are manual-sync and whether any unauthorized sync occurred.
5. Inspect AppProject restrictions and Kubernetes audit evidence.
6. Stop further generator changes; avoid deleting the ApplicationSet blindly.
7. Revert the offending GitLab commit through an approved MR.
8. Review Application owner references, finalizers and deletion behavior.
9. Confirm the expected four Applications remain and no unauthorized resources were deployed.
10. Add preventive schema/allowlist and alerting controls.

**Recovery warning:** \`applicationsSync: create-update\` is not a universal deletion-protection guarantee. Treat ApplicationSet deletion as a potentially destructive operation.

## 23. Observability and SRE alerts

Track:

| Signal | Reason |
| --- | --- |
| ApplicationSet controller availability | Generator control-plane health |
| Generator evaluation failures | Git/schema/template problems |
| Expected vs actual generated count | Unauthorized or missing Apps |
| Git merge-to-generation latency | Reconciliation timeliness |
| Cluster registration/label changes | Fleet target drift |
| AppProject denials | Security boundary enforcement |
| Application OutOfSync duration | Pending approval or drift |
| Application Degraded duration | Runtime reliability |
| Unexpected deletion events | Destructive change risk |
| HTTP error rate/p95/p99 | End-user impact |

Choose thresholds from measured baselines and approved maintenance windows.

## 24. EKS, AKS and GKE alignment

The Git file generator works identically when Argo CD is hosted on EKS, AKS or GKE. Cluster generator fleet operations additionally require secure cluster registration, private API access, cloud workload identity, RBAC and network policy.

| Area | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Workload identity | EKS Pod Identity/IRSA | Entra Workload ID | Workload Identity Federation |
| Registry | ECR | ACR | Artifact Registry |
| Secrets | AWS Secrets Manager | Azure Key Vault | Secret Manager |
| Connectivity | VPC DNS/egress | VNet DNS/egress | VPC DNS/egress |

Do not use static cloud-admin credentials in ApplicationSet cluster Secrets.

## 25. Acceptance checklist

- [ ] Git file and directory generator behavior understood.
- [ ] Environment inventory validated against explicit allowlist.
- [ ] Four Applications generated for one cluster/four namespaces.
- [ ] Go template missing-key errors enabled.
- [ ] AppProject source/destination restrictions verified.
- [ ] Generated Applications remain manual-sync.
- [ ] Chart-local values and immutable image digests validated.
- [ ] Cluster generator inspected read-only without registering new clusters.
- [ ] Generator cardinality and ownership reviewed.
- [ ] GitLab CODEOWNERS/MR policy documented.
- [ ] At least three failure scenarios tested or marked not tested.
- [ ] Incident recovery and monitoring evidence captured.

## 26. Evidence worksheet

\`\`\`text
CHAPTER 043 — GIT AND CLUSTER GENERATORS
Date:
Operator/reviewer:
Cluster/context:
Argo CD version:
ApplicationSet:
GitLab repository and commit:
Inventory files:
Validator output:
Expected Application count:
Actual Application count:
Generated names:
Destination namespaces:
AppProject:
Manual sync policy:
Chart and values validation:
Verified image digest:
Cluster generator discovery (read-only):
Cluster Secret labels (no secret data):
Controller errors/reconciliation time:
Failure tests:
Recovery Git commit:
Audit evidence:
Open risks:
Decision: PASS / NOT READY / NOT TESTED
\`\`\`

## 27. Knowledge checks

1. How do Git file and Git directory generators differ?
2. Why should environment inventory be schema validated?
3. Why must the template reject missing parameters?
4. Why does the one-cluster/four-namespace lab not need a Cluster generator?
5. What can cause a label-selected Cluster generator to return no clusters?
6. Why are ApplicationSet definitions and inventory files security-sensitive?
7. What happens when a Matrix generator multiplies parameter sets?
8. Why does ApplicationSet \`create-update\` not guarantee retention after deletion?
9. How do you diagnose a generated Application that is OutOfSync but Healthy?
10. What is the safest response to an unauthorized generated Application?

## 28. Completion

**Pass:** You can manage an approved four-environment inventory using a Git file generator, enforce template and destination policy, inspect registered clusters safely, and recover from unexpected generator changes with evidence.

**Next: Chapter 044 — Argo CD Multi-Source Applications, Helm Values Repositories and ApplicationSet Governance.**
