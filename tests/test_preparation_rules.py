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

    def test_uses_quantile_from_context(self):
        context = {
            "error_ratios": [0.5, 1.0, 1.5],
            "quantile": 0.9,
        }

        self.assertEqual(
            empirical_preparation_rule(100, 20, context),
            130,
        )

    def test_uses_error_ratios_from_context(self):
        context = {
            "error_ratios": [0.8, 1.2, 1.6],
            "quantile": 0.5,
        }

        self.assertEqual(
            empirical_preparation_rule(100, 20, context),
            100,
        )

    def test_repeated_calls_do_not_carry_stock_between_cases(self):
        context = {
            "error_ratios": [1.0],
            "quantile": 0.5,
        }

        first = empirical_preparation_rule(100, 80, context)
        second = empirical_preparation_rule(100, 0, context)

        self.assertEqual(first, 20)
        self.assertEqual(second, 100)
        self.assertEqual(
            context,
            {"error_ratios": [1.0], "quantile": 0.5},
        )