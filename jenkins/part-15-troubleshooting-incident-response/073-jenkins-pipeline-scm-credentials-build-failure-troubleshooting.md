# Chapter 073 — Jenkins Pipeline, SCM, Credentials and Build Failure Troubleshooting

**Part 15 — Troubleshooting and Incident Response**  
**Audience:** Jenkins SRE, DevOps, platform engineers and on-call responders  
**Prerequisites:** Chapters 071–072; isolated Jenkins LTS, Git repository, synthetic credentials and test agents.

## Learning objectives

Investigate failed Declarative/Scripted Pipelines, checkout and webhook failures, credentials and secret-provider errors, workspace contamination, artifact failures, flaky tests and agent/environment mismatches. Classify infrastructure versus application errors and perform safe recovery without leaking secrets.

## 1. End-to-end failure domains

```text
Git webhook → SCM event → Jenkins queue → agent → checkout
                                              ↓
                                      dependencies/build
                                              ↓
                                         test/package
                                              ↓
                                      artifact/deployment
```

A red build does not automatically indicate Jenkins infrastructure failure. Determine the first failed boundary and whether the failure is deterministic, transient, configuration-related or caused by an external dependency.

## 2. First-response workflow

1. Record build URL, job, branch, commit SHA, timestamp, environment and impact.
2. Check whether the job triggered at all; inspect webhook delivery before Pipeline logs.
3. Inspect the **first meaningful error** and stage where it occurred.
4. Compare successful builds for the same revision, agent image and plugin versions.
5. Correlate controller/agent logs, queue wait, SCM and artifact service health.
6. Test a single falsifiable hypothesis with a synthetic build or staging replay.
7. Apply an approved fix and verify a clean rerun.

Never print full environment variables, secret files or raw credentials in incident evidence.

## 3. Pipeline syntax and runtime errors

| Symptom | Suspect | Validation |
|---|---|---|
| Jenkinsfile parser error | Declarative syntax | Linter on exact core/plugins |
| Missing Pipeline step | Plugin absent/incompatible | Plugin inventory |
| Groovy sandbox rejection | Script approval/security | Approval audit |
| CPS serialization failure | Non-serializable object | Stack trace |
| Stage skipped | `when` or upstream failure | Stage conditions |
| Timeout | External dependency or capacity | Timing and logs |
| Retry loop | Unbounded retry logic | Pipeline source |
| Parallel branch failure | Shared workspace/state | Stage isolation |

Prefer reviewed changes in Git over interactive production edits. Avoid broad script approvals or disabling the sandbox to force a build.

## 4. Safe Jenkinsfile pattern

```groovy
pipeline {
  agent { label 'trusted-ci' }
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Test') {
      steps {
        sh './ci/test.sh'
      }
    }
    stage('Package') {
      steps {
        sh './ci/package.sh'
      }
    }
  }
  post {
    always {
      echo "Result: ${currentBuild.currentResult}"
    }
  }
}
```

The scripts are repository-specific and must exist and be executable on the agent. `disableConcurrentBuilds()` is appropriate only when concurrency is unsafe; it may increase queue wait.

## 5. SCM and webhook troubleshooting

Check:
- SCM delivery history and HTTP response (GitHub/GitLab).
- Correct webhook URL, reverse proxy, TLS and DNS.
- Repository/branch/refspec and multibranch indexing.
- Token permissions, deploy keys and organization access.
- Git server rate limits, availability and clone size.
- Agent Git binary/version, known-hosts policy and CA trust.

A successful webhook delivery does not guarantee a build if branch filters, permissions or triggers exclude the event. Never disable host key or TLS verification as a workaround.

## 6. Credentials and secret-provider failures

Classify errors into missing credential ID, wrong scope, expired/revoked secret, wrong credential type, insufficient SCM/registry permissions, vault/cloud secret provider outage, token audience mismatch and agent identity problems.

Safe pattern for a trusted shell step:

```groovy
withCredentials([string(credentialsId: 'lab-api-token', variable: 'API_TOKEN')]) {
  sh '''
    set +x
    ./ci/check-api.sh
  '''
}
```

Use a **synthetic** credential and avoid passing secret values as Groovy-interpolated command strings. Masking is best-effort, not a security boundary. Restrict untrusted PR code from accessing secrets and use least-privilege identities.

## 7. Agent environment and workspace failures

Common causes: missing CLI/JDK, wrong architecture, stale workspace, disk full, permission denied, wrong `PATH`, incompatible Docker socket access, package cache corruption, time skew, memory limits and shared workspaces across concurrent jobs.

