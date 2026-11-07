"""Range by forecast size: tighter, more realistic ranges for stable high-volume meals.

Calibrate on weeks 116-125; check coverage on weeks 126-135. Weeks 136-145 untouched.
Outputs (in outputs/, not committed): range_by_tier.csv, demo_decision_inputs.csv (overwritten).
"""
import os

import pandas as pd

from freshwise.next_week import (DEMO_PAIRS, METHOD, apply_range, calibrate_range,
                                 calibrate_range_by_tier, coverage, rolling_forecasts)

train = pd.read_csv(os.path.join(os.environ["FRESHWISE_DATA_DIR"], "train.csv"))
demo = pd.DataFrame(DEMO_PAIRS, columns=["center_id", "meal_id"])

calib = rolling_forecasts(train, 116, 125, METHOD)
check = rolling_forecasts(train, 126, 135, METHOD)

table = calibrate_range_by_tier(calib)
checked = apply_range(check, table)
inside = (checked["actual_orders"] >= checked["scenario_low"]) & (checked["actual_orders"] <= checked["scenario_high"])
table["coverage_126_135"] = inside.groupby(checked["volume_tier"]).mean().reindex(table["tier"]).to_numpy()
table.to_csv("outputs/range_by_tier.csv", index=False)

demo_checked = checked.merge(demo)
demo_inside = (demo_checked["actual_orders"] >= demo_checked["scenario_low"]) & (demo_checked["actual_orders"] <= demo_checked["scenario_high"])
pooled_low, pooled_high, _ = calibrate_range(calib)

decision = apply_range(pd.concat([calib.merge(demo), check.merge(demo)], ignore_index=True), table)
decision.to_csv("outputs/demo_decision_inputs.csv", index=False)

print("Range by forecast size (calibrated 116-125, checked 126-135)\n")
print(table.round(2).to_string(index=False))
print(f"\nOverall coverage 126-135 (tiered): {inside.mean():.3f}   demo meals: {demo_inside.mean():.3f}")
print(f"Old pooled range for comparison: x{pooled_low:.2f} to x{pooled_high:.2f}, "
      f"coverage {coverage(check, pooled_low, pooled_high):.3f}")
print("\nDemo meals, week 126-135 (tiered range):")
print(decision[decision.target_week >= 126][["meal_id", "target_week", "forecast_orders",
      "scenario_low", "scenario_high", "actual_orders"]].round(0).to_string(index=False))
