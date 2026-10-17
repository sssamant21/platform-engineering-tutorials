import copy
import json
import unittest
from pathlib import Path
from validate_toolchain import validate

BASE = json.loads((Path(__file__).parent / "toolchain.json").read_text(encoding="utf-8"))

class ManifestTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(BASE), [])

    def test_latest_rejected(self):
        data = copy.deepcopy(BASE)
        data["cli_version"] = "latest"
        self.assertTrue(validate(data))

    def test_unpinned_image_rejected(self):
        data = copy.deepcopy(BASE)
        data["ci_image"] = "infra/terraform:latest"
        self.assertTrue(validate(data))

    def test_missing_lockfile_rejected(self):
        data = copy.deepcopy(BASE)
        data["providers"][0]["lockfile_committed"] = False
        self.assertTrue(validate(data))

    def test_unpinned_modules_rejected(self):
        data = copy.deepcopy(BASE)
        data["module_sources_pinned"] = False
        self.assertTrue(validate(data))

    def test_unknown_engine_rejected(self):
        data = copy.deepcopy(BASE)
        data["engine"] = "other"
        self.assertTrue(validate(data))

if __name__ == "__main__":
    unittest.main()
