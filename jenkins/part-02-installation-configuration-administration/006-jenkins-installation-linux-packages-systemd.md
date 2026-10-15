# Chapter 006 — Jenkins Installation on Linux, Packages and systemd

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 02:** Installation, Configuration and Administration  
**Chapter:** 006 / 100  
**Companion lab:** [006 — Jenkins Linux and systemd Installation Check](labs/006-jenkins-linux-systemd-installation-check.md)

> **Safety:** Perform package installation only on an approved disposable Linux VM. Official repository key URLs, supported Java versions and Jenkins LTS requirements evolve: verify current Jenkins documentation before installation. Never disable repository signature verification, expose Jenkins directly to the Internet or change production services without a change window.

## 1. Learning objectives

Install Jenkins LTS using signed Linux packages, validate Java and OS compatibility, manage the service with systemd, configure JENKINS_HOME and systemd drop-ins, secure network exposure with a TLS reverse proxy, inspect logs, plan backup/restore and perform controlled rollback.

## 2. Linux controller architecture

```text
Git provider / trusted administrators
              |
       TLS reverse proxy
              |
      loopback Jenkins port
              |
      systemd jenkins.service
              |
       supported Java runtime
              |
       Jenkins LTS controller
        |       |        |
      JCasC   plugins  credentials
        \       |       /
        persistent JENKINS_HOME
              |
      encrypted backup + keys
              |
         isolated agents
```

Jenkins core is stateful. A systemd service provides process supervision, **not** active/active high availability. Do not mount one writable JENKINS_HOME on multiple running controllers.

## 3. Installation choices and prerequisites

| Platform | Package manager | Service manager | Config considerations | Package inspection |
|---|---|---|---|---|
| Debian/Ubuntu | apt | systemctl | /etc/default/jenkins or systemd overrides depending on packaging | apt-cache policy jenkins |
| RHEL/Fedora derivatives | dnf | systemctl | systemd drop-in and vendor package defaults | dnf info jenkins |

Before any install, record:

```bash
cat /etc/os-release
uname -m
free -h
df -h
df -i
java -version
systemctl --version
```

**Sizing guidance:** for a disposable Linux lab, start around 2 vCPU, 4 GiB RAM and 20 GiB disk; this is an illustrative planning baseline, not a vendor minimum. Production sizing requires JVM/GC, queue, plugin and I/O measurements. Keep build execution on separate agents.

## 4. Verify official Jenkins LTS package instructions

Use the current official Jenkins installation documentation for your OS, rather than blindly copying stale repository URLs or keys:

- Debian/Ubuntu: https://www.jenkins.io/doc/book/installing/linux/#debianubuntu
- Red Hat family: https://www.jenkins.io/doc/book/installing/linux/#red-hat-centos

Verify the supported Java runtime for the **specific Jenkins LTS** selected. Record the repository signing-key fingerprint from a trusted source and use the distribution's modern signed repository configuration.

### Debian/Ubuntu package workflow

After configuring the official verified repository and installing a supported Java runtime:

```bash
sudo apt-get update
apt-cache policy jenkins
sudo apt-get install --yes jenkins
sudo systemctl enable --now jenkins
sudo systemctl status jenkins --no-pager
```

### RHEL-family package workflow

After configuring the official verified repository and Java runtime:

```bash
sudo dnf makecache
dnf info jenkins
sudo dnf install --assumeyes jenkins
sudo systemctl enable --now jenkins
sudo systemctl status jenkins --no-pager
```

Do **not** run the install commands until the repository, signing key, package version, Java runtime and host identity have been verified.

## 5. Dedicated service account and home directory

```bash
id jenkins
systemctl show jenkins -p User -p Group -p ExecStart -p Environment
systemctl cat jenkins
sudo stat -c '%U:%G %a %n' /var/lib/jenkins
sudo namei -l /var/lib/jenkins
```

Package defaults can vary by distribution and version. Verify the effective `JENKINS_HOME` and the actual service identity; do not assume a hardcoded path if a drop-in overrides it.

## 6. Manage Jenkins using systemd

