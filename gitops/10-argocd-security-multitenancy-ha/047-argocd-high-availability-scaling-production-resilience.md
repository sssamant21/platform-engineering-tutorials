# Chapter 047 — Argo CD High Availability, Scaling and Production Resilience

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 10:** Argo CD Security, Multi-Tenancy and High Availability  
**Chapter:** 047 / 100  
**Audience:** Platform Engineers, Kubernetes Administrators, SREs, DevSecOps Engineers

> **Safety:** Run failure injection only in a disposable staging cluster with a tested recovery path. Never delete production Redis, Argo CD application state, or cluster credentials as a resilience experiment.

## 1. Learning objectives

By the end of this chapter, you can:
1. Explain the availability boundaries of the Argo CD API server, application controller, repository server, Redis, ApplicationSet controller, and Dex or external OIDC.
2. Deploy a supported HA installation and verify replica placement, readiness, disruption budgets and dependencies.
3. Capacity-plan reconciliation and manifest generation without indiscriminately raising concurrency.
4. Troubleshoot repository timeouts, controller backlog, API failures, OOMKills, and Redis outages.
5. Perform controlled staging failure tests and validate recovery using measurable acceptance criteria.
6. Design GitOps recovery so that cluster workloads continue serving while the control plane is unavailable.

## 2. Reference architecture and availability model

```text
GitLab (desired state) ---> repo-server replicas <--- application-controller
                               |                           |
External OIDC ---> ingress ---> argocd-server replicas     |
                               |                           v
                           Redis HA                 Kubernetes API
                               ^
                        ApplicationSet controller
                               |
                      Git / cluster generators

Prometheus / Alertmanager <-- component metrics and logs
```

Argo CD is a **reconciliation control plane**, not an application data plane. If Argo CD is unavailable, already-running workloads generally keep serving traffic; new GitOps changes, drift correction and sync operations may be delayed. This is not a guarantee of application availability: workloads can still fail independently, and Argo CD-managed automation may be required to repair them.

| Component | Availability concern | Primary operational signal |
| --- | --- | --- |
| `argocd-server` | API/UI access, authentication, CLI operations | API success rate, latency, ready replicas |
| `argocd-repo-server` | Git/Helm/Kustomize manifest generation | Generation latency/errors, CPU, memory |
| `argocd-application-controller` | Cluster reconciliation and application state | Queue backlog, reconciliation duration, errors |
| Redis | Transient cache/coordination dependency | Availability, failover, connection errors |
| ApplicationSet controller | Application generation and lifecycle | Generator errors, controller availability |
| Dex / external OIDC | User authentication | Login failures, provider reachability |
| Kubernetes API / etcd | Cluster state and deployment operations | API latency, 429/5xx, connectivity |

**Critical distinction:** Multiple controller pods do not automatically mean all replicas actively reconcile every application. HA sharding, leadership and behavior depend on the installed Argo CD version and configuration. Validate effective distribution in metrics and logs.

## 3. Prerequisites and baseline capture

Use a non-production cluster, `kubectl`, `helm`, `argocd`, a Git repository containing a test Application, and a metrics stack. Confirm the installation method and chart/version before changing settings.

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl -n argocd get deploy,sts,pods -o wide
kubectl -n argocd get pdb
kubectl -n argocd get svc,ingress
kubectl -n argocd get cm argocd-cm argocd-cmd-params-cm -o yaml
argocd version --client
helm -n argocd list
```

Record replica counts, resource requests/limits, node and zone placement, component restarts, CPU/memory utilization, GitOps application counts and reconcile latency. Store baseline measurements with a timestamp and change ticket.

## 4. Install a supported HA baseline

Prefer a **version-pinned, upstream-supported HA installation** over manually duplicating Deployments. For Helm-based installations, first inspect the exact chart values for the selected chart release; names and supported settings can change.

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm show values argo/argo-cd --version "$CHART_VERSION" > upstream-values.yaml
helm show chart argo/argo-cd --version "$CHART_VERSION"
```

Example staging overlay (verify against the pinned chart before use):

```yaml
# argocd-ha-values.yaml — illustrative, version-dependent chart keys
global:
  domain: argocd.example.internal
server:
  replicas: 2
repoServer:
  replicas: 2
controller:
  replicas: 2
applicationSet:
  replicas: 2
redis-ha:
  enabled: true
```

**Do not blindly apply the example.** In particular, confirm whether the chart supports the controller replica/sharding mode and whether Redis HA requires additional configuration. Confirm the chart's handling of PodDisruptionBudgets, anti-affinity, security contexts and replica defaults. Use a non-placeholder domain and configure TLS/SSO through the existing secure installation process.

