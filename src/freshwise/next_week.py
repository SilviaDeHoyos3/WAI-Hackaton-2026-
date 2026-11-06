"""Next-week forecast rows for the FreshWise demo (owner: Silvia).

Produces the `forecast_rows` handoff table described in the team plan.
Demo IDs and the selection rule are documented in docs/scope.md.

Scenario range = MODEL uncertainty only. Manager contextual adjustments
(e.g. a local event) are applied later in the decision module, not here.
"""
import numpy as np
import pandas as pd

from .forecast import KEYS, predict

# Selected using weeks 1-115 only; see docs/scope.md.
DEMO_PAIRS = [(13, 2306), (13, 2444), (13, 1198), (13, 2664)]

# Default frozen on Nov 4 from development weeks 116-125 (WAPE 41.5% vs 42.9% for trailing4).
# "hgb" is available as an option; the team decides the default at the Nov 7 freeze.
METHOD = "last"

# Fallback range: hand-set sensitivity assumption, NOT calibrated.
SCENARIO_LOW = 0.8
SCENARIO_HIGH = 1.2

# Ranges: 10th / 90th percentile of actual/forecast, by forecast-size tier, calibrated on
# each method's OWN one-week-ahead errors for weeks 116-125 (all observed pairs).
# Coverage checked on weeks 126-135 (target 80%). Weeks 136-145 not used.
#   last: coverage 81.8% / 80.8% / 79.4%  (outputs/calibrate_range_by_tier.py)
#   hgb:  coverage 82.3% / 79.3% / 76.5%, overall 79.4%, demo 80% (model fit on weeks <= 115)
RANGE_TABLES = {
    "last": pd.DataFrame({
        "tier": [0, 1, 2],
        "lower_edge": [-np.inf, 69.0, 230.0],
        "upper_edge": [69.0, 230.0, np.inf],
        "low_mult": [0.481, 0.367, 0.395],
        "high_mult": [3.929, 1.978, 1.409],
    }),
    "hgb": pd.DataFrame({
        "tier": [0, 1, 2],
        "lower_edge": [-np.inf, 70.891, 214.849],
        "upper_edge": [70.891, 214.849, np.inf],
        "low_mult": [0.441, 0.521, 0.660],
        "high_mult": [2.023, 1.752, 1.471],
    }),
}
RANGE_TABLE = RANGE_TABLES["last"]  # backwards compatible name
RANGE_SOURCE = "empirical_p10_p90_by_size_weeks116_125"
CALIBRATION_LAST_WEEK = 125  # ranges are out-of-sample only for target weeks > 125


def forecast_rows(train, history_end_week, pairs=DEMO_PAIRS, method=METHOD):
    """Forecast orders for week history_end_week + 1, using only outcomes up to history_end_week.

    method: "last" or "trailing4" (raw train.csv rows are enough) or "hgb" (needs
    enriched rows from freshwise.data.enrich, including the target-week planning row
    with price and promotion values; requires scikit-learn).

    Returns one row per centre-meal pair with: center_id, meal_id, target_week,
    history_end_week, forecast_orders, method, volume_tier, scenario_low, scenario_high,
    range_source. The range is model uncertainty only; manager adjustments are applied
    later. Pairs that cannot be forecast with the requested method use the documented
    fallback and say so in `method`.
    """
    history = train[train["week"] <= history_end_week]
    if history.empty:
        raise ValueError("No history at or before history_end_week")
    future = pd.DataFrame(list(pairs), columns=KEYS)
    seen = future.set_index(KEYS).index.isin(history.set_index(KEYS).index)
    baseline = np.asarray(predict(history, future, "last" if method == "hgb" else method), dtype=float)
    if method == "hgb":
        from .supervised import next_week_forecast

        hgb = next_week_forecast(train, history_end_week, pairs)["forecast_orders"].to_numpy()
        use_hgb = ~np.isnan(hgb)
        prediction = np.where(use_hgb, hgb, baseline)
        labels = np.where(use_hgb, "hgb",
                          np.where(seen, "fallback_last_no_planning_row", "fallback_recent_meal_or_global_mean"))
    else:
        prediction = baseline
        labels = np.where(seen, method, "fallback_recent_meal_or_global_mean")
    if not np.isfinite(prediction).all() or (prediction < 0).any():
        raise ValueError("Forecasts must be finite and non-negative")
    rows = future.assign(
        target_week=history_end_week + 1,
        history_end_week=history_end_week,
        forecast_orders=prediction,
        method=labels,
    )
    table = RANGE_TABLES.get(method, RANGE_TABLES["last"])
    source = RANGE_SOURCE if method in RANGE_TABLES else RANGE_SOURCE + "_borrowed_from_last"
    if history_end_week + 1 <= CALIBRATION_LAST_WEEK:
        source = "in_sample_calibration_overlap"
    return apply_range(rows, table).assign(range_source=source)


