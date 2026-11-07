"""Find centre-meal pairs eligible for the demo (weeks 1-115 only). See docs/scope.md."""
import os
import pandas as pd

df = pd.read_csv(os.path.join(os.environ["FRESHWISE_DATA_DIR"], "train.csv"))
hist = df[df["week"] <= 115]  # only pre-evaluation history

pairs = hist.groupby(["center_id", "meal_id"]).agg(
    weeks_observed=("week", "nunique"),
    weeks_104_115=("week", lambda w: w.between(104, 115).sum()),
    mean_orders=("num_orders", "mean"),
).reset_index()

ok = pairs[(pairs["weeks_observed"] >= 90) & (pairs["weeks_104_115"] == 12)]
ok.to_csv("outputs/demo_candidates.csv", index=False)

print(len(ok), "qualifying centre-meal pairs")
print("\nCentres with the most qualifying meals:")
print(ok.groupby("center_id").size().sort_values(ascending=False).head(10))
