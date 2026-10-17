import unittest
from network_diagnostics import valid_host, diagnose

class NetworkTests(unittest.TestCase):
    def test_valid_hostname(self):
        self.assertTrue(valid_host("registry.terraform.io"))

    def test_invalid_hostname(self):
        self.assertFalse(valid_host("https://registry.terraform.io/path"))
        self.assertFalse(valid_host("-bad.example"))

    def test_invalid_host_skips_network(self):
        ok, msg = diagnose("not/a/hostname", resolver=lambda *a, **kw: self.fail("network should not run"))
        self.assertFalse(ok)
        self.assertEqual(msg, "invalid hostname")

    def test_dns_error(self):
        def fail(*args, **kwargs):
            raise OSError("simulated DNS failure")
        ok, msg = diagnose("registry.terraform.io", resolver=fail)
        self.assertFalse(ok)
        self.assertIn("OSError", msg)

if __name__ == "__main__":
    unittest.main()
