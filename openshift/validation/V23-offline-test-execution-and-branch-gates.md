# V23 — Verified remote scope and executable offline acceptance gates

Date: 2026-11-22. Status: **remote scope inspected; runtime tests NOT RUN**.

## GitHub state inspected

- PR #1 is merged; PR #2 is open and draft. Continue PR #2, do not create duplicate chapters or merge automatically.
- PR #2 head: `docs/openshift-ch010-security-governance`; base: `main`.
- GitHub compare `main...docs/openshift-ch010-security-governance` returned **80 changed files**, all within `openshift/`; **372 ahead, 1 behind**. This is a remote path-scope observation, not proof that file contents, commands or security controls are correct.
- At inspection, main commit was `d6df882b7dd64c8ef1998d1d7a689f8ed5cd7f7b`; merge base `21e989ba82f38870390e55868086bedda6c6df3f`. The branch still needs explicit reconciliation review.

## Environment blocker

An isolated `git ls-remote https://github.com/sssamant21/platform-engineering-tutorials.git HEAD` failed with exit **128**: `Could not resolve host: github.com`. Do not report repository test execution or a successful local diff check from this environment.

## Credential-isolated offline acceptance procedure

Run on an approved workstation or CI runner with Git/Python, with **no kubeconfig, cloud tokens, production credentials or cluster access**. Capture versions and all exit codes; redact host/user paths if evidence is shared.

```bash
git clone https://github.com/sssamant21/platform-engineering-tutorials.git oc-review
cd oc-review
git fetch origin main docs/openshift-ch010-security-governance
git switch --detach origin/docs/openshift-ch010-security-governance
git status --porcelain=v1 --untracked-files=all
git diff --no-renames --name-only -z origin/main...HEAD > /tmp/oc-pr-paths.bin
git diff --check origin/main...HEAD
python -m unittest discover -s openshift/validation -p 'test_pr_scope.py' -v
python -m unittest discover -s openshift/validation -p 'test_pr_scope_git_integration.py' -v
python openshift/validation/check_pr_scope.py --base origin/main
```

The scope checker intentionally rejects a dirty checkout, empty comparison, cross-track changes and a root README change requiring manual review. A zero exit code is **only a changed-path PASS**, never a content/security/production PASS. Check each command's exit status separately; do not use the final command alone as evidence of the entire procedure. Do not upload `/tmp/oc-pr-paths.bin` if filenames could disclose sensitive details.

PowerShell equivalents for the test invocations:

```powershell
py -m unittest discover -s openshift/validation -p test_pr_scope.py -v
$unitExit = $LASTEXITCODE
py -m unittest discover -s openshift/validation -p test_pr_scope_git_integration.py -v
$integrationExit = $LASTEXITCODE
py openshift/validation/check_pr_scope.py --base origin/main
$scopeExit = $LASTEXITCODE
Write-Output "unit=$unitExit integration=$integrationExit scope=$scopeExit"
```

## Review and acceptance requirements

1. Verify GitHub head SHA and base SHA again immediately before testing. Re-run the scope check after any reconciliation.
2. Review all modified Markdown links and version-sensitive OCP 4.22 commands, prioritizing SCC/RBAC, ClusterVersion, MCP, etcd restore, upgrades and stateful HA.
3. Run Chapter 015 Bash/PowerShell mocks in a disposable, credential-free environment; record exact commands, versions, outputs and exit codes.
4. Keep isolated OCP lab validation separate from offline tests. No live cluster validation, backup/restore rehearsal or independent platform/security review has been completed.
5. Do not certify or merge without independent review; production changes require separate change approval, rollback/restore planning and owner sign-off.

## Evidence record template

| Gate | Actual command/environment | Exit code | Result | Reviewer |
| --- | --- | --- | --- | --- |
| GitHub compare | Connector remote compare | N/A | 80 paths, all `openshift/`; divergence remains | Pending |
| Local checkout | `git ls-remote` | 128 | BLOCKED: DNS | Pending |
| Python unit suite | Not run | N/A | PENDING | Pending |
| Real-Git integration suite | Not run | N/A | PENDING | Pending |
| Markdown/security audit | Not run | N/A | PENDING | Pending |
| Chapter 015 mocks | Not run | N/A | PENDING | Pending |
| Isolated OCP 4.22 labs | Not run | N/A | PENDING | Pending |

No tests, production operations, or approvals are claimed by this evidence note.
