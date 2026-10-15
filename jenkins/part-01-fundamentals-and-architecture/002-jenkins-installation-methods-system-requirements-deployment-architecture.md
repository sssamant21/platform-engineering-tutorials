# Chapter 002 — Jenkins Installation Methods, System Requirements and Deployment Architecture

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 01:** Jenkins Fundamentals and Architecture  
**Chapter:** 002 / 100  
**Companion lab:** [002 — Jenkins Installation and Deployment Check](labs/002-jenkins-installation-deployment-check.md)

> **Safety:** Use a disposable local environment for exercises. This chapter's Linux and Kubernetes commands are templates for approved infrastructure; do not run them on production without a reviewed change, tested backup and version compatibility assessment.

## 1. Objectives

Compare Jenkins installation on Linux, Docker, Kubernetes/Helm and cloud VMs; size controller CPU/RAM/storage from observed workloads; select supported Java and Jenkins LTS versions; design persistent JENKINS_HOME, network, TLS, identity, backup and restore; perform safe installation, validation, upgrade planning and troubleshooting.

## 2. Installation decision matrix

| Method | Good fit | Critical controls | Operational risks |
|---|---|---|---|
| Linux package / systemd | Persistent Linux VM or bare metal | OS package management, service unit, reverse proxy, dedicated user, patching | Host lifecycle, JVM compatibility, disk growth and restore ownership |
| Docker container | Local evaluation or small controlled installations | Persistent JENKINS_HOME volume, image pin, non-root container, restricted ports | Volume ownership, backup consistency, upgrades and network boundaries |
| Kubernetes Helm | Container-native controlled deployment | Pinned Helm chart, PVC, ingress, workload identity, resource limits | PVC recovery, plugin compatibility, controller disruption and CSI availability |
| Cloud VM image | Enterprise infrastructure standardization | Golden image, IaC, managed disks, identity, TLS and logging | Immutable image rollout, disk snapshots and failover runbook |
| Managed CI alternatives | When controller operations are not justified | Compare integrated CI services and hosted products | Avoid unnecessary Jenkins platform ownership |

**Recommendation:** use a disposable Docker controller for the learning lab. For an enterprise installation, select Linux/VM or Kubernetes according to storage, operations maturity, security and restore requirements—not merely deployment convenience. Jenkins controllers are stateful, even when deployed in a container.

## 3. Reference deployment architecture

```text
Users / SCM webhooks
       |
  TLS reverse proxy / ingress + SSO
       |
   Jenkins controller (0 build executors)
   |        |           |           |
  JCasC   plugins     credentials  metrics/logs
   |        |           |           |
   +--------+-----------+-----------+
               |
     persistent JENKINS_HOME
     encrypted backup + key escrow
               |
       agent provisioner
       /       |         \
    VM agent  Docker     Kubernetes pod
       \       |         /
          build/test/scan
               |
       signed artifact registry
               |
        approved GitOps change
```

**Do not** configure multiple independent ordinary Jenkins controllers to mount one writable JENKINS_HOME for active/active high availability. Use tested backup/restore, infrastructure recreation and appropriately designed recovery/failover.

## 4. System requirements and sizing

Exact supported Java and Jenkins minimum requirements change with Jenkins releases. Verify the official current LTS support matrix and the chosen plugins before pinning an image or package. The sizing below is **illustrative lab planning**, not a Jenkins vendor requirement.

| Deployment | Starting allocation | Notes |
|---|---|---|
| Disposable local lab | 2 vCPU, 4 GiB RAM, 20 GiB disk | Keep browser, Docker and plugins overhead in mind |
| Small shared controller | 4 vCPU, 8–16 GiB RAM, fast persistent disk | Profile heap, GC, queue and disk I/O |
| Larger controller | Benchmark and capacity-test | Scale agents independently; avoid excessive controller-side Groovy |
| Ephemeral agent | Per build toolchain and concurrency | CPU/memory and disk requests follow actual job profiles |

Capacity depends on job metadata, Pipeline complexity, plugin count, concurrent controller operations, queue pressure, log retention and number of connected agents. Reserve disk space for JENKINS_HOME, plugin state, build records and backups; keep large artifacts in external storage.

## 5. Installation method A — disposable Docker controller

Use the Jenkins LTS JDK 21 image only after confirming compatibility with your environment. This tag is mutable and should be pinned by digest in a controlled environment.

