# Chapter 008 — Jenkins Configuration Files, Environment Variables and JENKINS_HOME Management

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 02:** Installation, Configuration and Administration  
**Chapter:** 008 / 100  
**Companion lab:** [008 — Jenkins Configuration and JENKINS_HOME Check](labs/008-jenkins-configuration-jenkins-home-check.md)

> **Safety:** Inspect only a disposable controller. JENKINS_HOME contains encryption keys and sensitive state. Never publish raw config.xml, credentials.xml, secrets/, API tokens or user records. Do not directly edit live XML or attach the same writable home to two controllers.

## 1. Objectives

Identify Jenkins configuration files and their ownership, distinguish process environment from global configuration and Pipeline environment, inspect effective JENKINS_HOME, apply reviewed systemd/Docker overrides, use JCasC, prevent drift, troubleshoot persistence and perform secure backup/restore.

## 2. Configuration layers and precedence

```text
Infrastructure / runtime configuration
   |-- systemd service + drop-ins
   |-- Docker image, args, mounts, env
   |-- Kubernetes Pod, ConfigMap, Secret
   |
Jenkins controller configuration
   |-- JENKINS_HOME XML/state
   |-- JCasC (if installed/configured)
   |-- approved init.groovy.d scripts
   |-- UI/API administrative changes
   |
Job and Pipeline configuration
   |-- Jenkinsfile in SCM
   |-- job/folder settings
   |-- Pipeline environment / credentials binding
   |
Isolated agent process environment
```

**Important:** there is no universal precedence rule across all plugins and runtime layers. Some settings are loaded from XML, overwritten by JCasC on startup/reload, or changed by approved scripts/UI. Establish a source-of-truth policy and verify behavior on the exact Jenkins/plugin versions.

## 3. JENKINS_HOME directory inventory

| Path | Typical content | Security/operational note |
|---|---|---|
| `config.xml` | Global Jenkins settings and security configuration | Sensitive; controller-owned; backup and change-control |
| `jobs/<job>/config.xml` | Job definition and properties | May contain sensitive metadata; use approved SCM/JCasC/Job DSL |
| `nodes/` | Static agent definitions and configuration | Protect agent secrets and connection settings |
| `plugins/` | Installed plugin archives and expanded state | Pin versions, validate dependencies and compatibility |
| `secrets/` | Encryption keys, credentials support files | Highly sensitive; never commit, print or expose |
| `credentials.xml` | Encrypted credential records and metadata | Encryption keys required for restore; limit access |
| `users/` | User settings and identity metadata | Sensitive; honor privacy and access controls |
| `fingerprints/` | Artifact/build fingerprints | Retention and disk growth management |
| `workspace/` | Workspace data (may be elsewhere on agents) | Do not assume all workspaces live on controller |
| `builds/` | Build records under jobs | Retention, log growth and backup planning |
| `logs/` | Controller/plugin log files when configured | Retention, access controls, redaction |
| `init.groovy.d/` | Optional startup initialization scripts | Privileged code; strict review and ownership |

Exact files and paths vary by plugin, platform and Jenkins release. Not all workspaces live under controller JENKINS_HOME; remote agent workspaces are separate.

## 4. Identify effective home in Docker

```bash
docker volume create jenkins-ch008-home
docker run -d --name jenkins-ch008 --restart=no \
  -p 127.0.0.1:8086:8080 \
  --mount source=jenkins-ch008-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker inspect jenkins-ch008 --format '{{json .Mounts}}'
docker exec jenkins-ch008 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"'
docker exec jenkins-ch008 sh -c 'ls -ld /var/jenkins_home && df -h /var/jenkins_home'
```

The mutable image tag is for the lab; pin an approved digest in production. Avoid `docker inspect` output that includes environment secrets.

## 5. Linux systemd environment configuration

```bash
systemctl cat jenkins
systemctl show jenkins -p User -p Group -p Environment
sudo journalctl -u jenkins -n 60 --no-pager
```

Use `sudo systemctl edit jenkins` for approved overrides, rather than editing vendor units. Example (only if supported by installed unit):

```ini
[Service]
Environment="JAVA_OPTS=-Djava.awt.headless=true"
```

Validate the service unit actually consumes the setting. `systemctl show -p Environment` may reveal sensitive values if misconfigured, so redact logs. Avoid storing secrets in systemd environment variables when a protected credential source is available.

## 6. Docker environment and startup arguments

```bash
docker inspect jenkins-ch008 --format '{{.Config.Image}}'
docker inspect jenkins-ch008 --format '{{.Config.User}}'
docker inspect jenkins-ch008 --format '{{.HostConfig.RestartPolicy.Name}}'
docker exec jenkins-ch008 java -version
```

For production, review image digest, UID, mounted secrets, startup options, resource limits, JVM settings and logs. Container environment variables are not an appropriate secret vault; they can leak via inspection, diagnostics and child processes.

## 7. JCasC source-of-truth design

Jenkins Configuration as Code (JCasC) is plugin-provided and must be validated against the installed Jenkins and plugin versions. Example:

```yaml
jenkins:
  numExecutors: 0
  systemMessage: "Managed by reviewed JCasC"
```

Store approved non-secret YAML in Git, inject secrets via protected mechanisms, run syntax/schema validation in staging, and test reloads and restarts. Keep a documented rollback bundle. JCasC does not automatically manage every job/plugin setting.

## 8. Pipeline environment and credential binding

```groovy
pipeline {
  agent none
  environment {
    APP_ENV = 'lab'
  }
  stages {
    stage('Environment visibility') {
      steps {
        echo "Target environment: ${env.APP_ENV}"
        echo 'No credentials are printed.'
      }
    }
  }
}
```

