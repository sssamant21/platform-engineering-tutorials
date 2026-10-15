# Chapter 002 — Companion Lab: Jenkins Installation and Deployment Check

**Parent:** [Chapter 002 — Jenkins Installation Methods, System Requirements and Deployment Architecture](../002-jenkins-installation-methods-system-requirements-deployment-architecture.md)

## Safety and prerequisites

Docker with Linux containers, localhost port 8081 free, enough disk/RAM, no production credentials, and an operator who can confirm lab-owned resources. Do not publish the initial administrator password. Kubernetes/Helm sections are render-and-review only.

## Lab 01 — Host readiness

```bash
docker version
docker info
docker ps
```

**Pass:** daemon responds; host is disposable and local.

## Lab 02 — Verify host resources

```bash
docker system df
docker volume ls
```

**Pass:** sufficient free capacity and no conflicting lab name.

## Lab 03 — Create persistent home

```bash
docker volume create jenkins-ch002-home
docker volume inspect jenkins-ch002-home
```

**Pass:** dedicated volume exists.

## Lab 04 — Launch Jenkins

```bash
docker run -d --name jenkins-ch002 --restart=no \
  -p 127.0.0.1:8081:8080 \
  --mount source=jenkins-ch002-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
```

**Pass:** container starts with localhost-only port binding.

## Lab 05 — Verify container health

```bash
docker ps --filter name=jenkins-ch002
docker logs --tail 100 jenkins-ch002
```

**Pass:** no fatal startup error.

## Lab 06 — Complete initial setup

Retrieve password privately:

```bash
docker exec jenkins-ch002 cat /var/jenkins_home/secrets/initialAdminPassword
```

Open `http://127.0.0.1:8081`, complete setup, create disposable admin, install minimal reviewed plugins. **Do not include password in evidence.**

## Lab 07 — Set zero controller executors

In **Manage Jenkins → Nodes → Built-In Node → Configure**, set executors to zero. Record node status.

**Pass:** no ordinary build runs on controller.

## Lab 08 — Inspect runtime versions

```bash
docker exec jenkins-ch002 java -version
docker inspect jenkins-ch002 --format '{{.Config.Image}}'
```

**Pass:** Java and Jenkins image versions recorded; compatibility reviewed.

## Lab 09 — Inspect persistence

```bash
docker exec jenkins-ch002 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
docker inspect jenkins-ch002 --format '{{json .Mounts}}'
```

**Pass:** volume mapped to correct home path.

## Lab 10 — Verify restart persistence

```bash
docker restart jenkins-ch002
docker logs --tail 80 jenkins-ch002
```

Reopen UI and verify configuration persists.

**Pass:** controller returns with same administrator and settings.

## Lab 11 — Validate localhost-only exposure

```bash
docker port jenkins-ch002
```

**Pass:** host binding is 127.0.0.1:8081.

## Lab 12 — Inspect plugin versions

Review **Manage Jenkins → Plugins** and note installed plugin versions and compatibility warnings. Do not upgrade plugins without a tested rollback.

**Pass:** plugin inventory recorded.

## Lab 13 — Linux systemd design check

On an authorized Linux lab VM only:

```bash
java -version
systemctl status jenkins --no-pager
systemctl cat jenkins
journalctl -u jenkins -n 30 --no-pager
```

If Jenkins is not installed, document expected service user, JENKINS_HOME and reverse-proxy design rather than modifying the host.

**Pass:** service architecture explained.

## Lab 14 — Helm chart inspection

On a workstation with Helm:

```bash
helm repo add jenkins https://charts.jenkins.io
helm repo update
helm show chart jenkins/jenkins
helm show values jenkins/jenkins > /tmp/jenkins-values.yaml
```

**Pass:** chart metadata, default storage, security and controller executors reviewed. No cluster modification.

## Lab 15 — Helm rendering

Create `values.yaml` with the minimal controller/persistence values from the chapter, then run:

```bash
helm template jenkins-lab jenkins/jenkins -n jenkins-lab -f values.yaml > /tmp/jenkins-rendered.yaml
```

**Pass:** rendered manifests inspected for PVC, security contexts, Service and StatefulSet/Deployment. Pin chart version in a real implementation.

## Lab 16 — Backup design tabletop

List jobs, credentials, `JENKINS_HOME`, secret keys, plugin bill of materials and compatible Jenkins runtime. Write a clean-room restore plan with encrypted backup and verification. Do not copy secrets into Git.

**Pass:** candidate can explain how to recover a usable Jenkins controller.

## Lab 17 — Troubleshooting drill

Choose three cases: port conflict, volume permission denial and unsupported Java/plugin version. Document diagnostic command, root cause, safe remediation and rollback. Do not intentionally corrupt the live lab volume.

**Pass:** clear incident notes with safe mitigations.

## Lab 18 — Cleanup and acceptance

```bash
docker stop jenkins-ch002
docker rm jenkins-ch002
docker volume inspect jenkins-ch002-home
# Remove only if no other workload or restore exercise needs it:
docker volume rm jenkins-ch002-home
```

**Pass:** no residual disposable resources; final score at least 90/100.

## Assessment rubric

| Area | Points |
|---|---:|
| Docker install, access and persistence | 30 |
| Security and controller isolation | 20 |
| Linux/Helm architecture | 20 |
| Backup/restore design | 15 |
| Troubleshooting, cleanup and evidence | 15 |
| **Total** | **100** |

## Evidence template

```text
Lab date / operator:
Docker host and version:
Jenkins image and Java version:
Controller executors:
Volume name and mount:
Port binding:
Plugin inventory:
Restart validation:
Linux/Helm design findings:
Backup/restore strategy:
Troubleshooting results:
Cleanup verification:
Score and assessor:
```

**Next:** Chapter 003 — Jenkins Initial Setup, Global Configuration and Administration.