```bash
helm template argocd argo/argo-cd \
  --namespace argocd \
  --version "$CHART_VERSION" \
  -f argocd-ha-values.yaml > rendered-argocd.yaml

kubectl apply --dry-run=server -f rendered-argocd.yaml
# Only after review and change approval:
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd --create-namespace \
  --version "$CHART_VERSION" \
  -f argocd-ha-values.yaml \
  --wait --timeout 15m
```

For installations managed by Argo CD itself, avoid conflicting Helm and GitOps ownership. Make changes through the authoritative deployment mechanism and retain a bootstrap recovery procedure outside the affected Argo CD instance.

## 5. Replica placement, disruption budgets and capacity

HA requires more than replica count:

- Spread replicas across nodes and, where possible, availability zones using topology spread constraints or pod anti-affinity.
- Set realistic CPU/memory requests to prevent resource starvation; avoid limits that cause repeated OOMKills during manifest generation.
- Add PodDisruptionBudgets for components with safe redundant replicas; verify PDB selectors match the actual chart labels.
- Keep sufficient spare node capacity to survive one node/zone failure.
- Ensure ingress/load balancers, DNS, external identity, Git providers and Kubernetes API access do not remain single points of failure.
- For controllers, confirm sharding is working before assuming a two-pod installation doubles throughput.

```bash
kubectl -n argocd get pods -o wide
kubectl -n argocd get pdb -o wide
kubectl -n argocd describe pdb
kubectl -n argocd top pods
kubectl top nodes
kubectl -n argocd get events --sort-by=.lastTimestamp | tail -30
```

**Sizing approach:** measure application count, resource count, average manifest generation duration, Git refresh rate, reconciliation duration and peak bursts. Scale one bottleneck at a time and compare pre/post metrics. Avoid unbounded parallelism, which can overload Git servers and Kubernetes API servers.

## 6. Controller sharding and reconciliation performance

The application controller can become constrained by cluster/API latency, large application resource trees, expensive diff operations or an uneven workload distribution.

Inspect controller health and logs:

```bash
kubectl -n argocd get sts
kubectl -n argocd logs sts/argocd-application-controller --since=30m --tail=300
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-application-controller -o wide
argocd app list
```

StatefulSet names and labels vary by installation. If a controller is stuck, determine whether the root cause is a Git/provider outage, Kubernetes API throttling, cluster credential failure, excessive application count, or a resource-intensive manifest generator. Review documented controller shard configuration for the pinned Argo CD release before changing replica counts or sharding algorithms.

Tune reconciliation intervals and parallelism only with measured evidence and version-specific documentation. Back off aggressively if the Kubernetes API returns 429 responses or latency rises.

## 7. Repository server scaling and manifest generation

The repository server is sensitive to Helm dependency resolution, Kustomize processing, plugins, large repositories and concurrent generation requests.

```bash
kubectl -n argocd get deploy argocd-repo-server
kubectl -n argocd top pods -l app.kubernetes.io/name=argocd-repo-server
kubectl -n argocd logs deploy/argocd-repo-server --since=30m --tail=300
argocd repo list
```

When generation slows, compare request rate, p95/p99 latency, pod CPU/memory, OOM events and upstream Git response times. Avoid unsafe plugin execution and ensure custom plugins are sandboxed and resource-limited. Prefer immutable revisions and cached dependencies where appropriate. Scale repo-server replicas only after validating memory headroom and upstream rate limits.

## 8. Redis, authentication and dependency resilience

Redis HA requires a supported topology and a verified failover process. A Redis HA deployment is not equivalent to a zero-interruption guarantee: transient connection failures may occur during failover.

```bash
kubectl -n argocd get pods | grep -E 'redis|dex|server'
kubectl -n argocd get endpoints,endpointslices
kubectl -n argocd logs deploy/argocd-server --since=20m --tail=200
```

Avoid destructive Redis tests in production. During a Redis incident, first confirm endpoint readiness, DNS, authentication configuration and network policies. For SSO incidents, isolate external IdP failures from Argo CD server failures; verify token lifetimes and clock synchronization without exposing secrets.

## 9. Hands-on lab A — Validate HA placement and readiness

**Goal:** verify a staging installation remains accessible when one server or repo-server pod is terminated.

1. Record `kubectl -n argocd get pods -o wide` and `kubectl -n argocd get pdb`.
2. Confirm at least two ready server and repo-server replicas on different nodes.
3. Open the Argo CD UI or run a non-mutating `argocd app list`.
4. Delete **one identified staging server pod**, not a controller or Redis pod:

