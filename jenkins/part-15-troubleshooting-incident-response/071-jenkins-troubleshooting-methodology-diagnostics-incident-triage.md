# Chapter 071 — Jenkins Troubleshooting Methodology, Diagnostics and Incident Triage

**Part 15 — Troubleshooting and Incident Response**  
**Audience:** Jenkins SRE, DevOps/platform engineers, on-call responders and incident commanders  
**Prerequisites:** Chapters 066–070, Jenkins LTS lab, Jenkins UI/API access, Prometheus/Grafana, optional Kubernetes agents.

## Objectives

Apply a repeatable Jenkins incident investigation method, classify failures, preserve evidence, prioritize impact, distinguish controller/agent/Pipeline/SCM/security issues, mitigate safely, communicate status and produce RCA/COA.

## 1. Incident triage architecture

```text
Alert / user report / failed build
               |
       Confirm impact and scope
               |
   Controller? Queue? Agent? Pipeline?
        /         |        |        \
    JVM/I/O    labels    K8s/cloud  SCM/build
        \         |        |        /
       Evidence + timeline + hypotheses
               |
       Safe mitigation / rollback
               |
       Verify user-facing recovery
               |
       RCA + corrective actions
```

Avoid restarting the controller as the first diagnostic step. A restart can destroy ephemeral evidence and interrupt unrelated jobs.

## 2. First 15 minutes

| Time | Action | Evidence |
|---|---|---|
| 0–2 min | Acknowledge alert, assign incident owner | Incident ID |
| 2–5 min | Confirm affected users, environment and scope | Synthetic probe, build/queue |
| 5–8 min | Check recent changes and failure domain | Git SHA, plugin/JCasC rollout |
| 8–12 min | Preserve logs, events, metrics and timestamps | Evidence links |
| 12–15 min | Choose low-risk mitigation and communication | Decision record |

Time boxes are guidance, not rigid incident policy. Escalate immediately for security incidents, data integrity risks or widespread outage.

## 3. Failure classification

| Domain | Typical symptoms | First checks |
|---|---|---|
| Controller | UI/API unavailable, restarts, high GC | Pod/process, JVM, logs |
| Queue | Jobs stuck waiting, idle executors | Queue reason, labels, locks |
| Agent | Offline/disconnected, Pending pods | Remoting, K8s events |
| Pipeline | Syntax error, CPS/step failure | Jenkinsfile, plugin versions |
| SCM | Webhook missing, checkout failure | SCM delivery, auth, DNS |
| Credentials | Unauthorized or expired tokens | Secret provider, scope |
| Storage | Disk full, latency, missing metadata | Jenkins home I/O |
| Plugins/JCasC | Startup failure, missing step, drift | Version/config diff |
| Network | Proxy/TLS/DNS failures | Connectivity and certs |
| External service | Registry/artifact/test DB outage | Dependency health |

Separate application test failures from Jenkins infrastructure failures before assigning ownership.

## 4. Severity and impact

Illustrative severity:
- **SEV1:** Widespread production release blocking, security exposure or controller outage with no workaround.
- **SEV2:** Major CI capacity degradation or critical release path impaired.
- **SEV3:** Limited job/team impact with workaround.
- **SEV4:** Nonurgent warning, cleanup or documentation.

Use your organization's official definitions and escalation matrix. Prioritize impact, not just number of failed builds.

## 5. Evidence collection and chain of custody

Capture UTC timestamps, Jenkins core/Java/plugin versions, controller/agent IDs, build URL, queue reason, change history, metrics, logs and Kubernetes events. Record collection time and access restrictions. Redact secrets and personal data before sharing. Do not paste complete environment variables or credentials into tickets.

Useful commands in a lab:

```sh
kubectl get pods -n jenkins -o wide
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl logs -n jenkins deploy/jenkins --since=30m
kubectl describe pod <agent-pod> -n jenkins-build
```

Replace namespaces, deployment and pod names. Log access may be sensitive; use approved permissions. On VM installations, use systemd/service logs rather than Kubernetes commands.

## 6. Controller diagnostic workflow

1. Test UI/API externally and independently of metrics scrape.
2. Check process/pod restart, OOMKilled, ingress/proxy and TLS.
3. Review JVM heap, GC pauses, CPU and thread contention.
4. Inspect Jenkins home filesystem capacity, latency and errors.
5. Compare recent core/plugin/JCasC changes.
6. Decide whether to mitigate capacity, rollback or restart under approval.

A Prometheus target `up == 0` proves scrape failure, not necessarily user-facing outage.

## 7. Queue and executor diagnostic workflow

Inspect oldest queued items, assigned labels, compatible online executors, node permissions, lock/throttle constraints and cloud provisioning. A queue with idle executors can be a label mismatch. Avoid increasing controller executors to fix missing agent capacity.

## 8. Kubernetes and VM agents

