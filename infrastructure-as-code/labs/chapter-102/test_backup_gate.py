import unittest
from backup_gate import digest

class BackupGateTests(unittest.TestCase):
    def test_digest(self):
        self.assertEqual(len(digest(b'test')), 64)

if __name__ == '__main__':
    unittest.main()
