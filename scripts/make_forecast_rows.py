"""Next-week forecast example for Ari and Lan: week 126 (history to 125), last and hgb.

Week 126 is the first target week whose range is out-of-sample (ranges are calibrated on
weeks 116-125). Output stays in outputs/ (not committed). hgb training takes ~1 minute.
"""
import pandas as pd

from freshwise.data import enrich, load_data
from freshwise.next_week import forecast_rows

tables = load_data()
data = enrich(tables["train.csv"], tables["meal_info.csv"], tables["fulfilment_center_info.csv"])
rows = pd.concat([forecast_rows(data, 125, method=m) for m in ("last", "hgb")], ignore_index=True)
rows.to_csv("outputs/forecast_rows_week126.csv", index=False)
print(rows.round(1).to_string(index=False))