```bash
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-server
# Replace POD_NAME with one verified staging argocd-server pod.
kubectl -n argocd delete pod POD_NAME
kubectl -n argocd rollout status deploy/argocd-server --timeout=5m
kubectl -n argocd get pods -o wide
argocd app list
```

5. Repeat only for one repo-server pod if adequate replicas and headroom exist. Generate or refresh a test application's manifests and confirm success.

**Pass:** API operations remain available or recover within the documented test objective; a replacement pod becomes Ready; no sustained reconciliation errors; test workloads stay healthy. Capture actual outage/recovery duration rather than asserting zero downtime.

## 10. Hands-on lab B — Reconciliation backlog and recovery

Use a small disposable test Application and a dedicated namespace. Record the starting Git revision and application health.

```bash
argocd app get demo-staging
argocd app history demo-staging
kubectl -n argocd top pods
```

Temporarily block repository access **only in a dedicated lab** using a controlled network policy or lab-only test endpoint. Do not modify shared Git provider credentials. Observe refresh errors and reconciliation delay. Restore connectivity and verify the application returns to the expected Git revision.

```bash
argocd app get demo-staging --refresh
argocd app diff demo-staging
argocd app wait demo-staging --health --timeout 300
```

If auto-sync is disabled, a healthy status alone does not prove the latest revision was applied. Confirm the expected sync revision and sync status. Clean up the lab-only network restriction after testing.

## 11. Hands-on lab C — Safe node drain

Before testing, confirm enough cluster capacity, PDB allowances, replica placement and permission to drain the staging node.

```bash
kubectl -n argocd get pods -o wide
kubectl -n argocd get pdb
kubectl describe node NODE_NAME
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data --timeout=10m
kubectl -n argocd get pods -o wide
kubectl uncordon NODE_NAME
```

Do **not** force eviction or bypass PDBs merely to make the test pass. Stop and record a failed resilience criterion if eviction is blocked, scheduling capacity is insufficient, or replicas become unavailable.

## 12. Observability, dashboards and alerts

Collect component metrics using the pinned release's ServiceMonitor or scrape configuration. Verify actual metric names from `/metrics` before deploying rules, since metric availability varies by release.

Suggested dashboard panels:
- Ready vs desired replicas by component and node/zone.
- Application sync/health state, reconcile duration and reconcile error rate.
- Repo-server manifest generation latency and errors.
- API request latency and 5xx rate.
- Pod CPU, memory, OOMKills, restarts and throttling.
- Redis health and failover events.
- Git provider and Kubernetes API availability, latency and throttling.

**Illustrative alert conditions (calibrate against baseline):**

| Condition | Suggested severity | First response |
| --- | --- | --- |
| No ready Argo CD API server for 5 min | Critical | Check ingress, pods, DNS and authentication |
| Controller reconciliation backlog persistently increasing | Warning | Check API throttling, Git and controller load |
| Repo-server generation errors above baseline for 10 min | Warning | Inspect Git connectivity, memory and plugins |
| All replicas scheduled on one node or zone | Warning | Review topology spread and capacity |
| Sustained application OutOfSync after approved release | Warning | Verify revision, sync policy and deployment errors |

Avoid paging solely because an intentionally paused or manually synced application is OutOfSync. Scope alerts to production-critical applications and agreed SLOs.

## 13. Troubleshooting matrix — ten production scenarios

| # | Symptom | Likely causes | Checks | Recovery |
| --- | --- | --- | --- | --- |
| 1 | Argo CD UI returns 502/503 | Ingress, service endpoints, server pods | `get ingress,svc,endpoints,pods` | Restore server readiness/ingress |
| 2 | Login loops or OIDC errors | IdP outage, callback mismatch, clock skew | Server/Dex logs, redirect configuration | Restore IdP path/config; never disable auth as workaround |
| 3 | Apps remain Unknown | Controller unavailable, cluster credential/API issue | Controller logs, cluster status | Repair controller or API connectivity |
| 4 | Sync takes unusually long | API throttling, large diff, hooks | Events, controller metrics, app operations | Reduce load, fix blocking hooks |
| 5 | Repo-server OOMKilled | Large Helm/Kustomize renders, insufficient memory | `describe pod`, prior logs, metrics | Right-size and optimize manifests |
| 6 | Manifest generation timeout | Git latency, DNS, plugin hang | Repo-server logs, DNS/network checks | Restore dependency or fix plugin |
| 7 | Reconciliation uneven across controllers | Shard imbalance/misconfiguration | Pod logs, per-shard app counts | Review version-supported sharding |
| 8 | Redis connection errors | Failover, endpoint/DNS issue, auth | Redis health, endpoints, server logs | Restore supported Redis HA path |
| 9 | Pod evictions during node maintenance | PDB mismatch, no spare capacity | PDB, scheduling events | Restore headroom and replica spread |
| 10 | ApplicationSet apps stop updating | Generator API errors, controller outage | ApplicationSet status, logs | Repair generator dependency/controller |