Use immutable agent images and pin tool versions. Clean workspaces only after preserving necessary evidence and confirming cleanup will not destroy artifacts or concurrent work.

## 8. Build, test and artifact classification

- **Application failure:** compilation error, failing assertion, invalid code or schema.
- **Infrastructure failure:** agent disconnect, registry outage, filesystem error, unavailable build tool service.
- **Flaky failure:** nondeterministic tests, race conditions, external dependency jitter; requires repeated evidence.
- **Policy failure:** quality/security gate rejected output as designed.

Rerun only after classifying impact. A successful rerun does not by itself prove root cause or justify ignoring repeated flakiness.

## 9. Artifact and registry troubleshooting

Inspect authentication, repository URL, package coordinates, checksum, immutability policy, storage quota, proxy/TLS, upload timeout and artifact retention. Validate digest after publishing. Avoid overwriting immutable release tags or deleting artifacts without change approval.

## 10. Controlled diagnostics

```sh
git --version
java -version
df -h
id
env | cut -d= -f1 | sort
```

The final command prints **variable names only**; do not print values. Run in a disposable agent with approved permissions. Avoid enabling shell tracing around secrets.

## 11. Failure scenarios

| # | Symptom | First action |
|---|---|---|
| 01 | Webhook missing | Delivery history |
| 02 | Webhook 403 | Token/proxy auth |
| 03 | Wrong branch built | Refspec/branch filters |
| 04 | SCM clone 401 | Credential scope |
| 05 | Git TLS error | CA/trust |
| 06 | Git host key error | Approved known hosts |
| 07 | Rate limited SCM | Backoff/API budget |
| 08 | Jenkinsfile syntax error | Linter |
| 09 | Missing Pipeline step | Plugin inventory |
| 10 | Groovy approval blocked | Sandbox audit |
| 11 | CPS serialization failure | Stack trace |
| 12 | Agent label mismatch | Queue reason |
| 13 | Missing build tool | Agent image |
| 14 | Workspace permission denied | UID/GID |
| 15 | Disk full | Capacity |
| 16 | OOMKilled build | Agent limits |
| 17 | Flaky tests | Repeatability |
| 18 | Dependency registry unavailable | External health |
| 19 | Artifact upload 403 | Repository permissions |
| 20 | Secret provider timeout | Provider connectivity |

## 12. Five production runbooks

### A. Pipeline fails immediately
Inspect Jenkinsfile parsing, plugin step availability and sandbox approvals; compare last good commit and plugin set; fix through reviewed Git change; rerun synthetic and impacted build.

### B. SCM checkout or webhook outage
Check event delivery, branch filters, SCM availability, credentials and TLS; correct permissions/network; verify webhook trigger and checkout without exposing tokens.

### C. Credential or secret-provider incident
Identify credential ID/type/scope and provider health; avoid logging values; rotate/revoke if compromised; restore least privilege; verify negative and positive access tests.

### D. Agent/workspace failure
Inspect labels, tools, filesystem, resource limits and remoting; restore immutable agent image or isolated workspace; verify deterministic build.

### E. Artifact/test reliability incident
Separate application test failures from infrastructure; check test history, dependency health and artifact integrity; apply bounded retry only to known transient operations; confirm root cause and evidence.

## 13. RCA/COA evidence template

```text
Incident ID and severity:
Build URL / branch / commit:
First failed stage and UTC time:
Controller/agent image and plugin versions:
SCM webhook/checkout evidence:
Credential ID and scope (never secret value):
Error classification:
Hypotheses and tests:
Mitigation / rollback:
Verification:
Root cause:
Corrective actions / owner / due date:
```

## 14. Acceptance criteria

- [ ] First failed boundary identified.
- [ ] Webhook and SCM flow validated.
- [ ] Pipeline syntax and plugin dependencies checked.
- [ ] Credential ID/type/scope verified without disclosure.
- [ ] Agent tools, workspace and limits inspected.
- [ ] Application and infrastructure failures classified.
- [ ] Safe fix reviewed and applied.
- [ ] Clean representative build succeeds.
- [ ] Artifact integrity verified where relevant.
- [ ] RCA/COA and ownership documented.

**Companion:** [Chapter 073 hands-on lab](labs/073-jenkins-pipeline-scm-credentials-build-failure-troubleshooting-check.md).  
**Next:** Chapter 074 — Jenkins Agents, Kubernetes, Networking and Infrastructure Failure Troubleshooting.
