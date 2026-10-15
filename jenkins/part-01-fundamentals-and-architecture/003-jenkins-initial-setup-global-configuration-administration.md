# Chapter 003 — Jenkins Initial Setup, Global Configuration and Administration

**Curriculum:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 01:** Fundamentals and Architecture  
**Chapter:** 003 / 100  
**Companion lab:** [003 — Jenkins Initial Setup and Administration Check](labs/003-jenkins-initial-setup-administration-check.md)

> **Safety:** All modifications below target a disposable localhost Jenkins instance. Never weaken authentication, expose credentials, or use an administrative API token in a public repository. Organization SSO, production settings and security changes require a reviewed change.

## 1. Learning outcomes

After this chapter, you should be able to initialize Jenkins safely, administer global configuration, manage administrator identity and least privilege, set the controller executor count to zero, govern credentials, plugins and tools, apply Configuration as Code, operate Jenkins APIs safely, and recover administrative configuration after failure.

## 2. Administrative architecture

```text
Human admin / service identity
       |
   SSO + MFA + RBAC
       |
TLS ingress / reverse proxy
       |
Jenkins controller -- JCasC (reviewed Git)
       |               |
       |          protected secret source
       |
   Jenkins home + encryption keys
       |
  plugin catalog / job config / audit logs
       |
 isolated agents -> build and test
       |
 monitoring + consistent encrypted backup
```

The controller schedules Pipelines, hosts the UI/API and stores state. Set its built-in executors to **0**. Administrative access is not equivalent to build-agent access; an untrusted build must never inherit controller permissions.

## 3. Initial setup and bootstrap

For the disposable lab, use a supported Jenkins LTS image and a named Docker volume. Image tags are mutable; pin approved digests in production.

```bash
docker volume create jenkins-ch003-home
docker run -d --name jenkins-ch003 --restart=no \
  -p 127.0.0.1:8082:8080 \
  -v jenkins-ch003-home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker logs --tail 60 jenkins-ch003
docker exec jenkins-ch003 cat /var/jenkins_home/secrets/initialAdminPassword
```

Open `http://127.0.0.1:8082` and complete the unlock wizard. Create a unique lab administrator, install reviewed plugins, record the observed Jenkins/Java/plugin versions, and never paste the bootstrap password into submitted evidence.

## 4. Global configuration checklist

In **Manage Jenkins**, review the following (UI labels may vary by installed version/plugins):

| Area | Recommended practice | Evidence |
|---|---|---|
| Initial administrator and bootstrap | Use the one-time local unlock token, create named administrator, disable shared accounts, protect bootstrap evidence | Screenshot/config export with secrets redacted |
| Controller URL and reverse proxy | Set canonical HTTPS URL, verify proxy headers, webhook callbacks, trusted TLS and DNS | Screenshot/config export with secrets redacted |
| Authentication and authorization | Prefer organization SSO and matrix/role-based least privilege; retain audited break-glass access | Screenshot/config export with secrets redacted |
| Built-in node isolation | Set controller executors to zero and verify agents run all shell/build work | Screenshot/config export with secrets redacted |
| Credentials scope | Prefer folder-scoped and short-lived secrets; avoid passing secrets to untrusted PR builds | Screenshot/config export with secrets redacted |
| Global tools | Pin JDK, Git, Maven, Node or container toolchains on isolated agents, not on controller | Screenshot/config export with secrets redacted |
| System configuration | Review location, executors, quiet period, SCM polling, proxy and usage statistics | Screenshot/config export with secrets redacted |
| Folders and job governance | Apply folder boundaries, naming, ownership, permissions and job retention | Screenshot/config export with secrets redacted |
| Plugin administration | Record versions, update-center trust, dependencies, advisories and rollback | Screenshot/config export with secrets redacted |
| JCasC lifecycle | Store reviewed YAML, resolve secrets from protected sources, validate against installed plugins | Screenshot/config export with secrets redacted |
| Configuration backup | Capture consistent JENKINS_HOME, key material, job state and compatible plugin inventory | Screenshot/config export with secrets redacted |
| Logging and monitoring | Export controller/JVM/queue/agent metrics and retain access/audit logs appropriately | Screenshot/config export with secrets redacted |
| CSRF and API tokens | Keep CSRF protection enabled; prefer scoped user/service API tokens and webhook signatures | Screenshot/config export with secrets redacted |
| Session and network controls | Protect TLS, ingress, firewall, SSO session and admin access | Screenshot/config export with secrets redacted |
| Maintenance and upgrade windows | Plan plugin/Jenkins upgrades with staging, smoke tests, rollback and communication | Screenshot/config export with secrets redacted |
| Administrative automation | Use supported Jenkins CLI/API with least-privilege identities, not anonymous endpoints | Screenshot/config export with secrets redacted |
| Build retention and artifacts | Define discarders, external artifact registry and disk growth alerts | Screenshot/config export with secrets redacted |
| Agent cloud configuration | Review pod templates, resource requests, node labels and network trust boundaries | Screenshot/config export with secrets redacted |
| Disaster recovery governance | Test restore in isolated environment and protect secrets/master.key | Screenshot/config export with secrets redacted |
| Audit and readiness review | Maintain change approvals, evidence, runbooks, on-call owners and access review | Screenshot/config export with secrets redacted |

