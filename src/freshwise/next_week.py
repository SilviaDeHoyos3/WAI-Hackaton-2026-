"""Next-week forecast rows for the FreshWise demo (owner: Silvia).

Produces the `forecast_rows` handoff table described in the team plan.
Demo IDs and the selection rule are documented in docs/scope.md.
"""
import numpy as np
import pandas as pd

from .forecast import KEYS, predict

# Selected using weeks 1-115 only; see docs/scope.md.
DEMO_PAIRS = [(13, 2306), (13, 2444), (13, 1198), (13, 2664)]

# Labelled sensitivity assumptions, NOT a calibrated confidence interval.
SCENARIO_LOW = 0.8
SCENARIO_HIGH = 1.2


def forecast_rows(train, history_end_week, pairs=DEMO_PAIRS, method="trailing4"):
    """Forecast orders for week history_end_week + 1, using only rows up to history_end_week.

    Returns one row per centre-meal pair with: center_id, meal_id, target_week,
    history_end_week, forecast_orders, method, scenario_low, scenario_high.
    Pairs with no history are forecast with the documented fallback and labelled as such.
    """
    history = train[train["week"] <= history_end_week]
    if history.empty:
        raise ValueError("No history at or before history_end_week")
    future = pd.DataFrame(list(pairs), columns=KEYS)
    prediction = np.asarray(predict(history, future, method), dtype=float)
    if not np.isfinite(prediction).all() or (prediction < 0).any():
        raise ValueError("Forecasts must be finite and non-negative")
    seen = future.set_index(KEYS).index.isin(history.set_index(KEYS).index)
    return future.assign(
        target_week=history_end_week + 1,
        history_end_week=history_end_week,
        forecast_orders=prediction,
        method=np.where(seen, method, "fallback_recent_meal_or_global_mean"),
        scenario_low=prediction * SCENARIO_LOW,
        scenario_high=prediction * SCENARIO_HIGH,
    )
