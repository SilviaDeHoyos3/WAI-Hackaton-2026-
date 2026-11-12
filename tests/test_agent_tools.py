import json
import unittest

from freshwise.agent_tools import preparation_recommendation


class AgentToolTests(unittest.TestCase):
    def test_returns_plan_as_json_serializable_data(self):
        result = preparation_recommendation(
            100, 20, [0.8, 1.0, 1.2], 0.55
        )

        self.assertEqual(result["new_portions_to_prepare"], 80)
        self.assertEqual(result["total_available"], 100)
        self.assertEqual(result["usable_stock"], 20)
        self.assertFalse(result["manager_adjustment_applied"])

        decoded = json.loads(json.dumps(result, allow_nan=False))
        self.assertEqual(decoded, result)

    def test_existing_stock_can_exceed_target(self):
        result = preparation_recommendation(
            100, 150, [1.0], 0.55
        )

        self.assertEqual(result["new_portions_to_prepare"], 0)
        self.assertEqual(result["total_available"], 150)
        self.assertEqual(result["target_supply"], 100.0)

    def test_manager_adjustment_changes_preparation(self):
        from freshwise.agent_tools import (
            manager_adjusted_recommendation,
        )

        result = manager_adjusted_recommendation(
            100, 20, [0.8, 1.0, 1.2],
            0.55, "central", 140, 0.25,
        )

        self.assertEqual(
            result["original_plan"]["new_portions_to_prepare"], 80
        )
        self.assertEqual(
            result["adjusted_plan"]["new_portions_to_prepare"], 90
        )
        self.assertEqual(
            result["manager_context"]["demand_shift"], 10
        )
        json.dumps(result, allow_nan=False)

    def test_zero_opinion_weight_preserves_preparation(self):
        from freshwise.agent_tools import (
            manager_adjusted_recommendation,
        )

        result = manager_adjusted_recommendation(
            100, 20, [0.8, 1.0, 1.2],
            0.55, "central", 1000, 0,
        )

        self.assertEqual(
            result["original_plan"]["new_portions_to_prepare"],
            result["adjusted_plan"]["new_portions_to_prepare"],
        )
        self.assertEqual(
            result["manager_context"]["demand_shift"], 0
        )

    def test_central_plan_subtracts_stock_and_rounds_up(self):
        from freshwise.agent_tools import (
            central_preparation_recommendation,
        )

        result = central_preparation_recommendation(100.2, 20)

        self.assertEqual(result["new_portions_to_prepare"], 81)
        self.assertEqual(result["total_available"], 101)
        self.assertEqual(result["target_supply"], 100.2)
        self.assertEqual(
            result["policy"],
            "central_forecast_minus_usable_stock",
        )
        json.dumps(result, allow_nan=False)

    def test_central_plan_preserves_excess_existing_stock(self):
        from freshwise.agent_tools import (
            central_preparation_recommendation,
        )

        result = central_preparation_recommendation(100, 150)

        self.assertEqual(result["new_portions_to_prepare"], 0)
        self.assertEqual(result["total_available"], 150)

    def test_central_plan_rejects_invalid_stock(self):
        from freshwise.agent_tools import (
            central_preparation_recommendation,
        )

        for stock in (-1, 1.5):
            with self.subTest(stock=stock):
                with self.assertRaises(ValueError):
                    central_preparation_recommendation(100, stock)

    def test_central_adjustment_keeps_forecast_separate(self):
        from freshwise.agent_tools import (
            manager_adjusted_central_recommendation,
        )

        result = manager_adjusted_central_recommendation(
            100, 20, 140, 0.25
        )

        self.assertEqual(
            result["original_plan"]["new_portions_to_prepare"], 80
        )
        self.assertEqual(
            result["adjusted_plan"]["new_portions_to_prepare"], 90
        )
        self.assertEqual(
            result["adjusted_plan"]["forecast_orders"], 100
        )
        self.assertEqual(
            result["adjusted_plan"]["target_supply"], 110
        )
        json.dumps(result, allow_nan=False)

    def test_central_adjustment_respects_weight_endpoints(self):
        from freshwise.agent_tools import (
            manager_adjusted_central_recommendation,
        )

        for weight, expected in [(0, 80), (1, 120)]:
            with self.subTest(weight=weight):
                result = manager_adjusted_central_recommendation(
                    100, 20, 140, weight
                )
                self.assertEqual(
                    result["adjusted_plan"]["new_portions_to_prepare"],
                    expected,
                )

    def test_central_adjustment_rejects_invalid_context(self):
        from freshwise.agent_tools import (
            manager_adjusted_central_recommendation,
        )

        for estimate, weight in [
            (-1, 0.25),
            (140, -0.1),
            (140, 1.1),
        ]:
            with self.subTest(estimate=estimate, weight=weight):
                with self.assertRaises(ValueError):
                    manager_adjusted_central_recommendation(
                        100, 20, estimate, weight
                    )