For every incident, record detection time, customer impact, first failing dependency, mitigating action, recovery verification and prevention owner.

## 14. Production runbook — Argo CD control-plane degradation

**Trigger:** Argo CD UI/API errors, widespread Unknown applications, failed manifest generation or sustained reconciliation backlog.

**Triage (first 10 minutes)**

```bash
kubectl -n argocd get pods -o wide
kubectl -n argocd get deploy,sts,pdb
kubectl -n argocd get events --sort-by=.lastTimestamp | tail -40
kubectl -n argocd top pods
kubectl -n argocd logs deploy/argocd-server --since=15m --tail=200
kubectl -n argocd logs deploy/argocd-repo-server --since=15m --tail=200
```

**Containment:** pause nonessential GitOps promotions and avoid repeated manual sync attempts that increase load. Preserve currently healthy workloads. Do not delete Application CRs, credentials or Redis state to force recovery.

**Diagnosis:** separate API access, manifest generation, reconciliation, identity, Redis, Git provider and Kubernetes API faults. Confirm whether customer-serving workloads are actually impacted.

**Recovery:** restore the failed dependency, roll back the last reviewed configuration change, or restore capacity. Prefer the deployment's authoritative GitOps/Helm process. If Argo CD cannot manage itself, follow the documented bootstrap break-glass procedure with approval and audit logging.

**Validation:** check ready replicas, component error rate, application revision/sync/health, controller backlog and a canary sync. Close only after stable observation over the incident's agreed monitoring window.

## 15. Rollback, disaster recovery and configuration protection

Back up and version **declarative configuration**, not only runtime pods:
- Argo CD Helm values or installation manifests and exact chart version.
- AppProjects, Applications and ApplicationSets.
- RBAC/SSO configuration, repository/cluster registration process and secret references.
- External secret recovery procedures and credential rotation.
- Bootstrap repository and instructions for re-establishing Argo CD without relying on Argo CD itself.

Before an upgrade, export a sanitized configuration snapshot and record current images/versions:

```bash
helm -n argocd history argocd
helm -n argocd get values argocd -o yaml
kubectl -n argocd get deploy,sts -o wide
```

For a failed Helm upgrade, review the release history and roll back to a **known-good, compatible revision** after assessing schema and CRD changes:

```bash
helm -n argocd history argocd
# After approval, choose an actual known-good revision:
helm -n argocd rollback argocd REVISION --wait --timeout 15m
```

Helm rollback does not guarantee reversal of CRD schema migrations or external state changes. Follow the version-specific upgrade and downgrade documentation.

## 16. Acceptance checklist

- [ ] Argo CD components and dependency inventory documented.
- [ ] Version-pinned installation and upgrade/rollback procedure tested.
- [ ] Replica placement survives the agreed node failure scenario.
- [ ] PDBs and capacity allow safe planned maintenance.
- [ ] Controller sharding behavior verified for the installed release.
- [ ] Repo-server performance baseline and alert thresholds established.
- [ ] Git, Kubernetes API, Redis and IdP dependencies monitored.
- [ ] Staging pod-failure and node-drain exercises completed with timings.
- [ ] GitOps reconciliation recovers after dependency restoration.
- [ ] Application-serving impact distinguished from control-plane impact.
- [ ] Break-glass bootstrap and credential recovery runbook reviewed.
- [ ] Evidence, change ticket, owners and follow-up actions recorded.

## 17. Knowledge check

1. Why do healthy Kubernetes workloads usually continue serving during an Argo CD outage?
2. Why can adding application-controller replicas fail to improve reconciliation throughput?
3. What signals distinguish repo-server saturation from Git provider latency?
4. Why is replica count alone insufficient to guarantee high availability?
5. What must be verified before a node-drain experiment?
6. Why should Argo CD bootstrap recovery not depend solely on the same Argo CD instance?
7. What is the difference between application health and successful synchronization to the intended Git revision?
8. Which risks remain after a Helm rollback?

## 18. References

- [Argo CD operator manual](https://argo-cd.readthedocs.io/en/stable/operator-manual/)
- [Argo CD high availability](https://argo-cd.readthedocs.io/en/stable/operator-manual/high_availability/)
- [Argo CD metrics](https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/)
- [Argo Helm chart repository](https://github.com/argoproj/argo-helm)
- [Kubernetes disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

---

**Chapter 047 complete.** Next: **Chapter 048 — Argo CD Security Hardening, Auditability and Operational Governance** (proposed; confirm against the master plan when added).
