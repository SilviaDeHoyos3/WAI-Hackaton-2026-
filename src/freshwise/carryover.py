"""Shelf-life-aware preparation simulator ("use leftovers first"). Owner: Silvia.

Shared by every preparation rule so results are directly comparable
(see docs/FRESHWISE_FORECASTING_STORY.md, section 6.1).

Stock rules
- Each week: leftovers_in = usable stock carried from earlier weeks.
- prepare_fn(forecast, leftovers, context) returns the new portions to prepare (int >= 0).
- Sales use the oldest stock first (FIFO).
- After the week, stock ages by the number of weeks until the next observed row.
  Stock older than `shelf_life_weeks` expires and counts as waste (`expired`).
  shelf_life_weeks=0 means no carry-over (everything left at week end is waste).
- Stock still on hand after the last row of a group is counted as waste on that
  last row (conservative end-of-horizon rule).

Assumptions (simulated, not observed): one order = one portion; observed orders are
treated as demand; shelf life is an operational assumption, not data.
"""
import math

import numpy as np
import pandas as pd

KEYS = ["center_id", "meal_id"]
REQUIRED = KEYS + ["target_week", "forecast_orders", "actual_orders"]
OUTPUT = ["leftovers_in", "prepared", "supply", "sold", "unmet", "expired"]


def prepare_forecast_minus_leftovers(forecast, leftovers, context=None):
    """Rule (a): prepare what the forecast says is missing after leftovers."""
    return max(0, math.ceil(forecast - leftovers))


def _group_columns(rows):
    return [c for c in ("window", "method") if c in rows.columns] + KEYS


def simulate_carryover(rows, prepare_fn, shelf_life_weeks=1, start_stock=0):
    """Simulate carry-over week by week for every (window, method, centre, meal) group.

    Returns a copy of `rows` sorted by group and week, with columns
    leftovers_in, prepared, supply, sold, unmet, expired.
    """
    missing = [c for c in REQUIRED if c not in rows.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if shelf_life_weeks < 0 or start_stock < 0:
        raise ValueError("shelf_life_weeks and start_stock must be >= 0")
    groups = _group_columns(rows)
    if rows.duplicated(groups + ["target_week"]).any():
        raise ValueError("Duplicate rows for the same group and target week")
    if (rows["actual_orders"] < 0).any() or not np.isfinite(rows["forecast_orders"]).all():
        raise ValueError("Actual orders must be >= 0 and forecasts finite")

    data = rows.sort_values(groups + ["target_week"]).reset_index(drop=True)
    out = {c: np.zeros(len(data), dtype=np.int64) for c in OUTPUT}
    weeks = data["target_week"].to_numpy()
    forecasts = data["forecast_orders"].to_numpy(dtype=float)
    actuals = data["actual_orders"].to_numpy()
    records = data.to_dict("records")

    for idx in data.groupby(groups, sort=False).indices.values():
        stock = [[0, int(start_stock)]] if start_stock else []  # [age, qty], oldest first
        for pos, i in enumerate(idx):
            leftovers = sum(q for _, q in stock)
            context = records[i]
            prep = prepare_fn(float(forecasts[i]), leftovers, context)
            if not isinstance(prep, (int, np.integer)) or prep < 0:
                raise ValueError(f"prepare_fn must return an int >= 0, got {prep!r}")
            stock.append([0, int(prep)])
            demand = int(actuals[i])
            sold = 0
            for batch in stock:  # FIFO
                take = min(batch[1], demand - sold)
                batch[1] -= take
                sold += take
            stock = [b for b in stock if b[1] > 0]
            if pos + 1 < len(idx):
                gap = int(weeks[idx[pos + 1]] - weeks[i])
                for b in stock:
                    b[0] += gap
                expired = sum(q for a, q in stock if a > shelf_life_weeks)
                stock = [b for b in stock if b[0] <= shelf_life_weeks]
            else:
                expired = sum(q for _, q in stock)  # end of horizon
                stock = []
            out["leftovers_in"][i] = leftovers
            out["prepared"][i] = prep
            out["supply"][i] = leftovers + prep
            out["sold"][i] = sold
            out["unmet"][i] = demand - sold
            out["expired"][i] = expired
    return data.assign(**out)


def summarize(results, by=("method",), overage=2, underage=5):
    """Waste rate, unmet rate and penalty per group.

    waste rate = expired / prepared portions; unmet rate = unmet / actual orders;
    penalty = overage * expired + underage * unmet.
    """
    g = results.groupby(list(by))
    s = pd.DataFrame({
        "rows": g.size(),
        "actual": g["actual_orders"].sum(),
        "prepared": g["prepared"].sum(),
        "expired": g["expired"].sum(),
        "unmet": g["unmet"].sum(),
    })
    s["waste_rate"] = s["expired"] / s["prepared"].where(s["prepared"] > 0)
    s["unmet_rate"] = s["unmet"] / s["actual"].where(s["actual"] > 0)
    s["penalty"] = overage * s["expired"] + underage * s["unmet"]
    return s.reset_index()
