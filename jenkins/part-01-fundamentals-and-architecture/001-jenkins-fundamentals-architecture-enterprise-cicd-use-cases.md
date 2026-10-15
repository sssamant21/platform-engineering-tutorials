# Chapter 001 — Jenkins Fundamentals, Architecture and Enterprise CI/CD Use Cases

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 01:** Jenkins Fundamentals and Architecture  
**Chapter:** 001 / 100  
**Companion lab:** [001 — Jenkins Fundamentals Architecture Check](labs/001-jenkins-fundamentals-architecture-check.md)

> **Scope and safety:** This chapter teaches Jenkins architecture and safe operation using a disposable local lab. Never expose a lab controller to the public Internet, reuse production credentials or execute untrusted builds on the controller.

## 1. Learning objectives

By the end, explain controller, agent, executor, node, workspace, queue, plugin, job, Jenkinsfile, credential, multibranch pipeline, shared library and Configuration as Code (JCasC); distinguish controller from worker responsibilities; deploy a disposable lab; run a reproducible Pipeline; diagnose common failures; and identify enterprise reliability boundaries.

## 2. What Jenkins is

Jenkins is an extensible automation server that coordinates continuous integration and delivery workflows. A Pipeline is code describing stages and steps, generally stored as a `Jenkinsfile` in source control. Plugins integrate SCM, credentials, build tools, cloud agent provisioning, notifications and deployment systems.

**Jenkins is not itself a Kubernetes orchestrator, artifact registry, secrets manager or database.** A production CI/CD architecture integrates dedicated systems for those responsibilities.

## 3. Core architecture

```text
Developer -> Git provider -> webhook / SCM polling
                           |
                   Jenkins controller
          +----------------+----------------+
          |                |                |
       queue           scheduler       credentials/
       /jobs            /labels        config/plugins
          |                |                |
          +--------+-------+----------------+
                   |
             agent allocation
             /      |       \
        VM agent  container   Kubernetes pod
             \      |       /
               build/test/scan
                   |
             artifact registry
                   |
        GitOps PR / deployment approval
                   |
                Argo CD
                   |
               Kubernetes
```

### Controller

The controller serves the UI/API, stores configuration, schedules jobs, manages credentials and plugins, and coordinates Pipelines. Protect `JENKINS_HOME`, its encryption keys and controller identity. Do not run ordinary build workloads on the controller; configure controller executors to zero.

### Agent and executor

An agent is a worker attached to the controller. An executor is a concurrent build slot on a node. An agent with two executors may run two eligible jobs concurrently, subject to resource constraints. **Executors are not CPU cores**; set them using measured CPU, memory, I/O and workload isolation needs.

### Jobs, Pipelines and workspaces

Jobs define automation. Pipelines version their build logic. A workspace contains checkout/build files on the allocated agent. Ephemeral agents simplify cleanup and reduce cross-build contamination, but require deliberate artifact and cache management.

### Plugins and JCasC

Plugins extend Jenkins but create dependencies, compatibility and security exposure. Pin and test plugin versions. JCasC can manage supported controller settings declaratively; it does not automatically cover every plugin or replace backups of credentials and state.

## 4. Enterprise CI/CD workflow

```text
Pull request -> webhook -> checkout -> lint -> unit tests
  -> dependency/SAST scans -> build -> integration tests
  -> SBOM -> sign image -> publish immutable digest
  -> protected deployment/configuration PR -> GitOps reconcile
  -> synthetic tests -> SLO verification -> rollback readiness
```

**Separation of duties:** Jenkins builds and verifies; an approved release or GitOps process decides what is deployed. Restrict deploy identities and avoid exposing privileged credentials to untrusted pull requests.

## 5. Jenkins compared with GitLab CI/CD and Argo CD

| Capability | Jenkins | GitLab CI/CD | Argo CD |
|---|---|---|---|
| Build/test automation | Core strength | Core strength | Not primary role |
| Extensibility | Large plugin ecosystem | Integrated platform | Kubernetes-focused integrations |
| Runtime workers | Static/cloud/Kubernetes agents | GitLab runners | Reconciliation controllers |
| Kubernetes desired-state reconciliation | Via integration, not native primary role | Via integration | Core strength |
| Operations responsibility | Controller, agents, plugins, state | GitLab platform/runners | GitOps controllers and Kubernetes |
| Typical enterprise fit | Highly customized CI, heterogeneous tooling | Integrated SCM-to-CI workflow | Kubernetes deployment convergence |

These systems can coexist. A practical architecture is **GitLab as SCM + Jenkins as specialized CI + OCI registry + Argo CD as GitOps deployment controller**.

## 6. Disposable Docker lab