```bash
sudo systemctl status jenkins --no-pager
sudo journalctl -u jenkins -n 100 --no-pager
sudo systemctl restart jenkins
sudo systemctl is-enabled jenkins
sudo systemctl is-active jenkins
```

A restart interrupts controller availability and can affect nonresumable Pipeline steps. Schedule it appropriately; use a controlled quiet-down/maintenance process and verify jobs afterward.

### systemd drop-in configuration

Use `sudo systemctl edit jenkins` and apply a **reviewed** override appropriate to the installed package. Example:

```ini
[Service]
Environment="JENKINS_PORT=8080"
Environment="JAVA_OPTS=-Djava.awt.headless=true"
```

The package's service implementation must actually honor these variables. Inspect `systemctl cat jenkins`, `systemctl show jenkins -p Environment` and the vendor unit. Some installations use `JENKINS_OPTS` or different settings; never assume one override works everywhere.

```bash
sudo systemctl daemon-reload
sudo systemctl restart jenkins
sudo systemctl cat jenkins
```

Do not store passwords or API tokens directly in a world-readable systemd override.

## 7. Loopback listener and TLS reverse proxy

A production controller should sit behind a trusted TLS reverse proxy/ingress, with firewall and identity controls. Restrict direct access to the backend port. Set the Jenkins root URL to its canonical HTTPS endpoint and validate `Host` and forwarded headers.

```bash
sudo ss -ltnp
curl --fail --silent --show-error --head http://127.0.0.1:8080/login
```

A redirect or authentication response can be normal; check actual service health and URL. If Jenkins listens on all interfaces, fix the service binding and firewall before exposing it. Do not assume a reverse proxy alone makes an unprotected backend private.

## 8. Bootstrap and controller isolation

Read the initial unlock password on the VM through authorized access only:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

The actual path depends on JENKINS_HOME. Complete first-run setup, create a named administrator, enable appropriate authentication/authorization, and set **Manage Jenkins → Nodes → Built-In Node → Number of executors = 0**.

## 9. Linux security hardening

- Keep Jenkins LTS, Java and OS security patches supported and tested.
- Use dedicated least-privilege `jenkins` account; do not run Jenkins as root.
- Protect JENKINS_HOME and secret keys with restrictive ownership and encrypted backups.
- Use TLS, SSO/RBAC, firewall controls and audited emergency access.
- Avoid giving controller access to Docker socket or Kubernetes cluster-admin.
- Pin and review plugin versions and dependencies.
- Keep build agents separate from controller trust domain.
- Review SELinux/AppArmor and filesystem mount options before changing permissions.
- Configure log retention and monitor disk/inodes.

## 10. Backup, upgrade and rollback

Before upgrades, capture an application-consistent encrypted backup of JENKINS_HOME including encryption keys, plugin versions, jobs and global settings. Test a clean-room restore. Pin Jenkins package version and Java compatibility, validate plugins/JCasC in staging and define rollback gates.

**Do not blindly downgrade Jenkins or plugins in place** after persistent data migrations; a full compatible pre-upgrade snapshot may be necessary.

## 11. Monitoring and capacity baseline

Measure controller uptime, JVM heap/GC, CPU, file descriptors, disk/inodes, I/O latency, queue wait, agent connections, HTTP response time, plugin exceptions and backup age. Use baselines to establish alerts and on-call procedures.

## 12. Twenty Linux installation troubleshooting scenarios