```bash
docker version
docker volume create jenkins-ch002-home
docker run -d --name jenkins-ch002 \
  --restart=no \
  -p 127.0.0.1:8081:8080 \
  --mount source=jenkins-ch002-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch002
docker logs --tail 100 jenkins-ch002
```

Open `http://127.0.0.1:8081` locally. Retrieve the unlock password privately with `docker exec jenkins-ch002 cat /var/jenkins_home/secrets/initialAdminPassword`; do not commit it or include it in evidence.

After initialization, set built-in controller executors to **0**, enable authentication and create a disposable administrator. Install only reviewed plugins.

## 6. Installation method B — Linux package / systemd

This is a **design and inspection exercise**, not an unconditional installation recipe: exact package repository keys, URLs, supported distributions and Java packages depend on the current Jenkins LTS release.

```bash
java -version
id jenkins || true
systemctl status jenkins --no-pager
systemctl cat jenkins
journalctl -u jenkins -n 100 --no-pager
ss -ltnp
```

For a new Linux deployment: install a supported Java runtime, configure the official verified Jenkins package repository, install the Jenkins LTS package, use a dedicated `jenkins` service identity, persist `JENKINS_HOME` on appropriately protected storage, configure TLS through a reverse proxy, restrict network access and test service recovery.

Avoid editing vendor-managed service files directly. Use approved systemd drop-ins for environment overrides and document `JENKINS_HOME`, Java options and restart behavior.

## 7. Installation method C — Kubernetes / Helm

**Illustrative configuration fragment**, to be adapted to a pinned and validated Jenkins Helm chart version:

```yaml
controller:
  numExecutors: 0
  resources:
    requests:
      cpu: "500m"
      memory: "2Gi"
    limits:
      memory: "4Gi"
persistence:
  enabled: true
  size: 20Gi
```

```bash
helm version
kubectl version --client
helm repo add jenkins https://charts.jenkins.io
helm repo update
helm show values jenkins/jenkins > /tmp/jenkins-chart-values.yaml
helm template jenkins-lab jenkins/jenkins -n jenkins-lab -f values.yaml > /tmp/jenkins-rendered.yaml
```

Review chart version, CRDs, security contexts, ServiceAccounts, plugin installation strategy, ingress, storage class and PVC reclaim policy before applying anything. Kubernetes restart/recreation is **not** the same as stateful Jenkins recovery; JENKINS_HOME consistency, encryption keys and plugin compatibility still matter.

## 8. Persistent data and backup boundaries

`JENKINS_HOME` includes job definitions, build history, plugins, global settings, secrets and encryption key material. Backups must be encrypted, access-controlled and tested. Copying live state without a consistent snapshot can yield an unusable backup.

Protect credentials and secret keys separately according to your organization's escrow policy. A clean-room restore should validate login, a representative job, credentials decryption, plugin compatibility and audit logging. Do not blindly copy live controller state between two active controllers.

## 9. Security hardening checklist

- Supported LTS and compatible Java runtime
- Controller executors set to zero
- Least-privilege service user / container UID
- TLS, reverse proxy and controlled network access
- SSO and least-privilege authorization
- CSRF protection and safe webhook authentication
- No production secrets in disposable labs
- Reviewed plugins and pinned dependencies
- Configuration as Code where supported
- Isolated agents and no host Docker socket on controller
- Encrypted and restore-tested backups
- Monitoring, audit and upgrade rollback plan

## 10. Observability and operational baseline

Track uptime, HTTP health, JVM heap/GC, CPU, disk/inodes, I/O latency, build queue length/age, connected agents, provisioning delay, failed builds, plugin exceptions and backup age. Build dashboards and alerts from measured baselines; do not assume one-size-fits-all thresholds.

## 11. Twenty installation and deployment troubleshooting scenarios

