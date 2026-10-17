# Chapter 097 — Jenkins Enterprise Platform Deployment and CI/CD Integration Capstone

**Part 20 — Final Enterprise Jenkins Capstone**  
**Audience:** Jenkins SRE/DBRE, DevOps, Kubernetes platform engineers, security and release managers.  
**Prerequisites:** Chapter 096, Jenkins Pipeline, JCasC, Terraform/Ansible, Kubernetes/EKS/AKS, Python 3, Docker (optional).

## Mission

Implement a safe **staging-first enterprise Jenkins platform delivery workflow** that validates infrastructure, controller configuration, agent isolation, pipeline execution, artifact integrity, deployment approvals and rollback. This chapter supplies an executable **local-only integration simulation** plus production adaptation and acceptance gates. It does not deploy or modify a real Jenkins controller by itself.

## 1. Deployment architecture

```text
Protected Git branch / CODEOWNERS
              |
  CI: lint -> unit -> policy -> security
              |
    Terraform plan (read-only)
              |
       approval + change ticket
              |
 Terraform apply / Ansible / Helm
              |
    Jenkins controller + JCasC
              |
  Ephemeral Kubernetes build agents
              |
  Build -> test -> SBOM -> artifact digest
              |
  signed promotion + deployment approval
              |
      staging -> production
              |
  SLO gates -> rollback / RCA / COA
```

**Trust boundaries:** untrusted pull requests run only unprivileged validation without deployment credentials; protected release jobs receive short-lived, scoped identities after approval. Separate plan and apply permissions.

## 2. Repository layout

```text
jenkins-platform/
  terraform/
    modules/ controller/ agents/
  ansible/
    roles/jenkins-host/
  helm/
    values-staging.yaml
  casc/
    jenkins.yaml
  pipelines/
    Jenkinsfile
  scripts/
    validate_release.py
  policy/
    release.json
  tests/
    test_release.py
  evidence/
    staging-acceptance.md
  runbooks/
    rollback.md
```

Ownership: Terraform provisions infrastructure; Ansible configures host prerequisites; Helm deploys workloads; JCasC configures Jenkins; Pipeline-as-code orchestrates CI/CD. Do not allow competing tools to manage the same mutable resource.

## 3. Infrastructure deployment gates

1. Confirm environment/account/cluster identity and change ticket.
2. Pin Terraform providers/modules and lock remote state.
3. Run format, validate, static policy checks and **reviewed plan**.
4. Verify IAM least privilege, encryption, backup, network policy, quotas and capacity.
5. Obtain approval before apply; restrict apply to protected branch and trusted runner.
6. Validate controller health, JCasC reload and supported plugin/Java matrix.
7. Execute synthetic build/agent/artifact smoke tests.
8. Record rollback conditions, observed SLOs and evidence.

Never run `terraform apply -auto-approve` against production as part of an unreviewed example. Never place production secrets in Terraform outputs, CI logs or public repositories.

## 4. Jenkins controller and JCasC design

Illustrative configuration fragment (adapt to installed plugin schemas):

```yaml
jenkins:
  numExecutors: 0
  mode: EXCLUSIVE
  systemMessage: "Managed by GitOps/JCasC"
```

Validate JCasC using the exact Jenkins/plugin versions in staging. Plugin compatibility and JCasC export/import schemas vary; do not assume this fragment is a complete controller configuration.

## 5. Agent isolation and CI/CD stages

- Run build agents as ephemeral, non-root Kubernetes pods where possible.
- Apply namespace, service-account, network, CPU/memory and image policies.
- Use immutable image digests and signed base images for sensitive workflows.
- Keep SCM pull-request validation separate from release deployment agents.
- Publish immutable artifacts and verify digest before promotion.
- Generate SBOM and provenance with approved tooling; never invent signatures.
- Use manual or policy approval for production changes and auditable rollback.

## 6. Jenkinsfile reference (staging only)

```groovy
pipeline {
  agent { label 'trusted-staging' }
  options {
    timestamps()
    timeout(time: 20, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
  environment {
    DEPLOY_ENV = 'staging'
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Validate release contract') {
      steps { sh 'python3 scripts/validate_release.py policy/release.json' }
    }
    stage('Unit tests') {
      steps { sh 'python3 -m unittest discover -s tests -v' }
    }
    stage('Staging smoke test') {
      steps { echo 'Replace with approved Jenkins/agent/artifact integration checks' }
    }
    stage('Approval') {
      steps {
        input message: 'Approve staging acceptance review?', ok: 'Approve'
      }
    }
  }
  post {
    always { echo 'Archive nonsecret evidence in approved retention system' }
  }
}
```

