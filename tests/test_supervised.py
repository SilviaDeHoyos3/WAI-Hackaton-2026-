import unittest

import numpy as np
import pandas as pd

try:
    import sklearn  # noqa: F401
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False

from freshwise.next_week import forecast_rows
from freshwise.supervised import build_features, fit_predict_block, next_week_forecast


def synthetic(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for c in (1, 2, 3):
        for m in (10, 11, 12):
            mu = rng.uniform(50, 500)
            for w in range(1, 41):
                if w % 7 == 0 and m == 12:
                    continue  # gappy history, not zero-filled
                promo = int(rng.random() < 0.2)
                rows.append({"week": w, "center_id": c, "meal_id": m,
                             "checkout_price": 200 * (0.8 if promo else 1), "base_price": 200,
                             "emailer_for_promotion": promo, "homepage_featured": 0,
                             "num_orders": int(mu * (2 if promo else 1) + rng.integers(0, 20)),
                             "category": "A", "cuisine": "X", "center_type": "T1",
                             "city_code": c, "region_code": 1, "op_area": 3.0})
    return pd.DataFrame(rows)


@unittest.skipUnless(HAVE_SKLEARN, "scikit-learn not installed")
class SupervisedTests(unittest.TestCase):
    def test_future_outcomes_never_used(self):
        data = synthetic()
        base = fit_predict_block(build_features(data), 30, 31, 31)
        changed = data.copy()
        changed.loc[changed.week >= 31, "num_orders"] = 10**7
        again = fit_predict_block(build_features(changed), 30, 31, 31)
        np.testing.assert_allclose(base.forecast_orders, again.forecast_orders)

    def test_shuffled_rows_keep_keys(self):
        data = synthetic()
        keys = ["center_id", "meal_id"]
        a = fit_predict_block(build_features(data), 30, 31, 31).sort_values(keys)
        b = fit_predict_block(build_features(data.sample(frac=1, random_state=1)), 30, 31, 31).sort_values(keys)
        np.testing.assert_allclose(a.forecast_orders.to_numpy(), b.forecast_orders.to_numpy())

    def test_outputs_finite_nonnegative_and_keyed(self):
        out = fit_predict_block(build_features(synthetic()), 30, 31, 35)
        self.assertTrue(np.isfinite(out.forecast_orders).all())
        self.assertTrue((out.forecast_orders >= 0).all())
        self.assertTrue((out.history_end_week == out.target_week - 1).all())
        self.assertFalse(out.duplicated(["center_id", "meal_id", "target_week"]).any())

    def test_duplicate_rows_rejected(self):
        data = synthetic()
        with self.assertRaises(ValueError):
            build_features(pd.concat([data, data.head(1)]))

    def test_next_week_ignores_the_outcome_being_predicted(self):
        data = synthetic()
        pairs = [(1, 10), (2, 11)]
        a = next_week_forecast(data, 30, pairs)
        changed = data.copy()
        changed.loc[changed.week >= 31, "num_orders"] = 10**7
        b = next_week_forecast(changed, 30, pairs)
        np.testing.assert_allclose(a.forecast_orders, b.forecast_orders)

    def test_forecast_rows_hgb_keeps_the_interface(self):
        data = synthetic()
        pairs = [(1, 10), (3, 12), (9, 99)]
        hgb = forecast_rows(data, 30, pairs, method="hgb")
        last = forecast_rows(data, 30, pairs, method="last")
        self.assertEqual(list(hgb.columns), list(last.columns))
        self.assertEqual(hgb.method.tolist()[:2], ["hgb", "hgb"])
        self.assertEqual(hgb.method.tolist()[2], "fallback_recent_meal_or_global_mean")
        self.assertTrue((hgb.scenario_low <= hgb.forecast_orders).all())
        self.assertTrue((hgb.forecast_orders <= hgb.scenario_high).all())
        self.assertTrue((hgb.range_source == "in_sample_calibration_overlap").all())

    def test_hgb_needs_enriched_data(self):
        data = synthetic().drop(columns=["category"])
        with self.assertRaises(ValueError):
            next_week_forecast(data, 30, [(1, 10)])


if __name__ == "__main__":
    unittest.main()
