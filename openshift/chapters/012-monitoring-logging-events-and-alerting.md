# Chapter 012 — Monitoring, Logs, Events and Alerting (60 minutes)

**Audience:** OCP platform administrators, SREs, DBREs. **Baseline:** Red Hat OCP 4.22; check installed version and supported observability components before applying guidance. **Status:** Draft; not cluster-tested.

## Objectives and timing
- 0–10 min: OpenShift platform monitoring versus optional user-workload monitoring
- 10–20 min: Prometheus, Alertmanager, monitoring Operators, dashboards
- 20–35 min: read-only cluster and namespace health diagnostics
- 35–50 min: [Lab 012](../labs/012-observability-read-only-evidence.md)
- 50–60 min: [alert triage runbook](../runbooks/monitoring-alert-logging-triage.md) and evidence review

## OpenShift-specific architecture
OpenShift includes a platform monitoring stack managed by the Cluster Monitoring Operator (CMO), with Prometheus, Alertmanager and related components. The web console exposes Observe views subject to permissions. User-workload monitoring is a distinct, optionally configured capability; do not assume it is enabled. Logging and log aggregation are not interchangeable with monitoring: the availability and architecture of the Red Hat OpenShift Logging Operator, log collection, and any external log backend depend on installed components and their versions. Do not assume Elasticsearch or Loki is deployed.

Cluster events are short-lived diagnostic records, not a durable audit trail. Pod logs can rotate and disappear after replacement. Export only sanitized evidence in accordance with retention and privacy policy. Avoid downloading full pod logs indiscriminately.

## Prerequisites and RBAC
- Approved read-only access, installed `oc`, correct kubeconfig context, and an identified namespace.
- `get/list` permissions on clusteroperators, clusterversions and nodes for cluster-wide checks; namespace `get/list` for pods, events, deployments and services; `get` on `pods/log` only if specifically authorized.
- Monitoring namespace inspection requires explicit access; `cluster-monitoring-view` or organization-defined read-only roles may be appropriate depending on scope. Do not grant `cluster-admin` to run this lab.
- Confirm RBAC with `oc auth can-i` before each restricted resource.

## Safe baseline commands
```bash
oc whoami
oc config current-context
oc version
oc get clusterversion
oc get clusteroperators
oc auth can-i list pods -n openshift-monitoring
oc auth can-i get pods --subresource=log -n <approved-namespace>
oc get pods -n <approved-namespace>
oc get events -n <approved-namespace> --sort-by=.lastTimestamp
oc get --raw /readyz
```
Replace placeholders before execution; the last endpoint may be forbidden by policy. Never paste `oc config view --raw` or login tokens into evidence.

To inspect platform monitoring where authorized:
```bash
oc get clusteroperator monitoring
oc get pods -n openshift-monitoring
oc get deployments,statefulsets -n openshift-monitoring
```
Monitoring components vary by platform version and topology. Missing components are not automatically failures.

For targeted logs, obtain approval and use a named pod/container, a short tail and time range:
```bash
oc logs -n <approved-namespace> <pod-name> -c <container-name> --since=10m --tail=100
```
Review output for credentials, patient data, identifiers and tokens before sharing.

PowerShell: the same `oc` commands run in PowerShell; use `$env:KUBECONFIG` only for a pre-existing approved local kubeconfig path. Avoid shell redirection into shared folders.

## Alert interpretation
Correlate firing alerts with ClusterOperator conditions, node pressure, namespace events and workload symptoms. Alertmanager silence or inhibition is not incident resolution. Querying metrics in the console requires monitoring permissions and may be restricted. A quiet alert list does not establish healthy service-level objectives.

## Expected results and failure modes
- Healthy cluster: monitoring ClusterOperator typically Available=True, Progressing=False, Degraded=False; investigate exceptions in context, including planned upgrades.
- `Forbidden`: insufficient RBAC, request narrowly scoped view access; do not elevate yourself.
- `NotFound`: verify namespace, component availability and OCP version.
- `CrashLoopBackOff`: inspect pod status/events, resource pressure and operator conditions before changing resources.
- Missing metrics/logs: distinguish collector/target failures, scrape permissions, optional logging stack absence, retention expiration and query selection.

## Production change gate
Do not modify monitoring ConfigMaps, retention, scrape configuration, Operator subscriptions, Alertmanager routes or silences during this read-only lab. Any state-changing response needs a change ticket, platform/security approval, tested backup or config snapshot, blast-radius analysis, rollback procedure and post-change SLO verification. Alert silence must have a documented expiry and incident owner.

## Acceptance and escalation
Capture sanitized timestamps, cluster version, context alias, namespace, command results, alert identifiers and correlated impact. Escalate platform monitoring failures to platform SRE; application alerts to application owner; persistent data service signals to DBRE; log pipeline and retention to observability/security owners. Never declare production readiness without independent review and real cluster evidence.

## References
- [Red Hat OCP 4.22 Observability](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/observability/index)
- [Red Hat OCP 4.22 Monitoring](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/monitoring/index)
- [Kubernetes fundamentals in this repository](../../kubernetes/README.md)
