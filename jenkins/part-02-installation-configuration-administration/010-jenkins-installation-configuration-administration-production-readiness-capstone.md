# Chapter 010 — Jenkins Installation, Configuration and Administration Production Readiness Capstone

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 02:** Installation, Configuration and Administration  
**Chapter:** 010 / 100 — **Part 02 capstone**  
**Companion lab:** [010 — Jenkins Production Readiness Capstone Check](labs/010-jenkins-production-readiness-capstone-check.md)

> **Safety:** Execute the hands-on portion only on a disposable localhost controller. Enterprise TLS/SSO/production integration exercises are review or staging-only unless separately approved. Do not inject faults into production, expose controller backend ports, disable authentication or publish credentials.

## 1. Capstone mission

Demonstrate a secure, persistent, observable, recoverable Jenkins controller deployment by integrating Chapters 006–009. The deliverable is a **production-readiness evidence package**, not an unverified claim that a lab is production-ready.

### Prerequisite chapters

- [006 — Linux Packages and systemd](006-jenkins-installation-linux-packages-systemd.md)
- [007 — Docker and Containerized Controller Deployment](007-jenkins-docker-containerized-controller-deployment.md)
- [008 — Configuration Files, Environment Variables and JENKINS_HOME](008-jenkins-configuration-files-environment-variables-jenkins-home-management.md)
- [009 — Reverse Proxy, HTTPS, Networking and Access](009-jenkins-reverse-proxy-https-networking-access-configuration.md)

## 2. Target architecture

```text
                GitHub / GitLab / users
                        |
              TLS reverse proxy / SSO
              sanitized forwarding headers
                        |
               private Jenkins backend
                        |
                Controller (0 executors)
                   /     |       \
                JCasC  plugins   audit/metrics
                   \     |       /
                   encrypted persistent home
                     + protected keys
                        |
                  agent scheduler
                 /              \
          isolated VM agent    Kubernetes pod
                 \              /
                test / scan / build
                        |
                registry + GitOps PR

       monitoring + alerting + encrypted backup
                         |
                  clean-room restore
```

Standard Jenkins does not support active/active controllers sharing a single writable JENKINS_HOME. Availability planning must account for state, storage, failover fencing and restore time.

## 3. Production readiness control matrix

| Domain | Minimum acceptance requirement |
|---|---|
| Runtime and installation | Supported LTS, Java, OS/container image digest, signed packages, dedicated identity |
| State and persistence | Effective JENKINS_HOME, encrypted keys, durable volume, filesystem capacity |
| Configuration governance | JCasC, versioned plugin catalog, approved changes, rollback |
| Network and TLS | Private backend, canonical HTTPS URL, trusted proxy, valid cert chain |
| Authentication and authorization | SSO/MFA, named identities, RBAC, audited break-glass |
| Controller isolation | Zero built-in executors, isolated trusted/untrusted agents |
| SCM and webhooks | Signed delivery, least privilege, no deployment credentials for untrusted PRs |
| Monitoring and SLO | HTTP, JVM/GC, queue, agents, disk/inodes, plugin errors, backup freshness |
| Backup and DR | Consistent encrypted backup, keys, clean-room restore, RPO/RTO |
| Operations | Runbooks, change window, upgrade staging, ownership, escalation |

## 4. Lab deployment (disposable Docker)

The mutable `jenkins/jenkins:lts-jdk21` image is only for learning; pin a reviewed digest in production.

```bash
docker version
docker volume create jenkins-ch010-home
docker run -d --name jenkins-ch010 --restart=no \
  -p 127.0.0.1:8088:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch010-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch010
docker logs --tail 80 jenkins-ch010
docker port jenkins-ch010
```

Open `http://127.0.0.1:8088`, unlock privately and create a named lab admin. Set **Manage Jenkins → Nodes → Built-In Node → Number of executors = 0**.

## 5. Validate persistence and runtime identity

```bash
docker inspect jenkins-ch010 --format '{{.Config.Image}} {{.Config.User}}'
docker inspect jenkins-ch010 --format '{{json .Mounts}}'
docker exec jenkins-ch010 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"'
docker exec jenkins-ch010 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
docker stats --no-stream jenkins-ch010
```

Capture only redacted evidence. `docker inspect` can expose sensitive environment settings if misconfigured.