Prerequisites: Docker Engine/Desktop with Linux containers, a supported Jenkins LTS image, sufficient disk/RAM and no conflicting local port. Pin an approved image digest in a real team environment; `jenkins/jenkins:lts-jdk21` below is a convenient mutable learning tag and must not be used unreviewed in production.

```bash
docker volume create jenkins-ch001-home
docker run -d --name jenkins-ch001 \
  --restart=no \
  -p 127.0.0.1:8080:8080 \
  -v jenkins-ch001-home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker logs --tail 60 jenkins-ch001
docker exec jenkins-ch001 cat /var/jenkins_home/secrets/initialAdminPassword
```

Open `http://127.0.0.1:8080`, complete first-run setup, create a disposable administrator, and install only required plugins. **Do not publish the bootstrap password in logs, screenshots, tickets or Git.** Remove the lab when finished.

### Important lab execution note

The controller should have zero executors. A build-capable agent must be configured separately before running a Pipeline using `agent { label 'lab-agent' }`. The companion lab shows how to verify the controller/agent boundary and gives a safe no-agent Pipeline for initial learning.

## 7. First Jenkinsfile

This Pipeline uses `agent none` and controller-coordinated steps only; it does not require a build executor and must not be expanded to execute shell commands on the controller.

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  stages {
    stage('Validate pipeline syntax') {
      steps {
        echo 'Jenkins controller coordinates this Pipeline.'
      }
    }
    stage('Architecture check') {
      steps {
        echo 'Real builds should run on an isolated agent.'
      }
    }
  }
  post {
    always {
      echo 'Record the build result and clean up the lab when done.'
    }
  }
}
```

For real build stages, allocate an isolated agent and use a reviewed toolchain:

```groovy
pipeline {
  agent { label 'lab-agent' }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Verify worker') {
      steps { sh 'id && uname -a && pwd' }
    }
  }
}
```

This second example requires a configured Unix-like agent, SCM-backed Pipeline and the relevant Pipeline plugins. Never assign `lab-agent` to the controller.

## 8. Baseline administrative checks

```bash
docker ps --filter name=jenkins-ch001
docker logs --tail 100 jenkins-ch001
docker exec jenkins-ch001 sh -c 'df -h /var/jenkins_home'
docker inspect jenkins-ch001 --format '{{.State.Status}}'
```

In the Jenkins UI inspect **Manage Jenkins → Nodes**, installed plugins, credentials scope, security realm and authorization strategy. Confirm controller built-in node has zero executors and no untrusted workloads execute there.

## 9. Security foundations

- Use a supported Jenkins LTS release and compatible Java runtime.
- Terminate TLS through a trusted ingress/reverse proxy; restrict administrative network access.
- Use SSO/RBAC or equivalent authorization and least-privilege service identities.
- Isolate agents by trust boundary; untrusted PRs must not access deploy credentials.
- Store secrets in Jenkins credentials or an approved external secrets system, never hardcoded in Jenkinsfiles.
- Review plugin provenance, updates, permissions and vulnerabilities.
- Protect `JENKINS_HOME`, encryption keys, backup archives and audit logs.
- Validate restore procedures; a backup without a clean-room restore test is unproven.

## 10. Reliability and capacity model

Key signals: controller availability, JVM heap/GC, thread health, disk/inodes, build queue length/age, agent connection state, provisioning latency, build success, test flakiness, plugin errors and backup freshness.

**Illustrative SLOs (not universal defaults):** controller availability 99.9%, p95 queue wait under 2 minutes for normal jobs, agent provisioning under 3 minutes, daily successful backups and quarterly restore drills. Choose targets based on business needs and measure them from real traffic.

## 11. Twenty troubleshooting scenarios

| # | Symptom | Diagnosis and remediation |
|---|---|---|
| 1 | Controller overloaded — High CPU, queue delay, GC pauses | Check /metrics or JVM metrics, build queue, thread dumps and controller logs; move builds off controller |
| 2 | No available executor — Jobs remain queued | Check agent online state, label expression, executor count, node restrictions and cloud provisioner |
| 3 | Agent disconnected — Remoting channel offline | Check agent log, DNS, TLS, WebSocket/inbound connectivity, JVM compatibility and credential rotation |
| 4 | Plugin dependency failure — Startup warning after install | Inspect plugin dependency graph, compatibility and update-center metadata; roll back via tested backup |
| 5 | Disk full in JENKINS_HOME — Cannot save jobs | Check filesystem/inodes, logs, artifact retention and workspace ownership; avoid deleting state blindly |
| 6 | Credential exposure — Secret appears in console | Revoke and rotate credential, restrict access, review masking and process arguments, preserve evidence |
| 7 | Pipeline checkout failure — Git authentication denied | Check credentials scope, host key, token expiry, repo permissions and branch reference |
| 8 | Controller restart during build — Build aborted or resumed | Review Pipeline durability, step resumability and external side effects before rerun |
| 9 | Build queue starvation — Long queue despite agents | Inspect labels, throttles, locks, resource constraints and cloud quota |
| 10 | Web UI unreachable — HTTP 502/503 | Check reverse proxy, TLS, controller process, health and ingress routes |
| 11 | JCasC rejects config — Configuration load error | Validate schema/plugin versions in isolated environment, compare last-known-good bundle |
| 12 | Agent image mismatch — Tools not found | Pin build image, Java runtime and tooling; validate immutable agent image |
| 13 | Build artifact missing — Archive step finds nothing | Inspect workspace path, glob patterns, stage conditions and ephemeral agent lifecycle |
| 14 | Security realm lockout — Admins cannot log in | Use documented break-glass with approval and audit; restore identity provider access |
| 15 | Webhook not triggering — Commit not built | Verify endpoint delivery, SCM permissions, multibranch scan and event filters |
| 16 | Kubernetes agent pending — Pod unschedulable | Inspect pod events, requests, quotas, node selectors, image pull and service account |
| 17 | Slow Pipeline startup — Long CPS initialization | Inspect shared libraries, SCM latency, controller load and excessive Groovy work |
| 18 | Unexpected plugin upgrade — Behavior changed | Review pinned plugin catalog, dependency resolution and restore tested version |
| 19 | Backup not restorable — Missing credentials or config | Validate encrypted backup scope, secrets and clean-room restore with compatible plugin versions |
| 20 | Untrusted PR runs privileged code — Privilege boundary breached | Quarantine executor, rotate secrets, isolate forks, remove production credentials from untrusted jobs |

## 12. Eight SRE operational runbooks

### Controller startup failure

**Procedure:** Capture logs and JVM exit code; verify filesystem, Java compatibility, plugin dependencies and config changes; restore last-known-good backup if necessary.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Agent connectivity recovery

**Procedure:** Check labels, node status, remoting transport, DNS/TLS, Java compatibility and ephemeral provisioning; recycle only the affected disposable agent.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Build queue incident

**Procedure:** Identify queue age and label mismatch, verify executor and resource pressure, limit concurrent jobs, recover capacity without enabling builds on controller.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Credential compromise

**Procedure:** Suspend impacted jobs, revoke/rotate credentials, investigate logs and access, restore least-privilege secrets, record security incident.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Plugin change rollback

**Procedure:** Freeze new changes, compare plugin bill of materials, reproduce in staging, restore compatible plugin and JCasC bundle, run smoke tests.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Controller performance triage

**Procedure:** Review JVM heap, GC, thread dumps, I/O, queue, controller-side Groovy work and retention; fix root cause before scaling.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Backup and clean-room restore

**Procedure:** Snapshot consistent Jenkins home and secret keys securely, verify retention and encryption, restore to isolated instance and validate representative pipelines.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

### Change readiness and handoff

**Procedure:** Check owner, approved window, CI smoke tests, rollback, alerting, access, RPO/RTO and evidence before signoff.

**Closeout:** capture owner, UTC timeline, controller/agent version, affected jobs, incident ID, synthetic verification and follow-up.

## 13. Acceptance assessment (100 points)

| Competency | Points |
|---|---:|
| Explain controller, agent, executor and queue | 20 |
| Describe Jenkins Pipeline and SCM integration | 15 |
| Launch and secure disposable controller | 15 |
| Validate agent isolation and first Jenkinsfile | 15 |
| Explain credentials, plugins and JCasC risks | 15 |
| Diagnose representative operational failures | 10 |
| Backup, rollback and cleanup evidence | 10 |
| **Total** | **100** |

**Pass:** at least 90/100, no exposed secrets, no production changes and no untrusted build executed on the controller.

## 14. Cleanup and evidence

```bash
docker stop jenkins-ch001
docker rm jenkins-ch001
# Only after verifying the volume belongs solely to this disposable lab:
docker volume rm jenkins-ch001-home
```

**Evidence template:** lab host, Docker/Jenkins versions, controller URL, node/executor status, Pipeline build URL and result, screenshots without credentials, diagnostic notes, cleanup verification, score.

## 15. Definition of done

You can explain Jenkins architecture, identify controller/agent boundaries, create a disposable lab, run a no-agent Pipeline, plan a worker-based CI stage, describe enterprise integrations and perform initial SRE diagnostics.

**Next:** Chapter 002 — Jenkins Installation Methods, System Requirements and Deployment Architecture.
