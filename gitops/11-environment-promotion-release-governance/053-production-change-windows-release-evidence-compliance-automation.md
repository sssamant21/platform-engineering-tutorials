# Chapter 053 — Production Change Windows, Release Evidence and Compliance Automation

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 11:** Environment Promotion and Release Governance  
**Chapter:** 053 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Release Managers, Security and Compliance Teams

> **Safety:** All labs use a production-simulation environment, not customer-serving workloads. Treat change windows as a governance control, not as a substitute for automated technical enforcement. Never expose credentials, raw Secret values, customer data or sensitive audit logs in pipeline artifacts.

## 1. Learning objectives

By completing this chapter, you will be able to:

1. Design standard, normal and emergency production change workflows.
2. Enforce approved deployment windows and release freezes without bypassing GitOps.
3. Integrate GitLab CI/CD release gates, protected branches and approval evidence.
4. Understand the difference between GitLab deployment approvals and Argo CD reconciliation.
5. Build a verifiable release evidence package from GitLab, artifact registry, Argo CD and Kubernetes.
6. Automate preflight and post-deployment compliance checks.
7. Operate emergency changes, failed releases and audit-evidence recovery.
8. Validate governance using reproducible staging labs and acceptance criteria.

## 2. Architecture and trust boundaries

~~~text
Change request / approved window / risk assessment
                       |
                       v
GitLab MR -> tests -> scan -> protected branch approvals
                       |
                       v
           GitOps promotion commit
                       |
                Argo CD controller
                       |
          Kubernetes target environment
                       |
          health + revision + image digest
                       |
             evidence collector
                       |
         immutable/controlled audit store
~~~

**Critical distinction:** GitLab protected environments and deployment approvals gate GitLab deployment jobs when configured and supported. They do **not automatically prevent Argo CD auto-sync** from deploying a merged GitOps commit. For a genuine change-window gate, the system must control the effective action: permission to merge the production GitOps change, a manual Argo CD sync, or another explicitly enforced promotion controller.

An approval comment, calendar entry or pipeline variable alone is not an enforceable boundary.

## 3. Change categories and policy

| Category | Example | Review and scheduling |
| --- | --- | --- |
| Standard | Repeated low-risk, preapproved maintenance | Documented template, automated tests, predefined eligibility |
| Normal | New service version or configuration change | Risk assessment, approvals, scheduled window |
| Emergency | Security fix or outage mitigation | Authorized incident/change commander, documented exception, retrospective review |

Do not use emergency classification to bypass basic identity, logging, artifact integrity or rollback checks. Define who may invoke emergency changes, how approval is recorded, and when retrospective review is due.

## 4. Change record contract

Store a non-sensitive, machine-readable release manifest alongside the promotion MR.

~~~yaml
apiVersion: platform.example/v1
kind: ChangeRecord
metadata:
  name: demo-web-release-053
spec:
  changeId: CHG-053
  classification: normal
  application: demo-web
  environment: prod-sim
  sourceCommit: REPLACE_WITH_FULL_GIT_SHA
  gitopsCommit: REPLACE_WITH_FULL_GIT_SHA
  imageDigest: sha256:REPLACE_WITH_64_LOWERCASE_HEX
  plannedWindow:
    startsAt: "2026-10-20T22:00:00Z"
    endsAt: "2026-10-20T23:00:00Z"
  requiredChecks:
    - tests
    - artifact-verification
    - manifest-policy
    - staging-health
    - independent-approval
  rollback:
    previousDigest: sha256:REPLACE_WITH_PREVIOUS_64_HEX
    runbook: runbooks/demo-web-rollback.md
~~~

This is a **repository data document**, not a Kubernetes resource. Validate it using a schema and a CI policy; do not run kubectl apply on it. Times are illustrative UTC examples, not an actual scheduled production window.

Avoid storing secret tokens, full unredacted cluster configuration, or sensitive incident details in the record.

## 5. Production change window rules

A reliable window gate must answer:

