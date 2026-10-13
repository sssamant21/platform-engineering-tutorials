# Chapter 024 — Secure CI/CD Supply-Chain Policies, Artifact Promotion and Registry Governance

**Part 05 — Container Builds and Software Supply-Chain Security** | **Chapter 024 / 100**  
**Audience:** SRE, infrastructure, platform, security and release engineering teams  
**Lab:** GitLab CI, OCI registry, digest-based promotion policy, Python standard library, optional Helm/Argo CD review  
**Production model:** GitLab builds once on a trusted protected ref; the same verified image digest is promoted by reviewed GitOps changes across \`demo-dev\`, \`demo-test\`, \`demo-staging\` and \`demo-prod\`. These are namespaces in one shared cluster, not independent security boundaries.

> **Lab safety:** All repository, workload and environment names are generic. Use a disposable project. The executable policy lab uses synthetic metadata and never deploys to a cluster, signs with production identities, or writes to a real registry. Production rollout must use independently verified evidence and approved policies.

## 1. Learning objectives

After completing this chapter you will be able to:

1. Design supply-chain release gates that separate build, security validation, authorization and deployment.
2. Explain digest-based promotion and why rebuilding per environment breaks artifact continuity.
3. Govern registry repository access, tag immutability, retention and artifact deletion.
4. Define required evidence for source, tests, vulnerability scanning, SBOM, signature and provenance.
5. Implement a fail-closed, testable promotion policy using synthetic release evidence.
6. Apply different approval requirements to Dev, Test, Staging and Production.
7. Design protected GitLab pipelines and reviewed GitOps promotion without exposing privileged credentials.
8. Troubleshoot missing artifacts, mismatched digests, stale scans, signer distrust and policy bypasses.
9. Produce an SRE release readiness report and recovery runbook.

## 2. Enterprise promotion architecture

\`\`\`text
Feature merge request
    |
    +--> unit / integration / policy / SAST / secret / dependency gates
    |
Approved merge into protected main
    |
    v
Isolated trusted builder
    |
    +--> build ONCE and publish registry.example.com/training/demo-app@sha256:...
    +--> vulnerability scan and SBOM for EXACT digest
    +--> provenance and signature for EXACT digest
    |
    v
Release evidence bundle + policy decision
    |
    v
Reviewed GitOps MR for demo-dev
    |
    v
Argo CD reconciles demo-dev
    |
    v
Promote SAME digest to demo-test
    |
    v
Promote SAME digest to demo-staging
    |
    v
Explicit approval -> demo-prod
    |
    v
Post-deployment smoke tests, SLOs and audit evidence
\`\`\`

**Core invariant:** The promoted digest is identical across environments. The configuration can vary by environment, but the application artifact must not be rebuilt or retagged as a substitute for digest pinning.

**Security invariant:** An MR pipeline must not have signing authority, production registry write access or production Kubernetes credentials.

## 3. Supply-chain policy layers

| Layer | Enforced control | Evidence |
| --- | --- | --- |
| Source governance | Protected branches, CODEOWNERS, approvals | MR and commit |
| Build trust | Isolated builder and protected pipeline | Builder identity and build record |
| Image integrity | Immutable digest | Registry manifest/index digest |
| Component visibility | SBOM tied to digest | CycloneDX/SPDX |
| Vulnerability risk | Scan coverage, freshness and approved exceptions | Scanner result and risk record |
| Authenticity | Approved signer signature | Verified signature identity |
| Provenance | Trusted builder and source relationship | Verified attestation |
| Promotion | Environment-specific approvals | GitOps MR and release record |
| Admission | Reject untrusted artifact | Policy decision/event |
| Runtime | Readiness, security and SLO verification | Argo CD and observability |

No single check proves end-to-end safety. A signature alone does not imply a clean vulnerability scan, and a clean scan alone does not establish a trusted build.

## 4. Environment promotion policy

| Environment | Approval model | Required gates | Rollback |
| --- | --- | --- | --- |
| \`demo-dev\` | Authorized engineering review | Build/test, digest, signature and baseline scan | Prior approved digest |
| \`demo-test\` | Test owner acceptance | Dev validation, contract/integration tests | Prior tested digest |
| \`demo-staging\` | Release owner approval | Test acceptance, production-like smoke and capacity checks | Prior staged digest |
| \`demo-prod\` | Explicit production change approval | All earlier gates, fresh evidence, risk sign-off, readiness/SLO checks | Prior known-good retained digest |

This is a reference policy, not a claim that a shared cluster isolates production. Production-critical workloads may require a separate cluster, cloud account/subscription/project and stricter identities.

## 5. Registry governance controls

### Identity and authorization

- Grant trusted build automation **write** access only to designated image repositories.
- Give scanner, verification and deployment identities **read-only** access where possible.
- Use short-lived, scoped CI tokens or cloud workload identity; avoid static personal tokens.
- Do not expose registry write credentials to untrusted merge-request pipelines.
- Audit repository creation, tag mutation, artifact deletion, token creation and permissions.

### Immutability and retention

- Prefer immutable release tags where supported, but always deploy by digest.
- Retain active and rollback digests, their signatures, SBOMs and attestations.
- Coordinate garbage collection with release retention and disaster recovery requirements.
- Preserve registry replication and backup evidence where cross-region recovery is required.
- Test whether a digest remains pullable after tag changes; do not assume retention.

### Risk of tag mutation

\`\`\`text
demo-app:release-1  -> sha256:AAA (first push)
demo-app:release-1  -> sha256:BBB (later overwrite)
\`\`\`

The tag may move. A GitOps manifest referencing \`demo-app@sha256:AAA\` remains pinned to the original artifact **if** that artifact is retained and accessible.

## 6. Hands-on lab — deterministic promotion gate

This lab evaluates a **synthetic release record**, not real registry signatures or vulnerability reports. Its purpose is to test policy logic and failure behavior. Production release automation must fetch and verify evidence directly from trusted systems.

### Repository layout

\`\`\`text
demo-release-policy/
├── .gitlab-ci.yml
├── policy/
│   ├── evaluate.py
│   └── environments.json
├── evidence/
│   ├── release-approved.json
│   └── release-denied.json
├── tests/
│   └── test_policy.py
└── docs/
    └── promotion-runbook.md
\`\`\`

### Step A — Environment policy

Create \`policy/environments.json\`:

\`\`\`json
{
  "demo-dev": {
    "required_approvals": 1,
    "max_scan_age_hours": 72
  },
  "demo-test": {
    "required_approvals": 1,
    "max_scan_age_hours": 48
  },
  "demo-staging": {
    "required_approvals": 2,
    "max_scan_age_hours": 24
  },
  "demo-prod": {
    "required_approvals": 2,
    "max_scan_age_hours": 12
  }
}
\`\`\`

The values are **training examples**. Production thresholds must be approved by security, operations and change governance.

### Step B — Release evidence

Create \`evidence/release-approved.json\`:

\`\`\`json
{
  "release_id": "demo-release-001",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "image": "registry.example.com/training/demo-app@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "built_by_trusted_runner": true,
  "tests_passed": true,
  "scanner_succeeded": true,
  "scan_age_hours": 2,
  "critical_findings": 0,
  "high_findings": 0,
  "approved_exceptions": [],
  "sbom_verified": true,
  "signature_verified": true,
  "provenance_verified": true,
  "builder_identity_approved": true,
  "approvals": ["release-owner", "operations-owner"],
  "promoted_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
\`\`\`

The digest is a syntactically valid **placeholder**, not a real registry artifact. The booleans are synthetic; a production gate must never accept user-supplied \`signature_verified: true\` as proof of cryptographic verification.

Create \`evidence/release-denied.json\`:

\`\`\`json
{
  "release_id": "demo-release-denied",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "image": "registry.example.com/training/demo-app:latest",
  "built_by_trusted_runner": false,
  "tests_passed": false,
  "scanner_succeeded": false,
  "scan_age_hours": 999,
  "critical_findings": 1,
  "high_findings": 3,
  "approved_exceptions": [],
  "sbom_verified": false,
  "signature_verified": false,
  "provenance_verified": false,
  "builder_identity_approved": false,
  "approvals": [],
  "promoted_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
\`\`\`

### Step C — Policy evaluator

Create \`policy/evaluate.py\`:

\`\`\`python
import json
import re
import sys
from pathlib import Path

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^.+@sha256:([0-9a-f]{64})$")

REQUIRED_FLAGS = (
    "built_by_trusted_runner",
    "tests_passed",
    "scanner_succeeded",
    "sbom_verified",
    "signature_verified",
    "provenance_verified",
    "builder_identity_approved",
)


def evaluate(record, environment, policy):
    errors = []
    config = policy.get(environment)
    if not isinstance(config, dict):
        return [f"unknown environment: {environment}"]

    if not isinstance(record, dict):
        return ["release evidence must be an object"]

    if not COMMIT.fullmatch(str(record.get("source_commit", ""))):
        errors.append("invalid source commit")

    image = str(record.get("image", ""))
    match = IMAGE.fullmatch(image)
    digest = str(record.get("promoted_digest", ""))
    if not match:
        errors.append("image must use an immutable sha256 digest")
    if not DIGEST.fullmatch(digest):
        errors.append("invalid promoted digest")
    if match and digest != "sha256:" + match.group(1):
        errors.append("promoted digest does not match image")

    for flag in REQUIRED_FLAGS:
        if record.get(flag) is not True:
            errors.append(f"required gate failed: {flag}")

    age = record.get("scan_age_hours")
    if type(age) not in (int, float) or not (0 <= age <= config["max_scan_age_hours"]):
        errors.append("scan missing, invalid or too old")

    for severity in ("critical_findings", "high_findings"):
        count = record.get(severity)
        if type(count) is not int or count != 0:
            errors.append(f"disallowed or invalid {severity}")

    exceptions = record.get("approved_exceptions")
    if exceptions != []:
        errors.append("training policy does not support exceptions")

    approvals = record.get("approvals")
    if not isinstance(approvals, list) or any(
        not isinstance(x, str) or not x.strip() for x in approvals
    ):
        errors.append("invalid approval list")
    elif len(set(approvals)) < config["required_approvals"]:
        errors.append("insufficient distinct approvals")

    return errors


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: evaluate.py <evidence.json> <environment>")

    evidence = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    policy = json.loads(
        Path("policy/environments.json").read_text(encoding="utf-8")
    )
    errors = evaluate(evidence, sys.argv[2], policy)
    if errors:
        for error in errors:
            print("DENY:", error)
        raise SystemExit(1)
    print("ALLOW: synthetic release record satisfies training policy")


if __name__ == "__main__":
    main()
\`\`\`

**Important limitations:** This script checks structural consistency only. It does not query GitLab approvals, a registry, a scanner, Sigstore or Argo CD. Its \`scan_age_hours\` value is self-reported, and its approvals are untrusted strings. A production policy must calculate freshness from signed or trusted timestamps and verify all evidence against authoritative APIs.

### Step D — Unit tests

Create \`tests/test_policy.py\`:

\`\`\`python
import copy
import json
import unittest
from pathlib import Path
from policy.evaluate import evaluate


ROOT = Path(__file__).resolve().parents[1]
APPROVED = json.loads(
    (ROOT / "evidence/release-approved.json").read_text(encoding="utf-8")
)
POLICY = json.loads(
    (ROOT / "policy/environments.json").read_text(encoding="utf-8")
)


class PromotionPolicyTests(unittest.TestCase):
    def check_denied(self, changes, env="demo-prod"):
        record = copy.deepcopy(APPROVED)
        record.update(changes)
        self.assertTrue(evaluate(record, env, POLICY))

    def test_approved_prod(self):
        self.assertEqual(evaluate(APPROVED, "demo-prod", POLICY), [])

    def test_mutable_tag_denied(self):
        self.check_denied({"image": "registry.example.com/training/demo-app:latest"})

    def test_digest_mismatch_denied(self):
        self.check_denied({"promoted_digest": "sha256:" + "b" * 64})

    def test_untrusted_builder_denied(self):
        self.check_denied({"built_by_trusted_runner": False})

    def test_scan_failure_denied(self):
        self.check_denied({"scanner_succeeded": False})

    def test_stale_scan_denied(self):
        self.check_denied({"scan_age_hours": 13})

    def test_critical_vulnerability_denied(self):
        self.check_denied({"critical_findings": 1})

    def test_missing_signature_denied(self):
        self.check_denied({"signature_verified": False})

    def test_missing_provenance_denied(self):
        self.check_denied({"provenance_verified": False})

    def test_insufficient_approvals_denied(self):
        self.check_denied({"approvals": ["release-owner"]})

    def test_unknown_environment_denied(self):
        self.check_denied({}, env="demo-unknown")

    def test_invalid_scan_age_denied(self):
        self.check_denied({"scan_age_hours": "recent"})


if __name__ == "__main__":
    unittest.main()
\`\`\`

Create an empty \`policy/__init__.py\` if your environment requires it for import compatibility.

### Step E — Execute the lab

From the repository root:

\`\`\`bash
python -m unittest discover -s tests -v
python policy/evaluate.py evidence/release-approved.json demo-prod
python policy/evaluate.py evidence/release-denied.json demo-prod
\`\`\`

Expected: 12 unit tests pass; approved fixture exits 0; denied fixture exits 1 with multiple reasons.

**Do not** put the deliberately denied fixture as an unguarded step in a clean GitLab pipeline; test rejection through unit tests or a wrapper that asserts the nonzero result.

## 7. GitLab CI pipeline for the policy lab

Create \`.gitlab-ci.yml\`:

\`\`\`yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages: [validate, test, policy]

default:
  image: python:3.12-slim
  tags: [mr-validation]

syntax:
  stage: validate
  script:
    - python -m compileall -q policy tests

policy_tests:
  stage: test
  needs:
    - job: syntax
      artifacts: false
  script:
    - python -m unittest discover -s tests -v

promotion_policy_lab:
  stage: policy
  needs:
    - job: policy_tests
      artifacts: false
  script:
    - python policy/evaluate.py evidence/release-approved.json demo-prod
\`\`\`

This CI file demonstrates a deterministic **policy test**, not production promotion. It must not be interpreted as permission to deploy based on a JSON file supplied by the same MR.

## 8. Production promotion workflow

### Phase A — Build and record

1. Verify protected ref and reviewed source commit.
2. Build in an isolated, approved runner.
3. Publish once to an authorized registry repository.
4. Read the immutable digest back from the registry.
5. Capture builder identity, source commit and build invocation.
6. Attach a verified SBOM, vulnerability report, signature and provenance.

### Phase B — Validate trusted evidence

1. Retrieve scan results from the trusted scanner for that exact digest.
2. Check scan completeness, freshness, coverage and exception policy.
3. Verify signature using approved key or keyless identity constraints.
4. Verify provenance subject, trusted builder and source commit.
5. Validate registry retention and artifact availability.
6. Record a signed/controlled release decision.

### Phase C — Promote through GitOps

1. Open a reviewed GitOps MR changing the digest for \`demo-dev\`.
2. Confirm Argo CD health and smoke tests.
3. Promote the **same digest** to \`demo-test\`.
4. Confirm test acceptance and integration results.
5. Promote the **same digest** to \`demo-staging\`.
6. Confirm production-like health, capacity and readiness.
7. Require explicit production approval before \`demo-prod\`.
8. Verify post-deployment SLIs/SLOs and preserve audit evidence.

Never promote by rebuilding or using a mutable \`:latest\` tag.

## 9. GitOps manifest and Helm considerations

Example Kubernetes image reference:

\`\`\`yaml
containers:
  - name: demo-app
    image: registry.example.com/training/demo-app@sha256:<ACTUAL_VERIFIED_DIGEST>
\`\`\`

This is a **template fragment**. Replace the placeholder with a real digest before rendering or applying.

Example Helm values:

\`\`\`yaml
image:
  repository: registry.example.com/training/demo-app
  digest: sha256:<ACTUAL_VERIFIED_DIGEST>
\`\`\`

Example Helm template:

\`\`\`yaml
image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
\`\`\`

Validate the final rendered image string with \`helm template\`, and ensure the chart does not accidentally append a tag when a digest is supplied.

## 10. Negative acceptance exercises

| Scenario | Injection | Required behavior |
| --- | --- | --- |
| Mutable tag | Replace \`@sha256:...\` with \`:latest\` | DENY |
| Digest drift | Different \`promoted_digest\` | DENY |
| Untrusted build | Set trusted builder false | DENY |
| Missing scan | Set scanner success false | DENY |
| Stale scan | Exceed environment max age | DENY |
| Critical finding | Set critical count to 1 | DENY |
| Invalid signature | Set signature verified false | DENY |
| Invalid provenance | Set provenance verified false | DENY |
| Missing approvals | Remove production approver | DENY |
| Unknown environment | Use unconfigured namespace | DENY |
| Missing registry artifact | Simulate unavailable digest in a real integration test | Block release |
| Deleted rollback digest | Test retention in disposable repository | Block unsafe rollback |

The first ten are covered by unit tests. The last two require a separately authorized registry integration lab; do not claim they are validated by the synthetic policy script.

## 11. Registry incident runbook

### Incident: artifact unavailable during promotion

1. Record exact digest, repository and failing environment.
2. Inspect registry authentication, DNS, TLS and repository permissions.
3. Verify manifest/index existence and platform compatibility.
4. Check retention, garbage collection and replication events.
5. Stop promotion; do not silently substitute a different tag.
6. Restore the exact approved artifact from a trusted retained copy if available.
7. Reverify signature, provenance and vulnerability evidence.
8. Resume only through approved release workflow.

### Incident: compromised signing identity

1. Freeze promotion of affected artifacts.
2. Revoke/distrust the signer in policy.
3. Identify affected digests and deployed environments.
4. Investigate build runner, CI configuration and signer access logs.
5. Rebuild/re-attest in a trusted environment.
6. Restore a known-good digest under a currently trusted identity.
7. Verify admission, Argo CD and application health.

### Incident: vulnerability disclosed after release

1. Identify affected SBOM components and deployed digests.
2. Assess exploitability, exposure and severity.
3. Patch dependency/base image and rebuild a new digest.
4. Rescan, resign and verify provenance.
5. Promote through expedited approved GitOps workflow.
6. Preserve incident timeline and remediation evidence.

## 12. Observability and reliability indicators

| Metric | Purpose |
| --- | --- |
| Digest promotion consistency | Confirm one artifact across environments |
| Signed image coverage | Detect unsigned release artifacts |
| Verified provenance coverage | Detect missing/untrusted build evidence |
| Scan freshness | Detect outdated vulnerability decisions |
| Release policy rejection rate | Identify unsafe changes and policy drift |
| Approval lead time | Identify governance bottlenecks |
| Registry artifact availability | Protect deployment and rollback |
| Rollback digest retention | Measure recovery readiness |
| Post-promotion health failures | Detect unsafe releases |
| Release recovery time | Track operational effectiveness |

Use real observation windows, not invented SLO values. Separate legitimate security rejections from CI infrastructure outages.

## 13. Troubleshooting reference

| Symptom | Likely cause | Safe action |
| --- | --- | --- |
| Promotion policy rejects valid image | Evidence mismatch or stale scan | Verify authoritative digest and timestamps |
| Image scan clean but gate fails | Missing signature/provenance/approval | Repair missing evidence |
| Signature valid but source wrong | Weak provenance or wrong builder | Rebuild from trusted source |
| Tag points to unexpected image | Mutable tag overwrite | Deploy exact digest |
| ImagePullBackOff | Registry access or missing manifest | Check pod events and registry |
| Argo CD OutOfSync | Desired/live state drift | Inspect GitOps changes and sync policy |
| Admission rejects image | Untrusted signer or digest policy | Fix artifact/policy, not bypass |
| Rollback fails | Deleted artifact or invalid signer | Restore trusted retained digest |
| Policy tests pass but production bypass exists | Synthetic tests do not enforce real systems | Audit trusted integrations and permissions |
| Excessive exceptions | Poor governance or unpatched dependencies | Review owners, expiry and risk |

## 14. Governance checklist

- [ ] Protected GitLab branches and required approvals.
- [ ] CODEOWNERS for CI, Dockerfiles, Helm charts and GitOps manifests.
- [ ] Isolated trusted build/signing runner pools.
- [ ] Scoped, short-lived registry identities.
- [ ] Immutable digest references in deployments.
- [ ] Signature and provenance verification against approved identities.
- [ ] SBOM and vulnerability evidence tied to digest.
- [ ] Fail-closed policy on missing/stale/invalid evidence.
- [ ] Environment-specific promotion approvals.
- [ ] Admission controls verified in disposable namespace.
- [ ] Registry retention protects rollback artifacts.
- [ ] Audit evidence retained under approved policy.
- [ ] No production deployment rights in untrusted MR pipelines.

## 15. Acceptance checklist

- [ ] Training release policy parses approved and denied fixtures.
- [ ] All 12 unit tests pass.
- [ ] Mutable tag and digest mismatch are rejected.
- [ ] Untrusted builder and missing security gates are rejected.
- [ ] Scan freshness and severity gates are enforced.
- [ ] Production approval threshold is enforced.
- [ ] Synthetic evidence is explicitly distinguished from trusted production evidence.
- [ ] Registry governance model documented.
- [ ] Same-digest GitOps promotion design documented.
- [ ] Failure and recovery runbooks reviewed.
- [ ] No production credentials or cluster changes used.

## 16. Evidence worksheet

\`\`\`text
CHAPTER 024 — SECURE ARTIFACT PROMOTION AND REGISTRY GOVERNANCE
Date:
GitLab project:
Source commit:
Trusted builder identity:
Published image repository:
Published OCI digest:
SBOM reference:
Vulnerability scan reference and timestamp:
Signature verification:
Provenance verification:
Policy version:
Dev approval:
Test approval:
Staging approval:
Production approval:
Synthetic policy unit tests:
Negative tests:
Registry retention review:
Rollback digest:
Argo CD verification plan:
Reviewer:
Open risks / owners / due dates:
\`\`\`

## 17. Knowledge checks

1. Why is a verified signature not sufficient for release approval?
2. Why must vulnerability reports and attestations be bound to the same digest?
3. What is the operational difference between immutable tags and immutable digests?
4. Why should promotion update GitOps desired state rather than rebuild an image?
5. What makes self-reported release metadata insufficient for production enforcement?
6. Why must a rollback digest be retained and signed by a trusted identity?
7. How should approval and evidence freshness differ across environments?
8. Why do shared namespaces not provide complete production isolation?

## 18. Completion

**Pass:** You implement and test a fail-closed synthetic promotion policy, demonstrate negative gate enforcement, and document authoritative production evidence, registry governance, same-digest GitOps promotion and SRE recovery.

**Next: Chapter 025 — Enterprise Container Supply-Chain Security and Artifact Promotion Capstone**, completing Part 05.
