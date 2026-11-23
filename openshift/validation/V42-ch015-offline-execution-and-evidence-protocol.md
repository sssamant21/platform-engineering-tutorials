# V42 — Chapter 015 offline execution and evidence protocol

**Scope:** Chapter 015 recovery-readiness Bash and PowerShell mock suites. **Status:** Execution plan only; no test result is asserted. **Baseline:** OpenShift 4.22 documentation; mocks are not a substitute for cluster or restore validation.

## Preconditions and isolation

1. Use a disposable local checkout of the **existing draft PR branch**; record the exact commit SHA, operating system, Bash version and PowerShell version. Never run the tests on a production bastion or with production kubeconfig credentials.
2. Review each test harness and its fake `oc` executable before running it. The fake executable must be resolved before any real `oc` binary. Reject any harness that invokes real `oc`, `kubectl`, network access, or modifies cluster resources.
3. Use synthetic values only for `KUBECONFIG`, `AWS_SECRET_ACCESS_KEY` and `AZURE_CLIENT_SECRET`. Do not use live cloud credentials or copy production kubeconfigs. Prefer a disposable container/VM with no credentials, mounted sockets or cloud metadata access.
4. Run Bash suites under Bash and PowerShell suites under PowerShell 7 separately. If either interpreter is absent, record **NOT RUN**, not PASS.
5. Before executing, inventory all Chapter 015 test files in `openshift/` and their exact invocation documented by the harness. Do not guess test filenames or silently omit older suites.

## Required negative and positive assertions

| Case | Expected outcome |
| --- | --- |
| Correct approved API endpoint and explicit `yes` for all five resources | Five authorized read attempts; no state-changing calls |
| Missing or mismatched approved API endpoint | Nonzero failure before resource reads |
| Authorization command exits nonzero even if it prints `yes` | No corresponding resource read |
| Authorization prints `no`, `maybe` or empty text | Corresponding read skipped; never treated as authorized |
| MachineConfigPool permission denied | MCP read skipped; other independently authorized resources may still be read |
| Authorized resource read fails | Nonzero/incomplete result, not a healthy-readiness claim |
| Synthetic credentials present in parent environment | Fake `oc` rejects inherited sensitive values; harness demonstrates isolation |
| Unexpected command or argument | Fake `oc` rejects it; no fallthrough to real executable |

For each case, record actual exit code, sanitized stdout/stderr, fake-`oc` call count and the assertion outcome. Distinguish a deliberate `SKIP` from an actual `PASS`: a skipped resource remains an evidence gap. Ensure the harness tests **the current lab procedure**, not a duplicated implementation that can drift.

## Execution record template

| Field | Value |
| --- | --- |
| Branch / commit SHA | NOT RUN |
| Test file and SHA-256 | NOT RUN |
| Host OS / shell version | NOT RUN |
| Invocation and exit code | NOT RUN |
| Assertions passed / failed / skipped | NOT RUN |
| Evidence artifact (sanitized) | NOT RUN |
| Reviewer / review date | Pending |

## Stop, escalation and acceptance

- Stop if a test attempts to call a real cluster client, touches a credential-bearing path, makes a network call, or executes a mutating operation. Quarantine the harness and request a platform/security review.
- Any unexpected exit code or failed assertion is a **validation defect**. Create a reproducible issue with synthetic inputs and a redacted trace; fix and rerun before marking a suite verified.
- Offline mock PASS establishes only local control-flow behavior. It does **not** validate OCP 4.22 API behavior, backup integrity, etcd recovery, application data recovery, RPO/RTO, or production readiness.
- Lab-verified status requires authorized, independently reviewed cluster evidence. Production-approved status additionally requires approved recovery exercises, owner sign-off, and applicable change controls.

Related: [Lab 015](../labs/015-recovery-read-only-readiness-audit.md), [Runbook 015](../runbooks/etcd-backup-recovery-readiness-triage.md), [Progress tracker](../PROGRESS-TRACKER.md).

## V47 — Exact four-suite invocation inventory (2026-11-23)

The following four test entry points were confirmed to exist on the draft branch by GitHub source readback. Run **from the repository root** in a disposable checkout pinned to a recorded SHA, with Python 3 and Bash/PowerShell 7 installed as appropriate:

```sh
python -m unittest discover -s openshift/tests -p 'test_ch015_bash_mock.py' -v
python -m unittest discover -s openshift/validation -p 'test_lab015_bash_mock.py' -v
python -m unittest discover -s openshift/tests -p 'test_ch015_powershell_mock.py' -v
python -m unittest discover -s openshift/validation -p 'test_lab015_powershell_mock.py' -v
```

**Execution guardrails:** Run only after inspecting the checked-out harnesses and verifying that the executable named `oc` is a synthetic mock, that no real kubeconfig or cloud credentials are present, and that the test host cannot reach a live cluster. Do not paste output containing tokens or cluster identity into GitHub. The commands above are **documented, not executed** in this validation entry.

**Evidence classification:** Record each command's process exit status *and* unittest summary. An exit status of zero with skipped tests is **SKIPPED/NOT VERIFIED**, not PASS. An absent `bash` or `pwsh`, test discovery returning zero tests, or an interpreter/runtime failure must be recorded as **NOT RUN** or **FAIL** as applicable. Save SHA-256 checksums for each test file and the lab Markdown; review sanitized logs before publishing. Even four offline PASS results would not establish real-cluster behavior, backup recoverability, or production approval.

**Branch hygiene:** PR #1 is merged; continue on the existing open draft PR #2 branch. Compare against `main` before review and reconcile its one-behind divergence without modifying `kubernetes/` or auto-merging.
