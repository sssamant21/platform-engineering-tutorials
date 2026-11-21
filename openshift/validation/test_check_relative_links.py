#!/usr/bin/env python3
"""Offline regression tests for the read-only Markdown link checker."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check_relative_links.py")
spec = importlib.util.spec_from_file_location("check_relative_links", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LinkAuditTests(unittest.TestCase):
    def test_reference_definitions_before_and_after_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[before][ok]\n[ok]: target.md\n[after][ok]\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 2)
            self.assertEqual(failures, [])

    def test_missing_reference_target_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[broken][id]\n[id]: missing.md\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("missing.md", failures[0])

    def test_collapsed_reference_uses_its_link_text_as_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[target][]\n[target]: target.md\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])

    def test_collapsed_reference_missing_target_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[missing][]\n[missing]: absent.md\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)

    def test_reference_labels_collapse_whitespace_and_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[one][MULTI   WORD]\n[two][multi word]\n[multi word]: target.md\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 2)
            self.assertEqual(failures, [])

    def test_fenced_reference_definition_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[outside][id]\n```md\n[id]: missing.md\n```\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 0)
            self.assertEqual(failures, [])

    def test_inline_code_links_are_not_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "`[example](missing.md)` and `[real](target.md)`\n"
                "`[example][ref]`\n[ref]: missing.md\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])

    def test_first_reference_definition_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[link][id]\n[id]: target.md\n[id]: missing.md\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])


    def test_multi_backtick_code_spans_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "Before ``[not a link](missing.md)`` and [real](target.md)\n"
                "```[not a reference][bad]```\n"
                "[bad]: absent.md\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])

    def test_unmatched_backtick_does_not_hide_real_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "`` [real](missing.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)



    def test_code_span_does_not_join_link_fragments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[fragment`hidden`](missing.md) and [valid](present.md)\n", encoding="utf-8"
            )
            (root / "present.md").write_text("# present\n", encoding="utf-8")
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])

    def test_indented_code_links_and_definitions_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "    [fake](missing.md)\n"
                "    [id]: missing.md\n"
                "[outside][id]\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 0)
            self.assertEqual(failures, [])

    def test_tab_indented_code_link_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "\t[example](missing.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 0)
            self.assertEqual(failures, [])

    def test_fence_with_info_string_inside_block_does_not_close_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "```md\n"
                "```python\n"
                "[example](missing.md)\n"
                "```\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 0)
            self.assertEqual(failures, [])

    def test_invalid_backtick_fence_info_string_does_not_hide_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "```python`bad\n"
                "[broken](missing.md)\n"
                "```\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)


    def test_encoded_relative_path_with_query_and_fragment(self):
        # The audit validates the filesystem target, not the URL fragment.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release notes.md").write_text("# Notes\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[notes](release%20notes.md?view=compact#summary)\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])

    def test_tilde_fence_and_mismatched_fence_do_not_hide_broken_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "~~~bash\n"
                "[example](ignored.md)\n"
                "```\n"
                "[still-code](also-ignored.md)\n"
                "~~~\n"
                "[broken](missing.md)\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("missing.md", failures[0])

    def test_missing_percent_encoded_target_with_query_is_reported(self):
        # Query and fragment must not conceal a missing local Markdown target.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[missing](not%20present.md?mode=read#section)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("not%20present.md", failures[0])

    def test_reference_definition_percent_encoded_missing_target(self):
        # Reference-style links use the same path normalization and failure rules.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[missing][doc]\n[doc]: absent%20guide.md?view=1#intro\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("absent%20guide.md", failures[0])

    def test_absolute_existing_local_target_is_rejected(self):
        # A link to an existing host file must never count as a portable repo link.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.md"
            target.write_text("# target\n", encoding="utf-8")
            (root / "doc.md").write_text(
                f"[host-specific]({target.as_posix()})\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("absolute local path", failures[0])


    def test_windows_drive_path_is_not_treated_as_external_scheme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[host](C:/private/secret.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("absolute local path", failures[0])

    def test_existing_parent_file_outside_audit_root_is_rejected(self):
        # A real file above the checkout must not silently pass the audit.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "docs"
            root.mkdir()
            (Path(directory) / "outside.md").write_text("# outside\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[escape](../outside.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("escapes audit root", failures[0])


    def test_symlink_target_outside_repository_is_rejected(self):
        # resolve() must enforce the real target boundary, not just lexical '..'.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "docs"
            root.mkdir()
            outside = Path(directory) / "outside.md"
            outside.write_text("# outside\n", encoding="utf-8")
            try:
                (root / "alias.md").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("Creating symlinks is unavailable on this host")
            (root / "doc.md").write_text("[escape](alias.md)\n", encoding="utf-8")
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("escapes audit root", failures[0])

    def test_openshift_root_allows_existing_kubernetes_sibling(self):
        # A cross-track reference is allowed without permitting host escapes.
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            root = repo / "openshift"
            root.mkdir()
            sibling = repo / "kubernetes"
            sibling.mkdir()
            (sibling / "README.md").write_text("# Kubernetes\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[fundamentals](../kubernetes/README.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(failures, [])

    def test_percent_encoded_parent_traversal_is_rejected(self):
        # URL decoding must happen before filesystem containment checks.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "docs"
            root.mkdir()
            (Path(directory) / "outside.md").write_text("# outside\n", encoding="utf-8")
            (root / "doc.md").write_text(
                "[escape](%2e%2e/outside.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("escapes audit root", failures[0])

    def test_percent_encoded_absolute_path_is_rejected(self):
        # Encoded leading slash must not evade the absolute-path check.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[absolute](%2Ftmp%2Fexample.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("absolute local path", failures[0])

    def test_file_uri_is_rejected_even_when_target_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "local.md"
            target.write_text("# local\n", encoding="utf-8")
            (root / "doc.md").write_text(
                f"[host-local]({target.as_uri()})\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("unsafe URI scheme is not allowed", failures[0])

    def test_mixed_case_file_uri_scheme_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[local](FiLe:///tmp/secret.md)\n", encoding="utf-8"
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("unsafe URI scheme is not allowed", failures[0])


    def test_reference_style_unsafe_scheme_is_rejected(self):
        # A dangerous destination in a reference definition is still a link
        # when it is used, even if the definition occurs after the use.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.md").write_text(
                "[unsafe][destination]\n"
                "[destination]: JaVaScRiPt:alert(1)\n",
                encoding="utf-8",
            )
            checked, failures = checker.audit(root)
            self.assertEqual(checked, 1)
            self.assertEqual(len(failures), 1)
            self.assertIn("unsafe URI scheme", failures[0])

    def test_executable_and_embedded_uri_schemes_are_rejected(self):
        # Unsafe Markdown schemes must not be silently treated as external docs.
        for uri in ("javascript:alert(1)", "data:text/plain,secret", "vbscript:msgbox(1)"):
            with self.subTest(uri=uri), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "doc.md").write_text(
                    f"[unsafe]({uri})\n", encoding="utf-8"
                )
                checked, failures = checker.audit(root)
                self.assertEqual(checked, 1)
                self.assertEqual(len(failures), 1)
                self.assertIn("unsafe URI scheme", failures[0])

if __name__ == "__main__":
    unittest.main()
