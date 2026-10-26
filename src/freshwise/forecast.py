import numpy as np
import pandas as pd

KEYS = ["center_id", "meal_id"]

def predict(history, future, method="trailing4"):
    """Fixed-origin forecast. Trailing means use last observed rows, not zero-filled weeks.

    Future num_orders is never read. Unseen pairs fall back to recent meal means,
    then the recent global mean. No recursive access to held-out outcomes.
    """
    if method not in ("last", "trailing4"):
        raise ValueError("method must be last or trailing4")
    if history.empty:
        raise ValueError("History must not be empty")
    ordered = history.sort_values("week")
    recent = ordered[ordered.week > ordered.week.max() - 4]
    counts = 1 if method == "last" else 4
    pair = ordered.groupby(KEYS).tail(counts).groupby(KEYS).num_orders.mean()
    result = future[KEYS].join(pair.rename("prediction"), on=KEYS)
    fallback = result.meal_id.map(recent.groupby("meal_id").num_orders.mean())
    return result.prediction.fillna(fallback).fillna(recent.num_orders.mean()).to_numpy()

def backtest(train, cutoffs=(115, 125, 135), horizon=10):
    records = []
    for cutoff in cutoffs:
        history = train[train.week <= cutoff]
        heldout = train[(train.week > cutoff) & (train.week <= cutoff + horizon)]
        if heldout.empty or heldout.week.max() != cutoff + horizon:
            raise ValueError("Holdout does not cover requested horizon")
        for method in ("last", "trailing4"):
            y = heldout.num_orders.to_numpy()
            prediction = predict(history, heldout, method)
            records.append({"cutoff": cutoff, "horizon": horizon, "method": method,
                "rows": len(y), "mae": np.abs(y-prediction).mean(),
                "wape": np.abs(y-prediction).sum()/y.sum(),
                "rmsle": np.sqrt(np.mean((np.log1p(y)-np.log1p(prediction))**2))})
    return pd.DataFrame(records)
