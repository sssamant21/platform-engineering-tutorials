# Chapter 057 — Jenkins Role-Based Access Control, Folder Security and Least Privilege

**Part 12 — Security, RBAC, SSO, Credentials and Secrets**  
**Audience:** Jenkins SRE, IAM, platform security, release engineering and compliance  
**Prerequisites:** Chapter 056, disposable Jenkins LTS controller, Role Strategy or Matrix Authorization plugin, Configuration as Code plugin, synthetic test identities.

## Objectives

Design, implement, test and audit least-privilege Jenkins permissions across global, item/folder and agent scopes. Prevent privilege escalation through job configuration, shared libraries, credentials and build agents; create reproducible JCasC policy and emergency recovery runbooks.

## 1. Security model

```text
Identity provider (user, group, MFA)
         ↓
Jenkins security realm (authentication)
         ↓
Authorization strategy (global/item/agent grants)
         ↓
Folders and jobs ── credentials ── agents
         ↓
Kubernetes RBAC and cloud IAM (separate boundaries)
```

**Key principle:** A user allowed to configure a Pipeline can usually cause it to use any credential available to that job, even if the credential value is not visible in the UI. Job/Configure and trusted shared-library modification are high-trust permissions.

## 2. Authorization models

| Model | Strength | Operational caution |
|---|---|---|
| Matrix Authorization | Explicit global or item grants | Inheritance can widen access |
| Role Strategy | Named global/item/agent roles | Regex patterns and role assignments require review |
| Folder-based organization | Delegated ownership | Folder boundaries are not a substitute for credentials isolation |
| External IdP groups | Central identity lifecycle | Missing/stale group claims can cause access drift |

Use a **single supported authorization strategy** on each controller. The Role Strategy and Matrix Authorization plugins provide different JCasC configuration shapes; do not combine their authorization strategy blocks.

## 3. Reference enterprise role matrix

| Persona | Overall/Read | Job/Read | Job/Build | Job/Configure | Credentials/Manage | Overall/Administer |
|---|---|---|---|---|---|---|
| Platform administrator | Yes | Yes | Yes | Yes | Scoped | Yes |
| Security auditor | Scoped | Scoped | No | No | No | No |
| Developer | As required | Team folders | Team jobs | Restricted | No | No |
| CI service account | As required | CI jobs | CI jobs | No | No | No |
| Release operator | As required | Release folders | Approved releases | No | No | No |
| Production release maintainer | As required | Prod folder | Controlled | Only via reviewed change | No | No |
| Anonymous | Normally no | Normally no | No | No | No | No |

The table is a design baseline; plugin-specific permissions (e.g., Item/Discover, Job/Cancel, Run/Replay, SCM permissions and credential usage) must be assessed separately. Do not assume Overall/Read is harmless on a private controller.

## 4. Folder structure and delegation

```text
Jenkins/
├── shared-platform/
│   ├── security-audit/
│   └── platform-maintenance/
├── engineering/
│   ├── team-a/
│   └── team-b/
└── releases/
    ├── staging/
    └── production/
```

Folder administrators must not automatically receive global administration. Production folder Job/Configure and pipeline source control are restricted to trusted maintainers. Folder-scoped credentials reduce accidental exposure but cannot protect against malicious job authors who can execute code in that folder.

## 5. Role Strategy JCasC lab example

**Prerequisites:** Compatible Jenkins LTS, Configuration as Code and Role Strategy plugins. Confirm actual role schema and permission identifiers using the installed plugin's JCasC export/reference. The following is a **version-sensitive illustrative lab baseline**, not a drop-in production configuration.

```yaml
jenkins:
  authorizationStrategy:
    roleBased:
      roles:
        global:
          - name: "security-auditor"
            permissions:
              - "Overall/Read"
            entries:
              - user: "lab-auditor"
        items:
          - name: "team-a-builder"
            pattern: "engineering/team-a(/.*)?"
            permissions:
              - "Job/Read"
              - "Job/Build"
            entries:
              - group: "team-a-developers"
          - name: "production-operator"
            pattern: "releases/production(/.*)?"
            permissions:
              - "Job/Read"
              - "Job/Build"
            entries:
              - group: "prod-release-operators"
```

The example assumes identities and folders exist. The global role shown may require additional Overall/Read for users to navigate Jenkins; grant only the minimal needed and test real access. Depending on plugin version, JCasC uses specific entry and permission serialization. **Do not apply without validation on a disposable controller and an admin recovery plan.**

## 6. Permission evaluation and inheritance

Check permissions at the actual job path and folder nesting, not only the root. Review whether an inherited item role reaches children and whether broad patterns accidentally match similarly named folders. Test regex boundaries such as `engineering/team-a` versus `engineering/team-admin`.

An authorization test must use the actual identity, not just an administrator viewing a permissions table. Verify both permitted and denied actions.

## 7. Sensitive permissions and escalation paths

- **Overall/Administer:** effectively full controller control, including Script Console.
- **Job/Configure:** edit Pipeline definition/SCM, choose agents and credential IDs.
- **Run/Replay:** may allow altering Pipeline execution; restrict where secrets are available.
- **Job/Build:** can be risky when a parameterized job executes user-supplied commands.
- **Credentials/Manage:** creates/updates sensitive credentials; restrict and audit.
- **Agent/Configure:** may influence code execution environment and trust boundaries.
- **Trusted shared-library write:** changes code executed by many jobs; protect repository and review.
- **Job/Create:** may combine with credential availability or plugin behaviors to broaden risk.

