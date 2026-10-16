# Chapter 065 — Jenkins Plugins, JCasC and Configuration Governance Production Capstone

**Part 13 — Plugins, JCasC and Configuration Management (final capstone)**  
**Audience:** Jenkins SRE, platform engineering, security, release engineering, change managers  
**Prerequisites:** Chapters 061–064, isolated Jenkins LTS, reviewed plugin set, JCasC, Job DSL, protected Git repository and disposable test controller.

## Mission

Build, deploy, validate, observe and recover a Jenkins controller managed through Git, a pinned plugin manifest, Configuration as Code and Job DSL. Demonstrate drift detection, policy gates, safe upgrades, emergency changes, rollback and production-style governance. Complete a **100-point operational acceptance assessment** with traceable evidence.

**Safety:** All failure injection, deletion tests and identity changes belong in an isolated lab. Never attach two running Jenkins controllers to the same writable Jenkins home.

## 1. Target architecture

```text
Protected Git: plugins.txt + Dockerfile + casc/ + jobs/
                     |
           PR / CODEOWNERS / policy gates
                     |
           Immutable Jenkins controller image
                     |
          Staging controller + acceptance tests
                     |
         Approved production-style promotion
                     |
       Drift inventory + audit + incident response
```

JCasC configures supported controller/plugin settings, Job DSL generates jobs, Jenkinsfiles implement Pipeline behavior, and a plugin manifest controls extensions. State backups remain necessary even with immutable images.

## 2. Required deliverables

| Artifact | Minimum evidence |
|---|---|
| Controller image | Pinned digest and build log |
| Plugin manifest | Approved versions and dependency inventory |
| JCasC | Reviewed YAML and schema test |
| Job DSL | Protected seed and generated inventory |
| Security | SSO/RBAC/credential negative tests |
| Agent integration | Kubernetes/cloud identity checks |
| Policy gates | Secret scan, security rules and approvals |
| Drift report | Desired vs observed config |
| Rollback | Known-good restore and measured RTO |
| Change record | Git SHA, reviewer, ticket and sign-off |

## 3. Repository reference layout

```text
jenkins-platform/
├── Dockerfile
├── plugins.txt
├── casc/
│   ├── controller.yaml
│   ├── security.yaml
│   └── clouds.yaml
├── jobs/
│   ├── folders.groovy
│   ├── ci.groovy
│   └── releases.groovy
├── Jenkinsfile.seed
├── policies/
│   └── required-controls.md
├── tests/
│   ├── validate.sh
│   ├── acceptance.sh
│   └── rollback.md
└── evidence/
```

Never commit actual secret values, encryption keys, unredacted JCasC exports or live session tokens.

## 4. Immutable image and plugin baseline

```dockerfile
FROM jenkins/jenkins:lts-jdk21
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY --chown=jenkins:jenkins casc/ /usr/share/jenkins/ref/casc/
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc/
```

For production, pin the tested base image **digest** and plugin versions; the moving tag is for illustration only. Verify compatibility with the installed core, Java runtime and plugin dependencies. A Docker image alone is not a disaster-recovery backup.

## 5. Controller configuration and security

Example **lab-only** JCasC fragment:

```yaml
jenkins:
  numExecutors: 0
  systemMessage: "Managed by JCasC"
  crumbIssuer:
    standard:
      excludeClientIPFromCrumb: false
unclassified:
  location:
    url: "https://jenkins.example.test/"
```

Keep authentication and authorization in separate reviewed configuration files with validated plugin-specific schema. Never deploy permissive sample security realms to a shared or production controller. Test admin access, developer restrictions, secret scopes, untrusted PR behavior and protected emergency recovery.

## 6. Job DSL seed safety

```groovy
pipeline {
    agent { label 'trusted-seed-agent' }
    options {
        disableConcurrentBuilds()
        timestamps()
    }
    stages {
        stage('Generate reviewed jobs') {
            steps {
                checkout scm
                jobDsl(
                    targets: 'jobs/*.groovy',
                    removedJobAction: 'IGNORE',
                    removedViewAction: 'IGNORE',
                    lookupStrategy: 'JENKINS_ROOT',
                    sandbox: true
                )
            }
        }
    }
}
```

Protect the seed repository and its write permissions. Review Job DSL sandbox approvals; do not broadly approve untrusted methods. Automatic deletion must be separately approved and tested against backups.

## 7. CI/CD validation gates

| Gate | Expected result |
|---|---|
| YAML and Groovy validation | Parse succeeds |
| Duplicate JCasC key detection | No conflicting paths |
| Secret scanning | No plaintext secrets |
| Plugin dependency resolution | All compatible |
| Security advisory review | No unaccepted critical exposure |
| Controller startup | Healthy in isolated staging |
| JCasC schema | Valid against installed plugins |
| Job DSL seed | Expected jobs/folders |
| Idempotency | Second run does not change jobs unexpectedly |
| Auth/RBAC | Negative access tests pass |
| Credentials | Scoped and unavailable to untrusted jobs |
| Agent/cloud | Least privilege validated |
| Drift | Benign/security drift detected |
| Recovery | Known-good state restored |

These are separate checks; YAML syntax validation does not prove JCasC schema compatibility or RBAC correctness.

## 8. Controlled promotion

