"""One-shot comparison: last / trailing4 / blend / hgb / hgb_no_plan. EXPERIMENTAL.

Windows (weeks 136-145 are NOT touched):
  calibration A 96-105 (fit<=95)   -> evaluation A 106-115 (fit<=105)
  calibration B 116-125 (fit<=115) -> evaluation B 126-135 (fit<=125)

Decision assumptions match DECISION_EVALUATION.md: inventory 40, overage 2, underage 5,
1 order = 1 portion, tiers 69 / 230, quantiles from each method's OWN calibration ratios.
Pre-registered acceptance: hgb has lower excess AND no higher unmet than last
on BOTH evaluation windows (demo pairs, central and q0.55 policies). Run once.

Outputs (outputs/, not committed): supervised_forecasts.csv, supervised_summary.csv
"""
import math

import numpy as np
import pandas as pd

from freshwise.data import enrich, load_data
from freshwise.next_week import DEMO_PAIRS, rolling_forecasts
from freshwise.supervised import build_features, fit_predict_block

INVENTORY, OVER, UNDER = 40, 2, 5
EDGES = [69.0, 230.0]
WINDOWS = {"A": ((96, 105), (106, 115)), "B": ((116, 125), (126, 135))}
POLICIES = {"central": None, "q0.55": 0.55, "newsvendor_q0.714": UNDER / (UNDER + OVER)}

tables = load_data()
data = enrich(tables["train.csv"], tables["meal_info.csv"], tables["fulfilment_center_info.csv"])
features = build_features(data)
train = tables["train.csv"]

frames = []
for name, (cal, ev) in WINDOWS.items():
    for lo, hi in (cal, ev):
        print(f"Window {name}: forecasting weeks {lo}-{hi} ...", flush=True)
        last = rolling_forecasts(train, lo, hi, "last")
        t4 = rolling_forecasts(train, lo, hi, "trailing4")
        blend = last.assign(method="blend",
                            forecast_orders=0.5 * last["forecast_orders"].to_numpy()
                            + 0.5 * t4["forecast_orders"].to_numpy())
        hgb = fit_predict_block(features, lo - 1, lo, hi, plan_features=True)
        hgb_np = fit_predict_block(features, lo - 1, lo, hi, plan_features=False)
        for part in (last, t4, blend, hgb, hgb_np):
            frames.append(part.assign(window=name, role="calibration" if (lo, hi) == cal else "evaluation"))
rows = pd.concat(frames, ignore_index=True)
demo = pd.DataFrame(DEMO_PAIRS, columns=["center_id", "meal_id"])
rows["is_demo"] = rows.set_index(["center_id", "meal_id"]).index.isin(demo.set_index(["center_id", "meal_id"]).index)
rows.to_csv("outputs/supervised_forecasts.csv", index=False)


def tier(f):
    return np.searchsorted(EDGES, f, side="right")


def decide(ev, cal, q):
    f = ev["forecast_orders"].to_numpy()
    if q is None:
        target = f
    else:
        c = cal[cal["forecast_orders"] > 0]
        ratios = (c["actual_orders"] / c["forecast_orders"]).to_numpy()
        ct = tier(c["forecast_orders"].to_numpy())
        mult = np.array([np.quantile(ratios[ct == t], q, method="inverted_cdf") for t in range(3)])
        target = f * mult[tier(f)]
    prep = np.maximum(0, np.ceil(target - INVENTORY))
    supply = INVENTORY + prep
    a = ev["actual_orders"].to_numpy()
    excess = np.maximum(0, supply - a).sum()
    unmet = np.maximum(0, a - supply).sum()
    return excess, unmet, OVER * excess + UNDER * unmet


records = []
for (w, method), ev in rows[rows.role == "evaluation"].groupby(["window", "method"]):
    cal = rows[(rows.window == w) & (rows.role == "calibration") & (rows.method == method)]
    for pop, sub in (("all pairs", ev), ("demo pairs", ev[ev.is_demo])):
        ae = (sub.actual_orders - sub.forecast_orders).abs()
        rec = {"window": w, "population": pop, "method": method, "rows": len(sub),
               "mae": ae.mean(), "wape": ae.sum() / sub.actual_orders.sum()}
        for pname, q in POLICIES.items():
            e, u, p = decide(sub, cal, q)
            rec.update({f"{pname}_excess": e, f"{pname}_unmet": u, f"{pname}_penalty": p})
        records.append(rec)
summary = pd.DataFrame(records)
summary.to_csv("outputs/supervised_summary.csv", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
print("\nFORECAST ERROR (evaluation windows)")
print(summary.pivot_table(index=["population", "method"], columns="window", values="wape").round(3))
print("\nDECISIONS, demo pairs")
d = summary[summary.population == "demo pairs"]
for pname in POLICIES:
    print(f"\n{pname}")
    print(d.pivot_table(index="method", columns="window",
          values=[f"{pname}_excess", f"{pname}_unmet", f"{pname}_penalty"]).round(0))

print("\nPRE-REGISTERED CHECK (demo pairs): hgb vs last, lower excess AND unmet not higher")
for pname in ("central", "q0.55"):
    ok = True
    for w in WINDOWS:
        h = d[(d.window == w) & (d.method == "hgb")].iloc[0]
        b = d[(d.window == w) & (d.method == "last")].iloc[0]
        passed = h[f"{pname}_excess"] < b[f"{pname}_excess"] and h[f"{pname}_unmet"] <= b[f"{pname}_unmet"]
        ok &= passed
        print(f"  {pname} window {w}: {'PASS' if passed else 'FAIL'}")
    print(f"  {pname} overall: {'ACCEPT' if ok else 'DO NOT ADOPT'}")
