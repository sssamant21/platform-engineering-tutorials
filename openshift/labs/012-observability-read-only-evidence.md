# Lab 012 — Read-only Monitoring and Event Evidence

**Status:** Draft, not executed. **Duration:** 25–30 minutes. **Environment:** authorized OCP 4.22-compatible cluster; production allowed only with approved read-only access. No changes.

## Preconditions
Have `oc` installed, authenticated, known context and namespace, and explicit `get/list` access to required resources. For monitoring namespace access, request a least-privilege view role; no automatic escalation.

## Procedure
1. Confirm identity and version: `oc whoami`, `oc config current-context`, `oc version`, `oc get clusterversion`. Record a sanitized cluster alias only.
2. Check `oc auth can-i get clusteroperators`, `oc auth can-i list pods -n openshift-monitoring`, `oc auth can-i list events -n <namespace>`. Record yes/no.
3. Run `oc get clusteroperator monitoring`; if permitted `oc get pods -n openshift-monitoring`. Note Ready, Restarts, status, and Operator conditions.
4. Run `oc get pods -n <namespace>` and `oc get events -n <namespace> --sort-by=.lastTimestamp`. Correlate Warning events to workload symptoms.
5. Optionally, with approved `pods/log` permission, run `oc logs -n <namespace> <pod> -c <container> --since=10m --tail=100`; sanitize output before recording.
6. Inspect Observe > Alerting / Metrics in console if permitted; note unavailable access rather than requesting broad rights.

## Expected observations (illustrative, not test output)
- `oc auth can-i` returns `yes` or `no`.
- Operator monitoring typically reports Available=True, Progressing=False, Degraded=False when healthy.
- Events may be empty; this does not prove no past failures.
- `Error from server (Forbidden)`: expected for unauthorized scope; stop that check and request scoped access.
- `NotFound`: verify target namespace and component deployment, do not install software.

## Evidence template
| Field | Observation |
| --- | --- |
| Date/time UTC | Not executed |
| Cluster alias / exact OCP version | Not executed |
| Namespace and RBAC checks | Not executed |
| Monitoring operator conditions | Not executed |
| Pod status and warning events | Not executed |
| Alert correlation / user impact | Not executed |
| Sanitization and reviewer | Pending |

**Pass criteria:** identity verified, all permitted checks documented, permission denials classified, no mutations, sanitized evidence and reviewer sign-off. This file does **not** constitute a pass.

[Chapter](../chapters/012-monitoring-logging-events-and-alerting.md) · [Runbook](../runbooks/monitoring-alert-logging-triage.md)
