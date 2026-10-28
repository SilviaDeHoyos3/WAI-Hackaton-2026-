import unittest

from freshwise.decision import (
    recommend_preparation,
    evaluate_preparation,
    calculate_loss,
    average_scenario_loss,
)


class DecisionTests(unittest.TestCase):
    def test_subtracts_inventory(self):
        self.assertEqual(recommend_preparation(100, 20), 80)

    def test_enough_inventory(self):
        self.assertEqual(recommend_preparation(100, 120), 0)

    def test_rounds_up(self):
        self.assertEqual(recommend_preparation(100.4, 20), 81)

    def test_rejects_negative_inventory(self):
        with self.assertRaises(ValueError):
            recommend_preparation(100, -20)

    def test_rejects_negative_forecast(self):
        with self.assertRaises(ValueError):
            recommend_preparation(-10, 20)

    def test_evaluation_excess(self):
        result = evaluate_preparation(80, 20, 70)

        self.assertEqual(result["excess"], 30)
        self.assertEqual(result["unmet"], 0)

    def test_evaluation_unmet(self):
        result = evaluate_preparation(80, 20, 130)

        self.assertEqual(result["excess"], 0)
        self.assertEqual(result["unmet"], 30)

    def test_evaluation_rejects_negative_quantities(self):
        cases = [
            (-1, 20, 70),
            (80, -1, 70),
            (80, 20, -1),
        ]

        for prepared, inventory, actual_orders in cases:
            with self.subTest(
                prepared=prepared,
                inventory=inventory,
                actual_orders=actual_orders,
            ):
                with self.assertRaises(ValueError):
                    evaluate_preparation(
                        prepared, inventory, actual_orders
                    )

    def test_loss_for_excess(self):
        self.assertEqual(calculate_loss(30, 0, 2, 5), 60)

    def test_loss_for_unmet(self):
        self.assertEqual(calculate_loss(0, 30, 2, 5), 150)

    def test_loss_rejects_negative_costs(self):
        for overage_cost, underage_cost in [(-2, 5), (2, -5)]:
            with self.subTest(
                overage_cost=overage_cost,
                underage_cost=underage_cost,
            ):
                with self.assertRaises(ValueError):
                    calculate_loss(
                        30, 0, overage_cost, underage_cost
                    )

    def test_average_loss_for_80_prepared(self):
        result = average_scenario_loss(
            80, 20, [70, 100, 130], 2, 5
        )
        self.assertAlmostEqual(result, 70.0)

    def test_average_loss_for_110_prepared(self):
        result = average_scenario_loss(
            110, 20, [70, 100, 130], 2, 5
        )
        self.assertAlmostEqual(result, 60.0)

    def test_average_loss_rejects_empty_scenarios(self):
        with self.assertRaises(ValueError):
            average_scenario_loss(80, 20, [], 2, 5)