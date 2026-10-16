# Chapter 018 — Jenkins Build Workspaces, Artifacts and Test Reports

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 04:** Jenkins Jobs and Pipeline Fundamentals  
**Chapter:** 018 / 100  
**Companion lab:** [018 — Workspaces, Artifacts and Test Reports Check](labs/018-jenkins-workspaces-artifacts-test-reports-check.md)

> **Safety:** Run controller demonstrations only in a disposable localhost Jenkins. Workspace-dependent commands must execute on an isolated agent, never on the built-in controller node. Do not archive secrets or delete shared workspaces.

## 1. Learning objectives

Explain Jenkins workspace allocation and lifecycle; design isolated concurrent builds; archive and fingerprint artifacts; publish JUnit test reports; understand stash/unstash, retention, provenance, external repositories and storage SRE troubleshooting.

## 2. Architecture and data flow

```text
SCM -> Jenkins controller (0 executors)
                |
         queue / node label
                |
          isolated agent
                |
        workspace checkout
                |
        build -> test -> package
          |       |       |
          |     JUnit   artifacts
          |       |       |
          +-------+-------+
                  |
        controller metadata/results
                  |
      artifact store / test dashboard
                  |
      retention + cleanup + audit
```

A **workspace** is an agent-side working directory; it is not a durable artifact repository. Build records and selected archived outputs may be stored under controller-managed build data depending on artifact manager configuration.

## 3. Workspace lifecycle

1. Jenkins allocates an eligible agent/executor and a workspace.
2. SCM checkout and build tools create files.
3. Tests produce machine-readable reports.
4. Artifacts and reports are published before ephemeral agent teardown.
5. Job-owned workspace cleanup runs under approved policy.
6. External artifact lifecycle and build retention are managed separately.

Concurrent builds can use distinct workspace variants; never assume a hard-coded workspace path or safe shared directory. Prefer `pwd()` and relative paths.

## 4. Workspaces versus artifacts versus stashes

| Mechanism | Purpose | Important limitation |
|---|---|---|
| Workspace | Temporary checkout and build files | Agent-local, mutable, may disappear |
| archiveArtifacts | Publish selected build outputs | Not a substitute for durable release repository |
| fingerprint | Track selected artifact checksums/usage | Does not provide cryptographic signing |
| junit | Parse JUnit-compatible XML test results | Requires appropriate plugin and valid XML |
| stash/unstash | Move small files between stages in same run | Avoid large payloads; controller cost |
| External artifact repository | Versioned, immutable release assets | Requires identity, retention and provenance |

## 5. Disposable controller setup

```bash
docker volume create jenkins-ch018-home
docker run -d --name jenkins-ch018 --restart=no \
  -p 127.0.0.1:8096:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch018-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch018
docker logs --tail 60 jenkins-ch018
docker port jenkins-ch018
```

The mutable LTS tag is for disposable learning; pin a reviewed digest for production. Unlock privately at `http://127.0.0.1:8096`, create a named admin and set built-in executors to **0**.

## 6. Controller-only smoke (no workspace)

```groovy
pipeline {
  agent none
  stages {
    stage('Orchestration') {
      steps {
        echo 'Artifacts and tests require an agent workspace.'
      }
    }
  }
}
```

This can succeed without an agent. It does not test actual archive, JUnit or workspace execution.

## 7. Real agent-backed build, JUnit and artifacts

Requires a pre-provisioned trusted Linux agent labeled `lab-linux` with shell, `sha256sum` and a writable workspace. The Pipeline Utility Steps plugin is not required for this example; the JUnit plugin must be available.

```groovy
pipeline {
  agent { label 'lab-linux' }
  options {
    timestamps()
    timeout(time: 10, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10', artifactNumToKeepStr: '5'))
  }
  stages {
    stage('Build and test') {
      steps {
        sh '''
          set -eu
          mkdir -p dist reports
          printf "example artifact\n" > dist/package.txt
          sha256sum dist/package.txt > dist/SHA256SUMS
          cat > reports/junit.xml <<'EOF'
<testsuite name="example" tests="1" failures="0">
  <testcase classname="example" name="smoke"/>
</testsuite>
EOF
        '''
      }
    }
    stage('Publish') {
      steps {
        junit testResults: 'reports/*.xml'
        archiveArtifacts artifacts: 'dist/*', fingerprint: true
      }
    }
  }
  post {
    always {
      echo 'Check artifact and test result tabs.'
    }
  }
}
```

For production use real test-runner output, validated checksums and an approved immutable artifact repository. The static XML is a **lab fixture**, not evidence of a real test suite.

## 8. Stash and unstash between agents

```groovy
pipeline {
  agent none
  stages {
    stage('Prepare') {
      agent { label 'lab-linux' }
      steps {
        sh 'mkdir -p handoff && echo payload > handoff/input.txt'
        stash name: 'handoff', includes: 'handoff/**'
      }
    }
    stage('Consume') {
      agent { label 'lab-linux' }
      steps {
        unstash 'handoff'
        sh 'cat handoff/input.txt'
      }
    }
  }
}
```

Stashes are scoped to a Pipeline run; do not use them as long-term artifact storage. For large payloads, prefer an external repository or object storage integration.

## 9. Artifact security and integrity

