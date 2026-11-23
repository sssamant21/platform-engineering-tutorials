# V28 — Chapter 015 recovery-readiness mock acceptance specification

**Status:** Drafted test specification; no shell mocks or OCP cluster commands executed. **Scope:** Existing Chapter 015 lab and recovery runbook, not a new chapter. **Reference baseline:** OpenShift Container Platform 4.22; recheck supported recovery procedures against the installed cluster version before any actual operation.

## Safety boundary

The proposed harness must replace `oc` with an executable mock on a temporary PATH and must use a disposable temporary directory. Never read the operator's default kubeconfig, call a live API, invoke `oc adm must-gather`, collect raw secrets, or run `cluster-backup.sh` / `cluster-restore.sh`. Record only synthetic fixture output. Do not accept a mocked PASS as real-cluster health or as an etcd restore rehearsal.

## Mock matrix and expected assertions

| ID | Synthetic fixture | Required outcome |
| --- | --- | --- |
| M01 | Trusted API identity matches; every required `can-i` returns exit 0 and exact `yes`; all resource reads succeed | Read-only evidence captured; no write verbs |
| M02 | API identity mismatch | Stop before any resource read; mark identity unverified |
| M03 | Named ClusterVersion `get` denied | Skip ClusterVersion read; report authorization gap |
| M04 | ClusterOperator `list` denied | Skip Operator collection read; do not report healthy |
| M05 | MachineConfigPool `list` denied | Skip MCP read; report incomplete evidence |
| M06 | Node `list` denied | Skip node read; report incomplete evidence |
| M07 | Infrastructure named-object `get` denied | Skip infrastructure read; report incomplete evidence |
| M08 | `can-i` exits nonzero, even if stdout contains `yes` | Fail closed; no corresponding read |
| M09 | `can-i` exits 0 but stdout is `no`, blank, or unexpected | Fail closed; no corresponding read |
| M10 | Authorization succeeds but `oc get` fails/returns `Forbidden` | Mark query failed; do not infer healthy state |
| M11 | Missing `oc` or missing active context | Stop with explicit prerequisite failure |
| M12 | Read output includes synthetic sensitive fields | Ensure any evidence artifact is redacted before sharing |

For each case, capture: platform/shell, fixture identifier, mock invocation log, process exit code, expected/actual decision, pass/fail, and reviewer. Bash and PowerShell must be evaluated independently; a Bash PASS does not establish PowerShell parity.

## Non-negotiable checks

- Confirm exact resource scope: `get clusterversions.config.openshift.io/version` and `get infrastructures.config.openshift.io/cluster` are named-object reads; `list clusteroperators.config.openshift.io`, `list machineconfigpools.machineconfiguration.openshift.io`, and `list nodes` are collection reads.
- Verify no calls to `apply`, `patch`, `delete`, `drain`, `cordon`, `rollout restart`, `adm upgrade`, or recovery scripts.
- Treat missing permissions, unavailable API, partial output, and unsupported cluster topology as **unknown**, never as a green status.
- Keep etcd control-plane backup/recovery separate from application databases and PVC backups. No production recovery command belongs in this mock test.

## Acceptance and next work

1. Fetch the exact committed Lab 015 and runbook source from the active draft PR branch; do not test manually retyped substitutes.
2. Build isolated Bash and PowerShell `oc` mocks with the matrix above and capture actual exit codes.
3. Execute the existing Python unit and real-Git scope suites against a verified checkout; record the exact commit SHA.
4. Audit all Markdown links and OCP 4.22-sensitive recovery claims; seek independent platform/security review.
5. Reconcile the draft PR branch with `main` only after inspecting the diff; do not merge automatically.

**Validation classification:** test plan only. All 18 chapters remain drafted, not lab-verified or production-approved.
