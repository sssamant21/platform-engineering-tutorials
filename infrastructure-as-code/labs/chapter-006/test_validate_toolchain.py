import unittest
from validate_toolchain import audit, check_tool

BASE = {
    "required": [{"name": "Git", "command": "git"}],
    "optional": [{"name": "VS Code", "command": "code"}],
    "iac_engines": [{"name": "Terraform", "command": "terraform"}, {"name": "OpenTofu", "command": "tofu"}],
}

class AuditTests(unittest.TestCase):
    def test_valid_with_optional_missing(self):
        errors, notes = audit(BASE, lambda item: (item["command"] in {"git", "terraform"}, "fake"))
        self.assertEqual(errors, [])
        self.assertIn("WARN", [n[0] for n in notes])

    def test_missing_required(self):
        errors, _ = audit(BASE, lambda item: (item["command"] == "terraform", "fake"))
        self.assertTrue(any("required tool" in e for e in errors))

    def test_missing_both_engines(self):
        errors, _ = audit(BASE, lambda item: (item["command"] == "git", "fake"))
        self.assertTrue(any("at least one IaC engine" in e for e in errors))

    def test_bad_manifest(self):
        errors, _ = audit({"required": []})
        self.assertTrue(errors)

    def test_command_not_found(self):
        ok, reason = check_tool({"name": "Missing", "command": "definitely-not-installed-ch006"}, which=lambda _: None)
        self.assertFalse(ok)
        self.assertIn("PATH", reason)

    def test_version_command_success(self):
        class Result:
            returncode = 0
            stdout = "v1.2.3\n"
            stderr = ""
        ok, detail = check_tool({"name": "Mock", "command": "mock"}, which=lambda _: "/usr/bin/mock", runner=lambda *a, **kw: Result())
        self.assertTrue(ok)
        self.assertEqual(detail, "v1.2.3")

if __name__ == "__main__":
    unittest.main()
