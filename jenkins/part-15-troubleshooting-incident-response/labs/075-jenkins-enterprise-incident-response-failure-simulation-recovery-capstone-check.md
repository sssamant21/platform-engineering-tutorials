# Chapter 075 — Hands-on Enterprise Capstone: Jenkins Incident Response, Failure Simulation and Recovery

**Environment:** Disposable Jenkins LTS, test Git repository, synthetic credentials, Prometheus/Grafana, isolated Kubernetes/VM agents and approved lab registry. All failures must be injected in a sandbox.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller, plugins, Java and agents | Baseline |
| 02 | Create incident roles/severity matrix | RACI |
| 03 | Verify backup and rollback readiness | Restore proof |
| 04 | Build synthetic user-facing probe | Probe |
| 05 | Record normal queue and agent p95 | Graph |
| 06 | Simulate controller startup failure | Logs |
| 07 | Identify first startup exception | Hypothesis |
| 08 | Recover controller with approved rollback | Timeline |
| 09 | Inject JCasC/plugin regression in test | Error |
| 10 | Restore known-good config | Recovery |
| 11 | Simulate SCM webhook/checkout failure | Event |
| 12 | Recover SCM access without exposing secrets | Result |
| 13 | Inject Pipeline syntax failure | Lint |
| 14 | Fix via reviewed Git change | Commit |
| 15 | Simulate agent Pending/label mismatch | Queue/events |
| 16 | Recover scheduling and agent readiness | Graph |
| 17 | Simulate narrow NetworkPolicy/DNS failure | Test |
| 18 | Restore scoped connectivity and clean build | Build |
| 19 | Complete incident communications and RCA/COA | Report |
| 20 | Score 100-point assessment and handoff | Sign-off |

## 20 failure drills

1. Controller CrashLoopBackOff.
2. Java/core mismatch.
3. Plugin dependency failure.
4. JCasC schema failure.
5. Jenkins home permission failure.
6. JVM GC/heap pressure.
7. Queue label mismatch.
8. Agent capacity exhaustion.
9. Agent pod Pending.
10. ImagePullBackOff.
11. Agent OOMKilled.
12. Remoting disconnect.
13. DNS/NetworkPolicy outage.
14. TLS trust failure.
15. Webhook not delivered.
16. SCM credential failure.
17. Jenkinsfile syntax failure.
18. Missing Pipeline step.
19. Synthetic secret-provider outage.
20. Artifact registry outage.

## Lab diagnostic commands

```sh
kubectl get pods -n jenkins -o wide
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl logs -n jenkins <controller-pod> --since=30m
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
```

Adjust namespaces and names. Preserve previous-container logs when available. Do not dump secret values.

## Incident evidence worksheet

```text
Incident ID / severity:
Incident commander / technical lead:
Controller image / Java / plugins / JCasC SHA:
Fault and blast radius:
Start / detection / acknowledgment UTC:
First meaningful error:
Hypothesis A and falsification:
Hypothesis B and falsification:
Mitigation and rollback:
Independent service recovery:
Queue p95 / agent p95 before-after:
Representative build and artifact digest:
Security/redaction check:
RCA/COA and owner:
Reviewer and sign-off:
```

## Acceptance scorecard

| Category | Maximum |
|---|---:|
| Architecture, inventory and safety | 10 |
| Detection, severity and command | 10 |
| Evidence, timeline and hypotheses | 15 |
| Controller/plugin/JCasC recovery | 15 |
| Pipeline/SCM/credentials recovery | 15 |
| Agent/Kubernetes/network recovery | 15 |
| Communications/escalation | 10 |
| RCA/COA, validation and handover | 10 |
| **Total** | **100** |

Suggested pass: 85 and **all mandatory gates** from Chapter 075. An untested item is not a pass.

## Final acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 20 drills completed or explicitly blocked.
- [ ] No secrets disclosed.
- [ ] No production/shared resource disrupted.
- [ ] Controller and agent failures recovered.
- [ ] Independent service and Pipeline validation.
- [ ] Incident communications and RCA/COA complete.
- [ ] Scorecard and reviewer sign-off recorded.

**Related:** [Chapter 075 — Jenkins Enterprise Incident Response, Failure Simulation and Recovery Capstone](../075-jenkins-enterprise-incident-response-failure-simulation-recovery-capstone.md).
