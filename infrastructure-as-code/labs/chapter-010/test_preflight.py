import copy
import json
import tempfile
import unittest
from pathlib import Path
from preflight import validate, forbidden_artifacts, check_gitignore

BASE = json.loads((Path(__file__).parent / "readiness.json").read_text(encoding="utf-8"))

class PreflightTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(BASE), [])
    def test_auto_apply(self):
        d = copy.deepcopy(BASE); d["stacks"][1]["auto_apply"] = True
        self.assertTrue(any("auto_apply" in e for e in validate(d)))
    def test_dbre(self):
        d = copy.deepcopy(BASE); d["stacks"][1]["approvals"] = ["service-owner"]
        self.assertTrue(any("DBRE" in e for e in validate(d)))
    def test_duplicate_backend(self):
        d = copy.deepcopy(BASE); d["stacks"][1]["backend_key"] = d["stacks"][0]["backend_key"]
        self.assertTrue(any("duplicate backend_key" in e for e in validate(d)))
    def test_state_encryption(self):
        d = copy.deepcopy(BASE); d["stacks"][1]["state"]["encrypted"] = False
        self.assertTrue(any("state encryption" in e for e in validate(d)))
    def test_latest_cli(self):
        d = copy.deepcopy(BASE); d["cli_version"] = "latest"
        self.assertTrue(any("cli_version" in e for e in validate(d)))
    def test_mutable_image(self):
        d = copy.deepcopy(BASE); d["ci_image"] = "iac:latest"
        self.assertTrue(any("ci_image" in e for e in validate(d)))
    def test_missing_owner(self):
        d = copy.deepcopy(BASE); d["stacks"][0]["owner"] = ""
        self.assertTrue(any("owner" in e for e in validate(d)))
    def test_artifact_and_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "unsafe.tfstate"; p.write_text("dummy", encoding="utf-8")
            self.assertTrue(forbidden_artifacts(d))
            p.unlink()
            self.assertEqual(forbidden_artifacts(d), [])
    def test_cache_exclusion(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".terraform"; p.mkdir()
            (p / "sample.tfstate").write_text("dummy", encoding="utf-8")
            self.assertEqual(forbidden_artifacts(d), [])
    def test_gitignore(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".gitignore").write_text(".terraform/\n*.tfstate\n*.tfplan\n", encoding="utf-8")
            self.assertEqual(check_gitignore(d), [])

if __name__ == "__main__":
    unittest.main()
