# Chapter 009 — GitLab Repository Security, Audit Events, Compliance and Secret Protection

**Part 02 — GitLab Repository Administration**  
**Chapter:** 009 of 100  
**Audience:** Platform Engineers, SREs, DevSecOps, GitLab Administrators  
**Reference architecture:** GitLab CI/CD → immutable image → approved GitOps change → Argo CD → Kubernetes  
**Lab:** Disposable private GitLab project `demo-app`, with no real secrets

> **Safety and privacy:** Never paste real credentials into source, job logs, examples, tickets, or this tutorial. All demonstrations use synthetic markers. Security features, audit event availability, and policy enforcement depend on GitLab version, edition, licensing, and administrator configuration; verify your actual deployment.

## 1. Learning objectives

After this chapter, you should be able to:

1. Build a repository security threat model across Git, GitLab, runners, tokens, artifacts, and GitOps.
2. Apply least privilege, protected branches, merge approvals, and controlled project visibility.
3. Understand secret scanning, push protection, dependency and container scanning, and their limitations.
4. Inventory audit events and establish evidence retention, escalation, and compliance ownership.
5. Define safe credential lifecycle and an incident response playbook for suspected leaks.
6. Perform a hands-on security verification lab without exposing real credentials.
7. Validate security controls using positive and negative tests.

## 2. Enterprise threat model

```text
Developer / service account
          |
          v
GitLab group + private project
          |
          +-- Identity, MFA, SSO, membership, access tokens
          |
          +-- Protected branch / MR / CODEOWNERS / CI gates
          |
          v
CI pipeline -- ephemeral isolated runner
          |          |
          |          +-- restricted variables and OIDC identity
          |          +-- artifacts / logs / cache protection
          |
          v
Trusted image build / scan / SBOM / signing [later chapters]
          |
          v
GitOps repository -- separate production approval
          |
          v
Argo CD AppProject / RBAC / sync policy
          |
          v
Shared Kubernetes cluster
   demo-dev | demo-test | demo-staging | demo-prod
```

**Critical boundary:** Namespace separation is logical, not equivalent to separate clusters. Restrict production GitOps and Kubernetes access independently from GitLab source permissions. CI pipelines should not possess unrestricted production Kubernetes credentials.

### Threats and controls

| Threat | Impact | Primary controls |
| --- | --- | --- |
| Stolen developer token | Unauthorized source changes | SSO/MFA, scoped tokens, expiration, revocation |
| Malicious MR pipeline | Secret exfiltration or supply-chain compromise | Untrusted runner isolation, no protected secrets |
| CI config modification | Bypass validation or run privileged code | CODEOWNERS, approval gates, protected refs |
| Accidental secret commit | Credential exposure in Git history | Secret detection, push protection, rotation |
| Overprivileged runner | Registry/cloud/Kubernetes compromise | Runner trust tiers, short-lived identity, least privilege |
| Leaked artifact or job log | Data/credential disclosure | Restricted access, redaction, retention |
| Unauthorized GitOps update | Production misdeployment | Protected paths, release approvals, Argo CD RBAC |
| Tampered dependency/image | Supply-chain compromise | Dependency pinning, scanning, SBOM, provenance, signatures |
| Missing audit retention | Incomplete investigation | Central export, retention policy, clock synchronization |

## 3. Repository hardening baseline

### Identity and access

- Prefer centrally managed SSO and MFA with joiner/mover/leaver processes.
- Review direct, inherited, and shared group/project membership.
- Restrict Owner and Maintainer roles and maintain a break-glass process.
- Use private project visibility for internal source and GitOps repositories.
- Inventory personal, group, project, deploy and CI job tokens.
- Apply least-privilege scopes, expiration, rotation, and audit for automation.
- Use OIDC workload identity for short-lived cloud credentials where supported.

### Change governance

- Protect `main` and release tags; disallow ordinary direct pushes and force pushes.
- Require passing MR pipelines, independent review, and effective CODEOWNERS approval.
- Restrict modifications to `.gitlab-ci.yml`, Dockerfiles, Helm templates, policy, and GitOps production paths.
- Review overlapping protected-branch rules for unexpectedly permissive outcomes.
- Ensure approval rules cannot be bypassed by unauthorized project maintainers or tokens.

### CI and runner security

- Treat fork/MR code as untrusted.
- Isolate untrusted and privileged runners, ideally with ephemeral executors.
- Never expose protected production secrets to untrusted pipeline code.
- Prevent privileged runner workloads from sharing unrestricted caches with untrusted jobs.
- Restrict outbound network access where practical and monitor abnormal exfiltration.
- Prefer pinned container images and dependencies for trusted builds.
- Keep runners patched and audit registration tokens, project assignment, and executor settings.

## 4. Secret protection: prevention, detection, response

### Prevention

1. Do not commit credentials to Git.
2. Use a secret manager and workload identity for production credentials.
3. Configure GitLab secret detection and, where available, push protection.
4. Use approved local pre-commit scanners as defense in depth.
5. Protect CI variables, including scope, masking and eligible refs.
6. Do not include secrets in job arguments, tracing, caches, artifacts, Docker layers, or test fixtures.

