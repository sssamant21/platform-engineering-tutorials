# Chapter 001 — Companion Hands-On Lab: Jenkins Fundamentals and Architecture Check

**Parent chapter:** [001 — Jenkins Fundamentals, Architecture and Enterprise CI/CD Use Cases](../001-jenkins-fundamentals-architecture-enterprise-cicd-use-cases.md)

## Objective

Create a disposable Jenkins controller, verify architecture and security boundaries, execute a simple no-agent Pipeline, diagnose failures and clean up without touching production.

## Prerequisites and safety gates

- Docker Desktop or Engine using Linux containers, with sufficient local resources.
- Free local port 8080; localhost-only binding; no public exposure.
- No production credentials or external untrusted code.
- Controller executors must be zero; never attach a Docker socket or host root credentials.
- A disposable Docker volume, with its exact name recorded before cleanup.

## Lab 01 — Verify Docker runtime

```bash
docker version
docker info
docker ps
```

**Pass:** Docker daemon responds and operator confirms local disposable host.

## Lab 02 — Create persistent lab volume

```bash
docker volume create jenkins-ch001-home
docker volume inspect jenkins-ch001-home
```

**Pass:** volume exists and is dedicated to this lab.

## Lab 03 — Start Jenkins controller

```bash
docker run -d --name jenkins-ch001 --restart=no \
  -p 127.0.0.1:8080:8080 \
  -v jenkins-ch001-home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch001
```

**Pass:** container is running; port binds only to 127.0.0.1.

## Lab 04 — Inspect bootstrap logs and access

```bash
docker logs --tail 80 jenkins-ch001
docker exec jenkins-ch001 cat /var/jenkins_home/secrets/initialAdminPassword
```

Open `http://127.0.0.1:8080` and finish setup. Treat the initial password as sensitive; do not capture it in submitted evidence.

**Pass:** login works using a disposable administrator.

## Lab 05 — Verify controller executors

Open **Manage Jenkins → Nodes → Built-In Node → Configure** and set **Number of executors = 0**, if not already zero.

**Pass:** no ordinary build can run on the controller.

## Lab 06 — Review plugins and Java

```bash
docker exec jenkins-ch001 java -version
docker logs --tail 100 jenkins-ch001
```

Inspect installed plugins and versions in Manage Jenkins. Record any compatibility warnings.

**Pass:** Jenkins initializes without blocking plugin errors.

## Lab 07 — Verify filesystem capacity

```bash
docker exec jenkins-ch001 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Pass:** enough space and inodes remain for the lab.

## Lab 08 — Create a no-agent Pipeline

Create a Pipeline job named `ch001-architecture-check` with the following Pipeline script:

```groovy
pipeline {
  agent none
  options { timestamps() }
  stages {
    stage('Architecture') {
      steps { echo 'Controller schedules work; agents run builds.' }
    }
    stage('Security') {
      steps { echo 'Controller executors are zero; no secrets printed.' }
    }
  }
}
```

Run **Build Now** and inspect Console Output.

**Pass:** both stages succeed without a build agent.

## Lab 09 — Inspect queue behavior

Create a separate disposable Pipeline job using `agent { label 'missing-lab-agent' }` and one `echo` step. Trigger it, observe it remain queued due to missing label, then **cancel the queued item**. Do not create a controller executor to make it run.

**Pass:** candidate explains why no eligible agent is available.

## Lab 10 — Plan agent isolation

Document a future ephemeral agent design with: label, image digest, resource requests, service account, credential scope, network egress, workspace cleanup and concurrency. This is a design-only lab; Chapter 011 onward implements agents in depth.

**Pass:** no privileged controller-side build execution is proposed.

## Lab 11 — Validate Jenkins UI administration

Inspect Manage Jenkins security, Nodes, plugins and system logs. Do not disable security.

**Pass:** candidate can locate administrative health and security settings.

## Lab 12 — Practice a safe restart

```bash
docker restart jenkins-ch001
docker logs --tail 80 jenkins-ch001
```

Reopen UI and rerun the no-agent job.

**Pass:** configuration and Pipeline survive restart.

## Lab 13 — Inspect job evidence

Record build number, duration, result, console log and node/executor status. Redact any credential or personal data.

**Pass:** evidence is sufficient to reproduce the test.

## Lab 14 — Failure diagnosis drill

Pick three scenarios from the parent chapter: missing agent label, controller disk pressure (inspection only), and plugin dependency warning (tabletop only). Explain checks, mitigation and rollback without injecting destructive faults.

**Pass:** diagnoses are specific and safe.

## Lab 15 — Review backup scope

Identify `JENKINS_HOME`, encryption keys, credentials configuration, jobs, plugins, and configuration. Explain why copying files while Jenkins writes can produce inconsistent backups and why restore validation is essential.

**Pass:** recovery scope is complete without exporting secrets into Git.

## Lab 16 — Assess release architecture

Draw a flow from Git SCM to Jenkins to OCI registry to approved GitOps PR to Argo CD. Identify trust boundaries and artifact provenance checks.

**Pass:** CI and deployment reconciliation responsibilities are separated.

## Lab 17 — Cleanup disposable controller

```bash
docker stop jenkins-ch001
docker rm jenkins-ch001
docker volume inspect jenkins-ch001-home
# Delete only after confirming this exact volume is exclusively lab-owned:
docker volume rm jenkins-ch001-home
```

**Pass:** no lab container or dedicated volume remains.

## Lab 18 — Final assessment

Score: architecture 20, Pipeline 15, security 20, diagnosis 15, restart/restore knowledge 15, cleanup/evidence 15 = **100**. Pass at 90+ with zero critical safety violations.

## Troubleshooting quick reference

| Symptom | Check | Recovery |
|---|---|---|
| Container exits | `docker logs jenkins-ch001` | Resolve permissions/resources; restart |
| Port 8080 busy | `docker ps` and host listener | Choose another localhost port |
| Jenkins setup slow | Container logs and CPU/memory | Wait for initial plugins; inspect resource pressure |
| Build stuck queued | Node labels and executor availability | Cancel test job; provision isolated agent later |
| Pipeline syntax error | Job Console Output | Fix Jenkinsfile and rerun |
| Restart loses jobs | Volume mount and ownership | Restore correct lab volume; do not overwrite |
| Login fails | Security realm and local user | Use documented lab recovery; never disable prod auth |
| Disk pressure | `df -h` and `df -i` | Stop workload; safely clean only lab-owned data |

## Evidence template

```text
Lab date / operator:
Host and Docker version:
Jenkins image tag and observed version:
Controller executor count:
Job name / build number / result:
Queue failure observation:
Restart outcome:
Security checks:
Troubleshooting notes:
Cleanup verification:
Final score:
```

**Next:** Chapter 002 — Jenkins Installation Methods, System Requirements and Deployment Architecture.