### Jenkins URL

Set the canonical root URL to the trusted externally reachable HTTPS endpoint in real deployments. A localhost lab may use `http://127.0.0.1:8082/`. Validate redirects, webhook callbacks, agent connections and proxy forwarding.

### Security realm and authorization

Choose a supported SSO/security realm and role- or matrix-based authorization for production. Deny unnecessary anonymous access, use named accounts, apply least privilege and keep an audited emergency recovery procedure. Never disable security to fix an SSO incident.

### Controller isolation

Open **Manage Jenkins → Nodes → Built-In Node → Configure** and set **Number of executors = 0**. Confirm that agent labels are used for build stages. A controller-side `echo`-only Pipeline with `agent none` is not a substitute for testing actual build isolation.

## 5. Credentials and secrets administration

Credential stores may be system/global/folder scoped depending on plugin support. Prefer the narrowest available scope and short-lived workload identities. Use `withCredentials` on trusted, isolated agents when required, and avoid exposing secrets through process arguments, `set -x`, untrusted PRs or shell interpolation.

```groovy
pipeline {
  agent { label 'trusted-linux-agent' }
  stages {
    stage('Authenticated check') {
      steps {
        withCredentials([string(credentialsId: 'lab-api-token', variable: 'API_TOKEN')]) {
          sh '''
            set +x
            test -n "$API_TOKEN"
            echo "Credential is available; value intentionally not printed."
          '''
        }
      }
    }
  }
}
```

The example requires an explicitly configured trusted agent and the Credentials Binding plugin. The token should have only lab permissions. Jenkins masking is not a security boundary against malicious code running with access to the secret.

## 6. Configuration as Code (JCasC)

A minimal conceptual JCasC fragment, validated against the installed Configuration as Code plugin and Jenkins version:

```yaml
jenkins:
  numExecutors: 0
  systemMessage: "Managed by reviewed configuration"
  mode: EXCLUSIVE
  labelString: "controller"
```

`mode: EXCLUSIVE` alone does not provide agent isolation; the zero-executor setting is essential. Do not place secrets directly in YAML. For a real deployment, configure the security realm, authorization strategy, controller URL and approved plugins using version-specific supported JCasC schemas. Validate configuration in staging and preserve a tested rollback bundle before reload.

## 7. API and CLI administration

For a local lab, a user API token can access Jenkins' REST API using HTTPS in production or localhost HTTP in the isolated lab:

```bash
export JENKINS_URL=http://127.0.0.1:8082
read -r -p 'Jenkins username: ' JENKINS_USER
read -r -s -p 'Lab API token: ' JENKINS_TOKEN
printf '\n'
curl --fail --silent --show-error --user "$JENKINS_USER:$JENKINS_TOKEN" \
  "$JENKINS_URL/api/json?tree=mode,numExecutors,quietingDown" 
unset JENKINS_TOKEN
```

**Caution:** the `curl --user` argument can expose the credential to process inspection on some hosts. Prefer a secured credential helper or approved API client for enterprise automation; never run with shell tracing or on a shared untrusted machine. API permissions depend on the configured authorization strategy.

## 8. Global tool management

Pin Java, Git, Maven, Gradle, Node.js and other build tools in versioned agent images or approved tool installers. Document OS/architecture compatibility and avoid downloading arbitrary tool versions at build time. Tools should execute on agents, not on the controller.

## 9. Plugin governance

Maintain a tested plugin bill of materials, monitor security advisories, review plugin dependencies, stage upgrades, and capture rollback backups. Updating one plugin may require dependency upgrades; never blindly roll back individual plugin files after data-format changes without testing a full restore.

## 10. Administrative backups and restore

Protect consistent `JENKINS_HOME` backups including jobs, plugins, global settings, secrets and key material. Encrypt backups and restrict access. Test restores in a clean-room controller with compatible Jenkins and plugin versions, verify login, credentials decryption, representative Pipelines and webhook behavior. Do not share a writable home between two live controllers.

