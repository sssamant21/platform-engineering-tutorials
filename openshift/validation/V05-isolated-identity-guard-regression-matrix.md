# V05 — Isolated identity-guard regression matrix

**Status:** Drafted; no tests executed. **Scope:** Chapter 014–015 upgrade/etcd recovery worksheet V04 read-only preflight. OCP 4.22 is the reference baseline. This plan does not certify a cluster, upgrade or restore.

## Purpose and prerequisites

Verify that the Bash and PowerShell examples in [V04](V04-upgrade-etcd-recovery-evidence-worksheet.md) reject wrong or untrusted cluster identity **before** reading ClusterVersion, ClusterOperators, nodes or MachineConfigPools. Use an isolated disposable shell with Bash and PowerShell 7, Python 3, and a mock `oc` executable on a private test PATH. Do **not** use a real kubeconfig, production credentials, or production cluster. A reviewer must inspect the actual V04 script and extract it verbatim; do not substitute a rewritten implementation.

## Test design

Mock only these command families: `oc whoami`, `oc config current-context`, `oc config view --minify ...`, `oc auth can-i ...`, and `oc get ...`. Log invocations to a local temporary file without credentials. Use a fabricated server such as `https://api.test.invalid:6443` and fabricated context `isolated-test`. Match the exact `oc config view` flags and output format in V04. Exit nonzero for simulated failures. Run each scenario in a fresh process, with a fresh temporary HOME, KUBECONFIG and PATH; remove artifacts afterward.

| ID | Scenario | Expected outcome |
| --- | --- | --- |
| I01 | EXPECTED_CONTEXT unset | Abort before any `oc get` |
| I02 | EXPECTED_SERVER unset | Abort before any `oc get` |
| I03 | `oc whoami` fails | Abort before any `oc get` |
| I04 | Current-context lookup fails | Abort before any `oc get` |
| I05 | Active context differs | Abort before any `oc get` |
| I06 | API endpoint lookup fails or returns empty | Abort before any `oc get` |
| I07 | Active API endpoint differs | Abort before any `oc get` |
| I08 | Identity matches, `can-i` returns `no` | Skip corresponding `oc get`, do not escalate |
| I09 | Identity matches, `can-i` fails or returns ambiguous output | Skip corresponding `oc get`; flag inconclusive authorization |
| I10 | Identity matches, authorization `yes`, `oc get` fails | Record read failure; never imply a successful health check |
| I11 | Identity matches, authorization `yes`, reads succeed | Execute only permitted read-only commands |
| I12 | Identity matches, one permission denied, others granted | Denied resource skipped; independent authorized reads may proceed |

**Assertions:** For I01–I07, zero `oc get` calls; for I08–I12, verify exact resource-by-resource authorization gating. Record exit status, sanitized stdout/stderr, invocation log and whether unexpected writes occurred. Any invocation of `oc patch`, `delete`, `apply`, `adm upgrade`, `debug`, `drain`, or etcd restore is an automatic failure. Confirm no API server addresses, tokens, kubeconfig contents or sensitive metadata appear in committed evidence.

## Acceptance and limitations

- Execute all scenarios independently in Bash and PowerShell; report PASS/FAIL/SKIP per shell, exact source commit, shell versions and mock implementation revision.
- Inspect whether `oc config view` can be influenced by environment or overridden kubeconfig; a matching context and endpoint are **necessary but insufficient** proof of trusted cluster identity. Require approved inventory, certificate validation and an independently verified change target before any real operation.
- Do not claim mocked success is OCP 4.22 compatibility, production authorization, or real API behavior. Follow with authorized isolated OCP read-only checks and independent platform/security review.
- If any case fails, stop promotion, document a minimal reproducible failure, correct the V04 script, rerun both shell matrices, and obtain reviewer sign-off. No production rollback is needed for these offline tests because no cluster state may be changed.

**Approval boundary:** Upgrade execution, etcd snapshot/restore, MachineConfig rollout, and node maintenance require separate change approval, backup/recovery evidence, rollback feasibility analysis and named platform/DBRE/application owners. This V05 matrix grants none of those approvals.
