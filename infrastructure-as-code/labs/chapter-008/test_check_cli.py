import unittest
from check_cli import compare, parse_version

class CLITests(unittest.TestCase):
    def test_terraform(self):
        self.assertEqual(parse_version("Terraform v1.9.8\non linux_amd64"), "1.9.8")

    def test_opentofu(self):
        self.assertEqual(parse_version("OpenTofu v1.8.4"), "1.8.4")

    def test_expected_matches(self):
        self.assertTrue(compare("1.9.8", "Terraform v1.9.8")[0])

    def test_mismatch(self):
        self.assertFalse(compare("1.9.8", "Terraform v1.9.7")[0])

    def test_invalid(self):
        self.assertIsNone(parse_version("not a version"))

if __name__ == "__main__":
    unittest.main()
