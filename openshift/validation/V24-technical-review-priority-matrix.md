# V24 — OpenShift 4.22 independent technical review matrix

**Date:** 2026-11-22. **Status:** Review plan only; no OCP cluster or offline test execution. This is not a production certification.

## Review scope and evidence discipline

All 18 chapters are already drafted. Do **not** add duplicate chapters. Review the existing chapters and their labs/runbooks against the [Red Hat OpenShift 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22) and actual platform configuration. For every reviewed command, record the exact 4.22 documentation section, file/line, reviewer, result, and whether a lab was actually executed. Documentation inspection is not equivalent to runtime verification.

Prioritize these risk-based review gates:

| Priority | Existing chapter | Required review evidence | Stop / escalation trigger |
| --- | --- | --- | --- |
| P0 | 015 — etcd backup and recovery | Confirm documented backup/restore procedures for the exact OCP release and topology; distinguish backup collection from cluster restore; verify offline mocks and disaster recovery prerequisites | Any restore instruction lacking tested recovery plan, change approval, RPO/RTO and quorum assessment |
| P0 | 014 — upgrades | Check CVO upgrade channels, conditional updates, Cluster Operator health, MachineConfigPool readiness and version-specific rollback limitations | Any claim that an OCP upgrade can be casually rolled back |
| P0 | 010 — RBAC/SCC | Verify least-privilege access, SCC admission behavior, service-account scope, and no broad cluster-admin grants in routine labs | Any privilege escalation, token disclosure or undocumented SCC mutation |
| P1 | 005/011 — Machine API/MachineConfig | Separate read-only inspection from drain, rollout, node replacement and MachineConfig changes; define blast radius and approval | Any production MCP or node change presented as a harmless diagnostic |
| P1 | 008/017 — storage and stateful HA | Check CSI driver, access modes, volume topology, backup consistency, disruption budgets and failure-domain assumptions | Any assertion that PVCs or multiple replicas alone guarantee application HA |
| P1 | 004/012/016 — cluster health and incidents | Confirm interpretation of Available/Progressing/Degraded, CVO state, events, alert signals and escalation paths | Any diagnostic that masks an active degraded operator or modifies cluster state |
| P2 | 002/009 — access and networking | Validate context checks, impersonation/authorization probes, OVN-Kubernetes and Route/Ingress behavior | Any command exposing kubeconfig credentials or altering production routing |

## Evidence record (one row per reviewed command)

| Chapter / file / line | 4.22 authoritative reference | Static syntax review | Isolated lab result and exit code | Security / change reviewer | Status |
| --- | --- | --- | --- | --- | --- |
| Pending | Pending | Not reviewed | Not executed | Not assigned | DRAFT |

Allowed statuses: **DRAFT**, **STATIC-REVIEWED**, **ISOLATED-LAB-TESTED**, **INDEPENDENTLY-APPROVED**. Never infer a later status from an earlier one.

## Safe read-only baseline (requires approved access)

Use only an approved, least-privilege identity and the intended context. Avoid copying raw kubeconfig, tokens or sensitive command output into reports.

```bash
oc whoami
oc config current-context
oc auth can-i get clusterversions.config.openshift.io/version
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
# Execute each read separately ONLY if its matching can-i result is yes:
oc get clusterversion version
oc get clusteroperators
oc get mcp
```

The commands above are a manual permission checklist, **not** a script that enforces authorization. Run each `oc get` only after its corresponding `can-i` result is `yes`; `no`, an error, or indeterminate output means skip that read. `get` on the named `clusterversion/version` is distinct from `list` on ClusterOperator and MachineConfigPool collections. The MCP resource is cluster-scoped and needs `list` independently. Do not blindly paste the whole block. `oc auth can-i` returning `no` is a permission finding, not permission to elevate privileges. A forbidden `oc get` is an expected possible failure under least privilege. These commands are **examples to review**, not claims of successful execution. On PowerShell, the same `oc` invocations apply; inspect `$LASTEXITCODE` for each invocation and do not print environment secrets.

## Release gate

Before PR review or merge: (1) reconcile the PR branch with current `main` without changing `kubernetes/`; (2) run scope and offline tests on an actual clean checkout with recorded exit codes; (3) verify Markdown links and version-sensitive commands; (4) execute approved isolated OCP labs; (5) obtain independent platform/security sign-off. Keep PR draft until these gates are satisfied. **Never run disruptive etcd, MachineConfig, node or upgrade operations against production as part of tutorial validation.**
