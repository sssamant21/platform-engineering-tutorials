import copy
import json
import unittest
from pathlib import Path
from validate_registry import validate

BASE = json.loads((Path(__file__).parent / "registry-policy.json").read_text(encoding="utf-8"))

class RegistryTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(BASE), [])

    def test_checksum_disabled(self):
        d = copy.deepcopy(BASE)
        d["verify_checksums"] = False
        self.assertTrue(validate(d))

    def test_untrusted_mirror(self):
        d = copy.deepcopy(BASE)
        d["mirror"]["enabled"] = True
        self.assertTrue(validate(d))

    def test_duplicate_provider(self):
        d = copy.deepcopy(BASE)
        d["providers"].append(copy.deepcopy(d["providers"][0]))
        self.assertTrue(any("duplicate source" in e for e in validate(d)))

    def test_lockfile_missing(self):
        d = copy.deepcopy(BASE)
        d["providers"][0]["lockfile_committed"] = False
        self.assertTrue(any("lockfile" in e for e in validate(d)))

    def test_shared_writable_cache(self):
        d = copy.deepcopy(BASE)
        d["cache"]["shared_writable"] = True
        self.assertTrue(validate(d))

    def test_unapproved_registry(self):
        d = copy.deepcopy(BASE)
        d["providers"][0]["source"] = "untrusted.example/team/random"
        self.assertTrue(any("unapproved registry" in e for e in validate(d)))

if __name__ == "__main__":
    unittest.main()
