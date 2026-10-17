import copy
import json
import unittest
from pathlib import Path
from graph_policy import validate

BASE = json.loads((Path(__file__).parent / "graph.json").read_text(encoding="utf-8"))

class GraphPolicyTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(BASE), [])

    def test_missing_dependency(self):
        d = copy.deepcopy(BASE)
        d["nodes"][1]["depends_on"] = ["unknown"]
        self.assertTrue(any("missing dependency" in e for e in validate(d)))

    def test_cycle(self):
        d = copy.deepcopy(BASE)
        d["nodes"][0]["depends_on"] = ["audit"]
        self.assertTrue(any("cycle" in e for e in validate(d)))

    def test_duplicate_id(self):
        d = copy.deepcopy(BASE)
        d["nodes"][1]["id"] = "seed"
        self.assertTrue(any("duplicate id" in e for e in validate(d)))

    def test_prod_auto_apply(self):
        d = copy.deepcopy(BASE)
        d["environment"] = "prod"
        d["auto_apply"] = True
        self.assertTrue(any("auto_apply" in e for e in validate(d)))

    def test_prod_db_delete(self):
        d = copy.deepcopy(BASE)
        d["environment"] = "prod"
        d["nodes"][0].update(kind="database", action="delete", dbre_approved=False)
        self.assertTrue(any("DBRE" in e for e in validate(d)))

    def test_prod_db_approved(self):
        d = copy.deepcopy(BASE)
        d["environment"] = "prod"
        d["nodes"][0].update(kind="database", action="delete", dbre_approved=True)
        self.assertEqual(validate(d), [])

if __name__ == "__main__":
    unittest.main()