1. Open protected PR with plugin/JCasC/Job DSL diff.
2. Enforce CODEOWNERS and branch protection.
3. Build immutable controller image and record digest.
4. Run staging acceptance against the exact artifact.
5. Approve production-style rollout and record change ticket.
6. Quiet down/drain affected jobs; back up compatible state.
7. Deploy approved artifact without concurrent Jenkins-home writers.
8. Verify security, agents, representative jobs and monitoring.
9. Retain rollback target and close change only after observation.

## 9. Drift detection and reconciliation

Compare Git revision, plugin inventory, supported JCasC settings, generated job definitions, SCM trust, RBAC and cloud-agent settings. Exclude build history, queue and ephemeral agents from desired configuration. Redact secret values before saving any diff.

Classify drift as expected runtime state, approved emergency change, serialization noise or unauthorized configuration. Never blindly reload JCasC to erase an unknown security incident.

## 10. Failure simulation matrix

| # | Failure | Required recovery evidence |
|---|---|---|
| 01 | Missing plugin dependency | Startup log and corrected manifest |
| 02 | Plugin requires newer core | Compatibility decision |
| 03 | Plugin security advisory | Remediation plan |
| 04 | Invalid JCasC YAML | Parser failure |
| 05 | Unsupported JCasC attribute | Schema failure |
| 06 | Missing secret substitution | Provider recovery |
| 07 | Duplicate configuration path | Conflict resolution |
| 08 | Unauthorized admin grant | RBAC denial after restore |
| 09 | Seed job permission denied | Trusted role fix |
| 10 | Unsupported Job DSL method | API-compatible DSL |
| 11 | Unexpected job deletion policy | Recovery from backup |
| 12 | Untrusted PR attempts secret use | Access denied |
| 13 | Agent identity overprivileged | RBAC/IAM restriction |
| 14 | Manual UI drift | Detected/reconciled |
| 15 | Staging/prod image mismatch | Artifact parity |
| 16 | Plugin upgrade breaks Pipeline step | Known-good rollback |
| 17 | JCasC reload fails | Controlled restart |
| 18 | Update center unavailable | Approved artifact cache |
| 19 | Backup lacks encryption keys | Verified full restore |
| 20 | Emergency change not reconciled | Expiring exception and PR |

## 11. Production runbooks

### A. Controller bootstrap
1. Verify plugin/core/Java compatibility.
2. Build pinned image and inject secrets from approved provider.
3. Start isolated controller with JCasC.
4. Run protected seed job and validate generated jobs.
5. Capture inventory, audit and handover.

### B. Plugin and configuration upgrade
1. Capture baseline and compatible backup.
2. Review advisories and dependency graph.
3. Build/test proposed image and JCasC.
4. Deploy in maintenance window with controlled shutdown.
5. Run security/agent/job smoke tests and observe.

### C. Drift incident
1. Preserve redacted observed state and audit logs.
2. Classify unauthorized vs approved change.
3. Freeze privileged jobs if security-sensitive.
4. Restore approved config or codify approved exception.
5. Re-run negative tests and close RCA.

### D. Seed job failure or deletion
1. Stop competing seed executions.
2. Preserve job inventory and build history.
3. Restore from verified backup if jobs were removed.
4. Reapply approved DSL with safe removal policy.
5. Validate job ownership, SCM and permissions.

### E. Controller rollback and disaster recovery
1. Identify known-good image, plugin lock and JCasC revision.
2. Confirm backup includes Jenkins home and encryption keys.
3. Restore into isolated environment; check compatibility.
4. Validate authentication, credentials, agents and jobs.
5. Measure RTO/RPO and document unresolved risks.

## 12. Observability and audit

Monitor controller startup, plugin load failures, configuration reload errors, seed job success, generated job drift, auth denials, credential retrieval failures, agent connectivity and rollback events. Preserve Git SHAs, image digests, plugin inventory, change tickets and test results. Never export plaintext credentials into observability systems.

## 13. 100-point operational acceptance scorecard

| Domain | Points |
|---|---:|
| Architecture and source of truth | 10 |
| Plugin lifecycle and dependency control | 15 |
| JCasC validation and secret handling | 15 |
| Job DSL/seed idempotency and safety | 15 |
| Security and identity boundaries | 15 |
| Policy gates and drift detection | 10 |
| Promotion and change management | 10 |
| Incident recovery and rollback | 5 |
| Evidence and handover | 5 |
| **Total** | **100** |

Suggested pass: **85/100**, plus mandatory gates: no plaintext secrets, no unauthorized admin or production job modification, no untrusted PR access to release secrets, reproducible plugin/JCasC baseline, safe seed removal policy and verified rollback. Unsupported features are marked **not tested**, not passed.

## 14. Handover checklist

- [ ] Reviewed Git revision and CODEOWNERS.
- [ ] Pinned image digest and plugin inventory.
- [ ] JCasC schema and secret source verified.
- [ ] Seed job idempotent with safe deletion policy.
- [ ] Auth/RBAC/credential negative tests pass.
- [ ] Agents and cloud identities least privilege.
- [ ] Drift detection and exceptions documented.
- [ ] Rollback and restore evidence recorded.
- [ ] 100-point scorecard reviewed and signed.
- [ ] Residual risks and on-call ownership assigned.

**Companion:** [Chapter 065 hands-on capstone lab](labs/065-jenkins-plugins-jcasc-configuration-governance-production-capstone-check.md).  
**Part 13 complete:** Chapters 061–065.  
**Next:** Chapter 066 — Jenkins Monitoring Architecture, Metrics and Operational Observability (Part 14).