- Archive allowlisted relative paths only; exclude `.env`, private keys, tokens, kubeconfigs and secret files.
- Compute SHA-256 and retain provenance metadata for released outputs.
- Restrict artifact download permissions and audit access.
- Keep artifacts immutable in release repositories, with retention/legal hold as applicable.
- Fingerprinting tracks Jenkins relationships but does not replace signing, attestation or SBOMs.

## 10. Test reports and build result semantics

The `junit` step publishes JUnit-compatible XML and typically marks a build **UNSTABLE** when test failures are reported (subject to configuration). Distinguish test failures from infrastructure errors and missing reports. Never fabricate passing XML for real production acceptance.

## 11. Storage and FinOps

Track workspace bytes/inodes, build output growth, archived artifact sizes, controller disk usage, external repository retention and egress. Set size budgets, artifact retention and cleanup schedules. Avoid aggressive deletion without checking audit/legal retention.

## 12. Monitoring and alerting

Alert on workspace disk/inode pressure, artifact publication failures, missing JUnit reports, oversized stashes, archive storage growth, unexpected build result changes, checksum mismatches and secret scan findings.

## 13. Twenty failure scenarios

| # | Symptom | Investigation | Safe response |
|---|---|---|---|
| 1 | Workspace missing | Agent allocation, remote root and path | Restore agent and workspace |
| 2 | Workspace permission denied | UID/GID, ACL and volume mount | Fix least-privilege ownership |
| 3 | Workspace disk full | df -h, quota and build output | Approved cleanup or capacity |
| 4 | Workspace inode exhaustion | df -i and small-file growth | Reduce files or expand storage |
| 5 | Concurrent jobs overwrite files | Workspace isolation and concurrency | Use unique workspaces or serialize |
| 6 | Stale workspace contaminates build | Checkout and cleanup policy | Use clean isolated workspace |
| 7 | Agent pod removed before archive | Pod lifecycle and post-stage ordering | Archive before teardown |
| 8 | Archive pattern matches nothing | Relative path and glob syntax | Correct path and verify file |
| 9 | Artifact retention unexpectedly deletes | Build discarder and external retention | Correct retention policy |
| 10 | Huge artifacts saturate controller | Artifact size and storage backend | External repository/object store |
| 11 | Artifact contains credentials | Scan output, file ownership and masking | Quarantine and rotate secrets |
| 12 | Artifact checksum mismatch | Build manifest and digest | Rebuild from trusted source |
| 13 | JUnit XML missing | Test runner output and junit glob | Generate valid XML |
| 14 | JUnit XML malformed | Parser error and schema output | Repair test report generator |
| 15 | Test failure marked SUCCESS | JUnit plugin availability and result semantics | Publish tests and enforce policy |
| 16 | Pipeline post always fails | Post step logs and workspace availability | Handle cleanup/report failure explicitly |
| 17 | Stash too large | Stash size, transfer and controller load | Use external artifact storage |
| 18 | Cross-node unstash fails | Stash scope and build lifecycle | Keep stash within same run |
| 19 | Cleanup removes shared workspace | Delete path, job ownership and node | Restrict cleanup to job-owned paths |
| 20 | Plugin/core upgrade changes reports | Compatibility and baseline results | Rollback tested plugin bundle |

## 14. Eight SRE runbooks

### RB-01 Workspace permission or disk

**Procedure:** Inspect node, UID/GID, mount, df and inode pressure; restore safe workspace without broad chmod.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-02 Artifact publication failure

**Procedure:** Validate workspace-relative patterns, stage order, agent state and archive logs; rerun idempotently.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-03 Missing or invalid JUnit reports

**Procedure:** Check test runner output, XML syntax, plugin availability and failure semantics.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-04 Artifact integrity incident

**Procedure:** Compare SHA-256, provenance, build inputs and immutable repository records; quarantine mismatches.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-05 Credential leakage in artifacts

**Procedure:** Stop publication, revoke/rotate exposed secrets, preserve redacted evidence and review scanners.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-06 Retention and storage cost

**Procedure:** Audit discarder, external repository retention, object lifecycle and legal holds.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-07 Concurrent workspace collision

**Procedure:** Inspect executor/job concurrency, workspace allocation and cleanup; isolate and rerun.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

### RB-08 Operational handoff

**Procedure:** Record workspace owner, archive path, test report policy, alerts, retention and rollback.

**Exit criteria:** isolated workspace, valid reports, expected artifacts, integrity checks, retention controls and redacted incident evidence.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Built-in controller executors zero |
| G2 | Workspace, artifact and stash differences explained |
| G3 | No-agent orchestration smoke succeeds |
| G4 | Agent-backed archive/JUnit Pipeline reviewed |
| G5 | Workspace isolation and concurrency policy documented |
| G6 | Artifact allowlist and integrity controls designed |
| G7 | JUnit UNSTABLE/FAILURE semantics explained |
| G8 | Storage retention and FinOps budget defined |
| G9 | Three incidents and rollback rehearsed |
| G10 | Cleanup and redacted evidence complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Workspace lifecycle and isolation | 20 |
| Artifact publication and integrity | 25 |
| JUnit/test report semantics | 20 |
| Stash/retention and cost | 15 |
| Troubleshooting and monitoring | 10 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates. Local controller smoke is not proof of agent-backed archive/test execution.

## 17. Cleanup

```bash
docker stop jenkins-ch018
docker rm jenkins-ch018
# Destructive only after confirming exclusive lab ownership:
docker volume rm jenkins-ch018-home
```

**Next:** Chapter 019 — Jenkins Build History, Logs, Notifications and Job Lifecycle Management.
