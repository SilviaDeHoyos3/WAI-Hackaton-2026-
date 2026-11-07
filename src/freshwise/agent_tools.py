from .empirical import recommend_empirical_preparation


def preparation_recommendation(
    forecast,
    usable_stock,
    error_ratios,
    quantile,
):
    """Calculate a preparation plan using supplied calibration inputs."""
    result = recommend_empirical_preparation(
        forecast=forecast,
        inventory=usable_stock,
        error_ratios=error_ratios,
        quantile=quantile,
    )

    return {
        "forecast_orders": float(forecast),
        "usable_stock": int(usable_stock),
        "new_portions_to_prepare": result["prepare_qty"],
        "total_available": (
            int(usable_stock) + result["prepare_qty"]
        ),
        "target_supply": result["target_supply"],
        "quantile": result["quantile"],
        "calibration_sample_count": result["scenario_count"],
        "policy": "empirical_quantile",
        "manager_adjustment_applied": False,
        "assumptions": [
            "One order is treated as one portion.",
            "Usable stock has already been checked for expiry.",
            "Calibration inputs and policy settings are supplied by the application.",
        ],
    }
def manager_adjusted_recommendation(
    forecast,
    usable_stock,
    error_ratios,
    quantile,
    anchor,
    manager_estimate,
    opinion_weight,
):
    import math
    import numpy as np

    from .decision import adjust_demand_scenarios

    anchor_quantiles = {
        "low": 0.1,
        "central": 0.5,
        "high": 0.9,
    }
    if anchor not in anchor_quantiles:
        raise ValueError("Anchor must be low, central or high.")

    ratios = list(error_ratios)
    original = preparation_recommendation(
        forecast, usable_stock, ratios, quantile
    )

    scenarios = sorted(
        float(forecast) * float(ratio)
        for ratio in ratios
    )

    anchor_value = float(np.quantile(
        scenarios,
        anchor_quantiles[anchor],
        method="inverted_cdf",
    ))
    anchor_index = scenarios.index(anchor_value)

    adjustment = adjust_demand_scenarios(
        scenarios,
        anchor_index,
        manager_estimate,
        opinion_weight,
    )

    target = float(np.quantile(
        adjustment["updated_scenarios"],
        quantile,
        method="inverted_cdf",
    ))
    prepared = max(0, math.ceil(target - usable_stock))

    adjusted = {
        **original,
        "new_portions_to_prepare": prepared,
        "total_available": int(usable_stock) + prepared,
        "target_supply": target,
        "manager_adjustment_applied": True,
    }

    return {
        "original_plan": original,
        "adjusted_plan": adjusted,
        "manager_context": {
            "anchor": anchor,
            "anchor_value": anchor_value,
            "manager_estimate": float(manager_estimate),
            "opinion_weight": float(opinion_weight),
            "demand_shift": adjustment["adjustment"],
            "clipped_at_zero": adjustment["clipped"],
        },
        "adjustment_method": (
            "Shift all empirical demand scenarios by the weighted "
            "difference between the manager estimate and chosen anchor; "
            "clip negative demand at zero."
        ),
    }