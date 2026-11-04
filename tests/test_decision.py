import unittest

from freshwise.decision import (
    recommend_preparation,
    evaluate_preparation,
    calculate_loss,
    average_scenario_loss,
    optimize_preparation,
    adjust_demand_scenarios,
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

    def test_optimizer_finds_best_quantity(self):
        result = optimize_preparation(
            20, [70, 100, 130], 2, 5
        )

        self.assertEqual(result["prepare_qty"], 110)
        self.assertAlmostEqual(result["average_loss"], 60.0)

    def test_optimizer_prepares_zero_when_stock_is_enough(self):
        result = optimize_preparation(
            150, [70, 100, 130], 2, 5
        )

        self.assertEqual(result["prepare_qty"], 0)
        self.assertAlmostEqual(result["average_loss"], 100.0)

    def test_optimizer_prefers_smaller_quantity_on_tie(self):
        result = optimize_preparation(
            0, [0, 10], 1, 1
        )

        self.assertEqual(result["prepare_qty"], 0)
        self.assertAlmostEqual(result["average_loss"], 5.0)

    def test_optimizer_rejects_negative_inputs(self):
        cases = [
            (-1, [70, 100, 130], 2, 5),
            (20, [70, 100, 130], -2, 5),
            (20, [70, 100, 130], 2, -5),
            (20, [-70, 100, 130], 2, 5),
        ]

        for inventory, scenarios, overage, underage in cases:
            with self.subTest(
                inventory=inventory,
                scenarios=scenarios,
                overage=overage,
                underage=underage,
            ):
                with self.assertRaises(ValueError):
                    optimize_preparation(
                        inventory, scenarios, overage, underage
                    )

    def test_custom_adjustment_shifts_all_scenarios(self):
        result = adjust_demand_scenarios(
            [70, 100, 130], 1, 140, 0.25
        )

        self.assertAlmostEqual(result["custom_anchor"], 110.0)
        self.assertAlmostEqual(result["adjustment"], 10.0)
        self.assertEqual(
            result["updated_scenarios"],
            [80.0, 110.0, 140.0],
        )

    def test_zero_opinion_weight_keeps_original_scenarios(self):
        result = adjust_demand_scenarios(
            [70, 100, 130], 1, 140, 0
        )

        self.assertAlmostEqual(result["adjustment"], 0)
        self.assertEqual(
            result["updated_scenarios"],
            [70, 100, 130],
        )

    def test_full_opinion_weight_uses_manager_estimate(self):
        result = adjust_demand_scenarios(
            [70, 100, 130], 1, 140, 1
        )

        self.assertAlmostEqual(result["custom_anchor"], 140)
        self.assertAlmostEqual(result["adjustment"], 40)
        self.assertEqual(
            result["updated_scenarios"],
            [110, 140, 170],
        )

    def test_custom_adjustment_clips_negative_demand_to_zero(self):
        result = adjust_demand_scenarios(
            [70, 100, 130], 1, 20, 1
        )

        self.assertAlmostEqual(result["adjustment"], -80)
        self.assertEqual(
            result["updated_scenarios"],
            [0, 20, 50],
        )

    def test_custom_rejects_invalid_opinion_weights(self):
        for weight in [-0.1, 1.1]:
            with self.subTest(weight=weight):
                with self.assertRaises(ValueError):
                    adjust_demand_scenarios(
                        [70, 100, 130], 1, 140, weight
                    )

    def test_custom_rejects_out_of_range_anchor(self):
        for index in [-1, 3]:
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    adjust_demand_scenarios(
                        [70, 100, 130], index, 140, 0.25
                    )

    def test_custom_plan_tradeoff_on_original_scenarios(self):
        scenarios = [70, 100, 130]

        custom = adjust_demand_scenarios(
            scenarios, 1, 140, 0.25
        )

        original_plan = optimize_preparation(
            20, scenarios, 2, 5
        )

        custom_plan = optimize_preparation(
            20, custom["updated_scenarios"], 2, 5
        )

        original_loss = average_scenario_loss(
            original_plan["prepare_qty"],
            20, scenarios, 2, 5,
        )

        custom_loss_on_original = average_scenario_loss(
            custom_plan["prepare_qty"],
            20, scenarios, 2, 5,
        )

        self.assertEqual(original_plan["prepare_qty"], 110)
        self.assertEqual(custom_plan["prepare_qty"], 120)
        self.assertAlmostEqual(original_loss, 60)
        self.assertAlmostEqual(custom_loss_on_original, 80)

        self.assertEqual(scenarios, [70, 100, 130])

    def test_custom_plan_tradeoff_on_updated_scenarios(self):
        scenarios = [70, 100, 130]

        custom = adjust_demand_scenarios(
            scenarios, 1, 140, 0.25
        )

        updated_scenarios = custom["updated_scenarios"]

        original_plan = optimize_preparation(
            20, scenarios, 2, 5
        )

        custom_plan = optimize_preparation(
            20, updated_scenarios, 2, 5
        )

        original_loss_on_custom = average_scenario_loss(
            original_plan["prepare_qty"],
            20, updated_scenarios, 2, 5,
        )

        custom_loss = average_scenario_loss(
            custom_plan["prepare_qty"],
            20, updated_scenarios, 2, 5,
        )

        self.assertAlmostEqual(
            original_loss_on_custom, 190 / 3
        )
        self.assertAlmostEqual(custom_loss, 60)