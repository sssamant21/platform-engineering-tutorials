# Chapter 005 — Jenkins Architecture and Administration Fundamentals Capstone

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 01:** Jenkins Fundamentals and Architecture  
**Chapter:** 005 / 100 — **Part 01 capstone**  
**Companion lab:** [005 — Jenkins Fundamentals Capstone Check](labs/005-jenkins-fundamentals-capstone-check.md)

> **Safety boundary:** This capstone is for a disposable localhost controller and tabletop enterprise design. Do not use production credentials, expose the lab publicly, run untrusted builds on the controller or perform destructive failure injection. Production changes require approvals and a tested rollback.

## 1. Mission and outcomes

Integrate Chapters 001–004 into one practical Jenkins platform design and operational assessment. By the end, you can explain architecture and trust boundaries, initialize a secure controller, validate global administration and plugin dependencies, reason about agents and queues, investigate failures, define backup/restore, and produce an SRE handoff.

### Prerequisite chapters

1. [001 — Jenkins Fundamentals and Enterprise CI/CD](001-jenkins-fundamentals-architecture-enterprise-cicd-use-cases.md)
2. [002 — Installation Methods and Deployment Architecture](002-jenkins-installation-methods-system-requirements-deployment-architecture.md)
3. [003 — Initial Setup and Administration](003-jenkins-initial-setup-global-configuration-administration.md)
4. [004 — Core Components and Plugin Extension Architecture](004-jenkins-core-components-plugins-extension-architecture.md)

## 2. Capstone scenario

An enterprise platform team operates source repositories in GitHub or GitLab, specialized Jenkins Pipelines for builds and tests, an artifact registry and Argo CD for Kubernetes delivery. Teams need repeatable CI, protected deployment credentials, auditability, plugin governance and a tested controller recovery procedure.

### Reference architecture

```text
Developer -> GitHub/GitLab -> signed webhook
                               |
                        HTTPS ingress + SSO
                               |
                   Jenkins controller (0 executors)
                     /       |          \
                 JCasC    plugins      metrics/logs
                   |         |            |
                   +---------+------------+
                               |
                   encrypted JENKINS_HOME
                   + protected key material
                               |
                        agent scheduler
                       /        |        \
                  VM agent   container   K8s pod
                       \        |        /
                      lint/test/scan/build
                               |
                     OCI registry + SBOM
                               |
                  reviewed GitOps change
                               |
                           Argo CD
                               |
                       EKS/AKS workloads
```

**Architectural constraints:** Jenkins controller is stateful; ordinary Jenkins is not made active/active by sharing writable `JENKINS_HOME`. Agents must be isolated by trust level. The controller does not replace an artifact registry, secrets platform or GitOps reconciler.

## 3. Capstone deliverables

| Deliverable | Evidence |
|---|---|
| Architecture and trust boundaries | Diagram showing SCM, controller, agents, registry and GitOps |
| Disposable Jenkins controller | Docker command, runtime/version and localhost-only port |
| Secure administration | Named administrator, auth enabled, built-in executors zero |
| Pipeline smoke test | Successful `agent none` coordination-only Pipeline |
| Agent isolation plan | Labels, identities, tool images, network, cleanup, resources |
| Plugin bill of materials | Versions, dependencies, security review and change process |
| Configuration as Code plan | Reviewed YAML, secret source, validation and rollback |
| Operational baseline | JVM, disk/inodes, logs, queue, agents, backups and alerts |
| Recovery design | Consistent encrypted home backup, keys, clean-room restore |
| SRE handoff | Runbooks, acceptance score, owner and risks |

## 4. End-to-end execution plan

| Phase | Action |
|---|---|
| Requirements and trust boundaries | Identify administrators, SCM identities, trusted vs untrusted jobs, build agents, registry and GitOps controls |
| Controller provisioning | Start a disposable persistent Jenkins LTS controller bound to localhost, record image/runtime |
| Security baseline | Complete setup, create named admin, enforce auth, set controller executors to zero |
| SCM/Pipeline model | Create a no-agent validation Pipeline and design agent-based build stages |
| Plugin and JCasC governance | Inventory plugins, map dependency/version risks and validate configuration policy |
| Capacity and observability | Inspect JVM, disk/inodes, logs, queue, agent availability and backup age |
| Failure investigation | Triage queue starvation, plugin incompatibility and persistence failure without destructive injection |
| Recovery planning | Specify consistent encrypted backup, encryption keys, clean-room restore and rollback |
| Acceptance and handoff | Record evidence, run scorecard, remove lab resources and hand off Part 01 |

## 5. Deploy a disposable controller

