# Chapter 018 — Hands-On Lab: Workspaces, Artifacts and Test Reports

**Parent:** [Chapter 018](../018-jenkins-build-workspaces-artifacts-test-reports.md)

## Safety and prerequisites

Use a disposable controller bound to localhost. Agent-backed archive/JUnit and stash/unstash examples require an approved isolated Linux agent; without one, perform design review only. Never enable built-in controller executors.

## Exercise 01 — Docker prerequisites

```bash
docker version
docker ps
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Docker available. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 02 — Create controller volume

```bash
docker volume create jenkins-ch018-home
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Volume exists. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 03 — Start private controller

```bash
docker run -d --name jenkins-ch018 --restart=no -p 127.0.0.1:8096:8080 --memory 4g --cpus 2 --mount source=jenkins-ch018-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Controller started. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 04 — Inspect startup

```bash
docker logs --tail 60 jenkins-ch018
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** No fatal error. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 05 — Check loopback listener

```bash
docker port jenkins-ch018
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Local-only listener. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch018 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock at http://127.0.0.1:8096 privately; never record the password.

**Pass:** Private unlock; no secret capture. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 07 — Set built-in executors zero

```bash
docker ps --filter name=jenkins-ch018
```

**Operator action:** Set Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Controller executors zero. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 08 — Inspect runtime image

```bash
docker inspect jenkins-ch018 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Image and user recorded. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 09 — Inspect persistent home

```bash
docker inspect jenkins-ch018 --format '{{json .Mounts}}'
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Home mount verified. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 10 — Inspect disk and inodes

```bash
docker exec jenkins-ch018 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Disk baseline. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 11 — Create no-agent smoke Pipeline

```bash
docker logs --tail 20 jenkins-ch018
```

**Operator action:** Create a Pipeline job with the no-agent smoke from the chapter.

**Pass:** Smoke job saved. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 12 — Run no-agent Pipeline

```bash
docker stats --no-stream jenkins-ch018
```

**Operator action:** Run the smoke and capture result; this does not test artifact publication.

**Pass:** Orchestration succeeds. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 13 — Review agent-backed artifact Pipeline

```bash
docker inspect jenkins-ch018 --format '{{.State.Status}}'
```

**Operator action:** Review the agent-backed Pipeline in the chapter; execute only on a separately approved lab-linux agent.

**Pass:** Workspace requirement explained. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 14 — Review archive glob and retention

```bash
docker logs --tail 20 jenkins-ch018
```

**Operator action:** Verify relative archive glob and retention; do not archive secrets.

**Pass:** Artifact policy documented. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 15 — Review JUnit publishing

```bash
docker inspect jenkins-ch018 --format '{{.Config.Image}}'
```

**Operator action:** Explain JUnit XML, plugin requirement and UNSTABLE semantics.

**Pass:** Test report semantics documented. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 16 — Review stash and unstash

```bash
docker stats --no-stream jenkins-ch018
```

**Operator action:** Explain same-run stash scope and large-payload caveat.

**Pass:** Same-run cross-node transfer understood. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 17 — Review cleanup safety

```bash
docker exec jenkins-ch018 sh -c 'df -h /var/jenkins_home'
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** Only job-owned cleanup allowed. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 18 — Review checksum and provenance

```bash
docker logs --tail 30 jenkins-ch018
```

**Operator action:** Record redacted evidence; mark unexecuted external-agent work as design-only.

**Pass:** SHA-256 and repository policy. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 19 — Three incident table tops

```bash
docker logs --tail 40 jenkins-ch018
```

**Operator action:** Tabletop: disk full, missing artifacts and malformed JUnit; document rollback.

**Pass:** Workspace, artifact and JUnit incidents analyzed. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch018
docker rm jenkins-ch018
```

**Operator action:** Remove the dedicated volume only after verifying exclusive lab ownership.

**Pass:** Controller removed safely. **Rollback:** revert lab-only changes or safely stop/remove disposable resources.

## Controller-only smoke Jenkinsfile

```groovy
pipeline {
  agent none
  stages {
    stage('Orchestration') {
      steps { echo 'Workspace steps run on isolated agents.' }
    }
  }
}
```

## Agent-backed artifact and JUnit acceptance

The complete executable agent-backed Jenkinsfile is in the parent chapter. On an approved `lab-linux` agent, verify:

- `dist/package.txt` and `dist/SHA256SUMS` exist in the agent workspace.
- `reports/junit.xml` is valid and the JUnit plugin publishes one synthetic lab test.
- `archiveArtifacts` publishes only `dist/*`.
- Artifact fingerprint is recorded, and the build history retention policy is visible.
- The synthetic passing XML is **not** evidence of a real production test suite.

## Failure decision matrix

| Failure | Evidence | Safe recovery |
|---|---|---|
| Permission denied | Agent UID/GID and mount ACL | Least-privilege ownership fix |
| Disk/inodes full | df -h / df -i | Approved cleanup/expansion |
| Missing artifact | Archive glob and workspace path | Correct relative path |
| JUnit XML invalid | XML parser and test runner output | Fix report generator |
| UNSTABLE build | Failed test case report | Diagnose test failure |
| Secret in archive | Scan findings and download audit | Quarantine, revoke/rotate |
| Huge stash | Transfer time and controller load | External artifact storage |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Workspace lifecycle | 20 |
| Artifact publication/integrity | 25 |
| JUnit/test reports | 20 |
| Stash/retention/cost | 15 |
| Incident response | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and all security-critical gates.

## Evidence template

```text
Operator/date:
Controller URL/binding:
Built-in executors:
JENKINS_HOME volume:
Controller-only Pipeline result:
Agent-backed build (Executed / Design only):
Artifact paths and SHA-256:
JUnit XML and test report:
Stash/unstash review:
Workspace cleanup policy:
Artifact retention/cost:
Three incident diagnoses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 019 — Jenkins Build History, Logs, Notifications and Job Lifecycle Management.
