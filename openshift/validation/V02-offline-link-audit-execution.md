# V02 — Offline Markdown Link Audit Execution and Evidence

**Scope:** `openshift/` only; no cluster connection, credentials, production changes, or Kubernetes track edits. **Status:** Procedure drafted; branch-wide execution not yet verified.

## Prerequisites

- Checkout of the *existing* open draft PR #2 head, `docs/openshift-ch010-security-governance`, with the complete repository tree (including `kubernetes/README.md` for cross-track link resolution).
- Python 3.9 or later, Git, and read access to the repository. No pip packages required.
- Verify the current PR head SHA and save it with the evidence. Do not treat an older checkout as current.

## Linux / macOS (from repository root)

```sh
git status --short
git rev-parse HEAD
python3 -m unittest discover -s openshift/validation -p 'test_*.py' -v
python3 openshift/validation/check_relative_links.py --root openshift
```

## Windows PowerShell (from repository root)

```powershell
git status --short
git rev-parse HEAD
py -3 -m unittest discover -s openshift/validation -p 'test_*.py' -v
py -3 openshift/validation/check_relative_links.py --root openshift
```

The unittest command should run the currently authored **17** regression cases across two test modules; this is an expected count, **not** an executed result. The link audit prints the number of Markdown files scanned, local links checked and missing targets. Exit code 0 means the checker found no missing local *file targets within its supported syntax*, not that every Markdown link is valid. Exit code 1 means one or more missing targets; exit code 2 means invalid root. For PowerShell, inspect `$LASTEXITCODE` immediately after each Python invocation.

## Evidence and failure triage

Record UTC timestamp, exact PR head SHA, Python version, OS, both commands and exit codes, unittest summary, Markdown-file count, local-link count, missing-target count, and sanitized failure paths. Keep raw command output out of the repository until reviewed for internal paths or secrets. For each missing link, check whether it is a genuine path defect, a case-sensitive path mismatch, or a cross-track link that requires the repository root to be present. Correct only confirmed defects, then rerun both checks at the **new** commit SHA.

The count is a moving baseline: compare against the test files at the exact checked-out SHA rather than assuming 17 forever. Capture `python3 -m unittest discover` (or `py -3` on Windows) output and ensure discovery did not silently skip either module. The `--root openshift` argument limits Markdown discovery to this track; a relative link to `../kubernetes/README.md` still resolves against the full checkout, so the sibling `kubernetes/` directory must exist, but it must not be edited.

If checkout fails (for example DNS or GitHub connectivity), record the exact error and classify the **entire audit as blocked**. Do not infer a pass from fetching individual source files or from tests that were merely authored.

## Known coverage limitations

This lightweight checker does **not** certify URL availability, fragments/headings, HTML links, shortcut reference links, every nested Markdown construct, or Red Hat 4.22 command semantics. It may produce false negatives and false positives for unsupported Markdown. External documentation and command safety need separate review. A complete pass is **documentation QA only**, not lab-tested, independently reviewed, or production-approved.

## Acceptance

1. All authored regression tests actually executed and passed at a recorded SHA.
2. Complete repository checkout used; zero *confirmed* broken local file targets, with exceptions documented.
3. Any fixes committed on the existing draft PR branch and rerun at its new head.
4. Independent review of unresolved links and known parser limitations.

Related: [V01 validation gates](V01-documentation-security-and-runtime-evidence-gates.md), [progress tracker](../PROGRESS-TRACKER.md).
