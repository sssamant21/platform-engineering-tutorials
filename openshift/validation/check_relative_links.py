#!/usr/bin/env python3
"""Read-only Markdown local-link audit for the OpenShift track (Python 3.9+).

Run from repository root:
  python openshift/validation/check_relative_links.py
  py -3 openshift/validation/check_relative_links.py   # Windows PowerShell

No dependencies, network requests, credentials, or cluster access. Exit 1 on
missing local targets, 0 on success. External URLs and fragment identifiers
are not validated; this is not a complete Markdown parser.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK = re.compile(r"!?(?:\[[^\]]*\])\(\s*(<[^>]+>|[^\s)]+)(?:\s+['\"][^)]*['\"])?\s*\)")
REFERENCE_DEF = re.compile(r"^\s{0,3}\[([^]]+)\]:\s*(<[^>]+>|\S+)")
REFERENCE_USE = re.compile(r"!?\[([^]]+)\]\[([^]]*)\]")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def normalize_reference_label(label: str) -> str:
    """Markdown reference labels are case-insensitive and collapse whitespace."""
    return " ".join(label.split()).casefold()


def audit(root: Path) -> tuple[int, list[str]]:
    files = sorted(root.rglob("*.md"))
    failures: list[str] = []
    checked = 0
    for file in files:
        definitions: dict[str, str] = {}
        lines = file.read_text(encoding="utf-8").splitlines()
        # Reference definitions may occur after their uses.
        pre_fence_char = None
        pre_fence_length = 0
        for definition_line in lines:
            marker_match = FENCE.match(definition_line)
            if marker_match:
                marker = marker_match.group(1)
                if pre_fence_char is None:
                    pre_fence_char, pre_fence_length = marker[0], len(marker)
                elif marker[0] == pre_fence_char and len(marker) >= pre_fence_length:
                    pre_fence_char, pre_fence_length = None, 0
                continue
            if pre_fence_char is not None:
                continue
            definition = REFERENCE_DEF.match(definition_line)
            if definition:
                definitions.setdefault(normalize_reference_label(definition.group(1)), definition.group(2).strip("<>"))
        fence_char = None
        fence_length = 0
        for line_no, line in enumerate(lines, 1):
            match = FENCE.match(line)
            if match:
                marker = match.group(1)
                if fence_char is None:
                    fence_char, fence_length = marker[0], len(marker)
                elif marker[0] == fence_char and len(marker) >= fence_length:
                    fence_char, fence_length = None, 0
                continue
            if fence_char is not None:
                continue
            if REFERENCE_DEF.match(line):
                continue
            # Inline code spans are examples, not navigable Markdown links.
            # Match equal-length backtick delimiters; unmatched delimiters remain text.
            visible = re.sub(r"(?<!`)`(?!`)[^`\n]*`(?!`)", "", line)
            targets = [m.group(1).strip("<>") for m in LINK.finditer(visible)]
            for use in REFERENCE_USE.finditer(visible):
                label = normalize_reference_label(use.group(2) or use.group(1))
                if label in definitions:
                    targets.append(definitions[label])
            for raw in targets:
                if raw.startswith(("#", "//")) or SCHEME.match(raw):
                    continue
                # urlsplit also strips query strings and fragment identifiers.
                target = unquote(urlsplit(raw).path)
                if not target:
                    continue
                checked += 1
                resolved = (file.parent / target).resolve()
                if not resolved.exists():
                    failures.append(f"{file.relative_to(root)}:{line_no}: {raw} -> missing {resolved}")
    print(f"Markdown files scanned: {len(files)}; local links checked: {checked}; missing: {len(failures)}")
    return checked, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"Missing directory: {root}", file=sys.stderr)
        return 2
    _, failures = audit(root)
    for issue in failures:
        print(issue)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
