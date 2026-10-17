# Chapter 083 — Jenkins Core, Plugin and Java Upgrades with Compatibility Testing and Rollback

**Part 17 — Backup, Restore, Upgrades and Disaster Recovery**  
**Audience:** Jenkins SRE/DBRE, DevOps/platform engineers, security and change managers  
**Prerequisites:** Chapters 081–082, disposable Jenkins LTS controller, version-controlled JCasC and plugin list, synthetic pipelines, tested restore procedure.

## Outcomes

Design and execute a controlled Jenkins core, plugin and Java upgrade. Inventory dependencies, calculate compatibility risk, build a reproducible controller image, test in staging, establish rollback checkpoints, deploy with a single active writer and validate post-upgrade reliability.

> **Production guardrail:** Never run two Jenkins controllers simultaneously against the same writable `JENKINS_HOME`. A rollback to an older core/plugin set against state already migrated by a newer version is **not guaranteed safe**. Prefer restoring a compatible pre-upgrade backup to a separate clean volume after fencing the failed writer.

## 1. Upgrade architecture

```text
  Jenkins LTS + Java runtime + plugin dependency graph + JCasC
                          |
                 immutable build manifest
                          |
              security/compatibility review
                          |
          staging clone of sanitized Jenkins state
                          |
       plugin loading + auth + pipelines + agents
                          |
              pre-change consistent backup
                          |
          one active production controller writer
                          |
       smoke/SLO validation → promote or recover
```

Jenkins core, Java runtime, plugins and agent runtimes are a compatibility **set**, not independent knobs. Check the release-specific Jenkins Java support policy and each plugin's minimum Jenkins core, Java and dependency requirements before pinning versions. Use supported LTS releases and review security advisories.

## 2. Upgrade inventory and decision record

Record: current/target Jenkins core and Java, plugin IDs and versions, transitive dependencies, disabled/deprecated plugins, JCasC schema, security realm/RBAC, credential providers, controller/agent Java versions, remoting compatibility, Kubernetes plugin/pod templates, SCM and artifact integrations, persistent storage driver, backup ID and rollback owner.

| Change | Primary risk | Validation |
|---|---|---|
| Jenkins LTS | state format and behavior | staging restore and core smoke |
| Java runtime | unsupported runtime/JVM flags | supported matrix, startup, GC |
| Plugin upgrades | dependencies/API/JCasC changes | pinned dependency resolution |
| Agent images | remoting/Java/tools | representative jobs |
| JCasC | removed/renamed configuration | validation and authorization tests |
| Authentication | SSO/LDAP/RBAC drift | positive and negative access tests |
| Controller image | OS/CA/TLS libraries | SCM, registry, identity connectivity |

Do not rely on a version-number comparison alone to decide whether rollback is safe.

## 3. Plugin dependency management

- Maintain a reviewed, version-pinned plugin list and controller image digest.
- Use the official Jenkins plugin installation manager in a reproducible image build; resolve dependencies during CI, not opportunistically during production startup.
- Review plugin health, deprecations, advisories and minimum core requirements.
- Prefer small, tested upgrade batches for high-risk changes.
- Detect JCasC field changes and Groovy/shared-library behavior drift.
- Retain the **full** previous core/plugin/Java/image manifest alongside a consistent pre-change backup.

Example Dockerfile for a **lab**; substitute reviewed supported versions and image digest:

```dockerfile
ARG JENKINS_IMAGE=jenkins/jenkins:lts-jdk17
FROM ${JENKINS_IMAGE}
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
```

The tag above is illustrative, not a statement that JDK 17 supports every future Jenkins LTS. Production should use a tested supported base-image digest and explicit versions.

Example `plugins.txt` (replace with compatible tested versions before building):

```text
configuration-as-code
workflow-aggregator
git
kubernetes
credentials
matrix-auth
```

Unpinned entries are acceptable only for initial lab discovery; production should lock resolved versions and review dependency changes.

## 4. Pre-upgrade readiness checklist

1. Approve maintenance window, on-call owner, impact and communications.
2. Verify current supported Java/Jenkins/plugin compatibility and advisory status.
3. Snapshot/backup Jenkins home with a documented consistency method.
4. Verify encryption keys, manifests, retention and checksum.
5. Restore to **isolated** staging state and prove credentials decrypt.
6. Build target controller image with pinned dependencies and scan it.
7. Validate JCasC, authorization, SCM/webhooks, agents and critical jobs.
8. Capture baseline queue p95, agent readiness, heap/GC, startup time and external synthetic CI.
9. Define abort conditions and immutable rollback artifacts.
10. Confirm original controller fencing and **one active writer** during any cutover.

## 5. Executable inspection commands

```bash
# Execute against a disposable controller with approved credentials.
java -version
docker image inspect jenkins/jenkins:lts-jdk17 --format '{{.Id}}' 2>/dev/null || true
kubectl -n jenkins get pods -o wide
kubectl -n jenkins get pvc
kubectl -n jenkins get events --sort-by=.lastTimestamp
```

Inspect Jenkins plugin versions through the authenticated API using a restricted token, without logging the token:

```bash
: "${JENKINS_URL:?}"
: "${JENKINS_USER:?}"
: "${JENKINS_API_TOKEN:?}"
curl --fail --silent --show-error \
  --user "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/pluginManager/api/json?depth=1" \
  | python3 -c 'import json,sys; x=json.load(sys.stdin); print("\n".join(sorted(p["shortName"]+"="+p["version"] for p in x.get("plugins",[]))))'
```

