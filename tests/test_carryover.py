import unittest

import numpy as np
import pandas as pd

from freshwise.carryover import (prepare_forecast_minus_leftovers, simulate_carryover,
                                 summarize)


def rows(forecasts, actuals, weeks=None, center=1, meal=10):
    weeks = weeks or list(range(1, len(forecasts) + 1))
    return pd.DataFrame({"center_id": center, "meal_id": meal, "target_week": weeks,
                         "forecast_orders": forecasts, "actual_orders": actuals})


rule = prepare_forecast_minus_leftovers


class CarryoverTests(unittest.TestCase):
    def test_hand_calculated_path(self):
        # Week 1: prepare 10, sell 6, 4 left. Week 2: forecast 10 - 4 = prepare 6,
        # sell old 4 first then 3 new (demand 7), 3 new left. Week 3 (last): prepare 7,
        # sell old 3 then 5 new -> 2 new portions still usable at the end (terminal, not expired).
        r = simulate_carryover(rows([10, 10, 10], [6, 7, 8]), rule, shelf_life_weeks=1)
        self.assertEqual(r.prepared.tolist(), [10, 6, 7])
        self.assertEqual(r.leftovers_in.tolist(), [0, 4, 3])
        self.assertEqual(r.sold.tolist(), [6, 7, 8])
        self.assertEqual(r.unmet.tolist(), [0, 0, 0])
        self.assertEqual(r.expired.tolist(), [0, 0, 0])
        self.assertEqual(r.terminal_stock.tolist(), [0, 0, 2])

    def test_food_expires_after_shelf_life(self):
        # 5 left after week 1, demand 0 in week 2 -> those 5 are too old after week 2.
        r = simulate_carryover(rows([10, 1, 1], [5, 0, 0]), rule, shelf_life_weeks=1)
        self.assertEqual(r.expired.tolist()[1], 5)

    def test_shelf_life_zero_means_no_carry_over(self):
        r = simulate_carryover(rows([10, 10], [6, 7]), rule, shelf_life_weeks=0)
        self.assertEqual(r.leftovers_in.tolist(), [0, 0])
        self.assertEqual(r.expired.tolist(), [4, 3])
        self.assertEqual(r.terminal_stock.tolist(), [0, 0])

    def test_missing_week_ages_stock(self):
        r = simulate_carryover(rows([10, 10], [6, 6], weeks=[1, 3]), rule, shelf_life_weeks=1)
        self.assertEqual(r.leftovers_in.tolist(), [0, 0])
        self.assertEqual(r.expired.tolist()[0], 4)

    def test_portions_are_conserved(self):
        rng = np.random.default_rng(0)
        r = simulate_carryover(rows(rng.uniform(0, 50, 30).tolist(), rng.integers(0, 50, 30).tolist()),
                               rule, shelf_life_weeks=2, start_stock=7)
        self.assertEqual(7 + r.prepared.sum(), r.sold.sum() + r.expired.sum() + r.terminal_stock.sum())
        self.assertTrue(((r.sold + r.unmet) == r.actual_orders).all())

    def test_groups_are_independent_and_order_free(self):
        a = rows([10, 10], [6, 7], meal=10)
        b = rows([5, 5], [5, 1], meal=11)
        data = pd.concat([a, b])
        r1 = simulate_carryover(data, rule)
        r2 = simulate_carryover(data.sample(frac=1, random_state=1), rule)
        pd.testing.assert_frame_equal(r1.reset_index(drop=True), r2.reset_index(drop=True))
        self.assertEqual(r1[r1.meal_id == 11].leftovers_in.tolist(), [0, 0])

    def test_invalid_rule_output_rejected(self):
        with self.assertRaises(ValueError):
            simulate_carryover(rows([10], [5]), lambda f, l, c: -1)
        with self.assertRaises(ValueError):
            simulate_carryover(rows([10], [5]), lambda f, l, c: 2.5)

    def test_duplicate_rows_rejected(self):
        with self.assertRaises(ValueError):
            simulate_carryover(rows([10, 10], [5, 5], weeks=[1, 1]), rule)

    def test_summary_rates(self):
        r = simulate_carryover(rows([10, 10, 10], [6, 7, 8]), rule)
        s = summarize(r.assign(method="m")).iloc[0]
        self.assertAlmostEqual(s.waste_rate, 0.0)
        self.assertAlmostEqual(s.waste_rate_with_terminal, 2 / 23)
        self.assertAlmostEqual(s.unmet_rate, 0.0)
        self.assertEqual(s.penalty, 0)
        self.assertEqual(s.penalty_with_terminal, 4)

    def test_old_stock_at_the_end_is_expired_not_terminal(self):
        # 5 left after week 1 (age 1 in week 2), nothing sold in week 2 and nothing prepared:
        # at the end that stock would be 2 weeks old -> expired; nothing is terminal.
        r = simulate_carryover(rows([10, 0], [5, 0]), rule, shelf_life_weeks=1)
        self.assertEqual(r.expired.tolist(), [0, 5])
        self.assertEqual(r.terminal_stock.tolist(), [0, 0])


if __name__ == "__main__":
    unittest.main()
