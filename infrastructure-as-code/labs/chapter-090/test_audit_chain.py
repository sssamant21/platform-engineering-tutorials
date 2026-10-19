import unittest
from audit_chain import assess,digest
class AuditTests(unittest.TestCase):
    def setUp(self):
        a={'control':'IAC-001','status':'PASS'}
        b={'control':'IAC-002','status':'PASS'}
        self.chain=[{'payload':a,'digest':digest(a),'previous_digest':'GENESIS'},{'payload':b,'digest':digest(b),'previous_digest':digest(a)}]
    def test_valid(self):self.assertEqual(assess(self.chain),[])
    def test_invalid(self):self.assertTrue(assess(None))
    def test_empty(self):self.assertTrue(assess([]))
    def test_bad_entry(self):self.assertTrue(assess([None]))
    def test_bad_payload(self):
        self.chain[0]['payload']=[];self.assertTrue(assess(self.chain))
    def test_tamper(self):
        self.chain[0]['payload']['status']='FAIL';self.assertTrue(assess(self.chain))
    def test_digest(self):
        self.chain[1]['digest']='0'*64;self.assertTrue(assess(self.chain))
    def test_link(self):
        self.chain[1]['previous_digest']='wrong';self.assertTrue(assess(self.chain))
    def test_genesis(self):
        self.chain[0]['previous_digest']='';self.assertTrue(assess(self.chain))
    def test_canonical(self):self.assertEqual(digest({'b':2,'a':1}),digest({'a':1,'b':2}))
if __name__=="__main__":unittest.main()
