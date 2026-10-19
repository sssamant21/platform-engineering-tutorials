import copy,json,unittest
from pathlib import Path
from iam import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/iam-safe.json').read_text())
class IAMTests(unittest.TestCase):
    def bad(self,**kw):self.assertTrue(assess(dict(SAFE,**kw)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_environment(self):self.bad(environment='prod')
    def test_principal(self):self.bad(principal='admin')
    def test_resource(self):self.bad(resource='*')
    def test_actions(self):self.bad(actions=['*'])
    def test_admin(self):self.bad(actions=['iam:*'])
    def test_empty_actions(self):self.bad(actions=[])
    def test_passrole(self):self.bad(passrole=True)
    def test_duplicate_actions(self):self.bad(actions=['s3:GetObject','s3:GetObject'])
    def test_string_actions(self):self.bad(actions='s3:GetObject')
    def test_missing_principal(self):self.bad(principal='')
if __name__=="__main__":unittest.main()