This Jenkinsfile validates local fixtures and runs a placeholder smoke stage; it does **not** perform real deployments or prove a live staging system is healthy. Production promotion requires separate authenticated verification and controls.

## 7. Executable local release-policy validator

Create `policy/release.json`:

```json
{
  "environment": "staging",
  "protected_branch": true,
  "change_ticket": "CHG-EXAMPLE-097",
  "terraform_plan_reviewed": true,
  "state_locking": true,
  "least_privilege_identity": true,
  "untrusted_pr_deploy_secrets": false,
  "controller_executors": 0,
  "agent_isolation_verified": true,
  "artifact_digest_verified": true,
  "sbom_generated": true,
  "staging_smoke_passed": true,
  "slo_gate_passed": true,
  "rollback_documented": true,
  "approval_recorded": true
}
```

Create `scripts/validate_release.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_TRUE = (
    "protected_branch", "terraform_plan_reviewed", "state_locking",
    "least_privilege_identity", "agent_isolation_verified",
    "artifact_digest_verified", "sbom_generated", "staging_smoke_passed",
    "slo_gate_passed", "rollback_documented", "approval_recorded",
)

def validate(data):
    errors = []
    if data.get("environment") != "staging":
        errors.append("environment must be staging for this lab")
    ticket = data.get("change_ticket")
    if not isinstance(ticket, str) or not ticket.strip():
        errors.append("change_ticket missing")
    for key in REQUIRED_TRUE:
        if data.get(key) is not True:
            errors.append(f"{key} must be true")
    if data.get("untrusted_pr_deploy_secrets") is not False:
        errors.append("untrusted_pr_deploy_secrets must be false")
    if type(data.get("controller_executors")) is not int or data["controller_executors"] != 0:
        errors.append("controller_executors must equal zero")
    return errors

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    errors = validate(data)
    if errors:
        print("RELEASE DENIED", *errors, sep="\n")
        sys.exit(1)
    print("RELEASE CONTRACT ACCEPTED: synthetic fixture only")
```

```bash
python3 scripts/validate_release.py policy/release.json
```

## 8. Automated unit tests

Create `tests/test_release.py`:

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_release import validate

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / "policy/release.json").read_text())

    def test_valid(self):
        self.assertEqual(validate(self.base), [])

    def test_untrusted_secrets(self):
        self.base["untrusted_pr_deploy_secrets"] = True
        self.assertTrue(validate(self.base))

    def test_unreviewed_plan(self):
        self.base["terraform_plan_reviewed"] = False
        self.assertTrue(validate(self.base))

    def test_controller_executors(self):
        self.base["controller_executors"] = 2
        self.assertTrue(validate(self.base))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 9. Negative test

```bash
cp policy/release.json /tmp/jenkins-release-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-release-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["untrusted_pr_deploy_secrets"] = True
d["terraform_plan_reviewed"] = False
d["approval_recorded"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/validate_release.py /tmp/jenkins-release-unsafe.json; then
  echo "FAIL: unsafe release accepted"; exit 1
else
  echo "PASS: unsafe release denied"
fi
```

## 10. Production staging-to-release acceptance

| Gate | Evidence | Owner |
|---|---|---|
| IaC plan reviewed | immutable plan + approval | infra |
| Controller configured | JCasC validation + plugin inventory | platform |
| Agents isolated | namespace/RBAC/pod policy test | security |
| Pipeline executes | critical synthetic job logs | CI owner |
| Artifact verified | digest/SBOM/provenance | DevSecOps |
| SLO protected | queue/agent/API dashboard | SRE |
| Rollback ready | staging rollback drill | release owner |
| Change approved | ticket and reviewer | change manager |

Do not treat `approval_recorded: true` in a JSON fixture as an actual authorization.

## 11. Twenty-four hands-on exercises

