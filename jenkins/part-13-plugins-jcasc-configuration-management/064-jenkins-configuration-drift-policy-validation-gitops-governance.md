# Chapter 064 — Jenkins Configuration Drift Detection, Policy Validation and GitOps Governance

**Part 13 — Plugins, JCasC and Configuration Management**  
**Audience:** Jenkins SRE, platform engineering, security, compliance and change management  
**Prerequisites:** Chapters 061–063, Git-managed JCasC and Job DSL, immutable plugin baseline, isolated test controller.

## Learning outcomes

Detect divergence between approved Git state and running Jenkins; enforce policy before controller changes; implement review, promotion and reconciliation; distinguish intentional emergency changes from unauthorized drift; build audit-ready evidence and recover safely.

## 1. Governance architecture

```text
Protected Git (JCasC + plugins + Job DSL)
           |
   PR / CODEOWNERS / policy tests
           |
   Immutable controller build
           |
   Staging acceptance and approval
           |
   Production deployment
           |
  Observed Jenkins state + audit logs
           |
   Drift report → triage → approved reconciliation
```

Jenkins is not a native GitOps reconciler. JCasC, Job DSL and plugin manifests cover different portions of its configuration. Effective-state comparisons require plugin-aware normalization and must not assume every UI setting can be round-tripped.

## 2. Sources of truth

| Domain | Desired state | Observed state | Caveat |
|---|---|---|---|
| Core and Java | Image digest/build manifest | Running version | Stateful home persists |
| Plugins | Approved pinned manifest/lock | Installed versions | Transitive dependencies |
| Controller settings | JCasC YAML | JCasC export/API | Not all settings exported |
| Jobs/folders | Job DSL + Jenkinsfiles | Generated job config | Runtime state differs |
| RBAC | Reviewed JCasC/role matrix | Effective permissions | Group claims vary |
| Credentials | Inventory/secret references | Metadata/provider audit | Never export values |
| Agents/clouds | JCasC and IaC | Running agent templates | Ephemeral agents |
| SCM trust | Protected branches and policies | Branch-source settings | PR behavior matters |

## 3. Drift classification

- **Expected runtime changes:** build history, queue, ephemeral agents, temporary workspaces; exclude from configuration drift.
- **Authorized emergency drift:** time-bound UI change with ticket and owner; reconcile through Git promptly.
- **Unauthorized drift:** unreviewed security, plugin, job, credential or controller mutation; investigate.
- **Schema/serialization drift:** different export ordering/defaults; normalize before alerting.
- **Dependency drift:** plugin or base-image change without reviewed manifest revision.

Prioritize privilege, authentication, credential, Pipeline SCM and cloud-agent changes as high risk.

## 4. Git policy and ownership

```text
jenkins-config/
├── .github/CODEOWNERS
├── Dockerfile
├── plugins.txt
├── casc/
├── jobs/
├── policies/
│   ├── required-controls.md
│   └── exceptions.yaml
└── tests/
    ├── validate.sh
    └── acceptance.md
```

Example CODEOWNERS:

```text
/casc/ @platform-security @jenkins-admins
/plugins.txt @jenkins-admins @platform-security
/jobs/releases/ @release-engineering @platform-security
/policies/ @platform-security
```

Replace team handles with real authorized GitHub teams. Branch protection must enforce required reviewers; CODEOWNERS alone does not enforce approval.

## 5. Policy-as-code gates

Validate:
1. No plaintext secrets, tokens or private keys.
2. Reviewed plugin versions and known security advisories.
3. No anonymous admin, broad authenticated admin or unrestricted Script Console.
4. Controller executors disabled for workloads.
5. Production jobs use protected SCM and trusted agents.
6. No untrusted PR path to production credentials.
7. Agent Kubernetes RBAC and cloud IAM least privilege.
8. JCasC schema compatibility and Job DSL generation.
9. Backups and recovery evidence before high-risk changes.
10. Change ticket, approvers, expiry and exception ownership.

Use a policy engine such as OPA/Conftest where appropriate, but ensure tests inspect the actual YAML schema for the installed plugins. Text matching alone is not sufficient for security guarantees.

## 6. Illustrative OPA/Rego policy

```rego
package jenkins.security

deny contains msg if {
  input.jenkins.numExecutors > 0
  msg := "Controller executors must be disabled"
}
```

This Rego uses modern syntax requiring a compatible OPA version. It checks only one control and is **not** a complete Jenkins security policy. Ensure the input document shape matches parsed JCasC.

## 7. Safe comparison script

A plugin inventory is a low-risk starting point. Compare sorted `shortName:version` values from a trusted, authenticated Jenkins inventory export against an approved resolved plugin lockfile. Never include credentials or token-bearing URLs in comparison artifacts.

```sh
#!/usr/bin/env bash
set -euo pipefail
diff -u expected-plugins.txt observed-plugins.txt || {
  echo "Plugin inventory drift detected"
  exit 1
}
```

For JCasC, redact secrets, normalize nonsemantic defaults and compare only fields the installed plugins support. Do not commit raw Jenkins config exports without reviewing them for sensitive material.

## 8. CI/CD governance pipeline