Do not put passwords in the `environment` block or Jenkinsfile. Use scoped credentials binding only on trusted agents for real work; Jenkins masking does not protect against malicious code with secret access.

## 9. Configuration changes: safe workflow

```text
Git change -> review -> syntax/schema validation
  -> staging controller -> plugin compatibility test
  -> consistent backup -> approved maintenance
  -> deploy/reload -> smoke tests -> drift check
  -> audit and handoff
```

Prefer documented UI/API/JCasC changes over editing live XML. Editing `config.xml` while Jenkins is running risks being overwritten or corrupting state. Recovery changes require an approved controlled stop, backup and restore procedure.

## 10. Backup and clean-room restore

A usable backup must include consistent JENKINS_HOME, matching encryption keys, plugin inventory and compatible core/Java versions. Encrypt, restrict and test restore. Verify login, credential decryption, representative jobs, JCasC reconciliation and plugin health. Do not use a shared writable home as an HA design.

## 11. Observability and capacity

Track JENKINS_HOME disk/inodes, job/build history growth, plugin changes, JCasC validation errors, controller restart, permission denials, backup age, queue wait and agent state. Record file ownership and mount information without exposing secrets.

## 12. Twenty configuration troubleshooting scenarios

| # | Symptom | Diagnosis | Safe recovery |
|---|---|---|---|
| 1 | Config disappears after restart | Verify effective JENKINS_HOME and volume mount | Restore correct persistent home |
| 2 | Wrong JENKINS_HOME path | Check service unit, container env and process | Correct approved runtime setting |
| 3 | Permission denied on config.xml | Check UID/GID, mode and SELinux context | Restore ownership and policy |
| 4 | Credentials fail to decrypt | Verify secrets and master key from same backup | Restore complete protected key material |
| 5 | Config.xml overwritten | Check UI save, JCasC and startup scripts | Reconcile source of truth and restore approved config |
| 6 | JCasC key not recognized | Inspect plugin schema and version | Update tested configuration |
| 7 | JCasC reload fails | Review logs and YAML parsing | Revert last approved bundle |
| 8 | Secrets exposed via env | Inspect Docker/systemd env and audit logs | Rotate secrets and move to secret provider |
| 9 | Java options ignored | Inspect actual process command and service unit | Correct systemd override or runtime |
| 10 | Wrong Jenkins URL | Check location setting, proxy headers and DNS | Restore canonical HTTPS URL |
| 11 | Plugin state missing | Check plugins/ and volume identity | Restore compatible plugin catalog |
| 12 | Disk fills with builds | Inspect retention and job directories | Apply reviewed retention/expand storage |
| 13 | File inode exhaustion | df -i and directory counts | Expand or remove approved expired files |
| 14 | Concurrent controller writes | Check multiple processes mounting same home | Stop duplicate writers; restore integrity |
| 15 | Startup script changes security | Review init.groovy.d and recent commits | Disable unsafe script via approved recovery |
| 16 | Backup excludes keys | Inspect backup manifest | Rebuild protected complete backup |
| 17 | Stale job config after restore | Compare backup timestamp and source of truth | Reconcile desired state |
| 18 | Config permission too broad | stat, ACLs and filesystem mounts | Restrict service account access |
| 19 | Unexpected global config drift | Diff JCasC/Git against running configuration | Reapply reviewed version |
| 20 | Upgrade changes XML schema | Review Jenkins/plugin migration and rollback | Restore compatible pre-upgrade snapshot |

## 13. Eight SRE runbooks

### RB-01 JENKINS_HOME identity mismatch

**Procedure:** Stop writes, verify effective home and mount, recover correct data from known-good backup.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-02 Credentials decryption failure

**Procedure:** Validate protected secrets/key pairing, restrict access and restore matching encrypted data.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-03 JCasC reload incident

**Procedure:** Capture validation errors, plugin versions and YAML diff; revert approved bundle.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-04 Configuration drift

**Procedure:** Compare Git/JCasC, UI audit and startup scripts; reconcile source of truth.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-05 Disk/inode saturation

**Procedure:** Inspect builds, fingerprints, logs and workspaces; apply retention or expansion safely.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-06 Permission/SELinux incident

**Procedure:** Identify service UID, volume ownership and security labels; restore least privilege.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-07 Upgrade rollback

**Procedure:** Restore compatible pre-upgrade home with plugin/core version and encryption keys.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

### RB-08 Clean-room restore and handoff

**Procedure:** Restore encrypted consistent snapshot to isolated controller and verify login, jobs, credentials and audit.

**Exit criteria:** effective home verified, authenticated access, zero controller executors, secrets protected, representative Pipeline healthy, audit evidence recorded.

## 14. Acceptance assessment — 100 points

| Domain | Points |
|---|---:|
| JENKINS_HOME structure and security | 20 |
| Runtime and systemd/Docker environment | 20 |
| JCasC and configuration source of truth | 20 |
| Pipeline environment and credentials boundaries | 15 |
| Troubleshooting, monitoring and recovery | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ and mandatory gates: correct persistent home, no secret disclosure, controller executors zero, reviewed config workflow and restore design.

## 15. Cleanup

```bash
docker stop jenkins-ch008
docker rm jenkins-ch008
# Destructive: only after confirming this volume is exclusively lab-owned.
docker volume rm jenkins-ch008-home
```

**Next:** Chapter 009 — Jenkins Reverse Proxy, HTTPS, Networking and Access Configuration.