Protect the output if plugin inventory is sensitive; do not expose tokens in command traces or logs.

## 6. Staging acceptance matrix

| Gate | Minimum proof |
|---|---|
| Core/Java compatibility | startup and logs without incompatible runtime errors |
| Plugin dependency graph | no failed or missing mandatory plugins |
| JCasC | clean load and configuration diff reviewed |
| Authentication | approved admin login and negative unauthorized access |
| Credentials | decrypt and use synthetic secrets without printing values |
| SCM | checkout, webhook delivery and credential isolation |
| Pipelines | declarative, scripted and shared-library smoke |
| Kubernetes agents | pod provisioning, remoting and cleanup |
| Artifacts | publish and checksum |
| Controller state | jobs/history/config present and coherent |
| Reliability | queue/agent latency and synthetic CI within thresholds |
| Backup recovery | isolated restore of pre-upgrade state demonstrated |

Test interrupted Pipeline behavior separately; not every Pipeline step is resumable. Retrying non-idempotent deploy/release operations can cause duplicate side effects.

## 7. Production rollout and rollback decision tree

```text
Prechecks pass?
  no → block change
  yes → consistent backup + verify + drain/stop/fence writer
         |
       start target image with single writable home
         |
       smoke + SLO gates pass?
         yes → monitor + sign off
         no  → stop/fence new controller
               |
             determine state migration/compatibility
               |
             restore compatible pre-change backup to clean state
               |
             start previous pinned image with one writer
               |
             smoke, audit and reconcile work after backup point
```

Rollback may lose Jenkins changes made after the backup. Document reconciliation for queued builds, webhook deliveries, artifacts and deployment side effects. Do not simply downgrade binaries over a potentially migrated live home.

## 8. Monitoring and acceptance

Monitor controller external availability, boot time, plugin load errors, Java heap/GC, CPU, storage I/O, queue p95, agent provisioning, build interruption, webhook errors, authentication failures and synthetic Pipeline success. Annotate change start/end and evaluate pre/post baselines.

## 9. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Jenkins will not start | Java/core compatibility |
| 02 | Plugin requires newer core | dependency metadata |
| 03 | Plugin fails to load | logs/transitive dependencies |
| 04 | JCasC rejects key | schema migration |
| 05 | Credentials cannot decrypt | key custody |
| 06 | Admin login broken | SSO/RBAC |
| 07 | Unauthorized user gains access | security diff |
| 08 | Kubernetes agents Pending | pod template/quota |
| 09 | Remoting handshake fails | agent Java/remoting |
| 10 | Pipeline compilation fails | DSL/shared library |
| 11 | Webhook fails | endpoint/CSRF/SCM |
| 12 | TLS handshake error | CA/JVM truststore |
| 13 | Artifact upload fails | plugin/registry |
| 14 | Startup too slow | plugin initialization/probes |
| 15 | JVM OOM | heap/GC/limits |
| 16 | PVC mount blocked | zone/CSI/permissions |
| 17 | Downgrade corrupts state | restore from pre-change backup |
| 18 | Old and new writers overlap | fencing |
| 19 | Backup missing or inconsistent | recovery gate |
| 20 | Rollback succeeds but jobs missing | RPO/reconciliation |

## 10. Six operational runbooks

### A. Upgrade preflight failure
Block rollout, identify incompatible core/Java/plugins, correct pins, rerun staging matrix and secure approval.

### B. Startup/plugin failure
Preserve logs and manifests, identify first dependency failure, stop target controller, revert via compatible pre-change restore if state changed.

### C. Authentication regression
Restrict ingress if necessary, use approved audited break-glass procedure, restore prior security config and run negative authorization tests.

### D. Agent/Pipeline regression
Inspect remoting, pod templates, plugin changes and Java versions; pause affected jobs, revert agent/controller change and validate critical CI.

### E. Failed production rollout
Declare incident, fence writer, restore pre-change backup to clean volume, start pinned prior image, verify state and reconcile external side effects.

### F. Post-upgrade acceptance
Review error budget, synthetic CI, queue/agent p95, backup readiness, security audit, residual risk and COA; obtain sign-off.

## 11. 100-point upgrade readiness assessment

| Domain | Points |
|---|---:|
| Inventory, supported compatibility and dependency review | 20 |
| Reproducible image/plugin/JCasC build | 15 |
| Consistent backup and isolated restore | 20 |
| Staging functional and security validation | 20 |
| Controlled rollout, fencing and rollback | 15 |
| Monitoring, evidence, RCA/COA and sign-off | 10 |
| **Total** | **100** |

Suggested pass **85/100**, with mandatory gates: verified backup, isolated restore, single active writer, authentication negative test, critical Pipeline success, and tested rollback. Unexecuted gates are **blocked**, not passed.

## 12. Evidence template

```text
UTC/change owner/approval:
Current core/Java/plugins/image digest:
Target core/Java/plugins/image digest:
JCasC Git SHA and configuration diff:
Compatibility and advisory review:
Backup ID/checksum/restore result:
Single-writer/fencing proof:
Staging login/RBAC/credentials/SCM/agents:
Synthetic Pipeline/artifact checksum:
Baseline and post-upgrade SLIs:
Abort threshold and rollback result:
RPO/RTO and reconciliation:
Score/COA/reviewer sign-off:
```

**Companion:** [Chapter 083 hands-on lab](labs/083-jenkins-core-plugin-java-upgrades-compatibility-testing-rollback-check.md).  
**Next:** Chapter 084 — Jenkins Disaster Recovery Automation, Cross-Region Restore and Failover Validation.
