# Chapter 071 — Hands-on Lab: Jenkins Incident Triage and Diagnostic Methodology

**Environment:** Disposable Jenkins LTS, synthetic Pipelines, Prometheus/Grafana, optional Kubernetes agents. All faults must be injected in the lab, never production.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller/Java/plugins | Baseline |
| 02 | Define severity and ownership | Matrix |
| 03 | Draw failure-domain decision tree | Diagram |
| 04 | Create incident ticket with UTC timestamp | Ticket |
| 05 | Verify independent UI/API probe | Result |
| 06 | Compare scrape and service health | Graph |
| 07 | Capture controller logs safely | Redacted excerpt |
| 08 | Capture JVM/CPU/GC signals | Graph |
| 09 | Inspect Jenkins home I/O and capacity | Report |
| 10 | Inspect queue and oldest item | Snapshot |
| 11 | Check labels and executor compatibility | Matrix |
| 12 | Inspect agent provisioning | Evidence |
| 13 | Review Kubernetes pod events | Events |
| 14 | Inspect synthetic Pipeline failure | Build |
| 15 | Validate SCM webhook/checkout | Evidence |
| 16 | Review recent plugin/JCasC change | Diff |
| 17 | Write two competing hypotheses | Worksheet |
| 18 | Apply approved lab mitigation | Change |
| 19 | Verify user-facing recovery | Result |
| 20 | Write RCA/COA and handover | Report |

## 12 troubleshooting drills

1. Controller UI unavailable.
2. Metrics scrape failure only.
3. Controller OOMKilled.
4. JVM CPU/GC pressure.
5. Jenkins home storage pressure.
6. Queue starvation.
7. Idle executors with queued job.
8. Kubernetes agent Pending.
9. Agent ImagePullBackOff.
10. Remoting disconnect.
11. SCM authentication failure.
12. JCasC/plugin regression.

## Lab diagnostic commands

```sh
kubectl get pods -n jenkins -o wide
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl logs -n jenkins deploy/jenkins --since=30m
kubectl describe pod <agent-pod> -n jenkins-build
```

Adjust resources to your lab. Do not include credentials, tokens or complete environment dumps in evidence.

## Incident evidence worksheet

```text
Incident ID:
Severity and affected workflows:
Start/detection UTC:
Controller/Java/plugin versions:
External probe and scrape status:
Queue/executor/agent state:
Recent changes:
Log/metric/event evidence:
Hypothesis A and test:
Hypothesis B and test:
Mitigation and risk:
Recovery validation:
RCA/COA owner:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or marked blocked.
- [ ] Incident scope and severity defined.
- [ ] Evidence preserved before mitigation.
- [ ] Failure domain isolated with falsifiable hypotheses.
- [ ] Recovery independently validated.
- [ ] No secrets disclosed.
- [ ] RCA/COA and escalation documented.
- [ ] Reviewer signed off.

**Related:** [Chapter 071 — Jenkins Troubleshooting Methodology, Diagnostics and Incident Triage](../071-jenkins-troubleshooting-methodology-diagnostics-incident-triage.md).
