# V10 — Branch divergence and PR scope review (2026-11-22)

**Evidence source:** GitHub compare API for `main...docs/openshift-ch010-security-governance`, inspected on 2026-11-22. This is remote metadata review, not a local diff, test run or approval.

- Compare status: **diverged**; ahead **339**, behind **1**; changed paths **74**.
- Changed paths outside `openshift/`: **0**. Remote changed-path scope PASS at this comparison only.
- Base commit SHA: `d6df882b7dd64c8ef1998d1d7a689f8ed5cd7f7b`.
- Merge-base SHA: `21e989ba82f38870390e55868086bedda6c6df3f`.
- Existing draft PR: https://github.com/sssamant21/platform-engineering-tutorials/pull/2 (do not merge).

## Safe divergence reconciliation protocol

1. **Do not rebase, force-push or merge automatically.** First inspect the single main-only commit, its changed files, and whether it touches `openshift/`, the root README, or any shared tooling. The ahead/behind counts alone do not establish conflict or safety.
2. In a clean credential-isolated checkout, fetch `main` and the PR head, record both SHAs, inspect `git log --oneline HEAD..origin/main` and `git diff --name-status HEAD..origin/main`. Do not interpret the latter as a three-dot PR scope diff.
3. Run `git diff --name-only origin/main...HEAD` and `git diff --check origin/main...HEAD`; reject any unintended Kubernetes changes. Compare the full content and inspect secrets and dangerous commands.
4. If reconciliation is necessary, prepare it on a separate temporary review branch with an explicit conflict resolution plan, then rerun the complete offline validation suites. Do not update the existing PR head until the change is reviewed; avoid rewriting published history.
5. Obtain independent platform-owner review for any nontrivial conflict or changed operational procedure. Confirm PR remains draft. No production cluster operations are part of this protocol.

## Evidence and acceptance boundary

Remote filename scope alone does not prove no duplicate chapters, no secret exposure, clean whitespace, correct OCP 4.22 semantics, or reproducible lab behavior. **Python regressions, Markdown audit, Bash/PowerShell mocks, isolated OCP tests and independent technical approval remain NOT RUN/PENDING**. Repeat this remote comparison before PR acceptance; metadata can change after new commits.
