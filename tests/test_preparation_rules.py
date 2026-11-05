import unittest

from freshwise.preparation_rules import empirical_preparation_rule


class PreparationRuleTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "error_ratios": [0.5, 0.8, 1.0, 1.1, 1.6],
            "quantile": 0.55,
        }

    def test_subtracts_usable_leftovers(self):
        self.assertEqual(
            empirical_preparation_rule(200, 40, self.context),
            160,
        )

    def test_enough_leftovers_requires_no_preparation(self):
        self.assertEqual(
            empirical_preparation_rule(200, 220, self.context),
            0,
        )

    def test_no_leftovers_requires_full_preparation(self):
        self.assertEqual(
            empirical_preparation_rule(200, 0, self.context),
            200,
        )