**Important:** Masking is a log-display control, not a confidentiality boundary. A job that can read a secret may deliberately transmit it. Secret scanners also have false negatives and cannot replace secure identity design.

### Detection

Possible signals:
- GitLab secret-detection finding.
- Push-protection rejection.
- Security dashboard finding.
- Audit event for token creation or permission change.
- Suspicious pipeline behavior or unusual registry/cloud API access.
- Secret detected in a public artifact or job trace.

### Response to a suspected leak

1. **Contain:** Disable or revoke exposed credentials immediately.
2. **Rotate:** Issue replacement credentials and update trusted consumers.
3. **Investigate:** Determine exposure scope (Git commits, forks, mirrors, artifacts, caches, logs, CI jobs).
4. **Eradicate:** Remove leaked material from current configuration and restrict access to retained copies.
5. **Recover:** Validate application access, redeploy/restart affected consumers if necessary, and monitor for abuse.
6. **Document:** Preserve incident evidence, timeline, approvals and follow-up actions.

**Do not assume deleting a Git commit eliminates exposure.** Clones, forks, mirrors, caches and logs may retain the secret. Credential revocation/rotation is the primary immediate control. History rewriting is exceptional, disruptive, and requires coordinated authorization.

## 5. Audit events and compliance evidence

### Events worth monitoring

| Event category | Example | Operational response |
| --- | --- | --- |
| Identity | User added to privileged group | Validate approval and business need |
| Repository | Branch/tag protection changed | Review for unauthorized bypass |
| Merge governance | Approval setting modified | Verify controls and audit change |
| Token lifecycle | Token created, rotated, revoked | Validate owner, scope, expiry |
| CI/CD | Runner or variable settings changed | Inspect privilege and secret exposure |
| Project governance | Visibility changed or project shared | Review data classification |
| GitOps | Production desired-state change merged | Correlate release approval and Argo CD sync |

GitLab's audit event coverage, retention and streaming capabilities vary by deployment and tier. Export available events to a centralized SIEM or log platform if your governance program requires longer retention. Validate ingestion, event timestamps, source identity and alert delivery.

### Minimum evidence package

For a production release or security-sensitive change, capture:
- MR URL, approvers, approval state and merge SHA.
- Pipeline ID, status, runner identity and relevant security results.
- Artifact digest, SBOM, provenance/signature where implemented.
- GitOps commit and environment path.
- Argo CD application revision, sync and health status.
- Change ticket or incident ID, release window and rollback evidence.
- Access or policy changes relevant to the event.

Retention periods should follow your organization's applicable legal, regulatory, contractual and incident-response policies; there is no universal GitLab retention duration.

## 6. Hands-on lab — safe repository security validation

### Prerequisites

- A disposable private GitLab project: `https://gitlab.example.com/training/demo-app`.
- Administrator/Maintainer authorized to configure training settings.
- Separate Developer and Reviewer test identities.
- Git CLI and a nonprivileged runner.
- No real cloud, registry, database, or Kubernetes credentials.

### Step A — Establish a safe repository

Create `README.md`:

```markdown
# demo-app

Disposable repository security lab. Never store real credentials here.
```

Create `CODEOWNERS`:

```text
/.gitlab-ci.yml  @platform-reviewers
/CODEOWNERS      @platform-reviewers
/security/       @security-reviewers
```

Replace placeholders with actual authorized training groups. Verify effective CODEOWNERS enforcement; a file alone does not create mandatory approval.

### Step B — Add a safe repository policy check

Create `security/check_repository.py`:

```python
from pathlib import Path

required = [Path("README.md"), Path("CODEOWNERS"), Path(".gitlab-ci.yml")]
missing = [str(p) for p in required if not p.is_file()]
if missing:
    raise SystemExit(f"FAIL: missing files: {missing}")

# Only synthetic forbidden training markers; never use real secret values.
for path in Path(".").rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    if path.suffix not in {".md", ".py", ".yml", ".yaml", ".txt"}:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    if "DEMO_FORBIDDEN_MARKER_123" in text:
        raise SystemExit(f"FAIL: synthetic forbidden marker found in {path}")

print("PASS: required files present and no forbidden lab marker")
```

**Scope note:** This is a narrow training policy check, **not** a production secret scanner. It cannot detect real credential formats or all file types. Use GitLab-supported secret detection/push protection and dedicated scanners for real deployments.

Create `.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate

repository_policy:
  stage: validate
  image: python:3.12-slim
  script:
    - python security/check_repository.py
```