1. Create architecture and service boundary.
2. Define repo layout and CODEOWNERS.
3. Pin Terraform provider/module versions.
4. Validate remote state and lock policy.
5. Review Terraform plan workflow.
6. Review Ansible host role idempotency.
7. Review Helm staging values and quotas.
8. Validate JCasC schema and plugin matrix.
9. Verify controller zero-executor policy.
10. Design isolated Kubernetes agent pods.
11. Review service-account and secret scopes.
12. Validate SCM webhook trust.
13. Implement branch protection and PR isolation.
14. Review build/test and dependency scanning.
15. Define SBOM and artifact provenance.
16. Define staging smoke tests.
17. Define queue and agent SLO gates.
18. Define release approval workflow.
19. Define rollback and restoration path.
20. Create release-policy JSON fixture.
21. Run validator and unit tests.
22. Run unsafe negative fixture.
23. Conduct staged deployment tabletop.
24. Score release readiness and sign off.

## 12. Twenty deployment failure scenarios

| # | Failure | Response |
|---|---|---|
| 01 | Terraform state lock conflict | inspect holder; never blind unlock |
| 02 | Wrong cloud account | abort |
| 03 | Unreviewed destructive plan | reject |
| 04 | IaC drift | reconcile ownership |
| 05 | Ansible non-idempotent | repair role |
| 06 | Helm rollout timeout | inspect events |
| 07 | JCasC schema mismatch | revert config |
| 08 | Unsupported plugin | compatibility matrix |
| 09 | Controller executes builds | stop and reconfigure |
| 10 | Agent Pending | quotas/node capacity |
| 11 | Privileged agent | security gate |
| 12 | PR accesses deployment token | revoke/rotate |
| 13 | SCM webhook spoofing | verify signature |
| 14 | Dependency scan high severity | risk review |
| 15 | SBOM absent | promotion block |
| 16 | Artifact digest mismatch | quarantine |
| 17 | Queue SLO regression | capacity rollback |
| 18 | Staging smoke fails | release stop |
| 19 | Approval missing | no-go |
| 20 | Rollback path broken | recovery incident |

## 13. Eight production runbooks

### A. IaC deployment failure
Stop applies, preserve plan/state/audit, identify partial resources, execute reviewed rollback and verify drift.

### B. Jenkins controller startup/JCasC failure
Check supported plugin/Java matrix, logs and configuration, revert tested JCasC and restore health.

### C. Agent provisioning outage
Inspect Kubernetes scheduling, image pulls, IAM/service account, quotas and network policy; protect critical jobs.

### D. SCM/credential compromise
Disable affected triggers, rotate/revoke credentials, preserve evidence and invoke security response.

### E. Artifact integrity failure
Block promotion, inspect digest/SBOM/provenance, rebuild from trusted source and verify signing policy.

### F. SLO regression after deployment
Compare baseline, error budget, queue and agent latency; halt rollout and revert approved change.

### G. Failed deployment approval
Stop promotion, identify missing approver/change ticket and re-enter approved workflow.

### H. Rollback/restore failure
Escalate incident, protect single-writer safety, use validated backup/restore and capture RCA/COA.

## 14. 100-point acceptance

| Domain | Points |
|---|---:|
| IaC deployment and state safety | 20 |
| Controller/JCasC/agent integration | 20 |
| Pipeline and artifact security | 20 |
| SLOs, smoke tests and release gates | 15 |
| Rollback, DR and change approval | 15 |
| Tests, evidence and sign-off | 10 |
| **Total** | **100** |

Suggested pass **85/100** plus mandatory gates: reviewed plan, correct environment, trusted identity, PR secret isolation, verified artifact, successful real staging smoke, rollback proof and actual approval. Synthetic checks alone are not sufficient.

## 15. Evidence template

```text
UTC / environment / account:
IaC plan and change approval:
JCasC/plugin/Java validation:
Controller and agent isolation:
SCM/PR trust and credentials:
Pipeline tests and artifact provenance:
SLO baseline and smoke tests:
Rollback/DR evidence:
24 exercises / 20 failures:
Score / mandatory gates / RCA / COA / reviewer:
```

**Companion:** [Chapter 097 hands-on lab](labs/097-jenkins-enterprise-platform-deployment-cicd-integration-capstone-check.md).  
**Next:** Chapter 098 — Jenkins Enterprise Failure Injection, Incident Recovery and Disaster Recovery Capstone.
