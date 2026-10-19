import json,unittest
from pathlib import Path
from budget_gate import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/budget-safe.json').read_text())
class BudgetTests(unittest.TestCase):
    def bad(self,**changes):self.assertTrue(assess(dict(SAFE,**changes)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_environment(self):self.bad(environment='prod')
    def test_owner(self):self.bad(owner='unknown')
    def test_run_id(self):self.bad(run_id='other')
    def test_cost(self):self.bad(cost_usd=26)
    def test_lease(self):self.bad(lease_minutes=121)
    def test_orphan(self):self.bad(orphaned_resources=1)
    def test_cleanup(self):self.bad(cleanup_verified=False)
    def test_bool_cost(self):self.bad(cost_usd=True)
    def test_negative_cost(self):self.bad(cost_usd=-1)
    def test_string_lease(self):self.bad(lease_minutes='1')
if __name__=="__main__":unittest.main()
