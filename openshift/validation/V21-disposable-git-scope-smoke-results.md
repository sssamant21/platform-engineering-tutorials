# V21 — Disposable Git scope smoke results (2026-11-22)

**Status: partial offline smoke test, not repository-suite PASS.** The GitHub checkout failed with `Could not resolve host: github.com`. The scope checker was manually transcribed from the GitHub connector's fetched `openshift/validation/check_pr_scope.py` into an isolated local Python file. This is **not** a byte-for-byte authenticated checkout, so results must be rerun against the actual checked-out branch.

Environment: Python 3.13, local Git, Linux temporary directories, no kubeconfig, no GitHub network access, no OpenShift cluster operations. Test harness created disposable Git repositories and invoked the transcribed checker with `--base HEAD~1`.

| Scenario | Expected exit | Observed exit | Outcome |
| --- | ---: | ---: | --- |
| Committed change exclusively under `openshift/` | 0 | 0 | Matched |
| Move tracked file from `kubernetes/` into `openshift/` | 1 | 1 | Matched |
| Committed prohibited filename containing newline | 1 | 1 | Matched |
| Root `README.md` change requiring manual review | 2 | 2 | Matched |
| Untracked file in otherwise valid checkout | 2 | 2 | Matched on corrected fixture |

The first attempt at the untracked-file scenario failed during **test setup** because it tried to commit an unchanged tree; no checker result was obtained in that attempt. The fixture was corrected by committing an allowed OpenShift change before creating the untracked file; the checker then returned 2 as expected. These are five *smoke scenarios*, not the repository's full ten-case integration suite or Python unit tests.

## Remaining gates

1. Restore authenticated/verified branch checkout access and compare the local checker with the committed blob.
2. Execute `python -m unittest openshift/validation/test_pr_scope.py openshift/validation/test_pr_scope_git_integration.py -v` from the repository root and preserve actual exit codes.
3. Execute the Markdown, Bash and PowerShell validation suites in a credential-isolated environment; record PASS/FAIL/SKIP separately.
4. Reconcile the branch with `main` after reviewing the actual Git history and conflict status; do not merge the draft PR automatically.
5. Obtain independent technical review and authorized isolated OCP 4.22 lab evidence before marking any chapter verified.

No production cluster was accessed; no chapter status is upgraded by these smoke checks.
