import copy,json,unittest
from pathlib import Path
from supply_chain import assess
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/attestation.json').read_text())
class SupplyTests(unittest.TestCase):
    def bad(self,**changes):
        e=dict(SAFE,**changes);self.assertTrue(assess(e))
    def test_safe(self):self.assertEqual(assess(SAFE),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_builder(self):self.bad(builder_id='untrusted')
    def test_source(self):self.bad(source_commit='different')
    def test_artifact_digest(self):self.bad(artifact_digest='latest')
    def test_sbom_digest(self):self.bad(sbom_digest='missing')
    def test_provenance_digest(self):self.bad(provenance_digest='unsigned')
    def test_missing_builder(self):self.bad(builder_id='')
    def test_missing_source(self):self.bad(source_commit='')
if __name__=="__main__":unittest.main()
