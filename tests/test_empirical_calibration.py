import unittest

import numpy as np
import pandas as pd

from freshwise.empirical_calibration import build_ratio_lookup


class EmpiricalCalibrationTests(unittest.TestCase):
    def make_rows(self):
        records = []

        for window, cal_week, eval_week in [
            ("A", 96, 106),
            ("B", 116, 126),
        ]:
            for forecast in [50, 100, 300]:
                records.append({
                    "method": "last",
                    "window": window,
                    "role": "calibration",
                    "target_week": cal_week,
                    "forecast_orders": forecast,
                    "actual_orders": forecast * 2,
                })
                records.append({
                    "method": "last",
                    "window": window,
                    "role": "evaluation",
                    "target_week": eval_week,
                    "forecast_orders": forecast,
                    "actual_orders": forecast,
                })

        return pd.DataFrame(records)

    def test_ratios_come_from_calibration_only(self):
        rows = self.make_rows()
        lookup = build_ratio_lookup(rows, methods=("last",))

        self.assertEqual(len(lookup), 6)
        for sample in lookup.values():
            np.testing.assert_array_equal(sample, [2.0])

    def test_evaluation_outcomes_do_not_change_calibration(self):
        rows = self.make_rows()
        original = build_ratio_lookup(rows, methods=("last",))

        rows.loc[
            rows["role"] == "evaluation", "actual_orders"
        ] = 999999

        changed = build_ratio_lookup(rows, methods=("last",))

        self.assertEqual(original.keys(), changed.keys())
        for key in original:
            np.testing.assert_array_equal(original[key], changed[key])

    def test_wrong_calibration_week_is_rejected(self):
        rows = self.make_rows()
        rows.loc[
            (rows["window"] == "A")
            & (rows["role"] == "calibration"),
            "target_week",
        ] = 106

        with self.assertRaises(ValueError):
            build_ratio_lookup(rows, methods=("last",))


    def test_calibrated_rule_works_with_carryover(self):
        from freshwise.carryover import simulate_carryover
        from freshwise.preparation_rules import (
            make_calibrated_empirical_rule,
        )

        lookup = build_ratio_lookup(
            self.make_rows(), methods=("last",)
        )

        rows = pd.DataFrame({
            "center_id": [13, 13],
            "meal_id": [1198, 1198],
            "target_week": [106, 107],
            "method": ["last", "last"],
            "window": ["A", "A"],
            "forecast_orders": [100, 100],
            "actual_orders": [150, 180],
        })

        for quantile in (0.55, 5 / 7):
            with self.subTest(quantile=quantile):
                rule = make_calibrated_empirical_rule(
                    lookup, quantile
                )
                result = simulate_carryover(
                    rows, rule,
                    shelf_life_weeks=1,
                    start_stock=0,
                )

                self.assertEqual(
                    result["prepared"].tolist(), [200, 150]
                )
                self.assertEqual(
                    result["leftovers_in"].tolist(), [0, 50]
                )
                self.assertEqual(result["unmet"].sum(), 0)
                self.assertEqual(result["expired"].sum(), 0)
                self.assertEqual(
                    result["terminal_stock"].sum(), 20
                )