## 11. Observability and governance

Monitor HTTP availability, admin login failures, JVM/GC, disk/inodes, queue length and age, agent status, plugin errors, JCasC reloads and backup freshness. Retain audit trails for privilege changes, credentials access policy, plugin updates and configuration changes. Define on-call and break-glass ownership.

## 12. Twenty administration troubleshooting scenarios

| # | Failure | Investigation and safe response |
|---|---|---|
| 1 | Initial login fails | Inspect bootstrap setup logs and authentication realm; avoid disabling security |
| 2 | Admin account lost | Invoke documented break-glass and restore SSO, audit actions |
| 3 | SSO callback mismatch | Compare HTTPS Jenkins URL, IdP redirect, proxy headers and time skew |
| 4 | Webhook 403 | Check webhook secret, crumb/API token behavior and reverse proxy |
| 5 | CSRF error | Inspect crumb issuer and request authentication; do not globally disable CSRF |
| 6 | Controller executes builds | Set built-in executors to zero; isolate jobs on agents |
| 7 | Credential visible to untrusted PR | Revoke/rotate, isolate fork jobs and inspect credential scope |
| 8 | Global tool missing | Inspect agent tool installation and label; pin image/tool versions |
| 9 | Plugin incompatibility | Review dependency/version matrix; restore tested catalog |
| 10 | JCasC schema error | Validate against exact plugin versions in staging; roll back YAML |
| 11 | Job config drift | Compare config as code, audit logs and approved Git revision |
| 12 | Unauthorized folder access | Review role assignments, folder permissions and identity mapping |
| 13 | Reverse proxy redirects to HTTP | Correct Jenkins root URL and forwarded headers |
| 14 | Jenkins API returns 401 | Check token scope, account state and SSO integration |
| 15 | Unexpected anonymous read | Audit authorization strategy; disable unintended anonymous permissions |
| 16 | Build history fills disk | Review retention and offload artifacts; expand safely |
| 17 | Controller restart loses config | Verify persistent JENKINS_HOME and volume ownership |
| 18 | Agent provisioner access denied | Check cloud identity and Kubernetes service account/RBAC |
| 19 | Metrics missing | Check plugin, endpoint ACL and scraper auth; preserve least privilege |
| 20 | Restore cannot decrypt credentials | Restore correct protected encryption keys with matching data |

## 13. Eight production SRE runbooks

### RB-01 Admin access outage

**Procedure:** Verify identity provider, proxy, Jenkins security realm and approved break-glass; restore SSO without disabling auth.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-02 Credential exposure

**Procedure:** Quarantine job, revoke token, rotate secret, review console logs and SCM, notify security owner.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-03 Plugin change rollback

**Procedure:** Freeze updates, compare plugin bill of materials, restore compatible tested versions and smoke-test.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-04 JCasC configuration failure

**Procedure:** Review validation errors and plugin schema, revert to last approved configuration, test in staging.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-05 Jenkins URL/TLS failure

**Procedure:** Check certificate chain, DNS, proxy headers, Jenkins root URL and webhooks; verify authenticated access.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-06 Storage and retention pressure

**Procedure:** Inspect inodes, disk, build records, artifacts and workspaces; use approved retention and expansion.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-07 Restore administrative state

**Procedure:** Restore encrypted consistent home and key material in clean room, verify auth, jobs and plugin health.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

### RB-08 Governance handoff

**Procedure:** Document owners, RBAC matrix, emergency access, SLOs, changes, backups, alerts and audit artifacts.

**Exit criteria:** verified authenticated access, zero controller executors, no exposed credentials, audited recovery, named owner and incident/change record.

## 14. Acceptance assessment — 100 points

| Area | Points |
|---|---:|
| Secure initial setup and named administration | 20 |
| Global settings and controller isolation | 15 |
| Credentials and authorization boundaries | 20 |
| JCasC and plugin governance | 15 |
| API, tools and operational monitoring | 10 |
| Backup/restore and incident runbooks | 10 |
| Cleanup and evidence quality | 10 |
| **Total** | **100** |

**Pass:** at least 90/100 and all mandatory gates: no untrusted controller builds, no secrets in evidence, no production changes, and a documented restore path.

## 15. Cleanup

```bash
docker stop jenkins-ch003
docker rm jenkins-ch003
# Destructive: remove only after confirming the volume is exclusively lab-owned.
docker volume rm jenkins-ch003-home
```

**Next:** Chapter 004 — Jenkins Core Components, Plugins and Extension Architecture.
