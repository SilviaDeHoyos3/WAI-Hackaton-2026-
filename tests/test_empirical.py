import unittest
import numpy as np

from freshwise.empirical import recommend_empirical_preparation


class EmpiricalTests(unittest.TestCase):
    def test_empirical_preparation_example(self):
        result = recommend_empirical_preparation(
            forecast=200,
            inventory=40,
            error_ratios=[0.5, 0.8, 1.0, 1.1, 1.6],
            quantile=0.55,
        )

        self.assertEqual(result["prepare_qty"], 160)
        self.assertAlmostEqual(result["target_supply"], 200)
        self.assertEqual(result["scenario_count"], 5)

    def test_enough_inventory_requires_no_preparation(self):
        result = recommend_empirical_preparation(
            forecast=200,
            inventory=250,
            error_ratios=[0.5, 0.8, 1.0, 1.1, 1.6],
            quantile=0.55,
        )

        self.assertEqual(result["prepare_qty"], 0)
        self.assertAlmostEqual(result["target_supply"], 200)

    def test_preparation_rounds_up(self):
        result = recommend_empirical_preparation(
            forecast=100,
            inventory=20,
            error_ratios=[1.004],
            quantile=0.55,
        )

        self.assertAlmostEqual(result["target_supply"], 100.4)
        self.assertEqual(result["prepare_qty"], 81)

    def test_rejects_invalid_quantile(self):
        invalid_quantiles = [
            -0.1,
            1.1,
            float("nan"),
            "0.55",
            None,
            True,
        ]

        for quantile in invalid_quantiles:
            with self.subTest(quantile=quantile):
                with self.assertRaises(ValueError):
                    recommend_empirical_preparation(
                        200, 40, [0.8, 1.0, 1.2], quantile
                    )

    def test_rejects_invalid_error_samples(self):
        invalid_samples = [
            [],
            None,
            [-0.1, 1.0],
            [float("nan"), 1.0],
            [float("inf"), 1.0],
            ["1.0"],
            [True],
        ]

        for sample in invalid_samples:
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    recommend_empirical_preparation(
                        200, 40, sample, 0.55
                    )

    def test_accepts_numpy_sample_without_modifying_it(self):
        ratios = np.array([0.5, 0.8, 1.0, 1.1, 1.6])
        original_ratios = ratios.copy()

        result = recommend_empirical_preparation(
            forecast=np.float64(200),
            inventory=np.int64(40),
            error_ratios=ratios,
            quantile=np.float64(0.55),
        )

        self.assertEqual(result["prepare_qty"], 160)
        self.assertAlmostEqual(result["target_supply"], 200)

        np.testing.assert_array_equal(
            ratios, original_ratios
        )