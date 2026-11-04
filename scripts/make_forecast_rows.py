"""Build the week-116 forecast example for Ari and Lan. Output stays in outputs/ (not committed)."""
import os

import pandas as pd

from freshwise.next_week import forecast_rows

train = pd.read_csv(os.path.join(os.environ["FRESHWISE_DATA_DIR"], "train.csv"))
rows = forecast_rows(train, 115)
rows.to_csv("outputs/forecast_rows_week116.csv", index=False)
print(rows.round(1).to_string(index=False))
