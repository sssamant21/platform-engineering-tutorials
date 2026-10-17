# Chapter 078 — Jenkins High Availability, Workload Isolation and Controller Reliability Engineering

**Part 16 — Scaling, Controller Capacity and Reliability**  
**Audience:** Jenkins SRE, platform engineers, architects and incident responders  
**Prerequisites:** Chapters 076–077, isolated Jenkins LTS, backup/restore tooling, Prometheus/Grafana, test Kubernetes or VM agents.

## Objectives

Design reliable Jenkins service boundaries, understand controller availability limitations, separate workloads and trust zones, engineer graceful recovery, prevent shared-state corruption, define SLOs/RTO/RPO and test resilience without pretending that multiple Jenkins controller replicas are active-active.

## 1. Jenkins availability fundamentals

A conventional Jenkins controller owns its state in `JENKINS_HOME`: job configurations, build metadata, plugin data, credentials and queue/Pipeline state. **Do not run multiple independent active controller processes against one writable Jenkins home.** A Kubernetes Deployment with `replicas: 2` and a shared PVC is not a supported generic HA pattern.

Instead combine:
- Reliable infrastructure, durable storage and monitored single-active controller lifecycle.
- Kubernetes or VM restart/recovery and safe fencing.
- Verified backups, restoration and tested RTO/RPO.
- Ephemeral agents in multiple compatible node pools/zones.
- Multiple **independent** controllers for workload isolation.
- External SCM/artifact/secret services with their own availability controls.

## 2. Reference architecture

```text
                        GitHub/GitLab webhooks
                                  |
                         routing / organization
                           /               \
                Controller A            Controller B
                trusted releases        untrusted PR CI
                 own JENKINS_HOME        own JENKINS_HOME
                      |                        |
               protected agents          sandboxed agents
                      |                        |
              artifact/signing svc        test registries

  Each controller: durable state + backups + probes + metrics + on-call
```

Partitioning reduces blast radius but adds administrative and routing overhead. Shared SCM or artifact outages remain common dependencies.

## 3. Failure domains and isolation

| Failure domain | Mitigation |
|---|---|
| Controller process | Monitored restart and known-good rollback |
| Jenkins home storage | Durable volumes, I/O SLO, backup/restore |
| Plugin/JCasC rollout | Immutable images, canary staging, version lock |
| JVM memory/CPU | Baseline, limits, alerts and capacity |
| Agent node failure | Ephemeral replacement and compatible pools |
| Availability zone | Multi-zone agents, validated storage failover |
| SCM/registry/secret provider | Dependency SLO, bounded retries |
| Credential compromise | Separate trust zones and least privilege |
| Untrusted PR code | Isolated agents, no privileged secrets |
| Webhook routing | Per-controller ownership and replay plan |

## 4. Recovery topology: single active writer

Use a single controller writer to the state volume. During recovery:
1. Confirm prior controller has stopped and cannot write.
2. Verify storage detach/attach and fencing.
3. Restore compatible image, Java, plugin lock and JCasC.
4. Mount validated Jenkins home to **one** controller.
5. Confirm credentials/decryption keys and access controls.
6. Validate UI/API, jobs, queue, agents and representative Pipeline.
7. Record recovery time and reconciliation of interrupted jobs.

Storage replication does not remove the need for fencing and consistent backups. Kubernetes rescheduling may restore process availability but not protect against corrupted state or logical misconfiguration.

## 5. Kubernetes reliability patterns

- Use readiness/startup probes tuned to actual boot behavior; avoid liveness restart loops during slow plugin initialization.
- Set CPU/memory requests and limits based on measured controller requirements.
- Use PDBs and controlled node maintenance where they apply, but a PDB cannot create a second safe active controller.
- Ensure durable PVC behavior and zone topology are understood.
- Use graceful shutdown and planned maintenance windows.
- Run agents across zones/node pools, while preserving trust isolation.
- Validate external probes independently of Prometheus scrape health.

## 6. Workload and security isolation

Create separate controllers or agent pools when release signing, production deployment, untrusted pull requests, regulated workloads and high-volume CI have different risk profiles. Keep separate credentials and authorization scopes. Avoid exposing production secrets to untrusted Jenkinsfiles or shared workspaces.

## 7. SLO, RTO and RPO design

Illustrative objectives (validate with business owners):

