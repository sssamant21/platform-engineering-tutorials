#!/usr/bin/env python3
"""Fail-closed changed-path scope gate for the OpenShift draft PR.

Run from a clean repository checkout after independently fetching the PR base.
This does not fetch, execute oc, inspect credentials, or approve README content.
"""
import argparse
import subprocess
import sys


def run_git(*args):
    result = subprocess.run(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed (exit {result.returncode}); review stderr locally")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main", help="Previously fetched trusted PR base")
    args = parser.parse_args()
    try:
        run_git("rev-parse", "--verify", f"{args.base}^{{commit}}")
        run_git("rev-parse", "--verify", "HEAD^{commit}")
        root = run_git("rev-parse", "--show-toplevel").decode().strip()
        prefix = run_git("rev-parse", "--show-prefix").decode().strip()
        if prefix:
            raise RuntimeError("run from repository root")
        names = run_git("diff", "--name-only", "-z", f"{args.base}...HEAD")
        paths = [p.decode("utf-8", "surrogateescape") for p in names.split(b"\0") if p]
        if not paths:
            raise RuntimeError("empty PR diff: refusing to certify path scope")
        violations = [p for p in paths if not (p.startswith("openshift/") or p == "README.md")]
        readme = "README.md" in paths
        print(f"repository={root}; changed_paths={len(paths)}; outside_allowlist={len(violations)}")
        for p in violations:
            print(f"BLOCKED: unexpected path {p!r}", file=sys.stderr)
        if violations:
            return 1
        if readme:
            print("HOLD: root README.md changed; manual diff review required", file=sys.stderr)
            return 2
        print("PASS: changed-path scope only (not content, tests, or production approval)")
        return 0
    except (RuntimeError, UnicodeError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
