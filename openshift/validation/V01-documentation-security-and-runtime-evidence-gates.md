# V01 — Documentation, Security and Runtime Evidence Gates

**Scope:** OpenShift administration Chapters 001–018, labs and runbooks. **Baseline:** OCP 4.22; recheck against the actual cluster minor release. **Status:** Review plan drafted; full repository-wide automated audit and live OCP validation not performed.

## Review procedure (non-disruptive)

1. Inventory exactly one chapter and one matching lab for each number 001–018; record any missing/duplicate names. Runbook names may be descriptive rather than numbered. Check all chapter, lab, runbook, README and tracker relative links against the actual branch tree.
2. Inspect every fenced command for shell portability, required namespace, minimum RBAC verbs, resource scope, and OCP version-specific behavior. PowerShell examples must not assume Bash environment variables, grep, sed or Unix redirection.
3. Confirm each lab names the cluster/version preflight, access prerequisites, expected healthy output, expected authorization errors, evidence fields, stop conditions and escalation. Avoid assuming cluster-admin access for a read-only exercise.
4. Search for potentially sensitive examples: kubeconfig contents, bearer tokens, credentials, Secret YAML/data, cluster identifiers, customer records and support archives. Never publish real values.
5. Classify operations: **R** read-only API observation; **W** creates/changes resources; **D** destructive, recovery or disruption. Verify W/D commands are isolated or approval-only, have named owners, maintenance impact, explicit rollback feasibility and independent signoff.
6. Validate official Red Hat documentation references for the deployed version; verify especially upgrade path support, etcd restore, SCC admission, OLM and MachineConfig changes. A plausible command is not evidence that it was executed.
7. Record test results only after authorized execution in an isolated cluster. Include sanitized version, environment, command, timestamp, expected/actual output, negative-case result, reviewer and issue reference.

## Risk-focused sampling order

| Priority | Scope | Specific concern | Required reviewer |
| --- | --- | --- | --- |
| P0 | 014 upgrade, 015 recovery, 017 stateful HA | Unsupported rollback/restore assumptions; data consistency and quorum | Platform + DBRE |
| P0 | 010 RBAC/SCC, 018 governance | Overprivileged commands; credential disclosure; unapproved break-glass | Platform security |
| P1 | 005 Machine API, 011 OLM/MCP | Drain/rollout/InstallPlan disruption and topology applicability | Platform SRE |
| P1 | 008 CSI/PVC, 009 networking | Storage attachment and route failure diagnosis | Storage/network owner |
| P2 | 001–004, 006–007, 012–013, 016 | Evidence quality, diagnostics and command portability | Platform SRE |

## Evidence register (not executed)

| Gate | Current state | Completion evidence |
| --- | --- | --- |
| All 18 chapter drafts | Reported drafted in progress tracker | Per-file existence and link inventory |
| Complete Markdown link audit | Pending | Machine-readable broken-link report and fixes |
| Command semantic/security review | Pending | Reviewer signoff and issue register |
| Isolated runtime labs | Not run | Sanitized real command output and negative tests |
| Independent production approval | Not granted | Named approvals and environment-specific acceptance |

## Read-only preflight examples

Linux/Bash:
```bash
oc version --client
oc whoami
oc config current-context
oc auth can-i list clusteroperators
oc auth can-i list pods -n <approved-namespace>
```

PowerShell:
```powershell
oc version --client
oc whoami
oc config current-context
oc auth can-i list clusteroperators
oc auth can-i list pods -n <approved-namespace>
```

The ClusterOperator check uses `list` because the intended inventory is a collection query (`oc get clusteroperators`); use `get` only when reading a named object and check that permission separately. Replace the placeholder namespace before running. **Do not print kubeconfig or authentication tokens.** Authorization errors are legitimate evidence of least-privilege boundaries, not a reason to elevate access without approval.

## Next validation increment

Generate a branch-wide file inventory and relative-link audit; fix verified broken links only. Then inspect P0 recovery and upgrade examples against the exact Red Hat release documentation. Do not mark any gate complete without actual evidence.