## 6. Pipeline smoke test

Create a Pipeline job `ch010-readiness-smoke` with:

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  stages {
    stage('Controller readiness') {
      steps { echo 'Jenkins controller has zero build executors.' }
    }
    stage('Configuration governance') {
      steps { echo 'Plugin versions, JCasC and backups require review.' }
    }
    stage('Network security') {
      steps { echo 'Production ingress requires trusted HTTPS and SSO.' }
    }
  }
}
```

This is a controller-coordinated, **no-agent** smoke test; it does not exercise actual agent builds. Production acceptance additionally requires an isolated agent test.

## 7. Linux/systemd production alternative

If deploying to a Linux VM rather than Docker, verify signed package repository, supported Java, dedicated `jenkins` service identity, `systemctl cat jenkins`, effective environment, persistent home ownership and `journalctl -u jenkins`. Do not assume package defaults are identical across distributions.

## 8. HTTPS and access readiness

Production review must validate certificate SAN/chain/expiry, canonical HTTPS Jenkins root URL, trusted proxy forwarding, restricted backend, SSO/MFA and least privilege, signed webhooks and approved agent transport. The localhost lab does **not** satisfy production TLS/SSO gates; mark those as design evidence or staging-verified, not passed by local HTTP.

## 9. Plugin, JCasC and secrets governance

Record approved Jenkins/Java/plugin versions and immutable image digest. Validate JCasC schema against installed plugins, review changes in Git and store credentials in protected secret sources. Do not put secrets into Dockerfile, Compose, Jenkinsfile, environment dumps or screenshots.

## 10. Backup and clean-room restore strategy

A recoverable controller needs consistent encrypted JENKINS_HOME, matching encryption keys, plugin catalog, Jenkins runtime and tested restore procedures. Backups must be stored off-controller with restricted access, retention and integrity checks. Rehearse restore in an isolated environment; verify login, credentials, jobs, Pipeline smoke and agent connectivity.

## 11. Capacity, SLOs and observability

Measure JVM heap/GC, CPU/memory, disk/inodes, controller HTTP availability, queue latency, agent capacity, plugin exceptions, webhook delivery and backup freshness. Establish business-specific SLOs and alert thresholds. An example 99.9% controller availability target is illustrative and not automatically suitable for every organization.

## 12. Twenty production-readiness failure scenarios

| # | Failure | Investigation | Safe response |
|---|---|---|---|
| 1 | Service cannot start | Check systemd/container logs, Java, plugin dependencies | Restore approved runtime or compatible backup |
| 2 | Controller has wrong home | Inspect env, mounts, unit and data identity | Stop writes and reattach correct home |
| 3 | Home directory unwritable | Inspect UID, ACL, SELinux and volume mode | Restore least privilege |
| 4 | Credentials cannot decrypt | Check encryption keys and matching snapshot | Restore complete protected backup |
| 5 | Disk/inode exhaustion | df -h, df -i, build retention | Expand or approved cleanup |
| 6 | Plugin load failure | Inspect core/Java/plugin version matrix | Restore tested catalog |
| 7 | JCasC schema mismatch | Validate plugin schema and YAML diff | Revert reviewed config |
| 8 | Controller executing builds | Inspect node executors and job labels | Set executors zero and migrate builds |
| 9 | Agent queue starvation | Inspect labels, resources and queue reason | Provision isolated agents |
| 10 | Reverse proxy 502 | Check upstream listener, health and proxy logs | Restore upstream |
| 11 | HTTPS redirect loop | Inspect root URL and forwarded headers | Correct trusted proxy |
| 12 | TLS certificate expired | Check chain, SAN and expiry | Renew approved cert |
| 13 | SSO login loop | Check callback URI, cookies and clock | Correct IdP/proxy mapping |
| 14 | Webhook rejected | Check signature, plugin endpoint and proxy | Restore signed delivery |
| 15 | Untrusted PR accesses secrets | Inspect trust boundary and credential scope | Revoke/rotate and isolate jobs |
| 16 | Docker socket exposed | Inspect mounts and agent permissions | Remove privileged socket |
| 17 | Container OOMKilled | Inspect stats, JVM heap and state | Profile/right-size |
| 18 | Backup stale or incomplete | Check backup job, keys and restore test | Run consistent backup and drill |
| 19 | Upgrade changes job behavior | Compare plugin/core/Java and smoke results | Restore compatible pre-upgrade state |
| 20 | Monitoring blind spot | Inspect scrape/auth/log pipeline | Restore telemetry and on-call alert |

## 13. Eight SRE operational runbooks

### RB-01 Controller startup outage

**Procedure:** Declare incident, capture logs/version/volume, isolate root cause, restore tested controller and verify login.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-02 Authentication or SSO incident

**Procedure:** Check proxy, canonical URL, IdP and RBAC; use audited break-glass, never disable security.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-03 Credential exposure

**Procedure:** Quarantine job, revoke/rotate, inspect logs and identity permissions, engage security.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-04 Plugin/JCasC regression

**Procedure:** Freeze changes, validate compatibility, revert approved bundle or restore full snapshot.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-05 TLS/proxy/webhook outage

**Procedure:** Check cert chain, headers, ingress and provider delivery; restore trusted route.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-06 Queue/agent outage

**Procedure:** Inspect queue, labels, remoting and cloud capacity; recover isolated agents.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-07 Storage and DR incident

**Procedure:** Inspect disk/inodes, snapshot/key inventory; restore to clean room and test representative jobs.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

### RB-08 Production change acceptance

**Procedure:** Validate gates, record approvals, owners, evidence, rollback decision and SLO handoff.

**Exit criteria:** authenticated UI, persistent state, zero controller executors, approved TLS/security architecture, healthy agents, monitored backup and incident/change evidence.

## 14. Ten mandatory acceptance gates

| Gate | Required evidence | Lab vs production |
|---|---|---|
| G1 | Supported runtime and image/package provenance | Lab inspect; production approval |
| G2 | Durable, protected JENKINS_HOME | Lab validate; production storage review |
| G3 | Named admin, authentication and least privilege | Lab verify; production SSO/RBAC |
| G4 | Controller executors zero | Lab verify |
| G5 | Private backend and canonical HTTPS ingress | Lab private port; production TLS staging test |
| G6 | Reviewed plugins, JCasC and secret boundaries | Lab design; staging validate |
| G7 | Successful Pipeline smoke and agent isolation | Lab no-agent; production agent test |
| G8 | Metrics, alerts, SLO and on-call ownership | Design plus operational evidence |
| G9 | Consistent backup and tested clean-room restore | Design plus actual production rehearsal |
| G10 | Incident runbooks, rollback and signoff | Evidence and owner |

**Critical:** A lab-only run can pass the educational assessment, but **cannot** certify production readiness without verified production/staging evidence for the relevant gates.

## 15. Scoring rubric — 100 points

| Domain | Points |
|---|---:|
| Runtime and installation integrity | 15 |
| State persistence and security | 20 |
| Configuration, plugins and secrets | 15 |
| TLS, access and network boundaries | 15 |
| Pipeline/agent design and smoke test | 10 |
| Monitoring, incident response and DR | 15 |
| Cleanup, evidence and handoff | 10 |
| **Total** | **100** |

**Educational pass:** 90+ with no security-critical failures and honest lab-vs-production gate status. Production go-live additionally requires independent approval and all production gates verified.

## 16. Change and rollback plan

1. Capture approved versions, immutable image/package identifiers and config diff.
2. Confirm consistent encrypted backup and key escrow.
3. Stage Jenkins/Java/plugin/JCasC changes with smoke and agent tests.
4. Schedule quiet-down and maintenance, with on-call coverage.
5. Apply reviewed change, validate login, proxy/TLS, webhooks and representative jobs.
6. Roll back using the compatible pre-change snapshot if persistent migrations make downgrade unsafe.
7. Record signoff, residual risks and owner.

## 17. Cleanup

```bash
docker stop jenkins-ch010
docker rm jenkins-ch010
# Destructive: remove only after confirming the volume is exclusively lab-owned.
docker volume rm jenkins-ch010-home
```

**Part 02 completion:** Jenkins Installation, Configuration and Administration — Chapters 006–010.

**Next:** Chapter 011 — Jenkins Controller Architecture, Responsibilities and Operational Boundaries, beginning Part 03 — Controller, Agents and Executors.
