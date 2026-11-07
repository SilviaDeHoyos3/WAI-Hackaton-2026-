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
