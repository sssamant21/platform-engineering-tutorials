# Lab 014 — Read-only Upgrade Preflight and Go/No-Go

**Environment:** authorized non-production OCP 4.22 cluster preferred. **No upgrade performed.** Time: 25–30 minutes. **Status:** Draft only.

## Preconditions
A least-privilege cluster reader with `get` on the named `clusterversion/version` object and `list` on ClusterOperators, MachineConfigPools and nodes; approved cluster identifier; compatible `oc`; ticket/reference; no secrets in evidence. If a check is forbidden, record the missing permission and ask a designated administrator to collect only that output. Do not grant cluster-admin for the lab.

## Procedure
1. Verify cluster and identity without exposing tokens:
   ```sh
   oc whoami
   oc config current-context
   oc version
   ```
2. Check each authorization separately before making its corresponding read. The following examples work in Bash and PowerShell (run one command at a time); **only execute a read when its check returns `yes`**:
   ```sh
   oc auth can-i get clusterversions.config.openshift.io --resource-name=version
   oc auth can-i list clusteroperators.config.openshift.io
   oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
   oc auth can-i list nodes
   ```
   If authorized, run only the matching read:
   ```sh
   oc get clusterversion version -o json
   oc get clusteroperators.config.openshift.io
   oc get machineconfigpools.machineconfiguration.openshift.io
   oc get nodes
   ```
   The named-object `get` check is **not** a substitute for collection `list`. A `no` response or `Forbidden` means skip that read, record the gap and request an authorized collector; do not elevate privileges. On some clusters, `oc auth can-i` may itself be denied due to SelfSubjectAccessReview restrictions: stop and escalate. ClusterVersion JSON can contain internal URLs and configuration details; inspect locally and redact before sharing or committing evidence. For PowerShell, run the same individual commands directly; avoid shell-specific `&&` chaining.
3. Where the named ClusterVersion read was authorized, inspect `status.desired`, `status.history`, `status.availableUpdates`, `status.conditionalUpdates`, and conditions from ClusterVersion JSON. For each candidate target, verify support against the Red Hat OCP 4.22 update documentation; never assume that a listed conditional update is risk-free.
4. Compare ClusterOperator and MCP conditions, node readiness and application owners' baseline SLOs. Do **not** run `oc adm upgrade`, pause MCPs, drain nodes, change channels or change any resources.
5. Complete decision sheet below; report **NO-GO** for unknown upgrade path, unapproved risks, Degraded operators, degraded MCP, insufficient headroom, unverified backups or absent owner approval.

## Example interpretation (illustrative, not observed)
| Observation | Meaning | Decision |
| --- | --- | --- |
| `Available=True, Progressing=False, Degraded=False` | Typical healthy Operator conditions | Continue preflight, not automatic GO |
| `Progressing=True` | Reconciliation in progress | Investigate before planning change |
| `Degraded=True` | Operator reports degradation | NO-GO; escalate |
| `Forbidden` | Reader lacks access | Record gap; request authorized collector |
| No candidate update | No verified update target from API | NO-GO until path verified |

## Evidence worksheet
Record UTC time, sanitized cluster identifier, OCP version, topology, active context (sanitized), exact commands, actual outputs (redacted), CVO conditions, Operator/MCP exceptions, target support source, database-owner sign-off, backup evidence reference, change ID, GO/NO-GO rationale and reviewer. **Never store credentials, full kubeconfig, token-bearing URLs or raw Secrets.**

## Acceptance
Documentation exercise: classify at least one healthy and one degraded/forbidden scenario. Runtime validation: separately record actual command results from a permitted cluster. Independent review and production approval are separate gates.

See [Chapter 014](../chapters/014-upgrade-planning-gates-and-post-checks.md) and [upgrade triage](../runbooks/upgrade-cvo-mcp-triage.md).
