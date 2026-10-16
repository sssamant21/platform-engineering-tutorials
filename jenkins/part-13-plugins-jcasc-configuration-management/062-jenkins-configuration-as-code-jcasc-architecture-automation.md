# Chapter 062 — Jenkins Configuration as Code (JCasC) Architecture and Automation

**Part 13 — Plugins, JCasC and Configuration Management**  
**Audience:** Jenkins administrators, SRE, platform engineering, DevSecOps and change managers  
**Prerequisites:** Chapter 061, disposable Jenkins LTS controller, Configuration as Code plugin, tested plugin baseline, Docker, Git and protected lab secrets.

## Learning outcomes

Design a Git-managed Jenkins configuration architecture; author modular JCasC, separate secrets, validate configuration against installed plugin schemas, automate immutable controller builds, detect configuration drift and safely deploy/roll back controller changes.

## 1. Why JCasC?

Jenkins Configuration as Code (JCasC) configures supported Jenkins core and plugin settings from YAML. It enables reproducibility, review and environment promotion. It **does not automatically cover every plugin setting, job definition, secret lifecycle or stateful Jenkins home file**. Pair JCasC with Job DSL, SCM, plugin manifests and backups as appropriate.

```text
Git PR + CODEOWNERS
      ↓
YAML/schema/static validation
      ↓
Jenkins plugin/core compatibility test
      ↓
Immutable controller image + JCasC
      ↓
Staging smoke tests / security checks
      ↓
Approved production deployment
      ↓
Drift detection / audit / rollback
```

## 2. Repository architecture

```text
jenkins-controller/
├── Dockerfile
├── plugins.txt
├── casc/
│   ├── 00-controller.yaml
│   ├── 10-security.yaml
│   ├── 20-clouds.yaml
│   └── 30-unclassified.yaml
├── jobs/
│   └── seed.groovy
├── tests/
│   ├── validate.sh
│   └── acceptance.md
└── docs/
    ├── runbook.md
    └── change-record.md
```

Multiple JCasC YAML files must be **supplementary, not conflicting**; duplicate configuration paths can fail import. Keep environment-specific overrides explicit and reviewable. Plugin compatibility is pinned separately.

## 3. Minimal JCasC example

```yaml
jenkins:
  systemMessage: "Managed by Configuration as Code — lab only"
  numExecutors: 0
  mode: NORMAL
  labelString: "controller"
  crumbIssuer:
    standard:
      excludeClientIPFromCrumb: false

unclassified:
  location:
    url: "https://jenkins.example.test/"
```

This is an illustrative lab configuration; confirm attribute names against the installed Jenkins and JCasC plugin reference. Controller executors should generally remain disabled for production workloads. The example hostname is a placeholder.

## 4. Security realm and authorization

Never commit admin passwords, tokens, SAML private keys or cloud credentials into JCasC. Use environment or supported secret sources. A security realm and authorization strategy should be tested together with recovery access on an isolated controller.

```yaml
jenkins:
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: "lab-admin"
          password: "${JENKINS_LAB_ADMIN_PASSWORD}"
  authorizationStrategy:
    loggedInUsersCanDoAnything:
      allowAnonymousRead: false
```

**WARNING:** This authorization strategy grants broad control to every logged-in user and is **unsafe for enterprise or shared environments**. It is included solely to demonstrate JCasC syntax in a disposable, single-user lab. Use reviewed Role Strategy or Matrix Authorization mappings for enterprise systems (Chapters 056–057). Verify plugin-specific YAML shape before applying.

## 5. Secret substitution

JCasC supports variable substitution and compatible secret sources. Inject values from an approved secret store at runtime, not from committed plaintext files. Ensure the secret provider's identity and permissions are scoped to the controller and audit reads. Treat environment variables as sensitive: administrators or privileged processes may inspect them.

```yaml
unclassified:
  location:
    adminAddress: "${JENKINS_ADMIN_EMAIL}"
```

The variable name is a placeholder; the runtime must supply it. Do not archive environment dumps or resolved configuration containing secrets.

## 6. Plugin manifest and immutable image

```dockerfile
FROM jenkins/jenkins:lts-jdk21
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY --chown=jenkins:jenkins casc/ /usr/share/jenkins/ref/casc/
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc/
```

The moving base image tag is for a lab. Pin an approved image digest and reviewed plugin versions for production. A new image does not replace Jenkins state backups; do not mount one Jenkins home into multiple active controllers.

## 7. Validation pipeline

Run these gates in order:
1. YAML parse and duplicate-key checks.
2. Secret scanning and policy validation.
3. Plugin/core version and dependency resolution.
4. Disposable controller startup with JCasC.
5. JCasC schema validation against **installed plugins**.
6. Authentication, RBAC and credential negative tests.
7. Representative Pipeline, SCM and agent smoke tests.
8. Backup/rollback and audit evidence review.

The Configuration as Code plugin exposes validation and export mechanisms via supported Jenkins endpoints/UI, subject to authentication and plugin version. Avoid hardcoding endpoints without confirming the installed plugin documentation.

## 8. Declarative CI example