def rolling_forecasts(train, first_target, last_target, method=METHOD, pairs=None):
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


def calibrate_range(rows, lower_q=0.10, upper_q=0.90):
    """Empirical range multipliers from past one-week-ahead errors.

    Uses the ratio actual / forecast, pooled across all rows with a positive forecast.
    Returns (low_mult, high_mult, n_rows). Pooled because each pair has only ~10 weeks.
    """
    usable = rows[rows["forecast_orders"] > 0]
    if usable.empty:
        raise ValueError("No rows with a positive forecast to calibrate on")
    ratio = usable["actual_orders"] / usable["forecast_orders"]
    return float(ratio.quantile(lower_q)), float(ratio.quantile(upper_q)), len(usable)


def coverage(rows, low_mult, high_mult):
    """Share of rows whose actual orders fall inside [forecast*low_mult, forecast*high_mult]."""
    low = rows["forecast_orders"] * low_mult
    high = rows["forecast_orders"] * high_mult
    inside = (rows["actual_orders"] >= low) & (rows["actual_orders"] <= high)
    return float(inside.mean())


def calibrate_range_by_tier(rows, n_tiers=3, lower_q=0.10, upper_q=0.90):
    """Empirical range multipliers per forecast-size tier.

    Tiers are quantile bins of forecast_orders (known at prediction time, so no leakage).
    Returns a table with columns: tier, lower_edge, upper_edge, low_mult, high_mult, rows.
    The first lower_edge and last upper_edge are open (-inf / +inf).
    """
    usable = rows[rows["forecast_orders"] > 0]
    if usable.empty:
        raise ValueError("No rows with a positive forecast to calibrate on")
    inner = usable["forecast_orders"].quantile(np.linspace(0, 1, n_tiers + 1)[1:-1]).to_numpy()
    edges = np.concatenate([[-np.inf], inner, [np.inf]])
    tier = np.searchsorted(edges[1:-1], usable["forecast_orders"].to_numpy(), side="right")
    ratio = (usable["actual_orders"] / usable["forecast_orders"]).to_numpy()
    records = []
    for t in range(n_tiers):
        r = ratio[tier == t]
        records.append({"tier": t, "lower_edge": edges[t], "upper_edge": edges[t + 1],
                        "low_mult": float(np.quantile(r, lower_q)),
                        "high_mult": float(np.quantile(r, upper_q)), "rows": int(len(r))})
    return pd.DataFrame(records)


def apply_range(rows, table):
    """Add scenario_low / scenario_high using the tier table from calibrate_range_by_tier."""
    inner = table["lower_edge"].to_numpy()[1:]
    tier = np.searchsorted(inner, rows["forecast_orders"].to_numpy(), side="right")
    low = table["low_mult"].to_numpy()[tier]
    high = table["high_mult"].to_numpy()[tier]
    return rows.assign(volume_tier=tier,
                       scenario_low=rows["forecast_orders"].to_numpy() * low,
                       scenario_high=rows["forecast_orders"].to_numpy() * high)