| # | Symptom | Diagnosis | Safe remediation |
|---|---|---|---|
| 1 | Package not found | Inspect repository config and package metadata | Correct signed repository; avoid untrusted packages |
| 2 | Repository GPG verification fails | Check official signing key, permissions and clock | Reinstall verified key; never disable signature checks |
| 3 | Java unsupported | Check java -version and Jenkins LTS requirements | Install supported Java and restart after approval |
| 4 | Service fails immediately | journalctl -u jenkins -b and systemctl status | Fix runtime, options or ownership |
| 5 | Port 8080 occupied | ss -ltnp and service config | Assign approved port in systemd override |
| 6 | JENKINS_HOME permission denied | stat, namei, mount, SELinux/AppArmor | Restore dedicated user ownership and policy |
| 7 | No free disk/inodes | df -h and df -i | Expand or reclaim approved files |
| 8 | TLS certificate invalid | openssl s_client and reverse proxy logs | Renew certificate and fix chain |
| 9 | Proxy 502/503 | curl localhost, proxy upstream and service health | Restore backend/proxy connectivity |
| 10 | Jenkins root URL mismatch | Manage Jenkins location and forwarded headers | Set canonical HTTPS URL |
| 11 | Systemd override ignored | systemctl cat jenkins and daemon-reload | Correct drop-in, reload and restart |
| 12 | Environment variable missing | systemctl show jenkins and drop-in | Set approved environment source securely |
| 13 | Service starts as wrong user | systemctl show -p User and file ownership | Run under dedicated jenkins identity |
| 14 | SELinux denies access | ausearch or journal and labels | Apply approved context/policy |
| 15 | Firewall blocks ingress | ss, firewall and security group | Allow only trusted proxy/network |
| 16 | Plugin loading failure | Jenkins logs and dependency versions | Restore compatible plugin set |
| 17 | Service repeatedly restarts | systemctl status and restart policy | Resolve root cause before auto-restart |
| 18 | Backup inconsistent | Review snapshot and write activity | Take consistent backup and test restore |
| 19 | Upgrade breaks configuration | Compare package, Java and plugin versions | Restore pre-change snapshot |
| 20 | Controller running builds | Inspect built-in executors and node status | Set controller executors to zero |

## 13. Eight SRE runbooks

### RB-01 Package repository integrity

**Procedure:** Verify OS release, official Jenkins repo, HTTPS and signing key; never bypass signature validation.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-02 systemd startup outage

**Procedure:** Capture systemctl status, journal, Java version, port, JENKINS_HOME ownership and recent changes.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-03 Permission and SELinux failure

**Procedure:** Inspect service UID, mount ownership, context and denied events; correct only approved paths.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-04 Port/proxy/TLS incident

**Procedure:** Validate localhost listener, reverse proxy upstream, forwarded headers, TLS chain and Jenkins root URL.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-05 Disk and inode pressure

**Procedure:** Measure home disk/inodes, retention and plugin/build history; expand or clean only approved data.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-06 Java/core/plugin upgrade regression

**Procedure:** Compare approved compatibility matrix, capture logs and restore tested version set or snapshot.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-07 Backup and clean-room restore

**Procedure:** Capture consistent encrypted JENKINS_HOME including keys; restore separately and validate login/jobs.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

### RB-08 Change handoff and rollback

**Procedure:** Record change window, version pins, tests, on-call, RPO/RTO, rollback decision and evidence.

**Exit criteria:** systemd service active, authenticated UI, controller executors zero, plugins healthy, monitoring normal, approved evidence recorded.

## 14. Acceptance gates and assessment

| Gate | Requirement |
|---|---|
| G1 | Supported OS, Java and Jenkins LTS verified |
| G2 | Official signed repository configured |
| G3 | Dedicated Jenkins service identity |
| G4 | systemd startup and restart validated |
| G5 | Persistent home and ownership validated |
| G6 | Backend network restricted; TLS architecture documented |
| G7 | Controller executors zero and authentication enabled |
| G8 | Backup/restore and upgrade rollback designed |
| G9 | Three failures diagnosed with evidence |
| G10 | Lab resources safely cleaned up |

**100-point rubric:** prerequisite validation 15; package integrity 15; systemd 20; storage/security 20; troubleshooting 15; recovery/evidence 15. **Pass:** 90+ and all mandatory gates.

## 15. Rollback and cleanup

For a disposable Linux VM, prefer destroying the **entire lab VM through its owning IaC workflow** after evidence and backups are no longer needed. Do not run generic `rm -rf /var/lib/jenkins` or package removal commands on a shared host.

**Next:** Chapter 007 — Jenkins Docker and Containerized Controller Deployment.
