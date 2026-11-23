# Runbook — Monitoring, Alerts, Logs and Events Triage

**Status:** Draft only. **Scope:** read-only first response on OCP 4.22-compatible deployments. **Owners:** Platform SRE; application/DBRE/observability teams according to impact.

## Trigger and severity
Use for missing metrics, firing platform alerts, monitoring Operator degradation, log gaps, or absent dashboard data. Prioritize customer impact, failed availability SLOs, and data durability alerts over cosmetic dashboard errors.

## Safety and access
Confirm approved context and incident ticket. Require scoped `get/list` for Operator, pod and event diagnostics; log access only with explicit authorization. Do not expose Secrets, raw kubeconfigs, personal data, log payloads or bearer tokens.

## Read-only sequence
```bash
oc whoami
oc config current-context
oc get clusterversion
oc get clusteroperator monitoring
oc auth can-i list pods -n openshift-monitoring
oc get pods -n openshift-monitoring
oc get events -n openshift-monitoring --sort-by=.lastTimestamp
```
If RBAC denies an operation, document and stop that scope. Compare alert timestamps to cluster updates, node pressure, storage, DNS, and workload symptoms. For application-specific alerts inspect only approved namespaces. Confirm whether user-workload monitoring and OpenShift Logging are actually installed before diagnosing missing components.

## Decision guide
| Symptom | Check | Escalation |
| --- | --- | --- |
| Monitoring Operator Degraded | Operator conditions, monitoring pod states, recent updates | Platform SRE and vendor support |
| Target down / metrics gap | Target availability, scrape permissions, network and certificates (metadata only) | Platform + workload owner |
| Alert firing, app healthy | Alert expression, evaluation window, silences and SLO context | Alert owner |
| Log gap | Collector deployment, backend availability, retention, pipeline permissions | Observability owner |
| Forbidden | `oc auth can-i`, role scope | IAM/platform owner |
| Stateful database alert | DB health, PVC and node correlation without disruptive probes | DBRE and app owner |

## Change/rollback decision
No `oc patch`, `oc delete`, rollout restart, Alertmanager silence, retention adjustment or Operator reconfiguration as first response. For approved changes: capture baseline configuration safely, verify vendor-supported procedure and dependency impact, obtain change and service-owner approval, define rollback to known-good configuration (which may not restore lost telemetry), schedule a window, and validate metrics freshness, alert delivery and application SLOs. Escalate urgent unapproved changes through incident command.

## Closure
Record UTC timeline, sanitized evidence, affected scope, alert identifiers, operator conditions, customer impact, remediation approval, and post-change monitoring. A cleared alert is not sufficient evidence of recovery.

[Chapter](../chapters/012-monitoring-logging-events-and-alerting.md) · [Lab](../labs/012-observability-read-only-evidence.md)
