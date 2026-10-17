import unittest
from scorecard import WEIGHTS, weighted_score

class ScorecardTests(unittest.TestCase):
    def test_perfect_score(self):
        self.assertEqual(weighted_score({k: 5 for k in WEIGHTS}), 5.0)

    def test_minimum_score(self):
        self.assertEqual(weighted_score({k: 1 for k in WEIGHTS}), 1.0)

    def test_invalid_weight_sum(self):
        with self.assertRaises(ValueError):
            weighted_score({k: 3 for k in WEIGHTS}, {k: 1 for k in WEIGHTS})

    def test_missing_criterion(self):
        with self.assertRaises(ValueError):
            weighted_score({"coverage": 5})

    def test_invalid_score(self):
        with self.assertRaises(ValueError):
            weighted_score({k: (6 if k == "coverage" else 3) for k in WEIGHTS})

if __name__ == "__main__":
    unittest.main()
