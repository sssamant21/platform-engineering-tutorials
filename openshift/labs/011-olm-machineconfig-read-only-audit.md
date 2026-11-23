# Lab 011 — Read-only OLM and MachineConfig Audit

**Duration:** 25–30 minutes. **Environment:** approved OCP 4.22 test or authorized production read-only account. **Execution status:** NOT RUN.

## Preconditions

Record the approved cluster identifier, OCP version, timestamp and account role in a private evidence system; do not commit identity tokens. Verify context using `oc whoami`, `oc config current-context` and `oc get clusterversion`. Confirm authorization with `oc auth can-i list subscriptions.operators.coreos.com --all-namespaces` and `oc auth can-i list machineconfigpools`; denied access is an expected safe outcome.

## Procedure

1. Inventory platform Operators: `oc get clusteroperators`.
2. Inventory add-ons: `oc get subscriptions.operators.coreos.com -A`, `oc get clusterserviceversions.operators.coreos.com -A`, `oc get installplans.operators.coreos.com -A`.
3. Inventory catalog sources: `oc get catalogsources.operators.coreos.com -A`.
4. Inventory node configuration: `oc get machineconfigpools`, `oc get nodes`.
5. Select one authorized add-on namespace; use `oc -n <namespace> describe subscription <name>` and inspect its status/conditions, then inspect the referenced CSV/InstallPlan if present.
6. Inspect `oc describe machineconfigpool worker` only when that pool exists; otherwise record the actual pool name.

All commands are read-only. Replace placeholders after discovery; do not collect Secret objects or token-bearing logs.

## Evidence worksheet

| Check | Expected observation | Actual result |
| --- | --- | --- |
| Cluster identity/version | Approved target and version identified | Not run |
| Cluster Operators | Conditions visible or RBAC denial recorded | Not run |
| Subscriptions/CSVs | Inventory or no resources/permission denial | Not run |
| InstallPlan approval | Automatic/manual state captured when present | Not run |
| MCP conditions | Updated/Updating/Degraded interpreted | Not run |
| Safety | No modifications, secrets or production disruption | Not run |

## Failure scenarios (interpretation only)

- `Forbidden`: request least-privilege read role; do not elevate yourself.
- `No resources found`: check namespace and installation model, not an automatic outage.
- CSV not Succeeded: inspect conditions and events, do not delete/reinstall.
- MCP Degraded: capture condition details and escalate to platform on-call; do not modify pool.

**Pass criteria:** evidence of correct resource relationships, safe failure interpretation, and no mutations. **Not certified:** runtime execution, independent review and production acceptance pending.
