"""FINAL TEST - weeks 136-145. RUN ONCE with the frozen setup (docs/FRESHWISE_FORECASTING_STORY.md 6.4).

Frozen setup (agreed by Ari and Silvia, Nov 9):
- Forecast: hgb with planned prices and promotions, refit on weeks <= 135, one week ahead
  (lags use each completed week; the model is not refit inside the window).
- Stock: start 0, oldest usable stock first (FIFO), shelf life 1 extra week (simulation assumption).
- Default rule: prepare forecast minus usable stock.
- Baseline: last-week forecast, prepare the forecast, no carry-over.
- Optional labelled example: hgb + empirical quantile 5/7 (ratios from hgb's own one-week-ahead
  errors on weeks 126-135, model fit <= 125; size groups 69 / 230).
- Sensitivity only: default rule with shelf life 0 and 2 weeks.
- Metrics: waste_rate, waste_rate_with_terminal, unmet_rate, penalty, penalty_with_terminal
  (overage 2, underage 5), plus forecast WAPE; demo meals and all meals.

Before any data is touched, the script writes outputs/final_run_manifest.json with the git commit,
branch, training cutoff, library versions and frozen settings. It refuses to run a second time once
the manifest says "completed". Nothing may be changed after seeing these results.
"""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

MANIFEST = "outputs/final_run_manifest.json"
TRAIN_CUTOFF, FIRST, LAST = 135, 136, 145


def git(*args):
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


if os.path.exists(MANIFEST):
    with open(MANIFEST) as fh:
        previous = json.load(fh)
    if previous.get("status") == "completed":
        sys.exit(f"The final test already ran (commit {previous.get('commit')}, "
                 f"{previous.get('finished_utc')}). It must not be run again.")
    print("Note: an earlier final run did not complete (no results were produced). Recording a new attempt.")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402

from freshwise.carryover import prepare_forecast_minus_leftovers, simulate_carryover, summarize  # noqa: E402
from freshwise.data import enrich, load_data  # noqa: E402
from freshwise.fast_rules import make_fast_calibrated_empirical_rule  # noqa: E402
from freshwise.next_week import DEMO_PAIRS, rolling_forecasts  # noqa: E402
from freshwise.supervised import PARAMS, build_features, fit_predict_block  # noqa: E402

manifest = {
    "status": "started",
    "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "commit": git("rev-parse", "HEAD"),
    "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "uncommitted_changes": git("status", "--porcelain") not in ("", "unavailable"),
    "training_cutoff_week": TRAIN_CUTOFF,
    "test_weeks": [FIRST, LAST],
    "calibration_for_q5_7": {"model_fit_end": 125, "weeks": [126, 135]},
    "hgb_params": PARAMS,
    "frozen_setup": {"start_stock": 0, "shelf_life_weeks": 1, "fifo": True,
                     "default_rule": "forecast minus usable stock", "baseline": "last, no carry-over",
                     "option": "hgb + empirical quantile 5/7", "penalties": {"overage": 2, "underage": 5},
                     "size_groups": [69, 230]},
    "versions": {"python": platform.python_version(), "numpy": np.__version__,
                 "pandas": pd.__version__, "scikit-learn": sklearn.__version__,
                 "platform": platform.platform()},
}
os.makedirs("outputs", exist_ok=True)
with open(MANIFEST, "w") as fh:
    json.dump(manifest, fh, indent=2)
print("Recorded before running:\n" + json.dumps({k: manifest[k] for k in (
    "commit", "branch", "uncommitted_changes", "training_cutoff_week", "test_weeks")}, indent=2), flush=True)
if manifest["uncommitted_changes"]:
    print("WARNING: there are uncommitted changes; the recorded commit may not match the code that ran.")

tables = load_data()
train = tables["train.csv"]
features = build_features(enrich(train, tables["meal_info.csv"], tables["fulfilment_center_info.csv"]))
assert features["week"].max() >= LAST, "Final weeks missing from train.csv"