| Indicator | Example |
|---|---|
| Controller external availability | 99.9% monthly |
| Critical release queue p95 | under 2 min |
| Agent readiness p95 | under 90 s |
| Controller restore RTO | 60 min |
| Jenkins state RPO | 15 min |

RTO is maximum acceptable recovery time; RPO is maximum acceptable data loss. A backup schedule alone does not prove achievable RPO: include backup consistency, replication lag, encryption keys, restore speed and verification.

## 8. Backup and restore boundaries

Capture Jenkins home state, plugin/core/Java version manifest, JCasC and job definitions, encryption key material, external secret-provider references and storage configuration. Restrict backup access and encrypt at rest/in transit. Prefer application-consistent snapshots or a controlled quiesce/backup process; validate by restoring to an isolated controller.

Do not restore a snapshot over a running controller or expose the same home to two writers. Keep build artifacts in external immutable repositories when possible.

## 9. Failure injection and resilience experiments

Use a disposable environment:
1. Baseline probes, queue, agents and controller state.
2. Simulate agent/node failure and verify replacement.
3. Stop test controller; measure restart and service restoration.
4. Simulate failed plugin/JCasC upgrade and restore known-good.
5. Test backup restore in a **separate** namespace/storage copy.
6. Test temporary SCM/artifact unavailability and bounded retries.
7. Validate secret isolation with synthetic credentials.
8. Measure RTO/RPO and recovery acceptance.

Define abort conditions, evidence capture and owner before each test.

## 10. Troubleshooting scenarios

| # | Scenario | Diagnosis |
|---|---|---|
| 01 | Controller pod crash | JVM/pod logs |
| 02 | Restart loop | Startup probe/plugin initialization |
| 03 | PVC attach blocked | Storage topology |
| 04 | Two writers attempted | Fencing and deployment configuration |
| 05 | Jenkins home I/O slow | Volume metrics |
| 06 | Missing encryption keys | Backup completeness |
| 07 | Plugin upgrade breaks startup | Version compatibility |
| 08 | JCasC schema drift | Config validation |
| 09 | Agent node unavailable | Pool/zone capacity |
| 10 | Single-zone pool exhausted | Multi-zone scheduling |
| 11 | Webhook routed wrong | SCM/controller mapping |
| 12 | Untrusted PR reaches secret | Trust boundary |
| 13 | SSO unavailable | Identity provider |
| 14 | Registry outage | External dependency |
| 15 | SCM outage | Dependency health |
| 16 | Liveness probe too aggressive | Probe thresholds |
| 17 | PDB blocks drain | Disruption policy |
| 18 | Backup corrupt | Restore test |
| 19 | Restore exceeds RTO | Recovery bottleneck |
| 20 | Queue state lost after restart | Recovery reconciliation |

## 11. Six production runbooks

### A. Controller outage
Confirm external probe, preserve logs and verify single writer; inspect process/JVM/storage; restore compatible state; validate critical workflows.

### B. Storage/PVC incident
Identify volume health and attachment, fence old writer, preserve snapshot; restore compatible volume; validate jobs and credentials.

### C. Failed plugin/JCasC rollout
Freeze changes, capture first error, compare tested manifest; revert Git/image and restore compatible backup if necessary; verify auth and jobs.

### D. Agent zone outage
Inspect node pools, scheduling and cloud quotas; restore compatible agents in healthy zones; verify queue p95 and release isolation.

### E. Untrusted workload isolation failure
Stop affected jobs, restrict access, notify security, rotate affected credentials and review audit logs; validate negative access tests before resuming.

### F. Backup/restore exercise
Select known-good backup, verify integrity and keys, restore to isolated environment, measure RTO/RPO, execute representative Pipeline and record sign-off.

## 12. Recovery acceptance checklist

- [ ] Single active controller writer verified.
- [ ] Controller state/keys/backups protected.
- [ ] Failure domains and dependencies mapped.
- [ ] Trusted and untrusted workloads isolated.
- [ ] RTO/RPO agreed and restore-tested.
- [ ] External availability probe configured.
- [ ] Agent pools tolerate tested node failure.
- [ ] Upgrade rollback tested.
- [ ] Security/SSO and credentials validated.
- [ ] Representative builds and stakeholder sign-off recorded.

**Companion:** [Chapter 078 hands-on lab](labs/078-jenkins-high-availability-workload-isolation-controller-reliability-engineering-check.md).  
**Next:** Chapter 079 — Jenkins Resilience Testing, Failure Domains, SLOs and Disaster Recovery Readiness.
