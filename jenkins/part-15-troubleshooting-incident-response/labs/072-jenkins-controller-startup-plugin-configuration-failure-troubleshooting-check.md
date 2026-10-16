# Chapter 072 — Hands-on Lab: Jenkins Startup, Plugin and Configuration Recovery

**Environment:** Disposable Jenkins LTS with isolated Jenkins home, compatible backup, test plugin manifest and JCasC. Use synthetic credentials. Never modify a shared production controller.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory core, Java, plugins and image | Baseline |
| 02 | Capture successful startup log | Log |
| 03 | Record known-good backup and digest | Manifest |
| 04 | Validate JVM startup flags | Result |
| 05 | Simulate invalid JVM flag | Error |
| 06 | Inspect pod restart and exit reason | Event |
| 07 | Compare plugin dependency manifest | Diff |
| 08 | Simulate missing plugin dependency in lab | Log |
| 09 | Restore compatible plugin set | Recovery |
| 10 | Validate JCasC YAML syntax | Result |
| 11 | Inject invalid JCasC attribute | Error |
| 12 | Validate against installed JCasC schema | Result |
| 13 | Simulate missing synthetic secret variable | Error |
| 14 | Restore secret provider configuration | Recovery |
| 15 | Test read-only Jenkins home copy | Error |
| 16 | Restore correct volume permissions | Recovery |
| 17 | Simulate proxy context path mismatch | HTTP |
| 18 | Correct proxy configuration | HTTP |
| 19 | Restore known-good image/configuration | Timeline |
| 20 | Validate RBAC, agents, jobs and handover | Sign-off |

## 12 troubleshooting drills

1. Wrong Java version.
2. Invalid JVM option.
3. Controller OOMKilled.
4. Missing plugin dependency.
5. Plugin/core incompatibility.
6. Plugin class linkage error.
7. Invalid JCasC YAML.
8. Unknown JCasC schema attribute.
9. Missing secret substitution.
10. Jenkins home permission denied.
11. Reverse proxy redirect failure.
12. SSO realm unavailable.

## Diagnostic commands

```sh
kubectl get pods -n jenkins -o wide
kubectl describe pod -n jenkins <controller-pod>
kubectl logs -n jenkins <controller-pod> --previous
kubectl get events -n jenkins --sort-by=.lastTimestamp
```

Use your lab namespace and controller name. The previous-log command is valid only after a restart.

## Evidence template

```text
UTC timestamp:
Core/Java/plugin versions:
Controller image and JCasC Git SHA:
Failure injection:
Startup log/first exception:
Pod exit code:
Storage and permissions:
Backup state:
Mitigation:
Recovery checks (UI/API/RBAC/jobs/agents):
RTO:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Failure classified as JVM/core/plugin/JCasC/storage/proxy.
- [ ] Backup and recovery path verified.
- [ ] No secrets disclosed.
- [ ] No concurrent Jenkins home writers.
- [ ] Representative Pipeline and agent verified.
- [ ] RCA and handover signed off.

**Related:** [Chapter 072 — Jenkins Controller Startup, Plugin and Configuration Failure Troubleshooting](../072-jenkins-controller-startup-plugin-configuration-failure-troubleshooting.md).
