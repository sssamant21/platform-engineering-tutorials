# Chapter 025 — Enterprise Container Supply-Chain Security and Artifact Promotion Capstone

**Part 05 — Final Capstone** | **Chapter 025 / 100**  
**Audience:** SRE, platform engineering, DevSecOps, CI/CD and release operations  
**Scope:** GitLab CI → secure OCI build → registry digest → SBOM and vulnerability scan → signing and provenance → policy gates → reviewed GitOps promotion  
**Reference environment:** Dev, Test, Staging and Production are separate namespaces in the **same** Kubernetes cluster, deployed by Helm and reconciled by separate Argo CD Applications. Labs do not deploy to production.

> **Safety:** All names are synthetic. Use disposable repositories and a test registry. Never use production signing keys, expose secrets in CI logs, give MR runners registry-write access, or bypass admission controls to make the lab pass. The self-contained offline policy exercise deliberately uses simulated evidence; it is **not** production-grade cryptographic verification.

## 1. Capstone mission

As the release-platform SRE, establish a traceable and enforceable supply-chain workflow that answers:

- Which source commit produced this artifact?
- Which isolated builder created it?
- Which registry manifest/index digest identifies the exact image?
- What components and vulnerabilities were present at scan time?
- Who signed the image and attested to its origin?
- Who approved each promotion?
- Is the **same** image digest deployed across environments?
- Can the team safely reject, quarantine and roll back a compromised release?

This capstone combines Chapters 021–024. It has an **offline runnable acceptance track** and an **optional authorized registry integration track**. Do not confuse a simulated pass with completion of the integration track.

## 2. Learning outcomes

1. Build a non-root multi-stage container image and validate its runtime.
2. Generate CycloneDX/SPDX SBOMs and vulnerability reports.
3. Sign an immutable image digest and verify signatures and attestations.
4. Apply explicit release gates with environment-specific approvals.
5. Produce a consistent digest promotion plan for four namespaces.
6. Run negative tests for tampering, missing evidence, stale scans and approval failures.
7. Investigate registry, builder, scanner, signer and GitOps failures.
8. Complete a documented operational readiness assessment with evidence.

## 3. End-to-end architecture

