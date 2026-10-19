import json,unittest
from pathlib import Path
from rbac import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/rbac-safe.json').read_text())
class RBACTests(unittest.TestCase):
    def bad(self,**kw):self.assertTrue(assess(dict(SAFE,**kw)))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_namespace(self):self.bad(namespace='kube-system')
    def test_service_account(self):self.bad(service_account='default')
    def test_resource(self):self.bad(resource='secrets')
    def test_verbs(self):self.bad(verbs=['*'])
    def test_delete(self):self.bad(verbs=['delete'])
    def test_empty_verbs(self):self.bad(verbs=[])
    def test_cluster_scope(self):self.bad(cluster_scope=True)
    def test_automount(self):self.bad(automount_token=True)
    def test_duplicate_verbs(self):self.bad(verbs=['get','get'])
    def test_string_verbs(self):self.bad(verbs='get')
if __name__=="__main__":unittest.main()
