import json
import unittest

import numpy as np
import pandas as pd

try:
    import sklearn  # noqa: F401
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False

from freshwise.agent_data_tools import context_from_tables, evidence_tool, forecast_tool, menu_tool


def tables(seed=0):
    rng = np.random.default_rng(seed)
    rows, test_rows = [], []
    for c in (1, 2):
        for m in (10, 11, 12):
            mu = rng.uniform(50, 400)
            for w in range(1, 31):
                if c == 2 and m == 12:
                    continue  # meal 12 never sold at centre 2
                promo = int(rng.random() < 0.2)
                rows.append({"id": len(rows), "week": w, "center_id": c, "meal_id": m,
                             "checkout_price": 200.0, "base_price": 200.0,
                             "emailer_for_promotion": promo, "homepage_featured": 0,
                             "num_orders": int(mu * (1.5 if promo else 1) + rng.integers(0, 20))})
            test_rows.append({"id": 10**6 + len(test_rows), "week": 31, "center_id": c, "meal_id": m,
                              "checkout_price": 200.0, "base_price": 200.0,
                              "emailer_for_promotion": 0, "homepage_featured": 0})
    meals = pd.DataFrame({"meal_id": [10, 11, 12], "category": ["Rice Bowl", "Pasta", "Salad"],
                          "cuisine": ["Indian", "Italian", "Thai"]})
    centers = pd.DataFrame({"center_id": [1, 2], "city_code": [5, 6], "region_code": [1, 1],
                            "center_type": ["TYPE_A", "TYPE_B"], "op_area": [3.0, 4.0]})
    return pd.DataFrame(rows), pd.DataFrame(test_rows), meals, centers


class MenuToolTests(unittest.TestCase):
    def setUp(self):
        self.ctx = context_from_tables(*tables())

    def test_lists_only_meals_sold_at_the_centre(self):
        menu = menu_tool(2, self.ctx)
        self.assertEqual([m["meal_id"] for m in menu["meals"]], [10, 11])
        self.assertEqual(menu["meals"][0]["category"], "Rice Bowl")
        json.dumps(menu)

    def test_unknown_centre_returns_error(self):
        self.assertIn("error", menu_tool(99, self.ctx))


@unittest.skipUnless(HAVE_SKLEARN, "scikit-learn not installed")
class ForecastToolTests(unittest.TestCase):
    def setUp(self):
        self.ctx = context_from_tables(*tables())

    def test_live_next_week_forecast(self):
        f = forecast_tool(1, 10, self.ctx)
        self.assertEqual(f["target_week"], 31)
        self.assertEqual(f["history_end_week"], 30)
        self.assertEqual(f["method"], "hgb")
        self.assertLessEqual(f["range_low"], f["forecast_orders"])
        self.assertLessEqual(f["forecast_orders"], f["range_high"])
        self.assertEqual(len(f["recent_orders"]), 4)
        json.dumps(f)

    def test_meal_not_on_menu_returns_error(self):
        self.assertIn("error", forecast_tool(2, 12, self.ctx))

    def test_past_week_ignores_its_outcome(self):
        a = forecast_tool(1, 10, self.ctx, history_end_week=20)
        train, test, meals, centers = tables()
        train.loc[train.week == 21, "num_orders"] = 10**6
        b = forecast_tool(1, 10, context_from_tables(train, test, meals, centers), history_end_week=20)
        self.assertEqual(a["forecast_orders"], b["forecast_orders"])

    def test_cached_per_centre(self):
        forecast_tool(1, 10, self.ctx)
        forecast_tool(1, 11, self.ctx)
        self.assertEqual(len(self.ctx._cache), 1)


class EvidenceToolTests(unittest.TestCase):
    def test_is_labelled_development(self):
        e = evidence_tool()
        self.assertIn("Development", e["status"])
        json.dumps(e)


if __name__ == "__main__":
    unittest.main()