The image tag is mutable and suitable only for a lab; pin an approved digest in a production implementation. Check the selected Jenkins LTS and Java compatibility.

```bash
docker version
docker volume create jenkins-ch005-home
docker run -d --name jenkins-ch005 --restart=no \
  -p 127.0.0.1:8084:8080 \
  -v jenkins-ch005-home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch005
docker logs --tail 100 jenkins-ch005
```

Open `http://127.0.0.1:8084` and complete the initial wizard. Read the bootstrap password locally and privately:

```bash
docker exec jenkins-ch005 cat /var/jenkins_home/secrets/initialAdminPassword
```

Never include that password in screenshots, tickets or Git.

## 6. Secure initial administration

- Create a named disposable administrator; do not reuse production identity.
- Keep authentication and CSRF protection enabled.
- In **Manage Jenkins → Nodes → Built-In Node → Configure**, set executors to **0**.
- Review plugin inventory and Java/Jenkins versions.
- Confirm controller port is bound only to localhost.
- Plan least-privilege authorization and approved SSO for production.
- Keep untrusted pull requests away from privileged credentials and deploy identities.

## 7. Jenkinsfile smoke test

Create a disposable Pipeline job named `ch005-capstone-smoke`. This Pipeline deliberately uses no executor and no shell step.

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  stages {
    stage('Architecture') {
      steps { echo 'Controller coordinates; isolated agents execute builds.' }
    }
    stage('Policy') {
      steps { echo 'Authentication enabled, controller executors zero.' }
    }
    stage('Handoff') {
      steps { echo 'Plugin governance, monitoring and recovery documented.' }
    }
  }
  post {
    always { echo 'Capstone smoke check finished.' }
  }
}
```

**Expected:** success with no workspace-consuming shell/build step. Real build/test work requires an isolated agent and a reviewed agent template.

## 8. Agent and CI/CD design

Document the `trusted-linux`, `untrusted-pr` and `k8s-build` agent classes. Specify labels, immutable tool images, resource requests, service account and permissions, secret scope, workspace cleanup, network policy, concurrency and artifact retention.

Separate **CI** (Jenkins builds/tests/signs artifacts) from **CD reconciliation** (Argo CD applies approved Git desired state). Avoid giving all Jenkins jobs cluster-admin access.

## 9. Plugin governance and JCasC

Record the plugin bill of materials with plugin ID, approved version, dependency requirements, security advisories, Jenkins LTS/Java baseline, test status and rollback owner.

Minimal conceptual JCasC (validate against the actual installed plugin):

```yaml
jenkins:
  numExecutors: 0
  systemMessage: "Enterprise Jenkins — managed configuration"
