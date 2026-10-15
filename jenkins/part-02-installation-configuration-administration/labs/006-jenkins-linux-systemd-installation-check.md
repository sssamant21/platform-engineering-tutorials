# Chapter 006 — Companion Hands-On Lab: Jenkins Linux and systemd Installation Check

**Parent:** [Chapter 006](../006-jenkins-installation-linux-packages-systemd.md)

## Scope and safety

Use a **dedicated disposable Linux VM** with sudo, 2 vCPU, about 4 GiB RAM and 20 GiB disk as an illustrative baseline. Confirm OS/Java/Jenkins LTS compatibility using official documentation. Never disable package signature validation, expose port 8080 publicly or run against a production host.

## Preflight evidence

Record VM ID, OS, architecture, Java version, Jenkins LTS target, approved package repository, signing key fingerprint, change owner and cleanup method.

## Lab 01 — Confirm lab identity

```bash
hostnamectl
cat /etc/os-release
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Dedicated VM identified. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 02 — Check resource baseline

```bash
free -h
df -h
df -i
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Resources recorded. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 03 — Verify Java compatibility

```bash
java -version
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Selected Java supported by chosen Jenkins LTS. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 04 — Inspect official repository configuration

```bash
grep -R 'jenkins' /etc/apt/sources.list.d /etc/yum.repos.d 2>/dev/null || true
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Official signed repository and fingerprint reviewed. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 05 — Inspect package candidate

```bash
command -v apt-cache && apt-cache policy jenkins || true
command -v dnf && dnf info jenkins || true
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Approved package version identified. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 06 — Install Jenkins on approved VM

```bash
echo 'Use the verified apt-get or dnf install command from the parent chapter after repo verification'
```

**Procedure:** Choose only the package manager matching the lab OS, configure the official signed Jenkins repository and supported Java first, then execute the package installation commands in the parent chapter.

**Pass:** Jenkins installed from trusted signed repository. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 07 — Enable and start service

```bash
sudo systemctl enable --now jenkins
sudo systemctl status jenkins --no-pager
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Service active. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 08 — Inspect service unit

```bash
systemctl cat jenkins
systemctl show jenkins -p User -p Group -p ExecStart
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Service identity and runtime documented. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 09 — Inspect logs

```bash
sudo journalctl -u jenkins -n 100 --no-pager
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** No fatal startup errors. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 10 — Check home directory

```bash
sudo stat -c '%U:%G %a %n' /var/lib/jenkins
sudo namei -l /var/lib/jenkins
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Permissions reviewed. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 11 — Check listener and firewall design

```bash
sudo ss -ltnp
curl -I http://127.0.0.1:8080/login
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Local listener works and network boundary documented. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 12 — Complete private bootstrap

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

**Procedure:** Read the bootstrap password privately, open the approved local or tunneled UI and create a named disposable admin.

**Pass:** Named lab admin created; token not captured. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 13 — Set controller executors zero

```bash
sudo systemctl is-active jenkins
```

**Procedure:** Use Manage Jenkins → Nodes → Built-In Node and set executors to zero.

**Pass:** Built-in node shows zero executors. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 14 — Review systemd drop-in strategy

```bash
systemctl cat jenkins
systemctl show jenkins -p Environment
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Override requirements understood. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 15 — Validate controlled restart

```bash
sudo systemctl restart jenkins
sudo systemctl status jenkins --no-pager
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** UI returns and configuration persists. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 16 — Review Java and Jenkins process

```bash
ps -eo user,pid,cmd | grep '[j]enkins' || true
java -version
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Dedicated user and supported Java confirmed. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 17 — Practice safe troubleshooting

```bash
sudo journalctl -u jenkins -n 80 --no-pager
```

**Procedure:** Diagnose package-signature failure, service startup failure and permission denial as tabletop scenarios; do not inject faults.

**Pass:** Three failure tabletop scenarios documented. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 18 — Plan encrypted backup/restore

```bash
df -h /var/lib/jenkins
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Consistent home backup, keys and clean-room restore plan. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 19 — Verify monitoring handoff

```bash
systemctl is-enabled jenkins
systemctl is-active jenkins
```

**Procedure:** Record actual output, version and owner; do not include credentials in evidence.

**Pass:** Service/queue/heap/disk/backup signals and owners listed. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Lab 20 — Destroy disposable VM safely

```bash
echo 'Use the VM owner’s approved IaC or cloud-console teardown; do not delete shared disks'
```

**Procedure:** Remove only the explicitly identified lab VM and attached dedicated disks after evidence signoff.

**Pass:** Lab VM and its dedicated storage removed by owner. **Rollback:** use approved VM snapshot/backup or undo only the reviewed lab configuration.

## Optional systemd drop-in review

On a disposable VM, inspect `systemctl cat jenkins` first. The following is **illustrative** and must be adjusted to the actual package unit:

```ini
[Service]
Environment="JAVA_OPTS=-Djava.awt.headless=true"
```

Apply with `sudo systemctl edit jenkins`, then `sudo systemctl daemon-reload` and a controlled `sudo systemctl restart jenkins`. Validate the effective service environment and remove the drop-in if unsupported. Do not put credentials in the override.

## Failure triage quick reference

| Failure | Command | Response |
|---|---|---|
| Package signature error | apt/dnf repo metadata and key inspection | Restore official signed repo |
| Unsupported Java | java -version, journalctl | Install supported Java |
| Service failed | systemctl status, journalctl | Resolve logged root cause |
| Permission denied | stat, namei, SELinux logs | Fix dedicated account/context |
| Port conflict | ss -ltnp | Change approved binding |
| Reverse proxy 502 | curl localhost and proxy logs | Restore upstream |
| Disk/inodes exhausted | df -h, df -i | Expand or approved cleanup |
| Plugin incompatibility | Jenkins startup logs | Restore tested plugin set |

## Acceptance score (100 points)

| Competency | Points |
|---|---:|
| OS/Java/package integrity | 20 |
| systemd service administration | 20 |
| Persistent home and permissions | 15 |
| TLS/network and controller security | 20 |
| Incident triage and rollback | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with all ten gates in the parent chapter.

## Evidence template

```text
Operator/date:
VM ID and OS:
CPU/RAM/disk:
Java and Jenkins versions:
Repository and signing key verified:
systemd unit and service user:
JENKINS_HOME ownership:
Listener/firewall/TLS design:
Controller executor count:
Restart validation:
Three failure diagnoses:
Backup/restore strategy:
Monitoring and on-call:
VM teardown confirmation:
Score/assessor:
```

**Next:** Chapter 007 — Jenkins Docker and Containerized Controller Deployment.