| # | Symptom | Investigation | Safe remediation |
|---|---|---|---|
| 1 | Unsupported Java runtime | Check Jenkins LTS requirements, java -version and image/JDK compatibility | Upgrade to supported Java before rollout |
| 2 | Incorrect systemd service user | Inspect systemctl cat jenkins, file ownership and journal | Restore dedicated account and permissions |
| 3 | JENKINS_HOME not writable | Check mount, UID/GID, SELinux and volume ownership | Correct ownership in maintenance window |
| 4 | Disk full or inode exhaustion | df -h, df -i, artifact retention and logs | Expand or safely reclaim owned data |
| 5 | Port conflict | ss -ltnp or docker ps | Bind approved alternate port |
| 6 | TLS or reverse proxy loop | Inspect Host/X-Forwarded headers, Jenkins URL and TLS | Correct proxy configuration |
| 7 | Initial unlock password inaccessible | Check service/container logs and secrets file ownership | Read locally with approved access, never publish |
| 8 | Plugin install hangs | Inspect update center connectivity, proxy and plugin dependencies | Restore outbound access and pinned catalog |
| 9 | Controller crashloop | Check logs, JVM, config, volume and plugin compatibility | Revert bad change from known-good backup |
| 10 | Kubernetes PVC pending | Inspect StorageClass, CSI events and zone binding | Repair storage provisioner and binding |
| 11 | Ingress 502 | Inspect Service selectors, readiness and controller logs | Restore healthy endpoints |
| 12 | Pod OOMKilled | Inspect limits, JVM heap and memory usage | Tune memory after profiling |
| 13 | Node pressure eviction | Check kubectl describe node and pod events | Reschedule after capacity recovery |
| 14 | Container runs as root | Inspect image UID and securityContext | Use non-root image and volume permissions |
| 15 | Secrets accidentally logged | Audit console and logs, revoke and rotate | Remove unsafe echo and restrict access |
| 16 | JCasC invalid on startup | Validate config against pinned plugin versions | Revert config bundle |
| 17 | Plugin version drift | Compare plugin catalog and installed versions | Reapply tested bill of materials |
| 18 | Agent cannot connect | Check remoting transport, firewall, TLS and identity | Repair agent network and credentials |
| 19 | Backup restore missing keys | Verify secrets/master.key and credential encryption | Restore complete protected backup set |
| 20 | Upgrade rollback incompatible | Review data format migrations and plugin upgrade notes | Restore pre-upgrade snapshot, do not downgrade in place blindly |

## 12. Eight SRE runbooks

### RB-01 Linux service startup

**Procedure:** Check systemctl status, journalctl, Java, filesystem and service user; restore service after fixing the identified dependency.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-02 Docker controller startup

**Procedure:** Check image digest, container logs, volume mount/ownership and localhost binding; replace disposable container while preserving home.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-03 Kubernetes Helm recovery

**Procedure:** Check pod events, PVC, CSI, probes, chart values and ingress; restore healthy controller without detaching or overwriting live storage.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-04 TLS and access outage

**Procedure:** Verify reverse proxy routes, certificates, Jenkins root URL and SSO; avoid disabling security as a workaround.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-05 Disk and JVM saturation

**Procedure:** Collect disk/inodes, heap/GC, thread dumps and I/O; apply bounded retention and capacity changes.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-06 Plugin and JCasC rollback

**Procedure:** Freeze changes, identify incompatible plugin/config, restore tested versions and run smoke checks.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-07 Backup and disaster recovery

**Procedure:** Take consistent encrypted JENKINS_HOME backup including key material; test clean-room restore with matching versions.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

### RB-08 Upgrade/change handoff

**Procedure:** Record approved change, prerequisites, smoke tests, RPO/RTO, rollback decision, on-call owner and audit evidence.

**Exit criteria:** controller login, representative Pipeline smoke test, no credential exposure, version and configuration recorded, incident/change evidence preserved.

## 13. Production acceptance assessment (100 points)

| Competency | Points |
|---|---:|
| Explain deployment-method tradeoffs | 15 |
| Validate supported Java, Jenkins and plugin versions | 10 |
| Create and secure disposable Docker lab | 20 |
| Review Linux/systemd and Helm architecture | 15 |
| Design JENKINS_HOME and tested recovery | 15 |
| Troubleshoot representative startup failures | 15 |
| Cleanup, evidence and handoff | 10 |
| **Total** | **100** |

**Pass:** 90/100 or more, with mandatory gates: isolated lab, no exposed secrets, controller executors zero, persistent storage ownership understood, and documented restore approach.

## 14. Cleanup

```bash
docker stop jenkins-ch002
docker rm jenkins-ch002
# Destructive: only after confirming this volume is owned exclusively by this lab.
docker volume rm jenkins-ch002-home
```

Do not remove a volume if it is needed for the backup/restore exercise or another container.

## 15. Definition of done

You can justify an installation method, describe controller sizing, launch and secure a disposable Docker installation, inspect Linux/Helm deployment approaches, protect Jenkins state and diagnose startup, storage, Java, plugin and networking failures.

**Next:** Chapter 003 — Jenkins Initial Setup, Global Configuration and Administration.