```

Keep credentials in approved secret stores, not in YAML or logs. Review changes in Git and test in staging. Plugin upgrades may change JCasC schemas.

## 10. Capacity, monitoring and SLOs

Capture controller availability, JVM heap/GC, CPU, disk/inodes, queue wait, agent connectivity, Pipeline failure rate, plugin errors and backup freshness. Define alerts and runbooks based on measured baselines.

**Illustrative targets only:** controller availability 99.9%, p95 normal queue wait below 2 minutes, daily successful backup, quarterly clean-room restore drill. Adjust to workload and business needs.

## 11. Backup, restore and rollback

A usable backup requires consistent `JENKINS_HOME`, protected secrets/encryption keys, job history as needed, plugin versions and the compatible Jenkins runtime. Encrypt and access-control backups; test restore in a separate isolated instance. Do not attach the same writable home to two live controllers.

A failed plugin upgrade may require restoring the **entire pre-upgrade snapshot** rather than blindly downgrading one plugin in place. Record RPO/RTO and an approved rollback decision point.

## 12. Twenty incident and failure scenarios

| # | Failure | Diagnosis | Safe remediation |
|---|---|---|---|
| 1 | Controller won't start | Docker logs, Java/core compatibility, volume permissions, plugin dependency failures | Restore tested runtime/config or pre-change backup |
| 2 | JENKINS_HOME mounted incorrectly | Inspect volume mounts, UID/GID, jobs after restart | Reattach correct volume; do not overwrite |
| 3 | Administrator locked out | Check security realm, SSO, proxy and approved break-glass | Restore authentication and audit |
| 4 | Unauthorized anonymous access | Review security realm, matrix permissions and folder scopes | Remove unintended grants |
| 5 | Controller has build executors | Inspect built-in node and jobs | Set executors to zero; migrate builds to agents |
| 6 | Missing eligible agent | Inspect queue reason, labels and online nodes | Provision isolated agent or cancel job |
| 7 | Plugin dependency mismatch | Inspect plugin manager, Jenkins core, Java and startup logs | Restore tested plugin bill of materials |
| 8 | JCasC validation failure | Check schema/plugin versions and config diff | Revert reviewed config bundle |
| 9 | Credentials leaked in logs | Identify affected job, scope, token and viewers | Revoke/rotate and escalate |
| 10 | SCM checkout denied | Check credential scope, host keys, Git permissions | Repair least-privilege access |
| 11 | Webhook not delivered | Inspect provider delivery, endpoint auth and proxy | Restore trusted webhook |
| 12 | Pipeline syntax invalid | Inspect console and declarative syntax | Correct Jenkinsfile and rerun |
| 13 | Agent disconnected | Check remoting, TLS, DNS, JVM and network | Recover disposable agent |
| 14 | Controller disk pressure | Inspect df -h, df -i, build history and artifacts | Apply approved retention/expansion |
| 15 | High JVM GC pauses | Inspect heap, GC and plugin/thread activity | Profile before sizing changes |
| 16 | Reverse proxy 502 | Check controller process, service routing, TLS | Restore upstream |
| 17 | Kubernetes pod pending | Inspect scheduling, quota, service account and storage | Resolve capacity or permissions |
| 18 | Upgrade changes plugin behavior | Compare tested core/plugin/JCasC versions | Restore compatible snapshot |
| 19 | Backup missing secrets keys | Inspect backup manifest and restore rehearsal | Recover protected key material |
| 20 | Recovery succeeds but jobs fail | Run authenticated smoke jobs and check tools/agents | Repair integrations before signoff |

## 13. Eight SRE operational runbooks

### Controller outage

**Procedure:** Declare incident; capture logs and environment; identify runtime, volume, plugin or network fault; restore last-known-good and run smoke test.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Authentication incident

**Procedure:** Confirm SSO/proxy and RBAC; use audited break-glass; never disable security to regain access.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Credential exposure

**Procedure:** Stop affected builds, revoke and rotate, investigate logs and job trust boundary, record security incident.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Queue saturation

**Procedure:** Check queue reasons, agent labels, capacity and throttles; restore eligible isolated workers.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Plugin/JCasC regression

**Procedure:** Freeze changes, compare versions and config, reproduce in staging, restore approved catalog/bundle.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Storage saturation

**Procedure:** Inspect disk/inodes, controller home, retention and artifacts; expand safely or remove only approved disposable data.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Backup/restore rehearsal

**Procedure:** Use consistent encrypted backup and key material, restore in clean room, verify login, jobs and credentials.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

### Final operational handoff

**Procedure:** Record owners, SLOs, alerts, runbooks, approvals, version pins, RPO/RTO, risks and acceptance evidence.

**Exit criteria:** authenticated UI, controller isolation, representative Pipeline result, clean monitoring, protected secrets, owner and change/incident evidence.

## 14. Capstone acceptance gates

| Gate | Requirement | Mandatory |
|---|---|---|
| G1 | Disposable controller accessible on localhost only | Yes |
| G2 | Named administrator and security enabled | Yes |
| G3 | Controller executors set to zero | Yes |
| G4 | Successful no-agent Pipeline smoke test | Yes |
| G5 | Plugin versions and dependency review recorded | Yes |
| G6 | Agent isolation and CI/CD trust boundary documented | Yes |
| G7 | Consistent backup and clean-room restore design | Yes |
| G8 | Three failure scenarios diagnosed with rollback | Yes |
| G9 | Monitoring, on-call and operational handoff | Yes |
| G10 | Dedicated lab resources cleaned up | Yes |

## 15. Scoring rubric — 100 points

| Domain | Points |
|---|---:|
| Architecture and trust boundaries | 15 |
| Installation and persistence | 15 |
| Security and administration | 20 |
| Pipeline and agent isolation | 15 |
| Plugin/JCasC governance | 10 |
| Monitoring, troubleshooting and runbooks | 15 |
| Recovery, cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ and all mandatory gates; any credential exposure or production-impacting action is an automatic fail.

## 16. Cleanup and signoff

```bash
docker stop jenkins-ch005
docker rm jenkins-ch005
# Destructive: only after confirming this volume is exclusively lab-owned.
docker volume rm jenkins-ch005-home
```

Record observed Jenkins/Java versions, build number/result, controller executor count, volume and network inspection, plugin inventory, recovery design, evidence location and assessor.

**Part 01 completion:** Jenkins Fundamentals and Architecture — Chapters 001–005.

**Next:** Chapter 006 — Jenkins Installation on Linux, Packages and systemd, beginning Part 02 — Installation, Configuration and Administration.
