# Chapter 033 — Helm Dependencies, OCI Registries, Chart Packaging and Supply-Chain Security

**Part 07 — Enterprise Helm Chart Engineering** | **Chapter 033 / 100**  
**Audience:** SRE, infrastructure and platform engineers  
**Prerequisites:** Chapters 021–025 (software supply chain) and 031–032 (Helm chart engineering)  
**Architecture:** One Kubernetes cluster; \`demo-dev\`, \`demo-test\`, \`demo-staging\` and \`demo-prod\` are separate namespaces. GitLab CI produces trusted artifacts; Argo CD reconciles reviewed GitOps changes.

> **Safety:** Use a disposable GitLab project and registry, synthetic chart data and an approved test namespace. Never publish credentials or private registry tokens. Packaging and local verification are safe offline; pushing, installing and cloud-network changes require authorization. Examples that reference \`registry.example.com\` are placeholders.

## 1. Objectives

After this chapter, you can:

1. Explain Helm chart dependencies, subcharts, library charts and version constraints.
2. Use \`Chart.lock\` and \`helm dependency build\` for reproducible dependency resolution.
3. Package a chart and inspect its archive.
4. Publish and retrieve a Helm chart using an OCI registry.
5. Distinguish chart package digest, application image digest, chart version and Git commit.
6. Validate chart content, schemas, rendered manifests and artifact integrity.
7. Describe chart signing, provenance and registry trust boundaries.
8. Design GitLab CI pipelines for trusted chart publication.
9. Integrate versioned charts with Argo CD without mixing deployment managers.
10. Troubleshoot dependency, registry, digest and supply-chain failures.

## 2. Enterprise artifact flow

\`\`\`text
GitLab application source
  -> tests / security scans / SBOM / signing
  -> container image@sha256:<verified-image-digest>
  -> immutable registry artifact

GitLab Helm chart source
  -> lint / schema / render / policy tests
  -> dependency build from Chart.lock
  -> package demo-app-<chart-version>.tgz
  -> verify provenance / signature / digest
  -> OCI chart registry

Reviewed GitOps repository
  -> chart version / trusted OCI source
  -> verified application image digest
  -> environment values (nonsecret)
  -> Argo CD Application per namespace
  -> Kubernetes reconciliation
\`\`\`

**Key separation:** Helm chart packages describe *how* to deploy; OCI application images contain *what* executes. They have different digests, signing policies and release lifecycles.

## 3. Helm dependency fundamentals

| Mechanism | Purpose | SRE risk |
| --- | --- | --- |
| \`dependencies\` in Chart.yaml | Declare subcharts | Unreviewed transitive functionality |
| Version constraint | Select acceptable chart versions | Unexpected updates if loosely bounded |
| \`Chart.lock\` | Record resolved dependency versions and digest | Stale lockfile |
| \`helm dependency update\` | Resolve versions and regenerate lock | May change dependency graph |
| \`helm dependency build\` | Reconstruct from lockfile | Fails if locked artifacts unavailable |
| \`charts/\` directory | Holds dependency archives or unpacked charts | Vendored artifacts and size |
| Library chart | Shared template functions, not workload objects | Template API coupling |
| \`condition\` / \`tags\` | Control subchart enablement | Surprise resource creation |

A dependency lock improves reproducibility but does not automatically establish that a dependency is trusted, free of vulnerabilities or available forever.

## 4. Dependency design choices

Use a dependency only when it materially simplifies chart ownership. Avoid embedding a database, message broker or privileged infrastructure component as an implicit application dependency without operational approval.

For this chapter, create a **local library chart** to practice dependency mechanics without reaching a public registry.

Directory:

\`\`\`text
charts/
├── demo-app/
│   ├── Chart.yaml
│   ├── Chart.lock
│   ├── values.yaml
│   ├── values.schema.json
│   └── templates/
└── platform-common/
    ├── Chart.yaml
    └── templates/
        └── _labels.tpl
\`\`\`

## 5. Lab A — Create a local library chart

\`charts/platform-common/Chart.yaml\`:

\`\`\`yaml
apiVersion: v2
name: platform-common
description: Generic shared chart helpers for platform training
type: library
version: 0.1.0
\`\`\`

\`charts/platform-common/templates/_labels.tpl\`:

\`\`\`gotemplate
{{- define "platform-common.standardLabels" -}}
app.kubernetes.io/part-of: platform-training
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
{{- end -}}
\`\`\`

Library charts contribute named templates but do not independently create Kubernetes resources. They can be versioned and reused across charts.

## 6. Declare and lock the dependency

In \`charts/demo-app/Chart.yaml\`, preserve existing metadata and add:

\`\`\`yaml
dependencies:
  - name: platform-common
    version: 0.1.0
    repository: file://../platform-common
\`\`\`

Run from the repository root:

\`\`\`bash
helm dependency update charts/demo-app
helm dependency list charts/demo-app
helm dependency build charts/demo-app
helm lint charts/demo-app
\`\`\`

Expected: \`charts/demo-app/Chart.lock\` is generated and a packaged dependency is available in \`charts/demo-app/charts/\`.

Commit \`Chart.yaml\` and \`Chart.lock\`. Establish a repository policy for whether vendored \`.tgz\` dependencies are committed or reconstructed in CI; either way, make the policy explicit and test offline build requirements.

**Local path caveat:** \`file://../platform-common\` is convenient for a monorepo but requires that sibling directory in CI. A standalone checkout of \`charts/demo-app\` cannot resolve it.

## 7. Consume a library helper safely

In \`charts/demo-app/templates/_helpers.tpl\`, define a helper:

\`\`\`gotemplate
{{- define "demo-app.platformLabels" -}}
{{- include "platform-common.standardLabels" . -}}
{{- end -}}
\`\`\`

For example, append its output under the Deployment's \`metadata.labels\` using \`nindent\`, but **do not** add mutable shared labels to the Deployment's immutable selector unless the entire chart consistently uses them.

Example fragment:

\`\`\`gotemplate
metadata:
  labels:
    {{- include "demo-app.labels" . | nindent 4 }}
    {{- include "demo-app.platformLabels" . | nindent 4 }}
\`\`\`

Validate that helper names are globally unique enough to avoid collisions with other chart dependencies.

## 8. Lab B — Package the chart

First verify the chart version and dependencies:

\`\`\`bash
helm lint charts/demo-app
helm dependency build charts/demo-app
helm package charts/demo-app --destination dist
\`\`\`

Expected package name:

\`\`\`text
dist/demo-app-0.1.0.tgz
\`\`\`

Inspect without installing:

\`\`\`bash
helm show chart dist/demo-app-0.1.0.tgz
helm show values dist/demo-app-0.1.0.tgz
helm template demo-app dist/demo-app-0.1.0.tgz \
  --namespace demo-dev -f environments/dev/values.yaml
\`\`\`

On PowerShell, calculate a local file checksum:

\`\`\`powershell
Get-FileHash .\dist\demo-app-0.1.0.tgz -Algorithm SHA256
\`\`\`

On Linux/macOS:

\`\`\`bash
sha256sum dist/demo-app-0.1.0.tgz
\`\`\`

A local \`.tgz\` SHA-256 checksum is **not interchangeable** with an OCI registry manifest digest. Record each identifier with its artifact type.

## 9. Chart version and application version policy

\`Chart.yaml\`:

\`\`\`yaml
apiVersion: v2
name: demo-app
type: application
version: 0.1.0
appVersion: "1.0.0"
\`\`\`

Use a deliberate chart version bump whenever packaged chart content changes. Avoid silently overwriting a published chart version. Application image updates may occur independently, using the same chart with a new reviewed image digest in GitOps values.

Suggested release record:

\`\`\`text
Git commit:          <source-sha>
Chart name/version:  demo-app / 0.1.0
Chart OCI digest:    sha256:<registry-manifest-digest>
Image OCI digest:    sha256:<verified-image-digest>
Environment:         demo-dev
GitOps commit:       <approved-config-sha>
\`\`\`

## 10. OCI registry fundamentals

Helm 3 supports OCI chart storage in registries. A registry reference typically uses \`oci://\`:

\`\`\`text
oci://registry.example.com/platform/charts/demo-app
\`\`\`

When pushing a chart package, specify the **repository prefix**, not a final chart filename:

\`\`\`bash
helm push dist/demo-app-0.1.0.tgz \
  oci://registry.example.com/platform/charts
\`\`\`

The registry path and chart name/version must satisfy Helm OCI naming/version rules. The registry must support OCI artifacts and the account must have appropriate permissions.

## 11. Lab C — Authenticate to an approved registry

**Do not embed a token in command history.** Prefer an ephemeral CI job token or approved workload identity.

Example interactive login:

\`\`\`bash
helm registry login registry.example.com \
  --username "<approved-user>"
\`\`\`

Enter the credential only when prompted by the Helm CLI. In automation, use \`--password-stdin\` with an approved masked secret injection mechanism; do not echo tokens in logs.

Verify registry access and log out when appropriate:

\`\`\`bash
helm registry logout registry.example.com
\`\`\`

Avoid reusing personal long-lived credentials in shared GitLab runners.

## 12. Lab D — Push and pull a chart

**Optional, requires approved registry and credentials.**

\`\`\`bash
helm push dist/demo-app-0.1.0.tgz \
  oci://registry.example.com/platform/charts

helm pull oci://registry.example.com/platform/charts/demo-app \
  --version 0.1.0 --destination pulled

helm show chart \
  oci://registry.example.com/platform/charts/demo-app \
  --version 0.1.0
\`\`\`

Render the pulled artifact:

\`\`\`bash
helm template demo-app pulled/demo-app-0.1.0.tgz \
  --namespace demo-dev -f environments/dev/values.yaml
\`\`\`

Verify registry-provided digest and provenance through the approved registry/security tooling. Do not assume a successful \`helm pull\` proves the publisher is trusted.

## 13. OCI digest verification and signatures

There are several distinct controls:

1. **Integrity:** Content matches a known digest.
2. **Authenticity:** A signature or attestation is tied to a trusted signer identity.
3. **Provenance:** Evidence links the artifact to a reviewed source and build workflow.
4. **Policy:** Admission or CI evaluates trust, allowed publishers and vulnerability thresholds.
5. **Deployment identity:** The deployed chart and image are the exact approved artifacts.

Helm's traditional \`helm package --sign\` and \`helm verify\` use PGP-based provenance for chart packages. OCI registries and organizations may instead use compatible artifact-signing workflows (for example, Sigstore/Cosign) where the tooling and artifact media types are supported. **Do not assume all registries, Helm clients or Argo CD versions automatically verify OCI chart signatures.**

A verified image signature does not verify the chart, and a verified chart does not verify the image.

## 14. GitLab CI: trusted packaging pipeline

Illustrative \`.gitlab-ci.yml\`:

\`\`\`yaml
stages:
  - validate
  - package
  - publish

variables:
  CHART_DIR: "charts/demo-app"

helm_validate:
  stage: validate
  image: registry.example.com/platform/helm@sha256:<APPROVED_HELM_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - helm dependency build "$CHART_DIR"
    - helm lint "$CHART_DIR"
    - helm template demo-app "$CHART_DIR" --namespace demo-dev -f environments/dev/values.yaml > rendered-dev.yaml
    - helm template demo-app "$CHART_DIR" --namespace demo-test -f environments/test/values.yaml > rendered-test.yaml
    - helm template demo-app "$CHART_DIR" --namespace demo-staging -f environments/staging/values.yaml > rendered-staging.yaml
    - helm template demo-app "$CHART_DIR" --namespace demo-prod -f environments/prod/values.yaml > rendered-prod.yaml
  artifacts:
    paths:
      - rendered-*.yaml
    expire_in: 1 day

helm_package:
  stage: package
  image: registry.example.com/platform/helm@sha256:<APPROVED_HELM_TOOL_DIGEST>
  tags: [trusted-build]
  needs: [helm_validate]
  script:
    - helm dependency build "$CHART_DIR"
    - mkdir -p dist
    - helm package "$CHART_DIR" --destination dist
  artifacts:
    paths:
      - dist/*.tgz
    expire_in: 7 days

helm_publish:
  stage: publish
  image: registry.example.com/platform/helm@sha256:<APPROVED_HELM_TOOL_DIGEST>
  tags: [trusted-publish]
  needs:
    - job: helm_package
      artifacts: true
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
  script:
    - test -n "$REGISTRY_USER"
    - test -n "$REGISTRY_PASSWORD"
    - printf '%s' "$REGISTRY_PASSWORD" | helm registry login registry.example.com --username "$REGISTRY_USER" --password-stdin
    - helm push dist/demo-app-*.tgz oci://registry.example.com/platform/charts
\`\`\`

**Template only:** Replace tool image digests, registry hostname and credentials with approved equivalents. The \`publish\` job must additionally be protected by runner isolation, protected branches, authorized credentials, package-version immutability, signature/provenance policy and appropriate approvals. A default-branch rule alone is not a complete security boundary. Prefer a dedicated publish identity with least-privilege access.

## 15. GitOps chart consumption

Two common patterns:

**A. Git-sourced chart:** Argo CD reads the chart and values from the GitOps repository. A reviewed Git commit identifies chart changes.

**B. OCI-sourced chart:** Argo CD references a published chart version in a trusted OCI registry and applies approved values. Verify that the installed Argo CD version and repository configuration support your chosen OCI chart source.

For either approach:
- Use a distinct Argo CD Application per environment namespace.
- Keep environment configuration in Git.
- Promote the same immutable application image digest.
- Apply chart version changes deliberately, not as floating updates.
- Record the resolved chart artifact digest in release evidence when the platform supports it.
- Do not manage the same resources with an independent Helm release controller.

A chart version alone is not proof of immutability if the registry permits overwriting tags/versions.

## 16. Dependency governance

Before accepting a chart dependency:

1. Confirm maintainer, source repository and ownership.
2. Review dependency purpose and privileged resources.
3. Pin an approved version and commit \`Chart.lock\`.
4. Validate checksums and registry/source integrity.
5. Scan rendered manifests for permissions, host access, images and secret handling.
6. Review CRDs and hooks for cluster-wide effects.
7. Assess transitive dependencies and support lifecycle.
8. Document upgrade, rollback and vulnerability response procedures.

Helm dependencies may render cluster-scoped resources even when the parent chart is deployed to a namespace. Always inspect output.

## 17. CRDs, hooks and installation-order hazards

Charts may include CRDs in \`crds/\` or resources annotated with Helm hooks. These require special attention:

- CRDs are cluster-scoped and can affect multiple tenants.
- Helm has special CRD lifecycle behavior; do not assume upgrades/deletions are handled like ordinary resources.
- Hooks can create Jobs and side effects not obvious from standard Deployments.
- Argo CD and Helm handle hooks differently; verify compatibility before migration.
- Never let an unreviewed application chart implicitly install or upgrade shared platform CRDs.

Use dedicated, reviewed platform change procedures for cluster-scoped components.

## 18. Failure-injection matrix

Perform tests offline or in a disposable registry:

| Test | Fault | Expected symptom | Recovery |
| --- | --- | --- | --- |
| A | Delete \`Chart.lock\` | Locked build cannot reproduce expected state | Regenerate and review lock |
| B | Change dependency version without updating lock | Dependency mismatch or stale lock | Review \`helm dependency update\` diff |
| C | Remove local library chart path | Dependency build fails | Restore source or use trusted OCI repo |
| D | Corrupt chart archive | Package/render/verification fails | Rebuild from trusted source |
| E | Wrong registry credentials | OCI push/pull denied | Fix scoped identity |
| F | Pull nonexistent chart version | Not found | Restore approved version |
| G | Reuse chart version with changed content | Immutability/policy conflict | Bump version and republish |
| H | Mismatched chart/image digest records | Release provenance inconsistent | Reconcile artifact evidence |
| I | Untrusted subchart with cluster role | Security policy violation | Remove dependency and review |
| J | OCI signature absent/untrusted | Trust policy fails | Publish signed approved artifact |

A test is successful only when the failure is detected and the approved recovery is demonstrated.

## 19. SRE troubleshooting commands

\`\`\`bash
helm version
helm lint charts/demo-app
helm dependency list charts/demo-app
helm dependency build charts/demo-app
helm show chart dist/demo-app-0.1.0.tgz
helm show values dist/demo-app-0.1.0.tgz
helm template demo-app dist/demo-app-0.1.0.tgz \
  --namespace demo-dev -f environments/dev/values.yaml
\`\`\`

For authorized OCI access:

\`\`\`bash
helm show chart oci://registry.example.com/platform/charts/demo-app --version 0.1.0
helm pull oci://registry.example.com/platform/charts/demo-app --version 0.1.0
\`\`\`

Review registry audit logs, repository permissions and artifact metadata when troubleshooting authentication or integrity failures.

## 20. Incident runbook — Untrusted chart promotion

**Scenario:** A production GitOps change references a chart package whose content differs from the approved release evidence.

1. Stop further environment promotion and preserve audit records.
2. Identify GitOps commit, chart version, OCI digest, image digest and publisher.
3. Determine whether the registry artifact was overwritten or an incorrect version was selected.
4. Validate signatures, provenance and dependency lock against trusted records.
5. Assess rendered resources for privileged or unexpected changes.
6. Revert GitOps desired state to a retained, verified chart and image combination.
7. Verify Argo CD reconciliation and user-facing SLIs.
8. Rotate compromised registry credentials if indicated.
9. Record impact, root cause and registry immutability/policy improvements.

Do not “fix” the problem by disabling signature verification or admission policy.

## 21. Operational monitoring

Track:
- Helm dependency resolution failures.
- Chart lint/render/policy failure rate.
- OCI publish and pull failures.
- Chart version overwrite attempts.
- Signature/provenance validation failures.
- Registry credential and permission changes.
- Unexpected cluster-scoped resources.
- Argo CD OutOfSync/Degraded applications.
- Deployment availability and error/latency SLOs.

Establish alerts based on observed baselines and release criticality.

## 22. Cleanup

Local generated files may be removed after evidence is captured:

\`\`\`bash
rm -rf dist pulled rendered-*.yaml
\`\`\`

**PowerShell alternative:**

\`\`\`powershell
Remove-Item .\dist, .\pulled -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\rendered-*.yaml -Force -ErrorAction SilentlyContinue
\`\`\`

Keep \`Chart.lock\` and reviewed source files. Do not delete published registry artifacts or tags unless the authorized retention process explicitly permits it.

## 23. Acceptance checklist

- [ ] Local library chart created and referenced.
- [ ] \`Chart.lock\` generated, reviewed and retained.
- [ ] Dependency build and lint succeed.
- [ ] Chart package created and inspected.
- [ ] All four environment overlays render.
- [ ] Local archive checksum recorded.
- [ ] OCI push/pull tested or registry limitation documented.
- [ ] Chart and image digests recorded separately.
- [ ] Signing/provenance trust requirements documented.
- [ ] GitLab CI publish boundary reviewed.
- [ ] Argo CD chart consumption model selected.
- [ ] CRD/hook/dependency security risks reviewed.
- [ ] Negative tests and incident recovery documented.

## 24. Evidence worksheet

\`\`\`text
CHAPTER 033 — HELM DEPENDENCIES AND OCI SUPPLY CHAIN
Date:
Reviewer:
Source repository / commit:
Helm version:
Parent chart / version:
Dependency names / versions:
Chart.lock reviewed:
Dependency build:
Lint result:
Rendered Dev/Test/Staging/Prod:
Chart package filename:
Local package SHA-256:
OCI registry / chart version:
OCI manifest digest:
Signature/provenance verification:
Application image digest:
GitLab publish pipeline:
GitOps commit / Argo CD source:
Negative tests:
Rollback chart/image reference:
Open risks / owners:
\`\`\`

## 25. Knowledge checks

1. What does \`Chart.lock\` guarantee, and what does it not guarantee?
2. How do \`helm dependency update\` and \`helm dependency build\` differ?
3. Why use a library chart instead of duplicating helpers?
4. Why are the chart archive SHA-256 and OCI manifest digest different identifiers?
5. Why is chart signing independent of image signing?
6. What can go wrong if an OCI registry allows version overwrites?
7. Why do CRDs and Helm hooks require extra governance?
8. Why must a GitOps deployment record both chart and image provenance?

## 26. Completion

**Pass:** The operator packages a reproducible chart with a locked local library dependency, validates all environment overlays, documents trusted OCI publication and verifies artifact provenance and rollback boundaries.

**Next: Chapter 034 — Helm Release Lifecycle, Upgrades, Rollbacks and Production Troubleshooting.**