For Kubernetes: Pending, ImagePullBackOff, OOMKilled, eviction, service-account permissions, DNS, network policy, PVC and autoscaler limits. For VM agents: remoting/JVM version, disk, workspace permissions, CPU/memory, connectivity and SSH/service identity. Correlate agent failure timestamps with queued builds.

## 9. Pipeline and SCM diagnostics

Validate Jenkinsfile syntax and plugin step availability, agent label, checkout credentials, webhook delivery, branch protection, Git host rate limits, network and certificate trust. Reproduce with synthetic credentials in staging; do not disable TLS verification or print secrets as a shortcut.

## 10. Hypothesis-driven investigation

Use an incident worksheet:

```text
Observed symptom:
Customer impact:
Earliest confirmed timestamp (UTC):
Recent change:
Hypothesis A / supporting evidence / falsification test:
Hypothesis B / supporting evidence / falsification test:
Immediate mitigation and risk:
Verification signal:
RCA owner:
```

Avoid declaring root cause solely from temporal correlation. Compare baseline, logs and independent signals.

## 11. Safe mitigation hierarchy

1. Stop harmful new changes and protect evidence.
2. Reduce workload or isolate affected agent pool.
3. Restore known-good agent template, plugin/JCasC or image.
4. Recover dependencies and credentials through approved paths.
5. Restart or fail over only with assessed impact and recovery plan.
6. Validate synthetic and representative real workloads.

Never blindly delete `JENKINS_HOME`, plugin directories, build history or encryption keys. A plugin downgrade may not be compatible with persisted state; test backups.

## 12. Troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Jenkins UI 503 | Proxy/controller status |
| 02 | Metrics down, UI up | Scrape auth/path |
| 03 | Controller OOMKilled | Memory/heap/native |
| 04 | CPU 100% | Threads/GC/plugins |
| 05 | GC pauses | Heap/GC logs |
| 06 | Jenkins home full | Disk/inodes/retention |
| 07 | Queue grows | Executor capacity |
| 08 | Idle agents, queued jobs | Label mismatch |
| 09 | Lock contention | Lockable resources |
| 10 | Agent pod Pending | Scheduler/quota |
| 11 | Agent ImagePullBackOff | Registry/auth |
| 12 | Agent OOMKilled | Resource limits |
| 13 | Remoting disconnect | Network/versions |
| 14 | Checkout authentication | SCM credential scope |
| 15 | Webhook not delivered | SCM delivery log |
| 16 | Pipeline step missing | Plugin compatibility |
| 17 | JCasC reload failure | YAML/schema/secret |
| 18 | Secret provider unavailable | Provider status |
| 19 | Artifact registry timeout | External dependency |
| 20 | Failed upgrade | Change diff/rollback |

## 13. Five production runbooks

### A. Controller unavailable
Confirm external probe and affected users; inspect process/pod, ingress, JVM, storage and recent changes; preserve evidence; execute approved mitigation; verify UI, queue, agents and representative Pipeline.

### B. Queue starvation
Check oldest items and queue reasons; compare compatible executors, labels, locks and quotas; restore correct agent pool; validate queue p95 and oldest age.

### C. Agent provisioning incident
Inspect Kubernetes/VM events, image pulls, permissions and cloud limits; recover template or capacity; verify remoting and synthetic build.

### D. Pipeline/SCM failure
Classify application versus infrastructure; inspect Jenkinsfile, checkout, webhook, credentials and plugin steps; repair through reviewed change; rerun representative build.

### E. Security or credential incident
Restrict impacted access, preserve audit evidence, escalate security, rotate/revoke affected credentials, restore least privilege and verify negative access tests. Do not expose secret values during triage.

## 14. Communication templates

**Initial update:** Incident ID, severity, impacted workflows, start time (UTC), mitigation underway, owner and next update time.

**Progress update:** Current user impact, confirmed evidence, action taken, risks and next decision point. Distinguish confirmed facts from hypotheses.

**Resolution:** Recovery timestamp, validation evidence, residual risks, follow-up RCA owner and next review.

## 15. RCA/COA structure

Include summary, impact, timeline, detection gap, triggering change, contributing conditions, confirmed root cause with evidence, mitigation, recovery validation, preventive actions, owners and due dates. Avoid blame and unsupported causal claims.

## 16. Acceptance criteria

- [ ] Severity and impact classified.
- [ ] First-15-minute evidence collected.
- [ ] Controller/queue/agent/Pipeline domain isolated.
- [ ] At least two hypotheses evaluated.
- [ ] No secrets disclosed.
- [ ] Safe mitigation documented and approved.
- [ ] Recovery verified by user-facing checks.
- [ ] Incident communications recorded.
- [ ] RCA/COA and follow-up ownership assigned.
- [ ] Handover and escalation path tested.

**Companion:** [Chapter 071 hands-on lab](labs/071-jenkins-troubleshooting-methodology-diagnostics-incident-triage-check.md).  
**Next:** Chapter 072 — Jenkins Controller Startup, Plugin and Configuration Failure Troubleshooting.