print("Forecasting weeks 136-145 (hgb fit on weeks <= 135) ...", flush=True)
hgb = fit_predict_block(features, TRAIN_CUTOFF, FIRST, LAST, plan_features=True)
last = rolling_forecasts(train, FIRST, LAST, "last")
print("Calibrating the optional q5/7 example (hgb fit on weeks <= 125, errors on 126-135) ...", flush=True)
calib = fit_predict_block(features, 125, 126, 135, plan_features=True)

demo = pd.DataFrame(DEMO_PAIRS, columns=["center_id", "meal_id"])
demo_keys = demo.set_index(["center_id", "meal_id"]).index
rows = pd.concat([hgb, last], ignore_index=True).assign(window="FINAL")
rows["is_demo"] = rows.set_index(["center_id", "meal_id"]).index.isin(demo_keys)
assert rows["target_week"].between(FIRST, LAST).all()

c = calib[calib["forecast_orders"] > 0]
groups = np.searchsorted([69.0, 230.0], c["forecast_orders"].to_numpy(), side="right")
ratios = (c["actual_orders"] / c["forecast_orders"]).to_numpy()
lookup = {("hgb", "FINAL", g): ratios[groups == g] for g in range(3)}
q57 = make_fast_calibrated_empirical_rule(lookup, 5 / 7)

runs = [("baseline: last, no carry-over", "last", prepare_forecast_minus_leftovers, 0),
        ("DEFAULT: hgb + forecast minus leftovers", "hgb", prepare_forecast_minus_leftovers, 1),
        ("option: hgb + q5/7 (labelled example)", "hgb", q57, 1),
        ("sensitivity: default, shelf life 0", "hgb", prepare_forecast_minus_leftovers, 0),
        ("sensitivity: default, shelf life 2", "hgb", prepare_forecast_minus_leftovers, 2)]
results = []
for label, method, fn, life in runs:
    sim = simulate_carryover(rows[rows["method"] == method], fn, shelf_life_weeks=life, start_stock=0)
    results.append(sim.assign(setup=label, shelf_life_weeks=life))
res = pd.concat(results, ignore_index=True)
res.to_csv("outputs/final_rows.csv", index=False)

cols = ["waste_rate", "waste_rate_with_terminal", "unmet_rate", "penalty", "penalty_with_terminal"]
summary = pd.concat([summarize(res, ["setup"]).assign(population="all meals"),
                     summarize(res[res.is_demo], ["setup"]).assign(population="demo meals")],
                    ignore_index=True)
order = {label: i for i, (label, *_) in enumerate(runs)}
summary = summary.sort_values(["population", "setup"], key=lambda s: s.map(order) if s.name == "setup" else s)
summary.to_csv("outputs/final_summary.csv", index=False)


def wape(df):
    return (df["actual_orders"] - df["forecast_orders"]).abs().sum() / df["actual_orders"].sum()


forecast_quality = {pop: {m: round(float(wape(rows[(rows.method == m) & (mask)])), 4) for m in ("last", "hgb")}
                    for pop, mask in (("all meals", True), ("demo meals", rows.is_demo))}

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
for pop in ("demo meals", "all meals"):
    s = summary[summary.population == pop].set_index("setup")
    t = s[cols].copy()
    for c_ in ("waste_rate", "waste_rate_with_terminal", "unmet_rate"):
        t[c_] = (t[c_] * 100).round(1)
    print(f"\nFINAL TEST weeks 136-145 - {pop.upper()} (rates in %, penalties in units)")
    print(t.to_string())
print("\nForecast WAPE weeks 136-145:", json.dumps(forecast_quality))

manifest.update(status="completed", finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                forecast_wape=forecast_quality,
                outputs=["outputs/final_rows.csv", "outputs/final_summary.csv"])
with open(MANIFEST, "w") as fh:
    json.dump(manifest, fh, indent=2)
print(f"\nDone. Manifest: {MANIFEST} (commit {manifest['commit']}).")
