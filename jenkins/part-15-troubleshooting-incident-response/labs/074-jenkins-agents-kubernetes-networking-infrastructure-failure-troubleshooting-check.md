# Chapter 074 — Hands-on Lab: Jenkins Agent, Kubernetes and Network Recovery

**Environment:** Disposable Jenkins LTS, isolated Kubernetes namespace and synthetic agents, optional VM/SSH agent. Do not disrupt shared production clusters.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller/cloud plugin and agent templates | Baseline |
| 02 | Record queue labels and agent lifecycle | Diagram |
| 03 | Launch a known-good ephemeral agent | Build |
| 04 | Measure request-to-ready latency | Timeline |
| 05 | Inspect pod events and scheduling | Events |
| 06 | Inject lab node-selector mismatch | Pending pod |
| 07 | Restore matching scheduling policy | Recovery |
| 08 | Simulate ResourceQuota exhaustion | Error |
| 09 | Restore approved quota/capacity | Recovery |
| 10 | Inject invalid image reference | Pull failure |
| 11 | Restore pinned image digest | Recovery |
| 12 | Inspect Java/remoting handshake | Logs |
| 13 | Test Jenkins service DNS resolution | Result |
| 14 | Apply narrow lab NetworkPolicy deny | Failure |
| 15 | Restore least-privilege egress | Recovery |
| 16 | Simulate workspace permission error | Error |
| 17 | Restore UID/GID or mount policy | Recovery |
| 18 | Simulate bounded agent memory pressure | Status |
| 19 | Recover and compare provisioning p95 | Graph |
| 20 | Complete incident RCA/COA and handover | Report |

## 12 troubleshooting drills

1. Agent pod not created.
2. Service account RBAC denied.
3. Namespace quota exceeded.
4. Node affinity mismatch.
5. Missing taint toleration.
6. ImagePullBackOff.
7. Agent Java/remoting mismatch.
8. Jenkins URL/DNS failure.
9. NetworkPolicy egress denied.
10. TLS trust failure.
11. Agent OOMKilled or evicted.
12. PVC/workspace permission failure.

## Commands

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl describe pod <agent-pod> -n jenkins-build
kubectl get resourcequota -n jenkins-build
kubectl get networkpolicy -n jenkins-build
kubectl get nodes -o wide
```

Replace placeholders. Do not copy tokens, full environment values or unredacted agent logs into evidence.

## Evidence worksheet

```text
UTC timestamp:
Jenkins core/cloud plugin:
Agent image digest:
Queue label and reason:
Pod scheduling and readiness times:
Namespace quota and node constraints:
Image pull and remoting logs:
DNS/TLS/NetworkPolicy findings:
Resource limits and storage:
Injected fault:
Mitigation and rollback:
Provisioning p95 before/after:
Representative build:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Agent lifecycle and queue correlation validated.
- [ ] Scheduling/RBAC/quota faults isolated.
- [ ] Network/TLS repaired without bypass.
- [ ] Agent/workspace recovered.
- [ ] Representative build and cleanup succeed.
- [ ] No secrets in evidence.
- [ ] RCA/COA and reviewer sign-off complete.

**Related:** [Chapter 074 — Jenkins Agents, Kubernetes, Networking and Infrastructure Failure Troubleshooting](../074-jenkins-agents-kubernetes-networking-infrastructure-failure-troubleshooting.md).
