"""Fast, exactly equivalent version of Ari's calibrated empirical rule.

make_calibrated_empirical_rule (preparation_rules.py) recomputes the inverted-CDF
quantile of forecast * ratios on every call (~11k ratios, validated in a Python loop).
For forecast >= 0, that quantile equals forecast * quantile(ratios): scaling by a
non-negative number keeps the order, and inverted_cdf returns an actual sample
element, so the product is computed identically. We therefore compute one
multiplier per (method, window, size group) and quantile, once.

Equivalence with Ari's rule is checked in tests/test_fast_rules.py and again on
real rows at the start of scripts/evaluate_carryover.py.
"""
import math

import numpy as np

from .empirical_calibration import size_group


def make_fast_calibrated_empirical_rule(ratio_lookup, quantile):
    if not 0 <= quantile <= 1:
        raise ValueError("Quantile must be between 0 and 1.")
    multipliers = {}
    for key, ratios in ratio_lookup.items():
        r = np.asarray(ratios, dtype=float)
        if r.size == 0 or not np.isfinite(r).all() or (r < 0).any():
            raise ValueError(f"Invalid calibration ratios for {key}")
        multipliers[key] = float(np.quantile(r, quantile, method="inverted_cdf"))

    def prepare(forecast, leftovers, context):
        if not math.isfinite(forecast) or forecast < 0:
            raise ValueError("Forecast must be finite and non-negative.")
        if leftovers < 0 or leftovers % 1 != 0:
            raise ValueError("Inventory must contain whole portions.")
        key = (context["method"], context["window"], size_group(forecast))
        if key not in multipliers:
            raise ValueError(f"Missing calibration ratios for {key}")
        target_supply = float(forecast) * multipliers[key]
        return max(0, math.ceil(target_supply - leftovers))

    return prepare