### Step C — Commit and open an MR

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch009-security-controls
# Create files from Steps A and B with your editor
git add README.md CODEOWNERS .gitlab-ci.yml security/check_repository.py
git commit -m "security: add training repository policy check"
git push -u origin feature/ch009-security-controls
```

Open an MR, validate the pipeline and obtain the required independent review.

### Step D — Negative test: synthetic marker

Create a harmless file `security/lab-marker.txt` containing only:

```text
DEMO_FORBIDDEN_MARKER_123
```

Commit and push it to the feature branch. Expected: the `repository_policy` job fails, identifying the synthetic marker. Remove the file, commit, and push again. Expected: pipeline returns to green.

This demonstrates a custom CI check, not GitLab native push protection.

### Step E — Validate branch and approval controls

Using a separate nonprivileged test identity:

1. Attempt a direct push to protected `main`; it should be rejected.
2. Modify `.gitlab-ci.yml` through an MR; verify the designated code owner is required if supported.
3. Confirm an unapproved MR cannot merge.
4. Confirm the project remains private.
5. Inspect direct/inherited membership and runner permissions.

Do not attempt bypass tests in a production repository.

### Step F — Inspect native security features

In the training project, inspect the availability and effective configuration of:
- Secret detection and push protection.
- Dependency and container scanning.
- Security findings dashboards.
- Audit events and audit streaming.
- Token inventories and expiration settings.

**Record each as Enabled, Disabled, Unavailable, or Not Verified.** Do not claim that a capability is active solely because it appears in documentation.

### Step G — Audit evidence collection

Record:

```text
Project:
GitLab version / tier:
MR URL:
Pipeline URL / ID:
Policy negative-test result:
Branch push rejection:
Code-owner enforcement result:
Runner trust tier:
Secret detection status:
Audit event availability:
Token inventory review:
Reviewer:
Date:
```

### Step H — Cleanup

Remove the synthetic marker, merge or close the training MR, and delete only disposable branches/resources. Do not delete shared audit logs, runners, project groups or evidence under retention.

## 7. Enterprise operational runbooks

### Runbook A — Unexpected Maintainer access

1. Confirm effective membership, including inherited/shared groups.
2. Identify when and by whom access was granted.
3. Remove unauthorized access and revoke related tokens.
4. Review repository, CI/CD and GitOps changes during exposure.
5. Preserve audit evidence and escalate per incident severity.

### Runbook B — Suspected CI token abuse

1. Disable/revoke the token and stop affected privileged jobs.
2. Inspect pipeline source, commit SHA, job logs, runner identity and network access.
3. Rotate downstream credentials and verify cloud/registry activity.
4. Restore least-privilege scopes and trusted runner boundaries.
5. Document impact, detection gaps and prevention actions.

### Runbook C — Unauthorized production GitOps change

1. Preserve the GitOps commit, MR and Argo CD event history.
2. Assess active production health and incident severity.
3. Restore a previously approved digest/configuration through the authorized rollback process.
4. Investigate GitLab token, approval and Argo CD/Kubernetes permissions.
5. Confirm sync/health recovery and perform a post-incident review.

## 8. Troubleshooting matrix

| Symptom | Check | Corrective action |
| --- | --- | --- |
| Secret detection not running | GitLab tier, templates, rules, pipeline source | Configure supported scanner and verify execution |
| Push protection not blocking | Feature availability, settings, bypass policies | Enable and negative-test in training |
| CODEOWNERS ignored | File path, syntax, group access, enforcement tier | Fix rules and validate |
| Audit event missing | Event coverage, permissions, retention | Verify support and central export |
| Unexpected repo access | Inherited membership and project shares | Remove unauthorized access |
| Protected variable exposed | Pipeline source, protected ref, runner trust | Revoke/rotate and fix scope |
| Artifact contains sensitive data | Paths, logs, reports, retention | Revoke/rotate; restrict and remove exposed copies |
| GitOps changed without approval | Token scope, branch rules, merge policy | Restrict permissions and investigate |
| Scanner flags false positive | Detection evidence and context | Triage with documented exception process |

## 9. Production acceptance checklist

- [ ] Project and group access reviewed for least privilege.
- [ ] Protected branches/tags and approval policies tested.
- [ ] CODEOWNERS enforcement verified for sensitive paths.
- [ ] Untrusted CI jobs cannot access privileged secrets.
- [ ] Token inventory, expiration and rotation defined.
- [ ] Native secret detection and push protection status documented.
- [ ] Dependency/image scanning and supply-chain controls planned or active.
- [ ] Artifact, cache and job-log retention/access reviewed.
- [ ] Audit events are collected and retained according to policy.
- [ ] Security incident playbooks cover token leaks and unauthorized changes.
- [ ] Production GitOps approvals are separate from application code approval.
- [ ] Argo CD and Kubernetes RBAC enforce independent boundaries.
- [ ] All unavailable features and compensating controls are recorded.

## 10. Knowledge checks

1. Why is a masked CI variable not a sufficient defense against malicious pipeline code?
2. Why must exposed credentials be revoked even if a Git commit is removed?
3. Which evidence links a production deployment to an approved source change?
4. How can inherited GitLab group membership undermine a project security review?
5. Why must native scanner availability be verified against the deployed GitLab tier?
6. Which controls protect production when Dev/Test/Staging/Prod share a Kubernetes cluster?

## 11. Chapter completion

**Pass:** The disposable project enforces its documented branch/review controls; the synthetic marker is blocked by the training pipeline; effective token, runner, scanner and audit configurations are inventoried; and the team can explain credential incident response and production GitOps separation.

**Next: Chapter 010 — GitLab Repository Administration, Security and Governance Capstone.**
