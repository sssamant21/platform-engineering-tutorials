import copy
import json
import unittest
from pathlib import Path
from graph_policy import validate

ROOT=Path(__file__).parent
GRAPH=json.loads((ROOT/"dependency-graph.json").read_text(encoding="utf-8"))
PLAN=json.loads((ROOT/"sample-plan.json").read_text(encoding="utf-8"))
POLICY=json.loads((ROOT/"dependency-policy.json").read_text(encoding="utf-8"))

class GraphTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(GRAPH,PLAN,POLICY),[])
    def test_cycle(self):
        g=copy.deepcopy(GRAPH);g["edges"].append({"before":"audit","after":"foundation"});self.assertTrue(any("cycle" in x for x in validate(g,PLAN,POLICY)))
    def test_missing_node(self):
        g=copy.deepcopy(GRAPH);g["nodes"].remove("audit");self.assertTrue(validate(g,PLAN,POLICY))
    def test_duplicate_node(self):
        g=copy.deepcopy(GRAPH);g["nodes"].append("audit");self.assertTrue(validate(g,PLAN,POLICY))
    def test_missing_required_edge(self):
        g=copy.deepcopy(GRAPH);g["edges"].pop();self.assertTrue(validate(g,PLAN,POLICY))
    def test_unknown_edge_node(self):
        g=copy.deepcopy(GRAPH);g["edges"].append({"before":"audit","after":"ghost"});self.assertTrue(validate(g,PLAN,POLICY))
    def test_self_edge(self):
        g=copy.deepcopy(GRAPH);g["edges"].append({"before":"audit","after":"audit"});self.assertTrue(validate(g,PLAN,POLICY))
    def test_duplicate_edge(self):
        g=copy.deepcopy(GRAPH);g["edges"].append(g["edges"][0]);self.assertTrue(validate(g,PLAN,POLICY))
    def test_bad_edge_shape(self):
        g=copy.deepcopy(GRAPH);g["edges"].append({"before":"audit"});self.assertTrue(validate(g,PLAN,POLICY))
    def test_node_cap(self):
        p=copy.deepcopy(POLICY);p["max_nodes"]=3;self.assertTrue(validate(GRAPH,PLAN,p))
    def test_delete(self):
        p=copy.deepcopy(PLAN);p["resource_changes"][0]["change"]["actions"]=["delete"];self.assertTrue(validate(GRAPH,p,POLICY))
    def test_replace(self):
        p=copy.deepcopy(PLAN);p["resource_changes"][0]["change"]["actions"]=["delete","create"];self.assertTrue(validate(GRAPH,p,POLICY))
    def test_invalid_actions(self):
        p=copy.deepcopy(PLAN);p["resource_changes"][0]["change"]["actions"]=[];self.assertTrue(validate(GRAPH,p,POLICY))
    def test_missing_changes(self): self.assertTrue(validate(GRAPH,{},POLICY))
    def test_unsafe_policy(self):
        p=copy.deepcopy(POLICY);p["deny_deletes"]=False;self.assertTrue(validate(GRAPH,PLAN,p))
    def test_invalid_schema(self): self.assertTrue(validate([],PLAN,POLICY))
    def test_invalid_policy(self):
        p=copy.deepcopy(POLICY);p["max_nodes"]=0;self.assertTrue(validate(GRAPH,PLAN,p))

if __name__=="__main__":unittest.main()
