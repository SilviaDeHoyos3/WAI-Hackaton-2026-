"""Development evaluation: one-week-ahead forecasts for weeks 116-125 (not the final weeks).

Outputs stay in outputs/ (not committed):
- dev_eval_summary.csv : MAE / WAPE per method, all pairs and demo pairs
- dev_eval_demo_rows.csv : per-row forecasts + actual orders for the demo pairs (for Ari)
"""
import os

import pandas as pd

from freshwise.next_week import DEMO_PAIRS, error_summary, rolling_forecasts

train = pd.read_csv(os.path.join(os.environ["FRESHWISE_DATA_DIR"], "train.csv"))
METHODS = ("last", "trailing4")

all_rows = pd.concat([rolling_forecasts(train, 116, 125, m) for m in METHODS], ignore_index=True)
demo_rows = all_rows.merge(pd.DataFrame(DEMO_PAIRS, columns=["center_id", "meal_id"]))

summary = pd.concat([
    error_summary(all_rows).assign(population="all observed pairs"),
    error_summary(demo_rows).assign(population="demo pairs"),
], ignore_index=True)
per_meal = error_summary(demo_rows, by=("meal_id", "method"))

summary.to_csv("outputs/dev_eval_summary.csv", index=False)
demo_rows.to_csv("outputs/dev_eval_demo_rows.csv", index=False)

print("Weeks 116-125, one-week-ahead, observed rows only\n")
print(summary.round(3).to_string(index=False))
print("\nDemo pairs, per meal:\n")
print(per_meal.round(3).to_string(index=False))
