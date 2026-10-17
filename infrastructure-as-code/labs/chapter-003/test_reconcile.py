import tempfile
import unittest
from pathlib import Path
from reconcile import DESIRED, reconcile

class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "iac-chapter-003-python" / "desired.txt"

    def test_missing_file_check_is_read_only(self):
        self.assertEqual(reconcile(self.path), 2)
        self.assertFalse(self.path.exists())

    def test_apply_then_idempotent(self):
        self.assertEqual(reconcile(self.path, True), 0)
        self.assertEqual(self.path.read_text(), DESIRED)
        self.assertEqual(reconcile(self.path), 0)

    def test_drift_detection_and_repair(self):
        reconcile(self.path, True)
        self.path.write_text("owner=manual\n")
        self.assertEqual(reconcile(self.path), 2)
        self.assertEqual(self.path.read_text(), "owner=manual\n")
        self.assertEqual(reconcile(self.path, True), 0)
        self.assertEqual(self.path.read_text(), DESIRED)

    def test_rejects_outside_path(self):
        with self.assertRaises(ValueError):
            reconcile(Path(self.tmp.name) / "outside.txt", True)

if __name__ == "__main__":
    unittest.main()
