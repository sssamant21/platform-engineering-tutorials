# Chapter 035 — Enterprise Helm Chart Engineering, Security and Release Operations Capstone

**Part 07 — Enterprise Helm Chart Engineering (Final Capstone)**  
**Chapter:** 035 of 100  
**Audience:** SRE, infrastructure, Kubernetes and platform operations teams  
**Prerequisites:** Chapters 031–034 and the software supply-chain foundations in Chapters 021–025  
**Deployment model:** One shared training Kubernetes cluster with four namespaces: \`demo-dev\`, \`demo-test\`, \`demo-staging\`, \`demo-prod\`.

> **Safety and scope:** This capstone uses generic names and a disposable application. The four namespaces are not four separate clusters and do not provide hard security or control-plane isolation. Never test faults against production workloads. The default path is offline chart validation. Optional live exercises require an approved isolated namespace, verified image digest, authorized registry and clear resource ownership. In the reference production workflow **Argo CD owns deployments**, and GitLab CI builds, tests, packages and publishes; do not use independent Helm upgrades against Argo CD-managed objects.

## 1. Mission and exit criteria

You are the on-call platform engineer responsible for certifying a reusable Helm chart and its release process before the platform team adopts it.

Deliver a complete evidence-backed package that:

1. Renders a single chart correctly for Dev, Test, Staging and Production.
2. Enforces stable naming, selectors, typed values and configuration-driven rollouts.
3. Uses immutable OCI image digests and reviewed chart dependencies.
4. Applies non-root security, least privilege, probes, resource requests/limits and optional HPA/PDB/NetworkPolicy.
5. Detects invalid inputs and policy violations before deployment.
6. Supports approved packaging, publishing, provenance verification and environment promotion.
7. Demonstrates a failed rollout, diagnosis, rollback and restored application health.
8. Produces operational runbooks, a change record, evidence and a scored acceptance decision.

**Passing standard:** At least 85/100 points, with no failed critical controls and all required evidence present. An untested integration must be marked **Not Tested**, not assumed successful.

## 2. Reference architecture

\`\`\`text
                      GitLab source repository
                                |
                    tests / chart lint / policy
                                |
                  dependency lock + build checks
                                |
                 chart package + SBOM/provenance
                                |
                      trusted OCI chart registry
                                |
       verified application image@sha256:<immutable-digest>
                                |
                        reviewed GitOps MRs
                                |
                     Argo CD renders Helm chart
                                |
                  ONE Kubernetes cluster
                                |
        +-----------------------+----------------------+
        |                       |                      |
     demo-dev                demo-test            demo-staging
        |                       |                      |
        +-----------------------+----------------------+
                                |
                             demo-prod
                                |
                Deployment / Service / ConfigMap
                 optional HPA / PDB / NetworkPolicy
                                |
                  readiness / EndpointSlices / SLIs
\`\`\`

Each environment has a separate Argo CD Application, namespace and values overlay. Promotion changes approved GitOps desired state; it does not rebuild the image. Production-critical systems may warrant separate clusters, accounts and stronger boundaries.

## 3. Required repository deliverables

\`\`\`text
enterprise-helm-capstone/
├── .gitlab-ci.yml
├── charts/
│   ├── demo-app/
│   │   ├── Chart.yaml
│   │   ├── Chart.lock
│   │   ├── values.yaml
│   │   ├── values.schema.json
│   │   └── templates/
│   │       ├── _helpers.tpl
│   │       ├── configmap.yaml
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── serviceaccount.yaml
│   │       ├── hpa.yaml
│   │       ├── pdb.yaml
│   │       └── networkpolicy.yaml
│   └── platform-common/
│       ├── Chart.yaml
│       └── templates/_labels.tpl
├── environments/
│   ├── dev/values.yaml
│   ├── test/values.yaml
│   ├── staging/values.yaml
│   └── prod/values.yaml
├── tests/
│   ├── negative-values/
│   └── verify-render.py
└── docs/
    ├── CHANGE-RECORD.md
    ├── RUNBOOK.md
    ├── ACCEPTANCE.md
    └── EVIDENCE.md
\`\`\`

Reuse the **complete, tested chart from Chapters 031–033** rather than creating a new, incompatible chart. Chapter 032 adds conditional HPA/PDB/NetworkPolicy and validation guards; Chapter 033 adds the local library dependency. Chapter 034 provides the standalone Helm release exercises.

## 4. Preflight and operational safety

Verify the environment before any work:

\`\`\`bash
helm version
kubectl version --client
kubectl config current-context
git status --short
\`\`\`

Record:

\`\`\`text
Training cluster/context:
Namespace(s):
Chart source commit:
Chart version:
Dependency lock digest/revision:
Approved OCI chart digest:
Approved OCI image digest:
Release owner:
Rollback owner:
Authorized change window:
Application SLO baseline:
\`\`\`

For offline validation, no Kubernetes write permissions are required.

For optional live tests, use an **independent disposable namespace** such as \`demo-helm-capstone-lab\`, created by an authorized administrator. Check that no Argo CD Application or other controller already owns the chosen objects. Do not create or delete namespaces without approval.

## 5. Phase 1 — Chart architecture audit

Audit \`Chart.yaml\`, \`values.yaml\`, \`values.schema.json\`, helpers and templates.

| Control | Required outcome |
| --- | --- |
| Chart metadata | Correct \`apiVersion: v2\`, chart name and SemVer version |
| Dependencies | Explicit approved versions and reviewed \`Chart.lock\` |
| Labels | Stable Deployment selectors and matching Service selectors |
| Values | Typed defaults and environment-specific overlays |
| Configuration | ConfigMap nonsecret; checksum triggers new Pod template |
| Image | \`repository@sha256:<verified-digest>\` |
| Workload | Non-root, seccomp, no privilege escalation, capabilities dropped |
| Availability | Startup/readiness/liveness probes, rolling-update constraints |
| Resources | CPU/memory requests and limits |
| Identity | ServiceAccount and no unneeded API token mounting |
| Scaling | HPA conditional, no competing replica ownership |
| Disruption | PDB conditional and compatible with replica capacity |
| Network | NetworkPolicy off until real traffic flows reviewed |

**Security caveat:** A valid 64-character digest string proves format, not authenticity. Use approved registry and signing/provenance verification to establish trust.

## 6. Phase 2 — Four-environment values audit

Example environment matrix:

| Setting | Dev | Test | Staging | Production |
| --- | --- | --- | --- | --- |
| Namespace | \`demo-dev\` | \`demo-test\` | \`demo-staging\` | \`demo-prod\` |
| Replica baseline | 2 | 2 | 3 | 3 |
| HPA | Off | Off | On | On |
| PDB | Off | Off | On | On |
| Logging | debug | info | info | warn |
| Feature flag | On | Off | Off | Off |
| Image | Same verified digest | Same digest | Same digest | Same digest |
| Chart | Approved version | Approved version | Approved version | Approved version |

The image digest is **identical across a single promotion wave**. Each environment may be at a different approved version while promotion is in progress, but a promotion must never silently rebuild an environment-specific artifact.

Ensure the chart's \`values.schema.json\` accepts each overlay and that the values do not include real credentials.

## 7. Phase 3 — Dependency and packaging checks

From the repository root:

\`\`\`bash
helm dependency build charts/demo-app
helm dependency list charts/demo-app
helm lint charts/demo-app
mkdir -p dist
helm package charts/demo-app --destination dist
helm show chart dist/demo-app-0.1.0.tgz
\`\`\`

Replace \`0.1.0\` in the final command with the actual reviewed chart version if it differs. In CI, use the produced archive name rather than assuming the version.

Verify \`Chart.lock\` matches the reviewed dependency declaration and that the local \`platform-common\` library chart is present. A local \`file://\` dependency requires the sibling directory in the CI checkout.

**PowerShell:**

\`\`\`powershell
New-Item -ItemType Directory -Force dist | Out-Null
Get-FileHash .\dist\demo-app-0.1.0.tgz -Algorithm SHA256
\`\`\`

**Linux/macOS:**

\`\`\`bash
sha256sum dist/demo-app-0.1.0.tgz
\`\`\`

The archive SHA-256 and registry OCI manifest digest are different identifiers. Capture both when available.

## 8. Phase 4 — Render all environments

\`\`\`bash
helm template demo-app charts/demo-app \
  --namespace demo-dev \
  -f environments/dev/values.yaml > rendered-dev.yaml

helm template demo-app charts/demo-app \
  --namespace demo-test \
  -f environments/test/values.yaml > rendered-test.yaml

helm template demo-app charts/demo-app \
  --namespace demo-staging \
  -f environments/staging/values.yaml > rendered-staging.yaml

helm template demo-app charts/demo-app \
  --namespace demo-prod \
  -f environments/prod/values.yaml > rendered-prod.yaml
\`\`\`

Expected:
- Dev/Test: Deployment, Service, ConfigMap and ServiceAccount.
- Staging/Production: those resources plus HPA and PDB.
- NetworkPolicy: only where explicitly enabled and reviewed.
- Every Deployment image uses an immutable digest.
- Deployment selectors and Service selectors agree.
- HPA-enabled Deployment omits independent \`spec.replicas\`.

Helm's \`--namespace\` sets release namespace context, but rendered manifests need not include \`metadata.namespace\`. Actual destination is determined by the deployment controller or apply operation.

## 9. Phase 5 — Automated rendered-manifest verification

Create \`tests/verify-render.py\`:

\`\`\`python
#!/usr/bin/env python3
"""Validate rendered Helm manifests. Requires PyYAML."""
import pathlib
import re
import sys
import yaml

EXPECTED = {
    "dev": {"env": "dev", "hpa": False, "pdb": False},
    "test": {"env": "test", "hpa": False, "pdb": False},
    "staging": {"env": "staging", "hpa": True, "pdb": True},
    "prod": {"env": "prod", "hpa": True, "pdb": True},
}
DIGEST = re.compile(r"^.+@sha256:[a-f0-9]{64}$")
failures = []
images = {}

for name, expected in EXPECTED.items():
    file = pathlib.Path(f"rendered-{name}.yaml")
    if not file.exists():
        failures.append(f"{name}: missing rendered manifest")
        continue
    resources = [r for r in yaml.safe_load_all(file.read_text())
                 if isinstance(r, dict) and r.get("kind")]
    by_kind = {}
    for obj in resources:
        by_kind.setdefault(obj["kind"], []).append(obj)
    for kind in ("Deployment", "Service", "ConfigMap", "ServiceAccount"):
        if len(by_kind.get(kind, [])) != 1:
            failures.append(f"{name}: expected exactly one {kind}")
    for kind, enabled in (("HorizontalPodAutoscaler", expected["hpa"]),
                          ("PodDisruptionBudget", expected["pdb"])):
        if bool(by_kind.get(kind)) != enabled:
            failures.append(f"{name}: unexpected {kind} presence")
    if not all(by_kind.get(k) for k in ("Deployment", "Service", "ConfigMap")):
        continue
    dep = by_kind["Deployment"][0]
    svc = by_kind["Service"][0]
    cfg = by_kind["ConfigMap"][0]
    spec = dep["spec"]
    pod = spec["template"]
    if spec["selector"]["matchLabels"] != svc["spec"]["selector"]:
        failures.append(f"{name}: Deployment/Service selectors differ")
    if not all(pod["metadata"]["labels"].get(k) == v
               for k, v in spec["selector"]["matchLabels"].items()):
        failures.append(f"{name}: Pod labels do not match selector")
    if expected["hpa"] and "replicas" in spec:
        failures.append(f"{name}: HPA enabled but replicas is managed")
    if cfg["data"].get("APP_ENV") != expected["env"]:
        failures.append(f"{name}: APP_ENV mismatch")
    if "checksum/config" not in pod["metadata"].get("annotations", {}):
        failures.append(f"{name}: missing config checksum")
    containers = pod["spec"].get("containers", [])
    if len(containers) != 1:
        failures.append(f"{name}: expected one container")
        continue
    c = containers[0]
    image = c.get("image", "")
    if not DIGEST.fullmatch(image):
        failures.append(f"{name}: image not digest-pinned")
    images[name] = image
    if not c.get("resources", {}).get("requests"):
        failures.append(f"{name}: missing resource requests")
    if not c.get("resources", {}).get("limits"):
        failures.append(f"{name}: missing resource limits")
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        if probe not in c:
            failures.append(f"{name}: missing {probe}")
    sec = c.get("securityContext", {})
    if sec.get("allowPrivilegeEscalation") is not False:
        failures.append(f"{name}: privilege escalation not disabled")
    if sec.get("readOnlyRootFilesystem") is not True:
        failures.append(f"{name}: filesystem not read-only")
    if "ALL" not in sec.get("capabilities", {}).get("drop", []):
        failures.append(f"{name}: capabilities not dropped")
    if pod["spec"].get("securityContext", {}).get("runAsNonRoot") is not True:
        failures.append(f"{name}: non-root policy missing")
    if pod["spec"].get("automountServiceAccountToken") is not False:
        failures.append(f"{name}: service account token auto-mount enabled")

if len(images) == len(EXPECTED) and len(set(images.values())) != 1:
    failures.append("image digest differs across promotion environments")

if failures:
    print("FAIL:")
    for problem in failures:
        print(" -", problem)
    sys.exit(1)
print("PASS: all four rendered environments satisfy baseline checks")
\`\`\`

Install the local testing dependency in an isolated Python environment:

\`\`\`bash
python -m pip install PyYAML
python tests/verify-render.py
\`\`\`

This script checks structural controls but does **not** verify OCI signature trust, registry existence, admission, DNS, traffic flows, runtime behavior or user-facing SLOs. Add policy-as-code and runtime testing for those.

## 10. Phase 6 — Negative tests and guardrails

Create malformed values files or use approved overrides to prove rejection:

| Negative test | Injection | Required result |
| --- | --- | --- |
| Invalid digest | \`image.digest: latest\` | Schema failure |
| Replica count zero | \`replicaCount: 0\` | Schema failure |
| Wrong boolean type | \`networkPolicy.enabled: "yes"\` | Schema failure |
| HPA min > max | \`minReplicas: 8\`, \`maxReplicas: 2\` | Template guard failure |
| PDB too strict | \`minAvailable: 5\`, \`replicaCount: 2\`, HPA off | Guard failure |
| Selector override | Reserved label in \`extraLabels\` | Guard failure |
| Invalid Service type | \`service.type: LoadBalancer\` | Schema failure |
| Unavailable dependency | Remove local library chart in disposable copy | Dependency build failure |
| Missing config | Remove required config key | Schema or template failure |
| Secret in values | Synthetic sentinel string matching secret-scan rule | Policy failure |

Example:

\`\`\`bash
helm template demo-app charts/demo-app --set replicaCount=0
helm template demo-app charts/demo-app \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=8 \
  --set autoscaling.maxReplicas=2
\`\`\`

A negative test passes only if the command **exits nonzero** and the expected guard is responsible. Do not inject real credentials.

## 11. Phase 7 — GitLab CI pipeline

The following example assumes an approved internal Helm tool image that includes Helm, Python and PyYAML. Replace the tool digest and runner tags with your organization's approved values.

\`\`\`yaml
stages:
  - validate
  - package
  - publish

variables:
  CHART_DIR: "charts/demo-app"

helm_validate:
  stage: validate
  image: registry.example.com/platform/helm-python@sha256:<APPROVED_TOOL_DIGEST>
  tags: [mr-validation]
  script:
    - helm dependency build "$CHART_DIR"
    - helm lint "$CHART_DIR"
    - helm template demo-app "$CHART_DIR" --namespace demo-dev -f environments/dev/values.yaml > rendered-dev.yaml
    - helm template demo-app "$CHART_DIR" --namespace demo-test -f environments/test/values.yaml > rendered-test.yaml
    - helm template demo-app "$CHART_DIR" --namespace demo-staging -f environments/staging/values.yaml > rendered-staging.yaml
    - helm template demo-app "$CHART_DIR" --namespace demo-prod -f environments/prod/values.yaml > rendered-prod.yaml
    - python tests/verify-render.py
  artifacts:
    paths:
      - rendered-dev.yaml
      - rendered-test.yaml
      - rendered-staging.yaml
      - rendered-prod.yaml
    expire_in: 1 day

helm_package:
  stage: package
  image: registry.example.com/platform/helm-python@sha256:<APPROVED_TOOL_DIGEST>
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
  image: registry.example.com/platform/helm-python@sha256:<APPROVED_TOOL_DIGEST>
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

**Security gates beyond this skeleton:** trusted runners, protected credentials, protected branches/tags, MR approvals, secret scanning, policy validation, artifact immutability, signature/provenance checks and verified OCI digests. A successful pipeline alone does not certify production readiness.

## 12. Phase 8 — OCI publication and artifact evidence

If an authorized registry is available:

\`\`\`bash
helm push dist/demo-app-0.1.0.tgz \
  oci://registry.example.com/platform/charts

helm pull oci://registry.example.com/platform/charts/demo-app \
  --version 0.1.0 --destination pulled

helm show chart pulled/demo-app-0.1.0.tgz
\`\`\`

Use the actual chart version in place of \`0.1.0\` when necessary.

Record:
- Chart source commit and package version.
- Local package checksum.
- Registry artifact manifest digest.
- Approved signer identity/provenance evidence.
- Application image digest and its independent verification.
- GitLab pipeline/job identity.
- GitOps commit that references the release.

Do not treat \`helm pull\` or a syntactically valid digest as proof of trusted provenance. Signature verification must be explicitly implemented with supported tooling.

## 13. Phase 9 — GitOps promotion plan

A production-oriented workflow is:

1. GitLab CI validates chart and application artifacts.
2. The chart package and image are published to approved immutable registries.
3. A reviewed GitOps change pins chart version and verified image digest for \`demo-dev\`.
4. Argo CD reconciles the Dev Application; SRE validates readiness, connectivity and SLIs.
5. The **same image digest** is promoted through \`demo-test\` and \`demo-staging\`.
6. Production promotion requires explicit approval, change record and rollback readiness.
7. The \`demo-prod\` Application reconciles only after policy gates pass.
8. Any failed gate halts further promotion and initiates the recovery plan.

A separate Argo CD Application targets each namespace in the same cluster. Argo CD integration is implemented in Parts 08–10; this capstone verifies the interface contract and operating model rather than pretending a complete Argo CD deployment exists.

## 14. Phase 10 — Optional standalone Helm failure lab

**Do not perform this on Argo CD-managed resources.** Use a disposable independent Helm release, e.g. \`demo-app-helm-capstone\`, and a real verified application image.

Preflight:

\`\`\`bash
kubectl config current-context
kubectl get namespace demo-helm-capstone-lab
kubectl auth can-i create deployments -n demo-helm-capstone-lab
helm list -n demo-helm-capstone-lab -a
\`\`\`

Install:

\`\`\`bash
helm upgrade --install demo-app-helm-capstone charts/demo-app \
  --namespace demo-helm-capstone-lab \
  -f environments/dev/values.yaml \
  --wait --timeout 5m

helm status demo-app-helm-capstone -n demo-helm-capstone-lab
helm history demo-app-helm-capstone -n demo-helm-capstone-lab
\`\`\`

**Caution:** Use a disposable chart copy and set a unique \`fullnameOverride\` if necessary to avoid naming collisions. Ensure a valid real image digest is configured before installation.

Inject a broken readiness path in the **disposable copy** of \`deployment.yaml\`, then:

\`\`\`bash
helm upgrade demo-app-helm-capstone charts/demo-app \
  --namespace demo-helm-capstone-lab \
  -f environments/dev/values.yaml \
  --wait --timeout 90s
\`\`\`

Investigate:

\`\`\`bash
helm history demo-app-helm-capstone -n demo-helm-capstone-lab
kubectl describe deployment -n demo-helm-capstone-lab
kubectl get pods -n demo-helm-capstone-lab
kubectl get events -n demo-helm-capstone-lab --sort-by=.lastTimestamp
\`\`\`

Rollback using the actual verified previous revision:

\`\`\`bash
helm rollback demo-app-helm-capstone <KNOWN_GOOD_REVISION> \
  --namespace demo-helm-capstone-lab \
  --wait --timeout 5m
\`\`\`

Verify ready replicas, EndpointSlices and HTTP health. Do not assume rollback reverses database changes, CRD changes, PersistentVolume contents, hooks or external side effects.

## 15. Failure-injection and recovery matrix

| Failure | Detection | Recovery | Evidence |
| --- | --- | --- | --- |
| Invalid chart values | Lint/schema guard | Correct reviewed values | Failed test log |
| Missing dependency | Dependency build | Restore locked trusted dependency | Lockfile and build |
| Invalid image digest | CI/policy/Pod event | Restore approved digest | Registry verification |
| Broken readiness probe | Unready Pods/timeout | Git revert or Helm rollback by owner | Rollout timeline |
| Selector mismatch | Empty EndpointSlices | Restore stable helper selectors | Service/Pod comparison |
| ConfigMap not applied | Stale app config | Reviewed checksum-triggered rollout | Config endpoint |
| HPA metric failure | Unknown metrics | Repair metrics API; hold promotion | HPA events |
| PDB blocks eviction | Eviction denied | Review minAvailable/capacity | PDB status |
| NetworkPolicy blocks traffic | Connectivity failure | Revert reviewed policy | Traffic test |
| OCI artifact tampering | Signature/digest policy failure | Restore trusted artifact | Provenance record |
| Helm/Argo CD ownership conflict | Drift and unexpected changes | Restore single owner | Controller history |
| Upgrade with incompatible schema | Application/database errors | Compatible migration/recovery | DB rollback plan |

At least four failure cases must be executed or simulated with explicit evidence, including one rollback exercise in an authorized disposable environment.

## 16. Release reliability and SLO gate

A release is not successful solely because Kubernetes reports a healthy Deployment. Evaluate:

| Signal | Question |
| --- | --- |
| Deployment availability | Are desired Pods available? |
| Service endpoints | Are backends ready and routable? |
| Startup/readiness/liveness | Are probes correctly configured? |
| Application HTTP 5xx | Did errors increase after release? |
| p95/p99 latency | Did user experience regress? |
| CPU/memory | Is the workload throttled or OOM-killed? |
| HPA | Can scaling respond to load? |
| PDB | Is maintenance capacity sufficient? |
| Argo CD sync/health | Is desired state reconciled? |
| Security controls | Did admission or policy detect unsafe changes? |

Use service-specific measured baselines, error budgets and approved release gates. Do not invent universal thresholds.

## 17. Incident response runbook

Create \`docs/RUNBOOK.md\`:

\`\`\`markdown
# Helm and GitOps Release Incident Runbook

## Triage
1. Confirm cluster context, namespace, resource owner and change ID.
2. Stop further promotion.
3. Identify chart version, chart digest, image digest and GitOps commit.
4. Inspect Deployment, Pods, Service EndpointSlices and Kubernetes events.
5. Compare application error rate and latency to pre-release baselines.

## Containment
- Preserve nonsecret evidence and audit logs.
- Do not bypass admission, image verification or registry policy.
- Avoid ad hoc changes to Argo CD-managed live objects.

## Recovery
- Argo CD-managed: revert approved GitOps desired state.
- Standalone Helm-managed: rollback to a verified Helm revision.
- Verify Pods, Service routing and application SLO recovery.
- Confirm no external data or schema changes require separate recovery.

## Follow-up
Record root cause, impact, timeline, rollback duration, owners,
preventive checks, and next release acceptance conditions.
\`\`\`

## 18. Change record

Create \`docs/CHANGE-RECORD.md\`:

\`\`\`markdown
# Helm Chart Release Change Record

Change ID:
Change owner:
Approver:
Window:
Target namespaces:
Chart version and OCI digest:
Application image digest:
Source commit and GitOps commit:
Dependency lock reviewed:
Security and policy results:
Pre-release SLO baseline:
Deployment/rollback steps:
Stop conditions:
Backout artifact availability:
Communications and escalation:
Final result:
\`\`\`

## 19. Acceptance scoring rubric

| Category | Points |
| --- | ---: |
| Chart architecture, labels and templates | 15 |
| Values, schema and negative tests | 15 |
| Security context and least privilege | 10 |
| Dependency locking and packaging | 10 |
| OCI digest, provenance and supply-chain controls | 10 |
| Four-environment render and promotion design | 10 |
| HPA/PDB/NetworkPolicy and reliability | 10 |
| GitLab CI and GitOps ownership boundaries | 10 |
| Failure injection, rollback and SRE runbook | 5 |
| Evidence, change record and sign-off | 5 |
| **Total** | **100** |

**Critical controls (all mandatory):**
- Correct cluster and namespace context.
- No real secrets in values, manifests or logs.
- Real verified immutable image digest before deployment.
- Stable Deployment and Service selectors.
- Non-root workload and appropriate resource budgets.
- No unapproved privileged/cluster-scoped resources.
- A single authoritative deployment controller.
- Documented, tested rollback path.
- No bypass of registry/admission/security policy.

Score 85+ with any critical failure = **NOT READY**.

## 20. Acceptance checklist

- [ ] Chart renders and lints for all four namespaces.
- [ ] JSON schema rejects malformed values.
- [ ] Cross-field guards reject HPA/PDB incompatibilities.
- [ ] ConfigMap checksum changes when nonsecret configuration changes.
- [ ] HPA-enabled Deployment does not independently manage replicas.
- [ ] NetworkPolicy traffic review completed.
- [ ] Dependency lock and package integrity reviewed.
- [ ] Chart and image digests recorded separately.
- [ ] OCI signature/provenance policy documented and verified where available.
- [ ] GitLab CI validation and publication workflow reviewed.
- [ ] Argo CD ownership and GitOps promotion design documented.
- [ ] At least four negative tests captured.
- [ ] Approved rollback exercise completed or explicitly marked untested.
- [ ] Incident runbook and change record completed.
- [ ] SRE reviewer assigned acceptance decision.

## 21. Evidence worksheet

Create \`docs/EVIDENCE.md\`:

\`\`\`markdown
# Chapter 035 — Enterprise Helm Capstone Evidence

Date:
Reviewer:
Repository / source commit:
Cluster / context:
Chart name/version:
Dependency lock:
Chart archive checksum:
OCI chart digest:
Verified image digest:
Image signature/provenance:
Dev render:
Test render:
Staging render:
Production render:
Schema and guard negative tests:
Selector consistency:
ConfigMap checksum test:
Security policy checks:
HPA/PDB/NetworkPolicy review:
GitLab CI pipeline:
GitOps approval reference:
Failure injection cases:
Rollback exercise result:
SLO baseline / after:
Open risks / owners:
Score / 100:
Critical controls: PASS / FAIL
Final decision: PASS / NOT READY / INCOMPLETE
\`\`\`

## 22. Cleanup

For a **standalone disposable Helm release only**:

\`\`\`bash
helm uninstall demo-app-helm-capstone -n demo-helm-capstone-lab
\`\`\`

Delete only lab-owned local render artifacts after evidence capture. Keep reviewed chart source, \`Chart.lock\`, change records and accepted evidence. Do not delete shared namespaces, CRDs, registries, cluster metrics or Argo CD-managed resources.

## 23. Knowledge assessment

1. What is the operational distinction between a Helm chart and a Helm release?
2. Why must the chart OCI digest and application image digest be recorded separately?
3. What does \`Chart.lock\` provide, and what does it not establish?
4. Why must a ConfigMap update change the Pod template for environment variables?
5. Why is \`spec.replicas\` omitted when HPA manages scaling?
6. Which kinds of failures are outside the protection of a PDB?
7. Why can a valid chart render still fail admission or runtime readiness?
8. Why should Argo CD rollback use Git desired state rather than an independent Helm rollback?
9. What makes a production release gate different from a Deployment readiness check?
10. Which artifacts and evidence must be retained to support incident recovery?

## 24. Part 07 completion and next chapter

Part 07 now covers:

- **031:** Helm architecture, charts, templates and values fundamentals.
- **032:** Advanced templates, helpers, optional resources and schema design.
- **033:** Dependencies, OCI chart registries, packaging and supply-chain trust.
- **034:** Release lifecycle, upgrades, rollback and production troubleshooting.
- **035:** Integrated enterprise Helm engineering and operations capstone.

**Next: Chapter 036 — Argo CD Architecture, GitOps Reconciliation and Core Components**, beginning Part 08 — Argo CD Fundamentals and Installation.