- Is the current time inside an approved window?
- Is the change record approved, unexpired and for the correct environment?
- Are the source commit, image digest and GitOps revision the approved values?
- Is the release blocked by an active freeze, incident or dependency failure?
- Is the operator authorized to perform this class of change?
- Is the rollback or forward-recovery plan still valid?

Use UTC internally. Treat daylight-saving transitions explicitly when humans specify local times. Compare timestamps with a trusted service clock, not a user-editable pipeline variable.

### Example window validator

The following Python standard-library script is runnable as a standalone guard for **fixed UTC values supplied by a trusted workflow**. A real release system must retrieve the approved window from a protected change-management source and verify its authorization.

~~~python
#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone

def parse_utc(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return dt.astimezone(timezone.utc)

parser = argparse.ArgumentParser()
parser.add_argument("--start", required=True)
parser.add_argument("--end", required=True)
args = parser.parse_args()

start = parse_utc(args.start)
end = parse_utc(args.end)
now = datetime.now(timezone.utc)

if end <= start:
    raise SystemExit("DENIED: invalid change window")
if not start <= now < end:
    raise SystemExit("DENIED: outside approved change window")
print("WINDOW_VALID: time check passed; approvals must be checked separately")
~~~

~~~bash
python3 ci/check_window.py \
  --start "2026-10-20T22:00:00Z" \
  --end "2026-10-20T23:00:00Z"
~~~

The sample returns nonzero outside that historical/example window. This validates time only; it does **not** prove an approved change exists. Do not let arbitrary pipeline callers supply their own approval timestamps.

## 6. Enforceable GitLab release design

Use the following layers together:

1. Protected GitOps production branch and production overlay ownership.
2. Required merge-request approvals, pipeline success and CODEOWNERS enforcement.
3. A policy job that validates the approved change record, freeze status and artifact digest.
4. A release process that prevents production desired-state merge outside the authorized window.
5. Argo CD production AppProject restrictions and appropriately scoped sync permissions.
6. Kubernetes admission rules as independent safeguards.
7. Central audit logging for merge, sync and API mutations.

**Important:** If a production Application auto-syncs on merge, the protected **merge** must be held until the approved window. If production uses manual sync, the sync operator must check the approved window and approvals at execution time; a CI job that passes earlier cannot be treated as a permanent authorization.

### GitLab pipeline skeleton

~~~yaml
stages: [validate, evidence, release]

validate_change:
  stage: validate
  image: python:3.12-slim
  script:
    - python3 ci/validate_change_record.py changes/change.yaml
    - python3 ci/check_release_policy.py changes/change.yaml
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

collect_preflight_evidence:
  stage: evidence
  image: registry.example.internal/ci/audit-tools:PINNED_VERSION
  script:
    - ./ci/collect_preflight.sh
  artifacts:
    paths:
      - evidence/preflight.json
    expire_in: 7 days
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

release_prod_sim:
  stage: release
  image: registry.example.internal/ci/release-tools:PINNED_VERSION
  resource_group: prod-sim-release
  environment:
    name: prod-sim
  when: manual
  allow_failure: false
  script:
    - ./ci/verify_approved_window_and_change.sh
    - ./ci/verify_deployed_revision.sh
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

The scripts and internal images are **interfaces to implement**, not GitLab built-ins. In particular, the manual release job shown does not gate Argo CD auto-sync. Choose and enforce the actual production control boundary separately. Protected environment deployment approvals depend on GitLab tier/version and configuration.

## 7. Freeze calendar and exceptions

Maintain a controlled calendar for blackout periods such as major business events, financial close, migration freezes and high-traffic windows.

Suggested policy:
- Normal changes are denied during a freeze.
- Standard changes follow explicitly documented freeze exemptions, if any.
- Emergency changes require a separate authorized incident workflow.
- A freeze override records the approving authority, reason, scope and expiry.
- CI and promotion controllers query a protected authoritative source rather than a developer-controlled file alone.

A freeze rule must be evaluated **again immediately before the effective production action**, not just when the MR was created.

## 8. Release evidence model

| Evidence source | Required fields | Purpose |
| --- | --- | --- |
| GitLab source repository | Source commit, author, pipeline | Prove what was built |
| Container registry | Digest, signature/provenance, SBOM reference | Prove artifact identity |
| GitOps repository | MR, reviewers, approved commit | Prove desired-state authorization |
| Change system | Change ID, classification, window, approval | Prove scheduling/governance |
| Argo CD | Application, sync operation, revision, result | Prove reconciliation action |
| Kubernetes | Workload image digest, readiness, audit event | Prove observed deployment |
| Monitoring | Smoke tests, SLO signals, rollback status | Prove operational outcome |

**Evidence integrity:** Preserve timestamps, source IDs and hashes. Use access-controlled, retention-governed storage with immutability or tamper-evident controls appropriate to the compliance requirements. An ordinary mutable CI artifact is not, by itself, an immutable audit archive.

## 9. Evidence manifest and hashing

Example non-secret JSON record:

~~~json
{
  "schema_version": "1",
  "change_id": "CHG-053",
  "environment": "prod-sim",
  "application": "demo-web",
  "source_commit": "REPLACE_WITH_GIT_SHA",
  "gitops_revision": "REPLACE_WITH_GIT_SHA",
  "image_digest": "sha256:REPLACE_WITH_REAL_DIGEST",
  "approval_reference": "REPLACE_WITH_MR_URL",
  "sync_status": "Synced",
  "health_status": "Healthy",
  "evidence_collected_at": "2026-10-20T22:30:00Z"
}
~~~

~~~bash
jq -S . evidence/release.json > evidence/release.canonical.json
sha256sum evidence/release.canonical.json > evidence/release.sha256
~~~

A SHA-256 checksum detects changes **only if the reference checksum is stored in a separately trusted location**. It does not prove who created the evidence. Use authenticated upload, signed attestations and retention controls as required.

## 10. Preflight validation

Before a production-simulation release:

~~~bash
kubectl config current-context
argocd app get demo-prod-sim --refresh
argocd app diff demo-prod-sim
argocd app history demo-prod-sim
kubectl --context PROD_SIM_CONTEXT -n demo-prod get deploy,pods
~~~

Confirm:
1. Correct cluster, namespace and Application.
2. Approved source/GitOps revision and immutable image digest.
3. Staging tests and SLO checks passed.
4. No unresolved critical vulnerability or policy rejection.
5. Change window is currently open and no freeze is active.
6. Rollback plan, owner and on-call contacts are available.
7. No conflicting promotion is in progress.

Avoid storing full rendered manifests when they may contain secret material; retain redacted summaries or approved hashes.

## 11. Lab A — Change-window allow/deny tests

**Goal:** verify a policy guard denies changes outside a window.

1. Save the Python validator from Section 5 to ci/check_window.py.
2. Test a window that ended in the past.
3. Test a window that starts in the future.
4. Generate a temporary window containing the current UTC time for a **local test only**.
5. Confirm invalid and timezone-less timestamps are rejected.
6. Document that this time check is not equivalent to approval verification.

~~~bash
python3 ci/check_window.py \
  --start "2025-01-01T00:00:00Z" \
  --end "2025-01-01T01:00:00Z"
~~~

**Pass:** past/future windows deny, valid current test window allows, malformed input denies. A trusted change-record lookup remains required for real deployments.

## 12. Lab B — Approval and freeze enforcement

In a disposable GitLab project:

1. Protect the GitOps default branch.
2. Require production-simulation CODEOWNERS and independent MR approvals.
3. Attempt a direct push with a developer identity.
4. Attempt a merge without the required approvals.
5. Mark a test freeze active in the authoritative lab policy source.
6. Confirm the release controller refuses the production-simulation action.
7. Remove the freeze using an approved administrative action and revalidate.

**Pass:** direct pushes, unapproved merges and frozen releases are blocked and auditable. Do not use an administrator token to simulate a normal developer.

## 13. Lab C — Collect end-to-end release evidence

Use a harmless test application already deployed through Argo CD.

~~~bash
argocd app get demo-prod-sim --refresh
argocd app history demo-prod-sim
kubectl --context PROD_SIM_CONTEXT -n demo-prod \
  get deployment demo-web \
  -o jsonpath='{.spec.template.spec.containers[*].image}{"\n"}'
kubectl --context PROD_SIM_CONTEXT -n demo-prod \
  rollout status deployment/demo-web --timeout=180s
~~~

Compare the observed image reference against the approved digest. Collect the GitLab MR ID, reviewers, GitOps commit, Argo CD sync revision and rollout result into a **redacted** evidence record.

**Pass:** evidence links the approved change to the actual workload image and post-deployment health, with no tokens or Secret values.

## 14. Lab D — Simulate evidence loss and recovery

1. Generate a redacted release evidence manifest.
2. Store a trusted checksum in a separate controlled test location.
3. Modify the local evidence file.
4. Confirm checksum verification fails.
5. Recover the original record from the controlled test archive.
6. Confirm the checksum passes and audit metadata remains intact.

~~~bash
sha256sum evidence/release.canonical.json
sha256sum -c evidence/release.sha256
~~~

**Pass:** tampering is detected and an independently preserved copy can be recovered. A checksum without independent trust does not satisfy the control.

## 15. Lab E — Emergency change tabletop

**Scenario:** A severe staging-simulation vulnerability requires immediate remediation during a freeze.

1. Open an emergency change record with incident reference.
2. Identify authorized emergency approver and incident commander.
3. Confirm artifact integrity, blast radius and rollback owner.
4. Record the freeze exception with expiry and scope.
5. Promote the approved digest through the protected GitOps path.
6. Validate application health and monitor for regressions.
7. Perform retrospective review and remove temporary permissions.

**Pass:** the exception is narrow, time-bound, logged and independently reviewed after resolution. No permanent admin privilege is introduced.

## 16. Compliance automation design

A reliable compliance pipeline checks **policy as code** rather than relying solely on manual checklists.

Suggested checks:
- Change record schema and required fields.
- Allowed environment and approved release classification.
- Artifact digest format and provenance.
- Protected GitOps path and CODEOWNERS approval state.
- Freeze/window authorization from a trusted source.
- AppProject source/destination and Kubernetes admission policy.
- Expected Git revision and deployed digest.
- Redacted evidence package completeness.
- Required reviewer sign-off and retention destination.

Use OPA/Conftest, a schema validator or another approved policy engine. CI checks are advisory if privileged users can bypass the enforcement path; regularly test negative cases.

## 17. Monitoring and alerting

| Detection | Source | Response |
| --- | --- | --- |
| Production sync outside window | Argo CD event + change calendar | Security/release review |
| GitOps branch protection changed | GitLab audit | Investigate and restore policy |
| Missing deployment evidence | Evidence pipeline | Hold release closure |
| Unapproved digest deployed | Kubernetes workload vs release record | Stop promotion, investigate |
| Emergency override not expired | Change system | Revoke exception |
| Repeated approval failures | GitLab audit | Investigate permissions or abuse |
| Argo CD OutOfSync after approved merge | Argo CD status | Diagnose reconciliation |
| Post-release SLO regression | Metrics/APM | Roll back or mitigate |

Define alerts to distinguish planned emergency changes from suspicious activity; do not suppress evidence collection during incidents.

## 18. Ten troubleshooting scenarios

| # | Symptom | Likely cause | Resolution |
| --- | --- | --- | --- |
| 1 | Release denied during valid window | Clock/timezone or policy lookup | Verify UTC conversion and approved record |
| 2 | Release allowed during freeze | Gate checked only at MR creation | Recheck at effective deployment action |
| 3 | Deployment occurred before approval | Argo CD auto-sync after merge | Move gate to protected merge or controlled sync |
| 4 | GitLab approvals appear missing | Tier/settings/CODEOWNERS configuration | Validate enforcement with negative test |
| 5 | CI evidence artifact missing | Expiry or failed upload | Restore from controlled audit archive |
| 6 | Checksum mismatch | File changed or noncanonical serialization | Compare trusted hash and recover original |
| 7 | Argo CD Synced but wrong image | Incorrect source/digest record | Compare desired and observed workload digests |
| 8 | Change window expired mid-release | Long-running rollout | Apply documented continuation/abort policy |
| 9 | Emergency override remains active | Missing expiry/revocation automation | Revoke and audit scope |
| 10 | Audit shows sync but no actor | Identity/correlation gap | Correlate IdP, Argo CD, GitLab and K8s audit |

## 19. Production runbook — scheduled release

**T-60 minutes:** confirm owner, change approval, freeze status, artifact integrity, staging evidence, monitoring and rollback readiness.

**At window start:** revalidate approval and window against the trusted source; permit the protected GitOps merge or authorized manual sync; record the exact action time and actor.

**During rollout:** watch Argo CD revision, Kubernetes readiness, application smoke tests and error/latency metrics. Pause subsequent promotions on regression.

**At completion:** verify observed image digest, release revision, health and SLOs; collect redacted evidence; archive with retention controls; close the change only after validation.

## 20. Production runbook — unauthorized or out-of-window release

1. Declare the incident and identify the affected application/cluster.
2. Preserve GitLab, Argo CD, Kubernetes and identity audit evidence.
3. Determine whether the release is still progressing and whether customers are affected.
4. Stop subsequent promotions using approved controls; avoid broad control-plane disruption.
5. Validate the actual deployed digest and Git revision.
6. Restore reviewed known-good state if necessary and safe.
7. Revoke compromised credentials or overrides using the identity owner.
8. Repair the missing enforcement boundary and add a regression test.
9. Record root cause, detection gap, incident owner and follow-up deadline.

Do not delete audit logs, blindly disable Argo CD or assume reverting Git also reverses external data migrations.

## 21. Rollback and cleanup

For application rollback, revert the approved GitOps promotion to a previously tested digest, reconcile and verify readiness. For policy rollback, restore the last reviewed approval/window configuration without enabling broad bypasses. Database migrations and external side effects require separate recovery plans.

After labs, remove temporary test change records, freeze overrides and disposable GitLab branches. Preserve redacted evidence under the agreed retention policy. Do not remove shared production resources.

## 22. Acceptance criteria

- [ ] Change classifications, approvers and escalation paths are documented.
- [ ] Change windows and freezes are checked at the effective deployment boundary.
- [ ] GitLab protected branches and required approvals are enforced.
- [ ] Argo CD auto-sync cannot bypass the intended release governance.
- [ ] Approved source, GitOps revision and immutable image digest are linked.
- [ ] Staging validation and production-simulation health checks pass.
- [ ] Emergency override is time-bound, scoped and auditable.
- [ ] Evidence includes change ID, approvals, actor, revision and observed digest.
- [ ] Evidence archive has appropriate access, integrity and retention controls.
- [ ] Unauthorized and out-of-window negative tests are denied.
- [ ] Incident, rollback and evidence-recovery runbooks are tested.
- [ ] Security, release and platform owners sign off.

## 23. Knowledge check

1. Why does a GitLab deployment approval not automatically gate Argo CD auto-sync?
2. Where should a change-window check occur for an auto-sync production Application?
3. Why is a pipeline-supplied timestamp not proof of approval?
4. What distinguishes a standard change from an emergency change?
5. How can a checksum support evidence integrity, and what are its limits?
6. Which sources establish that an approved digest actually ran in Kubernetes?
7. What should happen when a deployment continues beyond its window?
8. Why should evidence be retained outside ordinary short-lived CI artifacts?

## 24. References

- [GitLab Protected Branches](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [GitLab Merge Request Approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
- [GitLab Protected Environments](https://docs.gitlab.com/ci/environments/protected_environments/)
- [GitLab Deployment Approvals](https://docs.gitlab.com/ci/environments/deployment_approvals/)
- [GitLab Job Artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
- [Kubernetes Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)

---

**Chapter 053 complete.** Next: **Chapter 054 — GitOps Release Rollback, Disaster Recovery and Deployment Safety Controls**.