\`\`\`text
Developer / GitLab merge request
           |
           +--> lint / unit / integration / secret / dependency / SAST
           |             untrusted runner, no publishing rights
           |
      approved merge to protected main
           |
           v
       trusted build runner
           |
           +--> reviewed Dockerfile + pinned base image
           +--> build ONCE, publish OCI artifact
           |                       |
           |                registry@sha256:DIGEST
           |                       |
           +--> SBOM + scan -------+
           +--> signer + provenance
                                   |
                       independent verification
                                   |
                          release policy gate
                                   |
                         reviewed GitOps MR
                                   |
                  +----------------+----------------+
                  |                |                |
               demo-dev        demo-test       demo-staging
                  |                |                |
                  +----------------+----------------+
                                   |
                           production approval
                                   |
                                demo-prod
                                   |
                          health / SLO validation
\`\`\`

The promotion arrows are logical approval progression, not separate clusters. All four namespaces share cluster-level failure domains; use stronger isolation for production-critical workloads.

## 4. Deliverables

| Deliverable | Acceptance evidence |
| --- | --- |
| Secure OCI image | Dockerfile, image digest, runtime UID and health test |
| Registry record | Actual immutable digest and platform metadata |
| SBOM | CycloneDX and SPDX files bound to artifact |
| Vulnerability scan | Tool/database versions, findings and policy decision |
| Signature | Verified trusted signing identity |
| Provenance | Verified subject, source and trusted builder |
| Release manifest | Digest, source commit, evidence references |
| Promotion policy | Enforced gates, approvals and freshness |
| GitOps change | Reviewed digest-only environment change |
| Operations runbook | Failure triage, quarantine, rollback |
| Acceptance report | Negative tests, evidence and reviewer decision |

## 5. Capstone repository structure

\`\`\`text
demo-supply-chain/
├── .gitlab-ci.yml
├── Dockerfile
├── .dockerignore
├── README.md
├── src/
│   ├── __init__.py
│   └── server.py
├── tests/
│   ├── test_server.py
│   └── test_release.py
├── policy/
│   ├── __init__.py
│   ├── evaluate.py
│   └── environments.json
├── evidence/
│   ├── approved.json
│   └── rejected.json
├── scripts/
│   └── promotion_plan.py
└── docs/
    └── OPERATIONS-RUNBOOK.md
\`\`\`

Create empty \`src/__init__.py\` and \`policy/__init__.py\`.

## 6. Application and secure image

\`src/server.py\`:

\`\`\`python
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def response(path):
    if path == "/healthz":
        return 200, {"status": "ok"}
    return 404, {"error": "not found"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, body = response(self.path)
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
\`\`\`

\`tests/test_server.py\`:

\`\`\`python
import unittest
from src.server import response


class AppTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(response("/healthz"), (200, {"status": "ok"}))

    def test_missing(self):
        self.assertEqual(response("/missing")[0], 404)


if __name__ == "__main__":
    unittest.main()
\`\`\`

\`Dockerfile\`:

\`\`\`dockerfile
# syntax=docker/dockerfile:1
# Training tag only. Pin reviewed base digest for production.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY src/ src/
RUN python -m compileall -q src

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /build/src/ /app/src/
USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "src.server"]
\`\`\`

\`.dockerignore\`:

\`\`\`dockerignore
.git/
.gitlab-ci.yml
.env
*.key
*.pem
tests/
policy/
evidence/
scripts/
docs/
reports/
__pycache__/
\`\`\`

\`README.md\`:

\`\`\`markdown
# demo-supply-chain

Disposable Chapter 025 container supply-chain capstone.
Offline tests use synthetic evidence; real artifact verification is separate.
\`\`\`

### Local build and runtime verification

\`\`\`bash
python -m unittest discover -s tests -v
docker build --pull -t demo-app:ch025 .
docker image inspect demo-app:ch025 --format '{{.Config.User}}'
docker run --rm -d --name demo-app-ch025 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  -p 127.0.0.1:8080:8080 demo-app:ch025
curl --fail --silent http://127.0.0.1:8080/healthz
docker stop demo-app-ch025
\`\`\`

Expected: non-root UID \`65532:65532\`, healthy JSON response, no privileged container permissions.

## 7. Offline promotion policy: environment rules

\`policy/environments.json\`:

\`\`\`json
{
  "demo-dev": {"approvals": 1, "scan_max_age_hours": 72},
  "demo-test": {"approvals": 1, "scan_max_age_hours": 48},
  "demo-staging": {"approvals": 2, "scan_max_age_hours": 24},
  "demo-prod": {"approvals": 2, "scan_max_age_hours": 12}
}
\`\`\`

These thresholds are **lab assumptions**, not universally applicable release policy.

## 8. Offline release evidence

\`evidence/approved.json\`:

\`\`\`json
{
  "release_id": "demo-025",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "image": "registry.example.com/training/demo-app@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "image_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "trusted_builder": true,
  "tests_passed": true,
  "scan_completed": true,
  "scan_age_hours": 2,
  "critical_findings": 0,
  "high_findings": 0,
  "sbom_verified": true,
  "signature_verified": true,
  "provenance_verified": true,
  "source_verified": true,
  "approvals": ["release-owner", "operations-owner"]
}
\`\`\`

\`evidence/rejected.json\`:

\`\`\`json
{
  "release_id": "demo-025-bad",
  "source_commit": "not-a-commit",
  "image": "registry.example.com/training/demo-app:latest",
  "image_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "trusted_builder": false,
  "tests_passed": false,
  "scan_completed": false,
  "scan_age_hours": 999,
  "critical_findings": 1,
  "high_findings": 4,
  "sbom_verified": false,
  "signature_verified": false,
  "provenance_verified": false,
  "source_verified": false,
  "approvals": []
}
\`\`\`

**Critical trust limitation:** These JSON records are untrusted fixtures. A production release gate must fetch evidence from trusted registry, scanner, signing, GitLab approval and build APIs, verify its cryptographic/identity binding and calculate freshness from authoritative timestamps. No self-reported boolean is proof of a signature or trusted build.

## 9. Offline policy evaluator

\`policy/evaluate.py\`:

\`\`\`python
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^([^@\s]+)@(sha256:[0-9a-f]{64})$")
FLAGS = (
    "trusted_builder", "tests_passed", "scan_completed",
    "sbom_verified", "signature_verified", "provenance_verified",
    "source_verified",
)


def evaluate(evidence, env, policy):
    failures = []
    rules = policy.get(env)
    if rules is None:
        return [f"unknown environment: {env}"]
    if not isinstance(evidence, dict):
        return ["evidence must be a JSON object"]

    if not COMMIT.fullmatch(str(evidence.get("source_commit", ""))):
        failures.append("invalid source commit")

    image = str(evidence.get("image", ""))
    match = IMAGE.fullmatch(image)
    digest = str(evidence.get("image_digest", ""))
    if not match:
        failures.append("image is not pinned by sha256 digest")
    if not SHA.fullmatch(digest):
        failures.append("invalid image_digest")
    if match and match.group(2) != digest:
        failures.append("digest mismatch")

    for name in FLAGS:
        if evidence.get(name) is not True:
            failures.append(f"required evidence missing: {name}")

    age = evidence.get("scan_age_hours")
    if type(age) not in (int, float) or not 0 <= age <= rules["scan_max_age_hours"]:
        failures.append("scan too old or invalid")

    for name in ("critical_findings", "high_findings"):
        if type(evidence.get(name)) is not int or evidence[name] != 0:
            failures.append(f"disallowed {name}")

    approvals = evidence.get("approvals")
    if not isinstance(approvals, list) or any(
        not isinstance(item, str) or not item.strip() for item in approvals
    ):
        failures.append("invalid approval list")
    elif len(set(approvals)) < rules["approvals"]:
        failures.append("insufficient independent approvals")

    return failures


def load_policy():
    return json.loads(Path("policy/environments.json").read_text(encoding="utf-8"))


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python policy/evaluate.py <evidence.json> <namespace>")
    evidence = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    failures = evaluate(evidence, sys.argv[2], load_policy())
    if failures:
        for item in failures:
            print("DENY:", item)
        raise SystemExit(1)
    print("ALLOW: synthetic evidence satisfies training policy")


if __name__ == "__main__":
    main()
\`\`\`

## 10. Policy unit and failure-injection tests

\`tests/test_release.py\`:

\`\`\`python
import copy
import json
import unittest
from pathlib import Path
from policy.evaluate import evaluate, load_policy

ROOT = Path(__file__).resolve().parents[1]
GOOD = json.loads((ROOT / "evidence/approved.json").read_text(encoding="utf-8"))
BAD = json.loads((ROOT / "evidence/rejected.json").read_text(encoding="utf-8"))


class ReleasePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()

    def deny(self, **updates):
        record = copy.deepcopy(GOOD)
        record.update(updates)
        self.assertTrue(evaluate(record, "demo-prod", self.policy))

    def test_valid_release(self):
        self.assertEqual(evaluate(GOOD, "demo-prod", self.policy), [])

    def test_rejected_fixture(self):
        self.assertTrue(evaluate(BAD, "demo-prod", self.policy))

    def test_mutable_tag(self):
        self.deny(image="registry.example.com/training/demo-app:latest")

    def test_digest_mismatch(self):
        self.deny(image_digest="sha256:" + "b" * 64)

    def test_untrusted_builder(self):
        self.deny(trusted_builder=False)

    def test_missing_tests(self):
        self.deny(tests_passed=False)

    def test_scanner_error(self):
        self.deny(scan_completed=False)

    def test_stale_scan(self):
        self.deny(scan_age_hours=13)

    def test_critical_finding(self):
        self.deny(critical_findings=1)

    def test_missing_sbom(self):
        self.deny(sbom_verified=False)

    def test_invalid_signature(self):
        self.deny(signature_verified=False)

    def test_invalid_provenance(self):
        self.deny(provenance_verified=False)

    def test_unverified_source(self):
        self.deny(source_verified=False)

    def test_missing_approver(self):
        self.deny(approvals=["release-owner"])

    def test_unknown_environment(self):
        self.assertTrue(evaluate(GOOD, "demo-unknown", self.policy))

    def test_malformed_scan_age(self):
        self.deny(scan_age_hours="today")


if __name__ == "__main__":
    unittest.main()
\`\`\`

Execute:

\`\`\`bash
python -m unittest discover -s tests -v
python policy/evaluate.py evidence/approved.json demo-prod
python policy/evaluate.py evidence/rejected.json demo-prod
\`\`\`

Expected: **18 tests** pass (2 app tests + 16 release-policy tests); approved fixture exits 0; rejected fixture exits nonzero with multiple reasons.

For a clean CI pipeline, assert rejection within tests; do not run the rejected fixture as an unguarded success-path job.

## 11. Generate a digest-only promotion plan

\`scripts/promotion_plan.py\`:

\`\`\`python
import json
import sys
from pathlib import Path
from policy.evaluate import evaluate, load_policy

ENVS = ("demo-dev", "demo-test", "demo-staging", "demo-prod")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m scripts.promotion_plan <evidence.json>")

    evidence = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    policy = load_policy()
    for env in ENVS:
        failures = evaluate(evidence, env, policy)
        if failures:
            raise SystemExit(f"DENY {env}: {', '.join(failures)}")

    plan = {
        "image": evidence["image"],
        "source_commit": evidence["source_commit"],
        "environments": [
            {
                "namespace": env,
                "image": evidence["image"],
                "action": "open-reviewed-gitops-merge-request",
            }
            for env in ENVS
        ],
    }
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
\`\`\`

Run from the repository root:

\`\`\`bash
python -m scripts.promotion_plan evidence/approved.json
\`\`\`

Expected: a JSON plan for four namespaces, each referencing **exactly the same digest**. This is a planning artifact only; it does not create GitLab MRs, change Helm values, trigger Argo CD or approve production.

## 12. GitLab CI — offline acceptance pipeline

\`.gitlab-ci.yml\`:

\`\`\`yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages: [syntax, test, policy, evidence]

default:
  image: python:3.12-slim
  tags: [mr-validation]

syntax:
  stage: syntax
  script:
    - python -m compileall -q src tests policy scripts

unit_and_policy_tests:
  stage: test
  needs:
    - job: syntax
      artifacts: false
  script:
    - python -m unittest discover -s tests -v

synthetic_policy_gate:
  stage: policy
  needs:
    - job: unit_and_policy_tests
      artifacts: false
  script:
    - python policy/evaluate.py evidence/approved.json demo-prod

promotion_plan:
  stage: evidence
  needs:
    - job: synthetic_policy_gate
      artifacts: false
  script:
    - python -m scripts.promotion_plan evidence/approved.json > promotion-plan.json
  artifacts:
    paths:
      - promotion-plan.json
    expire_in: 7 days
\`\`\`

**Important:** This is a safe training pipeline. It does not build, scan, sign, publish or promote a real artifact. Its green result proves only that synthetic acceptance tests pass. A production pipeline requires independently governed trusted build/sign/scan integrations and enforcement outside contributor-controlled CI YAML.

## 13. Authorized integration track: build, scan, SBOM and sign

Complete this section only with an approved disposable registry and verified tool versions.

### Step A — Build and publish

\`\`\`bash
export IMAGE_REPO="registry.example.com/training/demo-app"
export IMAGE_TAG="ch025-$(git rev-parse --short=12 HEAD)"

docker build --pull -t "$IMAGE_REPO:$IMAGE_TAG" .
docker push "$IMAGE_REPO:$IMAGE_TAG"
docker buildx imagetools inspect "$IMAGE_REPO:$IMAGE_TAG"
\`\`\`

Replace the placeholder registry with your authorized endpoint. Record the **actual** digest returned by the registry; never derive a fake digest from the tag or source commit.

### Step B — Scan and generate SBOM

\`\`\`bash
mkdir -p reports
export IMAGE_DIGEST="sha256:<ACTUAL_REGISTRY_DIGEST>"
export IMAGE_REF="$IMAGE_REPO@$IMAGE_DIGEST"

trivy image --scanners vuln --format json \
  --output reports/trivy.json "$IMAGE_REF"
syft "$IMAGE_REF" -o cyclonedx-json=reports/sbom.cdx.json
syft "$IMAGE_REF" -o spdx-json=reports/sbom.spdx.json
\`\`\`

Record scanner version, advisory database age, findings and report hashes. A report upload does not itself enforce a release gate.

### Step C — Sign and verify the exact digest

Using a **disposable** signing key generated and secured as in Chapter 023:

\`\`\`bash
cosign sign --yes --key ./cosign.key "$IMAGE_REF"
cosign verify --key ./cosign.pub "$IMAGE_REF"
\`\`\`

For provenance, follow the version-specific attestation workflow from Chapter 023. Self-declared training provenance does not establish SLSA assurance. Production provenance should be generated by a trusted builder and verified for source, subject and builder identity.

### Step D — Real promotion authorization

Before a release decision, authoritative automation must:

1. Read the image digest from the registry.
2. Confirm scan target and SBOM subject match that digest.
3. Confirm scanner success, coverage and freshness.
4. Verify image signature with an approved signer.
5. Verify trusted-builder provenance and source commit.
6. Query actual GitLab MR approvals and protected-branch state.
7. Apply centrally enforced environment policy.
8. Open a reviewed GitOps MR changing only the intended digest.

Do **not** reuse \`evidence/approved.json\` as authoritative production evidence.

## 14. GitOps deployment model

Suggested GitOps tree:

\`\`\`text
gitops-repo/
├── charts/demo-app/
├── environments/
│   ├── dev/values.yaml
│   ├── test/values.yaml
│   ├── staging/values.yaml
│   └── prod/values.yaml
└── argocd/
    ├── demo-dev.yaml
    ├── demo-test.yaml
    ├── demo-staging.yaml
    └── demo-prod.yaml
\`\`\`

Example environment values:

\`\`\`yaml
image:
  repository: registry.example.com/training/demo-app
  digest: sha256:<ACTUAL_VERIFIED_DIGEST>
\`\`\`

Helm template:

\`\`\`yaml
image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
\`\`\`

These are **templates**; substitute a real verified digest before rendering. Each Argo CD Application targets its own namespace in the shared cluster. Production synchronization should follow explicit approvals and change governance.

## 15. Enterprise failure-injection matrix

| Test | Fault | Expected enforcement | Evidence |
| --- | --- | --- | --- |
| 1 | Mutable image tag | DENY | Policy test |
| 2 | Mismatched digest | DENY | Policy test |
| 3 | Untrusted builder | DENY | Policy test |
| 4 | Unit test failure | DENY | Policy test |
| 5 | Scanner execution failure | DENY | Policy test |
| 6 | Stale vulnerability scan | DENY | Policy test |
| 7 | Critical finding | DENY | Policy test |
| 8 | Missing SBOM | DENY | Policy test |
| 9 | Invalid signature | DENY | Policy test |
| 10 | Invalid provenance | DENY | Policy test |
| 11 | Wrong source commit | DENY | Policy test |
| 12 | Missing production approver | DENY | Policy test |
| 13 | Unknown environment | DENY | Policy test |
| 14 | Wrong Cosign public key | Verification failure | Optional registry lab |
| 15 | Unsigned digest | Verification failure | Optional registry lab |
| 16 | Registry digest deleted | Promotion/rollback blocked | Optional isolated registry test |
| 17 | Admission rejects image | Workload blocked | Optional disposable namespace |
| 18 | Argo CD desired/live drift | Detect and reconcile per policy | Optional GitOps lab |

Only Tests 1–13 are covered by the supplied offline policy unit tests. Tests 14–18 require authorized integration environments and must not be marked complete based on synthetic fixtures.

## 16. SRE incident simulation

**Scenario:** A previously approved image has a newly disclosed critical vulnerability. Simultaneously, the registry has garbage-collected an older rollback digest, and a signer identity is suspected compromised.

### Incident commander workflow

1. Record the active digest, environments and affected workloads.
2. Stop new promotions; preserve approved audit evidence.
3. Determine whether exploitation is active and whether containment is required.
4. Identify affected components using trusted SBOM and scanner evidence.
5. Distrust compromised signing identity in verification policy.
6. Check which known-good digests are still retained and signed by trusted identities.
7. Rebuild from reviewed source using patched dependencies and a trusted builder.
8. Scan, sign, attest and verify the new digest.
9. Promote through an approved emergency GitOps change.
10. Verify Argo CD health, readiness, error rates and latency.
11. Document restoration time, gaps in retention and corrective actions.

**Never** roll back to an unavailable or untrusted digest, or disable signature policy as a shortcut.

## 17. Operations runbook

Create \`docs/OPERATIONS-RUNBOOK.md\`:

\`\`\`markdown
# Container Supply-Chain Operations Runbook

## Triage
1. Identify commit, builder, image repository and immutable digest.
2. Verify trusted scan/SBOM/signature/provenance records for that digest.
3. Check registry reachability, permissions, retention and platform support.
4. Determine whether failure is a security rejection or CI infrastructure outage.
5. Inspect GitOps MR approval, Argo CD sync and application health.

## Containment
- Freeze promotion of suspicious artifacts.
- Quarantine compromised runners/signers and revoke affected credentials.
- Preserve nonsecret audit evidence.
- Do not bypass mandatory admission or signature policies.

## Recovery
1. Select a retained, approved and trusted digest or rebuild securely.
2. Reverify all release evidence.
3. Propose a reviewed GitOps digest change.
4. Confirm Argo CD reconciliation and workload SLOs.
5. Record timeline, RTO, root cause and follow-up actions.

## Escalation
Security: signer compromise, suspected malicious image, secret exposure.
Platform: registry outage, build runner compromise, admission policy failure.
Release owner: failed promotion, approval dispute, rollback decision.
\`\`\`

## 18. Operational reliability metrics

| Signal | What to measure |
| --- | --- |
| Build-to-publish duration | p50/p95 by runner pool |
| Registry digest availability | Successful pull/inspect for approved artifacts |
| Scan and SBOM coverage | Verified artifacts / published artifacts |
| Scan freshness | Time since trusted advisory database update |
| Signed artifact coverage | Valid signatures / release candidates |
| Trusted provenance coverage | Verified builder attestations / candidates |
| Promotion lead time | Approval to healthy deployment |
| Failed promotion rate | Security vs infrastructure vs application failures |
| Rollback readiness | Retained known-good digests with valid evidence |
| Recovery time | Detection to restored SLOs |

Use measured baselines before setting numeric SLOs. Shared-cluster namespace isolation does not remove cluster-wide reliability risks.

## 19. Acceptance scoring

| Category | Points |
| --- | ---: |
| Secure image build and runtime | 15 |
| SBOM and vulnerability scanning | 15 |
| Signature and provenance verification | 15 |
| Release policy and negative tests | 20 |
| Digest-consistent GitOps promotion design | 10 |
| Registry retention and rollback | 10 |
| Operational runbook and incident response | 10 |
| Evidence and reviewer sign-off | 5 |
| **Total** | **100** |

**Offline lab completion:** All 18 local unit tests pass, the approved synthetic fixture is accepted, the rejected fixture is denied, and a four-environment same-digest promotion plan is generated. This qualifies as **Offline Policy Lab Complete**, not production release readiness.

**Full capstone completion:** At least 85/100 **and** all critical controls are demonstrated against real authorized artifacts: non-root runtime, verified image digest, real SBOM/scan coverage, trusted signature/provenance verification, protected publishing identities, enforceable release authorization and rollback availability. Failure of any critical control means **Not Ready**, regardless of score.

## 20. Evidence worksheet

\`\`\`text
CHAPTER 025 — ENTERPRISE SUPPLY-CHAIN CAPSTONE
Date:
GitLab project and MR:
Protected source commit:
Trusted build runner and identity:
Base image reference:
Published image repository:
Actual OCI manifest/index digest:
Supported platforms:
Runtime UID and health check:
Trivy version / DB timestamp / report:
Syft version / CycloneDX / SPDX:
Signature signer / verification result:
Provenance subject / trusted builder:
Production policy version:
Offline unit tests:
Negative integration tests:
Dev GitOps MR and digest:
Test GitOps MR and digest:
Staging GitOps MR and digest:
Production GitOps MR and digest:
Argo CD application health:
Registry retention and rollback digest:
Incident drill / recovery time:
Reviewer:
Decision: Offline Lab Complete / Full Capstone Ready / Not Ready
Risks / owners / due dates:
\`\`\`

## 21. Knowledge checks

1. Why must promotion use a single immutable image digest?
2. Why is a self-reported \`signature_verified\` boolean not sufficient for production?
3. What is the difference between a signature, an SBOM and provenance?
4. How should a pipeline behave when the scanner database cannot be updated?
5. Why must production approvers be verified against GitLab's authoritative approval state?
6. What happens if a rollback digest is garbage-collected?
7. Why can a valid signature become untrusted after signer compromise?
8. What additional isolation may be needed beyond namespaces for critical production workloads?

## 22. Part 05 completion

Chapters 021–025 establish the enterprise container supply-chain foundation: secure builds, registries and digests, scanning and SBOMs, signatures and provenance, release policies, and an end-to-end operational acceptance exercise.

**Next: Chapter 026 — Kubernetes Deployment Fundamentals for GitLab CI/CD and GitOps**, beginning Part 06 — Kubernetes Deployment Fundamentals.
