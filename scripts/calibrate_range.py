"""Build the low/high scenario range from real past forecast errors.

- Calibrate on weeks 116-125 (one-week-ahead errors of the frozen method).
- Check coverage separately on weeks 126-135 (not used for calibration).
- Weeks 136-145 are NOT touched (final evaluation on Nov 9).

Outputs (in outputs/, not committed):
- range_calibration.csv : multipliers + coverage
- demo_decision_inputs.csv : demo rows with forecast, low, high, actual (for Ari's decision evaluation)
"""
import os

import pandas as pd

from freshwise.next_week import DEMO_PAIRS, METHOD, calibrate_range, coverage, rolling_forecasts

train = pd.read_csv(os.path.join(os.environ["FRESHWISE_DATA_DIR"], "train.csv"))
demo = pd.DataFrame(DEMO_PAIRS, columns=["center_id", "meal_id"])

calib_rows = rolling_forecasts(train, 116, 125, METHOD)
low_mult, high_mult, n = calibrate_range(calib_rows)

check_rows = rolling_forecasts(train, 126, 135, METHOD)
check_demo = check_rows.merge(demo)

result = pd.DataFrame([{
    "method": METHOD,
    "calibration_weeks": "116-125",
    "calibration_rows": n,
    "quantiles": "10th / 90th of actual/forecast",
    "low_mult": low_mult,
    "high_mult": high_mult,
    "target_coverage": 0.80,
    "coverage_126_135_all": coverage(check_rows, low_mult, high_mult),
    "coverage_126_135_demo": coverage(check_demo, low_mult, high_mult),
    "demo_rows_126_135": len(check_demo),
}])
result.to_csv("outputs/range_calibration.csv", index=False)

decision_rows = pd.concat([calib_rows.merge(demo), check_demo], ignore_index=True).assign(
    scenario_low=lambda d: d["forecast_orders"] * low_mult,
    scenario_high=lambda d: d["forecast_orders"] * high_mult,
)
decision_rows.to_csv("outputs/demo_decision_inputs.csv", index=False)

print(result.round(3).T.to_string(header=False))
