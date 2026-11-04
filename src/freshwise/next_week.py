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


def rolling_forecasts(train, first_target, last_target, method="trailing4", pairs=None):
    """One-week-ahead forecasts for each target week from first_target to last_target.

    For target week t, only rows with week < t are used as history. Rows are produced
    only where an observed outcome exists in week t (missing rows are not treated as zero).
    Returns forecast rows plus `actual_orders` for evaluation.
    """
    pair_filter = pd.DataFrame(list(pairs), columns=KEYS) if pairs is not None else None
    frames = []
    for target in range(first_target, last_target + 1):
        actual = train[train["week"] == target]
        if pair_filter is not None:
            actual = actual.merge(pair_filter, on=KEYS)
        if actual.empty:
            continue
        history = train[train["week"] < target]
        prediction = np.asarray(predict(history, actual, method), dtype=float)
        frames.append(actual[KEYS].reset_index(drop=True).assign(
            target_week=target,
            history_end_week=target - 1,
            method=method,
            forecast_orders=prediction,
            actual_orders=actual["num_orders"].to_numpy(),
        ))
    if not frames:
        raise ValueError("No observed rows in the requested target weeks")
    return pd.concat(frames, ignore_index=True)


def error_summary(rows, by=("method",)):
    """MAE and WAPE per group. WAPE = total absolute error / total actual orders."""
    def summarise(group):
        abs_error = (group["actual_orders"] - group["forecast_orders"]).abs()
        total_actual = group["actual_orders"].sum()
        return pd.Series({
            "rows": len(group),
            "mae": abs_error.mean(),
            "wape": abs_error.sum() / total_actual if total_actual > 0 else np.nan,
        })
    return rows.groupby(list(by)).apply(summarise).reset_index()