```groovy
pipeline {
    agent { label 'trusted-config-validation' }
    options {
        timestamps()
        disableConcurrentBuilds()
    }
    stages {
        stage('Static policy') {
            steps { sh './tests/validate.sh' }
        }
        stage('Build controller') {
            steps { sh 'docker build -t jenkins-governance-lab:$BUILD_NUMBER .' }
        }
        stage('Staging acceptance') {
            steps { sh './tests/acceptance.sh' }
        }
        stage('Publish evidence') {
            steps {
                archiveArtifacts artifacts: 'evidence/*.txt', allowEmptyArchive: false
            }
        }
    }
}
```

This is a **pipeline skeleton**: supply reviewed scripts, Docker-capable trusted agent, redacted evidence and a disposable controller. Never archive resolved secrets, session cookies or raw credential exports.

## 9. Reconciliation strategy

1. Detect drift and preserve redacted evidence.
2. Classify impact and determine whether change was authorized.
3. Freeze privileged jobs if security-sensitive.
4. Compare running versions, JCasC and generated job definitions with approved Git.
5. If authorized, open PR to codify the change; otherwise restore reviewed configuration.
6. Validate in staging and roll forward using the approved image/revision.
7. Re-run negative authorization/credential tests and close the incident.

Avoid blind continuous reapplication of JCasC on a live controller: not all settings are safe to reload dynamically and plugin behaviors vary.

## 10. Exception management

A temporary exception requires scope, owner, ticket, reason, compensating controls, expiry and review date. Expired exceptions fail CI and trigger remediation. Never allow permanent unreviewed exceptions for admin rights, production secret exposure or disabled security controls.

## 11. Audit and evidence

Retain Git commit and reviewer IDs, controller image digest, plugin inventory, JCasC revision, generated job inventory, policy test results, drift diff, incident/change ticket, approver and post-change verification. Apply access controls and retention to evidence; redact identity tokens and secrets.

## 12. Troubleshooting matrix

| Symptom | Cause | Response |
|---|---|---|
| False drift alert | Defaults/ordering | Normalize |
| Missing config export | Plugin limitation | Use supported API/manual evidence |
| Plugin inventory differs | Transitive update | Pin/review |
| Job DSL overwrites UI edit | Desired state differs | Reconcile through Git |
| Policy blocks valid change | Schema mismatch | Fix rule/test |
| Unreviewed admin grant | Unauthorized drift | Revoke and investigate |
| Secret appears in export | Unsafe evidence handling | Purge/revoke as needed |
| CI cannot build image | Dependency/network | Restore builder |
| Staging differs from prod | Different digest/plugin | Align artifacts |
| JCasC reload fails | Unsupported runtime change | Planned restart |
| Git approval bypassed | Branch protection gap | Enforce rules |
| Exception expired | Governance failure | Remediate |
| Job deleted unexpectedly | Seed removal policy | Restore backup |
| SCM trust changed | Branch-source drift | Restore protected policy |
| Agent privileges expanded | IaC/RBAC drift | Revoke and retest |
| Drift job has admin token | Excess monitoring privilege | Reduce scope |

## 13. Five production runbooks

### A. Daily drift review
1. Collect approved and observed version metadata.
2. Normalize supported fields and compare.
3. Triage high-risk RBAC/secret/SCM drift first.
4. Assign owner and ticket.
5. Reconcile and record evidence.

### B. Unauthorized security change
1. Preserve audit events and freeze affected privileged jobs.
2. Identify actor, changed permission and affected jobs.
3. Revoke elevated access and compromised credentials.
4. Restore reviewed Git/JCasC state after validation.
5. Complete RCA and improve policy checks.

### C. Emergency change reconciliation
1. Record approved exception and expiry.
2. Apply minimal change with audit trail.
3. Open PR reflecting desired state.
4. Validate and deploy immutable configuration.
5. Close exception after verifying no drift.

### D. Policy pipeline failure
1. Identify failing rule and input.
2. Distinguish true violation from schema/test bug.
3. Correct configuration or rule via review.
4. Re-run isolated acceptance.
5. Do not bypass required security gates.

### E. Controller configuration rollback
1. Identify last known-good image/config revision.
2. Verify state compatibility and backup.
3. Deploy controlled rollback.
4. Test SSO/RBAC, credentials, agents and jobs.
5. Record recovery time and audit evidence.

## 14. Acceptance criteria

- [ ] Git source of truth and ownership defined.
- [ ] Required approvals enforced by branch protection.
- [ ] Plugin, JCasC and Job DSL drift covered.
- [ ] Secret values excluded from evidence.
- [ ] High-risk policy violations block promotion.
- [ ] Authorized emergency drift has expiry and reconciliation.
- [ ] Unauthorized security drift detected and remediated.
- [ ] Staging/production artifact parity verified.
- [ ] Rollback tested on disposable controller.
- [ ] Audit evidence and on-call ownership documented.

**Companion:** [Chapter 064 hands-on lab](labs/064-jenkins-configuration-drift-policy-validation-gitops-governance-check.md).  
**Next:** Chapter 065 — Jenkins Plugins, JCasC and Configuration Governance Production Capstone.