```groovy
pipeline {
    agent { label 'trusted-jcasc-validation' }
    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }
    stages {
        stage('Parse YAML') {
            steps {
                sh 'python3 -c "import yaml; [yaml.safe_load(open(p)) for p in __import__(\x27glob\x27).glob(\x27casc/*.yaml\x27)]"'
            }
        }
        stage('Secret scan') {
            steps {
                sh 'test -x ./tools/scan-secrets.sh && ./tools/scan-secrets.sh'
            }
        }
        stage('Build test controller') {
            steps {
                sh 'docker build -t jenkins-jcasc-lab:$BUILD_NUMBER .'
            }
        }
        stage('Acceptance') {
            steps {
                sh './tests/validate.sh'
            }
        }
    }
}
```

This is an **integration skeleton**, not a complete runnable system: supply a trusted agent with Python/PyYAML/Docker, the repository's `tools/scan-secrets.sh` and `tests/validate.sh`, isolated test credentials and a disposable controller. Do not grant untrusted PRs access to the Docker socket or production secrets.

## 9. Configuration promotion

Use protected PRs, CODEOWNERS and environment-specific approval. Promote the **same reviewed configuration revision and plugin/image digest** from staging to production. Record the configuration Git SHA, image digest, plugin inventory, change ticket, reviewer and rollback target.

## 10. Drift detection

Compare:
- Approved Git JCasC revision.
- Running controller image digest and plugin inventory.
- Effective security realm, authorization and cloud settings.
- Job DSL and shared library revisions.
- Manual UI changes and configuration export.

Not all settings are round-trippable via JCasC export. Treat exports as diagnostic evidence and investigate differences rather than blindly overwriting Git. Restrict UI mutation permissions to prevent uncontrolled drift.

## 11. Failure and recovery

| Symptom | Cause | Safe recovery |
|---|---|---|
| Controller fails startup | Invalid JCasC YAML | Restore last known-good image/config |
| Unknown attribute | Plugin schema mismatch | Align plugin/JCasC |
| Duplicate config key | Conflicting YAML files | Remove duplicate |
| Admin locked out | Authorization error | Protected recovery procedure |
| Secret substitution fails | Missing env/provider | Restore scoped secret |
| Cloud agents unavailable | Plugin/cloud config mismatch | Revert validated config |
| JCasC reload fails | Unsupported runtime reload | Restart tested image if needed |
| Manual UI drift | Unreviewed change | Audit and reconcile Git |
| Plugin dependency failure | Manifest mismatch | Restore tested set |
| Credential missing | Scope/ID/secret source | Fix integration |
| TLS/root URL mismatch | Proxy/location config | Restore trusted URL |
| Job DSL missing | Seed step/plugin | Restore dependency |
| Pipeline step missing | Workflow plugin | Restore plugin |
| Agent permissions excessive | Cloud template/RBAC | Reduce and retest |
| Backup restore incomplete | Missing keys/state | Restore verified backup |
| Environment promotion mismatch | Different image/config | Pin and redeploy |

## 12. Five production runbooks

### A. New controller onboarding
1. Approve architecture and ownership.
2. Pin Jenkins core, Java and plugin manifest.
3. Author JCasC and scoped secret references.
4. Test isolated controller and access matrix.
5. Deploy reviewed image and capture evidence.

### B. JCasC change deployment
1. Create PR with config diff and change ticket.
2. Run YAML, secret, plugin and controller tests.
3. Validate security and Pipeline smoke tests.
4. Deploy with monitored maintenance window.
5. Confirm expected effective configuration.

### C. JCasC startup failure
1. Preserve logs and last known-good revision.
2. Identify first schema/substitution/dependency error.
3. Revert image/config to tested baseline.
4. Restore compatible state if required.
5. Re-run acceptance before reopening builds.

### D. Configuration drift incident
1. Capture effective config and audit actor.
2. Compare with Git and plugin inventory.
3. Determine whether emergency change was authorized.
4. Reconcile through reviewed PR or restore baseline.
5. Close incident with preventive controls.

### E. Security misconfiguration recovery
1. Stop affected privileged jobs.
2. Preserve authorization and secret access logs.
3. Use protected recovery without disabling security.
4. Restore reviewed RBAC/JCasC and validate negative tests.
5. Audit blast radius and document RCA.

## 13. Acceptance criteria

- [ ] JCasC and plugin manifest stored in Git.
- [ ] No plaintext credentials in configuration.
- [ ] Schema validated against installed plugins.
- [ ] Controller executors disabled for builds.
- [ ] Auth/RBAC/credential negative tests pass.
- [ ] Agent and SCM smoke tests pass.
- [ ] Protected promotion and change evidence recorded.
- [ ] Configuration drift detection defined.
- [ ] Known-good rollback tested.
- [ ] Jenkins home and encryption keys backup verified.

**Companion:** [Chapter 062 hands-on lab](labs/062-jenkins-configuration-as-code-jcasc-architecture-automation-check.md).  
**Next:** Chapter 063 — Jenkins Job DSL, Seed Jobs and Reusable Configuration Patterns.
