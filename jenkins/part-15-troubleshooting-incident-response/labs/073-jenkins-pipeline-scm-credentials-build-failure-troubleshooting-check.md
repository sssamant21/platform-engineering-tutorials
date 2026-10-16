# Chapter 073 — Hands-on Lab: Pipeline, SCM, Credentials and Build Failure Recovery

**Environment:** Disposable Jenkins LTS, isolated Git repository, synthetic credentials, trusted test agent and test artifact registry. Never inject faults into production.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory core, plugins and agent image | Baseline |
| 02 | Run known-good synthetic Pipeline | Build URL |
| 03 | Record stage timings and first failure | Timeline |
| 04 | Validate Jenkinsfile syntax | Lint |
| 05 | Inject Declarative syntax error | Log |
| 06 | Restore syntax and rerun | Recovery |
| 07 | Inspect SCM webhook delivery | Event |
| 08 | Simulate wrong branch filter | Result |
| 09 | Correct branch/refspec | Recovery |
| 10 | Simulate missing synthetic SCM credential | Error |
| 11 | Restore credential scope | Result |
| 12 | Validate TLS/host key without bypass | Evidence |
| 13 | Simulate missing build tool in agent image | Error |
| 14 | Restore pinned tool image | Result |
| 15 | Simulate workspace permission issue | Error |
| 16 | Restore correct UID/GID | Result |
| 17 | Inject flaky synthetic test | Test history |
| 18 | Simulate test artifact upload failure | Error |
| 19 | Recover artifact upload and verify digest | Digest |
| 20 | Complete incident RCA/COA and handover | Report |

## 12 troubleshooting drills

1. Webhook not delivered.
2. Wrong branch trigger.
3. SCM checkout authentication failure.
4. Git TLS/known-hosts failure.
5. Jenkinsfile syntax error.
6. Missing Pipeline step.
7. Groovy sandbox approval.
8. Missing credential ID.
9. Secret provider timeout.
10. Agent tool mismatch.
11. Workspace permission denied.
12. Artifact registry failure.

## Safe diagnostic commands

```sh
git --version
java -version
df -h
id
env | cut -d= -f1 | sort
```

The environment command lists names only. Do not log secret values or enable shell tracing around credentials.

## Evidence worksheet

```text
UTC timestamp:
Jenkins core/plugins:
Build URL / branch / commit:
Webhook delivery:
First failed stage:
Agent image/tool versions:
Credential ID and scope (no value):
Failure category:
Hypothesis and test:
Fix and rollback:
Clean rerun:
Artifact digest:
RCA/COA owner:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] SCM and Pipeline failures distinguished.
- [ ] Credentials tested without exposure.
- [ ] Agent/workspace failures recovered.
- [ ] Test/application versus infrastructure classified.
- [ ] Representative clean build succeeds.
- [ ] RCA/COA and reviewer sign-off complete.

**Related:** [Chapter 073 — Jenkins Pipeline, SCM, Credentials and Build Failure Troubleshooting](../073-jenkins-pipeline-scm-credentials-build-failure-troubleshooting.md).
