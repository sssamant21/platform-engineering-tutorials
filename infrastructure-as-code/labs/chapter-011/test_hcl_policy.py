import tempfile
import unittest
from pathlib import Path
from hcl_policy import validate

SOURCE = Path(__file__).parent

class HCLPolicyTests(unittest.TestCase):
    def test_lab_passes(self):
        self.assertEqual(validate(SOURCE), [])

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any("missing" in x for x in validate(d)))

    def test_untyped_variable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ("versions.tf", "main.tf", "outputs.tf"):
                (p / name).write_text('terraform { required_version = ">= 1.5" }' if name == "versions.tf" else "", encoding="utf-8")
            (p / "variables.tf").write_text('variable "region" { default = "test" }', encoding="utf-8")
            self.assertTrue(any("untyped" in x for x in validate(p)))

    def test_hardcoded_credential(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ("versions.tf", "main.tf", "outputs.tf"):
                (p / name).write_text('terraform { required_version = ">= 1.5" }' if name == "versions.tf" else "", encoding="utf-8")
            (p / "variables.tf").write_text('variable "region" {\n type = string\n}', encoding="utf-8")
            (p / "main.tf").write_text('password = "fake-test-value"', encoding="utf-8")
            self.assertTrue(any("credential" in x for x in validate(p)))

    def test_missing_version(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ("versions.tf", "main.tf", "outputs.tf"):
                (p / name).write_text("", encoding="utf-8")
            (p / "variables.tf").write_text('variable "region" {\n type = string\n}', encoding="utf-8")
            self.assertTrue(any("required_version" in x for x in validate(p)))

if __name__ == "__main__":
    unittest.main()
