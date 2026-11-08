"""Data tools for the FreshWise assistant (owner: Silvia).

The assistant calls these tools; it never invents menus, forecasts or ranges.
They feed Ari's decision tools (freshwise.agent_tools):

    menu_tool(center_id)                       -> the centre's meals (from the data)
    forecast_tool(center_id, meal_id)          -> next-week forecast + range + provenance
    evidence_tool()                            -> development results the assistant may quote

All outputs are plain JSON-serialisable dicts. Load the data once with
build_context() (or context_from_tables() in tests) and pass it to each call.

Default "next week" = the week after the last observed week in train.csv (week 146),
using the planning-time prices/promotions for that week from test.csv. This is a live
forecast, not an evaluation: no accuracy is computed for it.
"""

import numpy as np
import pandas as pd

from .data import enrich, load_data
from .next_week import forecast_rows

DEFAULT_METHOD = "hgb"
ASSUMPTIONS = [
    "Forecasts are observed weekly orders, not guaranteed demand.",
    "The range is model uncertainty only (about 80% of past outcomes fell inside it); "
    "manager context is applied separately by the decision tools.",
    "hgb assumes next week's prices and promotions are known when planning.",
    "Meal names and recipes are not in the data; meals are identified by ID, category and cuisine.",
]

class AgentContext:
    """Loaded data shared by the tools. Build once per app session."""

    def __init__(self, train, test, meals, centers):
        self.meals = meals
        self.centers = centers
        self.last_week = int(train["week"].max())
        enriched_train = enrich(train, meals, centers)
        frames = [enriched_train]
        if test is not None and len(test):
            future = test[test["week"] > self.last_week]  # planning rows only, never past weeks
            if len(future):
                frames.append(enrich(future.assign(num_orders=np.nan), meals, centers))
        self.data = pd.concat(frames, ignore_index=True)
        self._cache = {}

def build_context(path=None):
    tables = load_data(path)
    return context_from_tables(tables["train.csv"], tables["test.csv"],
                               tables["meal_info.csv"], tables["fulfilment_center_info.csv"])

def context_from_tables(train, test, meals, centers):
    return AgentContext(train, test, meals, centers)

def _observed(ctx, history_end_week):
    d = ctx.data
    return d[(d["week"] <= history_end_week) & d["num_orders"].notna()]

def menu_tool(center_id, context, history_end_week=None):
    """Meals the centre has sold, with category and cuisine (no invented names)."""
    h = context.last_week if history_end_week is None else int(history_end_week)
    obs = _observed(context, h)
    centre = context.centers[context.centers["center_id"] == center_id]
    if centre.empty:
        return {"error": f"Unknown center_id {center_id}. Ask the manager to choose a listed centre."}
    sold = obs[obs["center_id"] == center_id]
    stats = sold.groupby("meal_id").agg(
        weeks_observed=("week", "nunique"),
        last_observed_week=("week", "max"),
        recent_mean_orders=("num_orders", lambda s: s.tail(4).mean()),
    ).reset_index().merge(context.meals, on="meal_id", how="left")
    c = centre.iloc[0]
    return {
        "center_id": int(center_id),
        "center_type": str(c["center_type"]),
        "city_code": int(c["city_code"]),
        "region_code": int(c["region_code"]),
        "op_area": float(c["op_area"]),
        "history_end_week": h,
        "meals": [
            {"meal_id": int(r.meal_id), "category": str(r.category), "cuisine": str(r.cuisine),
             "weeks_observed": int(r.weeks_observed), "last_observed_week": int(r.last_observed_week),
             "recent_mean_orders": round(float(r.recent_mean_orders), 1)}
            for r in stats.sort_values("meal_id").itertuples()
        ],
        "source": "train.csv + meal_info.csv + fulfilment_center_info.csv",
        "notes": ["Meals are identified by ID, category and cuisine; dish names are not in the data."],
    }

def _centre_forecasts(context, center_id, history_end_week, method):
    key = (int(center_id), int(history_end_week), method)
    if key not in context._cache:
        obs = _observed(context, history_end_week)
        meals = sorted(obs.loc[obs["center_id"] == center_id, "meal_id"].unique())
        pairs = [(int(center_id), int(m)) for m in meals]
        data = context.data[context.data["week"] <= history_end_week + 1]
        context._cache[key] = forecast_rows(data, history_end_week, pairs, method=method)
    return context._cache[key]

def forecast_tool(center_id, meal_id, context, history_end_week=None, method=DEFAULT_METHOD):
    """Next-week forecast with its range and provenance for one meal at one centre."""
    h = context.last_week if history_end_week is None else int(history_end_week)
    if (context.centers["center_id"] == center_id).sum() == 0:
        return {"error": f"Unknown center_id {center_id}."}
    rows = _centre_forecasts(context, center_id, h, method)
    row = rows[rows["meal_id"] == meal_id]
    if row.empty:
        return {"error": f"Meal {meal_id} has no sales history at centre {center_id} up to week {h}. "
                         "Use menu_tool to list available meals."}
    r = row.iloc[0]
    obs = _observed(context, h)
    recent = obs[(obs["center_id"] == center_id) & (obs["meal_id"] == meal_id)].sort_values("week").tail(4)
    return {
        "center_id": int(center_id),
        "meal_id": int(meal_id),
        "target_week": int(r["target_week"]),
        "history_end_week": int(r["history_end_week"]),
        "forecast_orders": round(float(r["forecast_orders"]), 1),
        "range_low": round(float(r["scenario_low"]), 1),
        "range_high": round(float(r["scenario_high"]), 1),
        "method": str(r["method"]),
        "range_source": str(r["range_source"]),
        "recent_orders": [{"week": int(w), "orders": int(o)}
                          for w, o in zip(recent["week"], recent["num_orders"])],
        "provenance": "freshwise.next_week.forecast_rows; hgb model refit on all weeks <= history_end_week",
        "assumptions": ASSUMPTIONS,
    }

def evidence_tool():
    """Development results the assistant may quote, with their labels. Not final-test results."""
    return {
        "status": "Development results (weeks 106-115 and 126-135). Final test on weeks 136-145 pending.",
        "setup": "Simulated from observed orders; start stock 0; leftovers used first; "
                 "1-week shelf life (assumption); overage 2 / underage 5.",
        "demo_meals_centre_13": {
            "today_last_no_carryover": {"waste": "20.9% / 14.4%", "unmet": "24.7% / 14.8%"},
            "default_hgb_forecast_minus_leftovers": {"waste": "4.7% / 0.1%", "unmet": "17.4% / 5.7%"},
            "fewer_shortages_hgb_q5_7": {"waste": "8.4% / 1.5%", "unmet": "8.2% / 1.6%"},
        },
        "all_meals": {
            "today_last_no_carryover": {"waste": "21.9% / 22.5%", "unmet": "21.1% / 22.8%"},
            "default_hgb_forecast_minus_leftovers": {"waste": "3.8% / 2.8%", "unmet": "13.8% / 19.8%"},
        },
        "waste_definition": "Expired plus end-of-horizon usable stock, divided by portions prepared.",
        "limits": [
            "Simulated outcomes, not measured food waste.",
            "Depends on the one-week shelf-life assumption.",
            "Manager adjustments were not part of the evaluated results.",
        ],
        "source": "docs/FRESHWISE_FORECASTING_STORY.md section 4.4",
    }
