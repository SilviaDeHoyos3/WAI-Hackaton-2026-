"""Supervised next-week forecast candidate (owner: Silvia). EXPERIMENTAL.

One pooled HistGradientBoostingRegressor on log1p(num_orders), fixed hyperparameters.

Leakage rules:
- Demand features use only EARLIER observed rows of the same centre-meal pair
  (shift before rolling). Missing weeks are never filled with zero.
- Target-week price / promotion columns are used only when plan_features=True,
  under the explicit assumption that they are known at planning time.
- The model for a block is fit only on rows with week <= fit_end.
"""
import numpy as np
import pandas as pd

KEYS = ["center_id", "meal_id"]
CATEGORICAL = ["center_id", "meal_id", "category", "cuisine", "center_type",
               "city_code", "region_code"]
DEMAND_FEATURES = ["lag1", "lag2", "weeks_since_lag1", "mean4", "mean8", "std8",
                   "history_len", "meal_mean_prev_week", "op_area"]
PLAN_FEATURES = ["checkout_price", "base_price", "discount", "price_vs_last",
                 "emailer_for_promotion", "homepage_featured"]
PARAMS = dict(learning_rate=0.05, max_iter=300, max_leaf_nodes=63, random_state=0)


def build_features(enriched):
    """Feature table: one row per observed (centre, meal, week). Past-only demand features."""
    if enriched.duplicated(KEYS + ["week"]).any():
        raise ValueError("Duplicate centre-meal-week rows")
    df = enriched.sort_values(KEYS + ["week"]).reset_index(drop=True)
    g = df.groupby(KEYS, sort=False)
    past = g["num_orders"].shift(1)
    df["lag1"] = past
    df["lag2"] = g["num_orders"].shift(2)
    df["weeks_since_lag1"] = df["week"] - g["week"].shift(1)
    df["mean4"] = past.groupby([df[k] for k in KEYS]).transform(lambda s: s.rolling(4, min_periods=1).mean())
    df["mean8"] = past.groupby([df[k] for k in KEYS]).transform(lambda s: s.rolling(8, min_periods=1).mean())
    df["std8"] = past.groupby([df[k] for k in KEYS]).transform(lambda s: s.rolling(8, min_periods=2).std())
    df["history_len"] = g.cumcount()
    meal_week = df.groupby(["meal_id", "week"])["num_orders"].mean().rename("meal_mean_prev_week").reset_index()
    meal_week["week"] += 1  # value from week t-1 attached to week t
    df = df.merge(meal_week, on=["meal_id", "week"], how="left")
    df["discount"] = (df["base_price"] - df["checkout_price"]) / df["base_price"]
    df["price_vs_last"] = df["checkout_price"] / df.groupby(KEYS)["checkout_price"].shift(1)
    for col in ["category", "cuisine", "center_type"]:
        df[col] = df[col].astype("category").cat.codes
    return df


def _columns(plan_features):
    return CATEGORICAL + DEMAND_FEATURES + (PLAN_FEATURES if plan_features else [])


def _fit(train, plan_features=True):
    from sklearn.ensemble import HistGradientBoostingRegressor

    cols = _columns(plan_features)
    model = HistGradientBoostingRegressor(
        categorical_features=[c in CATEGORICAL for c in cols], **PARAMS)
    model.fit(train[cols], np.log1p(train["num_orders"]))
    return model, cols


def _predict(model, cols, rows):
    return np.clip(np.expm1(model.predict(rows[cols])), 0, None)


def fit_predict_block(features, fit_end, first_target, last_target, plan_features=True):
    """Fit on weeks <= fit_end, predict observed rows in [first_target, last_target].

    Lags for later target weeks use actual outcomes of completed weeks (rolling origin
    for features; model refit only at fit_end).
    """
    train = features[features["week"] <= fit_end]
    test = features[(features["week"] >= first_target) & (features["week"] <= last_target)]
    model, cols = _fit(train, plan_features)
    return test[KEYS].reset_index(drop=True).assign(
        target_week=test["week"].to_numpy(),
        history_end_week=test["week"].to_numpy() - 1,
        model_fit_end=fit_end,
        method="hgb" if plan_features else "hgb_no_plan",
        forecast_orders=_predict(model, cols, test),
        actual_orders=test["num_orders"].to_numpy(),
    )


def next_week_forecast(enriched, history_end_week, pairs):
    """hgb forecast for week history_end_week + 1 for the given (center_id, meal_id) pairs.

    `enriched` = train.csv rows joined with meal_info and fulfilment_center_info
    (freshwise.data.enrich). The target-week row supplies the planning-time price and
    promotion values; its num_orders is masked before features are built, so the
    outcome being predicted is never used. Returns one row per pair with
    forecast_orders = NaN where the target-week planning row does not exist.
    """
    needed = {"category", "cuisine", "center_type", "city_code", "region_code", "op_area"}
    if not needed.issubset(enriched.columns):
        raise ValueError("hgb needs enriched data: use freshwise.data.enrich(train, meals, centers)")
    target = history_end_week + 1
    data = enriched[enriched["week"] <= target].copy()
    data.loc[data["week"] == target, "num_orders"] = np.nan
    features = build_features(data)
    model, cols = _fit(features[features["week"] <= history_end_week])
    wanted = pd.DataFrame(list(pairs), columns=KEYS)
    rows = wanted.merge(features[features["week"] == target], on=KEYS, how="left")
    prediction = np.full(len(rows), np.nan)
    has_row = rows["week"].notna().to_numpy()
    if has_row.any():
        prediction[has_row] = _predict(model, cols, rows[has_row])
    return wanted.assign(forecast_orders=prediction)
