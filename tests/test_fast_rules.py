import unittest

import numpy as np

from freshwise.fast_rules import make_fast_calibrated_empirical_rule
from freshwise.preparation_rules import make_calibrated_empirical_rule


class FastRuleTests(unittest.TestCase):
    def test_identical_to_aris_rule(self):
        rng = np.random.default_rng(0)
        lookup = {(m, w, g): rng.lognormal(0, 0.5, 2000)
                  for m in ("last", "hgb") for w in ("A", "B") for g in range(3)}
        for q in (0.55, 5 / 7, 0.0, 1.0):
            slow = make_calibrated_empirical_rule(lookup, q)
            fast = make_fast_calibrated_empirical_rule(lookup, q)
            for _ in range(500):
                f = float(rng.choice([0.0, rng.uniform(0, 3000)]))
                left = int(rng.integers(0, 300))
                ctx = {"method": str(rng.choice(["last", "hgb"])), "window": str(rng.choice(["A", "B"]))}
                self.assertEqual(fast(f, left, ctx), slow(f, left, ctx))

    def test_rejects_bad_inputs(self):
        lookup = {("last", "A", g): np.array([1.0, 2.0]) for g in range(3)}
        fast = make_fast_calibrated_empirical_rule(lookup, 0.55)
        ctx = {"method": "last", "window": "A"}
        for f, left in ((-1.0, 0), (10.0, -1), (10.0, 2.5), (float("nan"), 0)):
            with self.assertRaises(ValueError):
                fast(f, left, ctx)
        with self.assertRaises(ValueError):
            fast(10.0, 0, {"method": "hgb", "window": "A"})
        with self.assertRaises(ValueError):
            make_fast_calibrated_empirical_rule(lookup, 1.5)


if __name__ == "__main__":
    unittest.main()