Authorization plugins cannot compensate for untrusted Pipeline source or malicious plugins.

## 8. Credentials and job boundaries

Use folder-scoped credentials for trusted team and release jobs, separate production from staging, and prefer short-lived external identities. Do not share a production credential ID with untrusted PR jobs. Masking is not an exfiltration prevention boundary.

```groovy
pipeline {
    agent { label 'trusted-release-agent' }
    stages {
        stage('Scoped credential check') {
            steps {
                withCredentials([string(credentialsId: 'lab-scoped-readonly', variable: 'LAB_TOKEN')]) {
                    sh '''#!/bin/sh
                        set +x
                        test -n "$LAB_TOKEN"
                        echo "Credential available; secret not displayed"
                    '''
                }
            }
        }
    }
}
```

Never use this on an untrusted branch, and never assume `withCredentials` makes arbitrary Pipeline code safe.

## 9. Separation of duties for production

Implement independent approvals for changing production Jenkinsfiles, trusted libraries, release parameters, production credentials and authorization roles. Use protected Git branches, CODEOWNERS, change tickets, credential audit and immutable build artifacts. Ensure release operators can trigger approved jobs without editing their Pipeline or source.

## 10. Kubernetes and cloud permission boundaries

Jenkins authorization is **not** Kubernetes RBAC. Validate build and release service accounts separately:

```sh
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create deployments -n production \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

Both should be denied for an ordinary build identity. Trusted release agents may need narrowly scoped deploy permissions. For EKS/AKS, verify AWS IAM or Entra Workload Identity independently.

## 11. Access review and drift detection

Perform periodic reviews of global roles, folder roles, agent roles, group membership, service accounts, dormant identities, Job/Configure grants, Replay rights, trusted libraries and credential scope. Compare approved JCasC/Git baseline with effective permissions. Investigate unexpected grants and log who changed what, when and why.

## 12. Troubleshooting matrix

| Symptom | Diagnostic | Recovery |
|---|---|---|
| Developer cannot see folder | Overall/Read, Item/Discover | Add minimal access |
| Developer can see another team | Regex pattern/inheritance | Narrow item role |
| Job/Build unexpectedly denied | Item role and group claim | Correct mapping |
| User can configure prod job | Job/Configure inheritance | Revoke, audit |
| Replay available on release job | Run/Replay | Remove permission |
| Admin lost access | Role assignments/JCasC | Controlled recovery |
| LDAP/OIDC group missing | IdP claim mapping | Fix realm/groups |
| JCasC import fails | Plugin schema/version | Validate and revert |
| Service account overprivileged | Role assignments | Reduce scope |
| Folder credentials exposed | Job source and Configure | Isolate trusted jobs |
| Build agent lists K8s secrets | K8s RBAC/token mount | Revoke |
| Shared library bypass | SCM branch protection | Protect library |
| Regex matches unintended folder | Role pattern test | Anchor scope |
| Anonymous can discover private job | Anonymous permissions | Remove grant |
| Plugin update changes permissions | Plugin changelog/testing | Restore tested config |
| Break-glass misuse | Audit trail | Revoke and investigate |

## 13. Production runbooks

### A. New team onboarding
1. Verify IdP group and team ownership.
2. Create isolated folder and credential boundary.
3. Assign minimal item roles; avoid global admin.
4. Run positive/negative access tests.
5. Record approval, role pattern and review date.

### B. Access escalation request
1. Record business justification and duration.
2. Check whether Job/Configure, Replay or credentials access is truly needed.
3. Obtain independent approval.
4. Grant narrowly scoped access with expiry/review.
5. Validate effective permissions and audit.

### C. Unauthorized production job modification
1. Freeze affected release and preserve audit evidence.
2. Identify actor, modified Pipeline and executed builds.
3. Revoke access/credentials as needed.
4. Restore reviewed Pipeline and role assignments.
5. Verify downstream artifacts and complete incident RCA.

### D. Authorization lockout
1. Confirm IdP versus authorization failure.
2. Use documented protected administrator recovery.
3. Restore known-good JCasC/roles without disabling security.
4. Validate multiple test identities.
5. Record change and prevent recurrence.

### E. Periodic access review
1. Export approved and effective roles.
2. Compare identities, folders, agents and credential scope.
3. Remove dormant/excess grants.
4. Retest sensitive negative cases.
5. Obtain security sign-off.

## 14. Acceptance criteria

- [ ] No broad Overall/Administer outside approved admins.
- [ ] Team roles cannot access unrelated folders.
- [ ] Production operators cannot modify production Pipeline definitions.
- [ ] Untrusted PRs cannot access production credentials.
- [ ] Job/Configure and Replay reviewed as high risk.
- [ ] Agent and Kubernetes identities separately scoped.
- [ ] JCasC policy versioned and validated.
- [ ] Positive and negative tests recorded.
- [ ] Break-glass procedure tested without disabling security.
- [ ] Periodic access review and audit ownership established.

**Companion:** [Chapter 057 hands-on lab](labs/057-jenkins-rbac-folder-security-least-privilege-check.md).  
**Next:** Chapter 058 — Jenkins Enterprise SSO, LDAP, SAML and OIDC Integration.
