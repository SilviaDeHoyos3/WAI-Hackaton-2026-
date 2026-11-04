import math
import numpy as np

from .decision import (
    _validate_nonnegative_number,
    _validate_inventory,
)


def recommend_empirical_preparation(
    forecast,
    inventory,
    error_ratios,
    quantile,
):
    _validate_nonnegative_number(forecast, "Forecast")
    _validate_inventory(inventory)
    _validate_nonnegative_number(quantile, "Quantile")

    if quantile > 1:
        raise ValueError("Quantile must be between 0 and 1.")

    try:
        ratios = list(error_ratios)
    except TypeError:
        raise ValueError(
            "Error ratios must be an iterable of numbers."
        ) from None

    if not ratios:
        raise ValueError("Provide at least one error ratio.")

    for ratio in ratios:
        _validate_nonnegative_number(ratio, "Error ratio")

    demand_scenarios = (
        float(forecast) * np.asarray(ratios, dtype=float)
    )

    if not np.isfinite(demand_scenarios).all():
        raise ValueError("Generated demand must be finite.")

    target_supply = float(
        np.quantile(
            demand_scenarios,
            quantile,
            method="inverted_cdf",
        )
    )

    prepare_qty = max(
        0,
        math.ceil(target_supply - inventory),
    )

    return {
        "prepare_qty": prepare_qty,
        "target_supply": target_supply,
        "quantile": float(quantile),
        "scenario_count": len(ratios),
    }