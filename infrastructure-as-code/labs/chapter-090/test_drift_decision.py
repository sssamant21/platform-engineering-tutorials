import unittest
from drift_decision import decide
class DriftTests(unittest.TestCase):
    def test_low(self):self.assertEqual(decide(dict(environment='dev',impact='low',destructive=False,database=False)),'notify')
    def test_staging(self):self.assertEqual(decide(dict(environment='staging',impact='medium',destructive=False,database=False)),'review')
    def test_prod(self):self.assertEqual(decide(dict(environment='production',impact='low',destructive=False,database=False)),'review')
    def test_prod_db(self):self.assertEqual(decide(dict(environment='production',impact='low',destructive=False,database=True)),'quarantine')
    def test_destructive(self):self.assertEqual(decide(dict(environment='dev',impact='low',destructive=True,database=False)),'quarantine')
    def test_high(self):self.assertEqual(decide(dict(environment='dev',impact='high',destructive=False,database=False)),'quarantine')
    def test_critical(self):self.assertEqual(decide(dict(environment='dev',impact='critical',destructive=False,database=False)),'quarantine')
    def test_unknown(self):self.assertEqual(decide(dict(environment='unknown',impact='low',destructive=False,database=False)),'quarantine')
    def test_missing(self):self.assertEqual(decide({}),'quarantine')
    def test_invalid(self):self.assertEqual(decide(None),'quarantine')
    def test_type(self):self.assertEqual(decide(dict(environment='dev',impact='low',destructive='no',database=False)),'quarantine')
if __name__=="__main__":unittest.main()
