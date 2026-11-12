"""Compare forecasts x preparation rules with "use leftovers first". RUN ONCE (Nov 7),
only after the team has agreed the selection rule (docs/FRESHWISE_FORECASTING_STORY.md 6.2).

Input: outputs/supervised_forecasts.csv (from scripts/evaluate_supervised.py).
Evaluation windows: A = weeks 106-115, B = weeks 126-135. Weeks 136-145 are NOT used.
Start stock 0. Shelf life 1 week (headline), with 0 and 2 weeks as sensitivity.

Rule (b) uses the fast, exactly equivalent version of Ari's calibrated empirical rule
(freshwise.fast_rules). Before simulating, it is checked against Ari's original rule
(freshwise.preparation_rules) on 3,000 real evaluation rows; the script stops if any
recommendation differs.

Outputs (outputs/, not committed): carryover_rows.csv, carryover_summary.csv
"""
import numpy as np
import pandas as pd

from freshwise.carryover import prepare_forecast_minus_leftovers, simulate_carryover, summarize
from freshwise.empirical_calibration import build_ratio_lookup
from freshwise.fast_rules import make_fast_calibrated_empirical_rule
from freshwise.preparation_rules import make_calibrated_empirical_rule

METHODS = ["last", "blend", "hgb"]
SHELF_LIVES = [0, 1, 2]
QUANTILES = {"b_empirical_q055": 0.55, "b_empirical_q5_over_7": 5 / 7}

all_rows = pd.read_csv("outputs/supervised_forecasts.csv")
all_rows = all_rows[all_rows["method"].isin(METHODS)].copy()

ratio_lookup = build_ratio_lookup(all_rows, methods=METHODS)

rows = all_rows[all_rows["role"] == "evaluation"].copy()
assert rows.target_week.max() <= 135, "Final weeks must not be used here"

RULES = {"a_forecast_minus_leftovers": prepare_forecast_minus_leftovers}
rng = np.random.default_rng(0)
check = rows.sample(3000, random_state=0).to_dict("records")
for name, q in QUANTILES.items():
    fast = make_fast_calibrated_empirical_rule(ratio_lookup, q)
    slow = make_calibrated_empirical_rule(ratio_lookup, q)
    for r in check:
        leftovers = int(rng.integers(0, 300))
        f = float(r["forecast_orders"])
        if fast(f, leftovers, r) != slow(f, leftovers, r):
            raise SystemExit(f"Fast rule differs from Ari's rule for {name}: {r}")
    RULES[name] = fast
print("Equivalence check passed: fast rule (b) == Ari's rule (b) on 3,000 real rows x 2 quantiles", flush=True)

results = []
for rule_name, fn in RULES.items():
    for life in SHELF_LIVES:
        print(f"Simulating {rule_name}, shelf life {life} ...", flush=True)
        sim = simulate_carryover(rows, fn, shelf_life_weeks=life, start_stock=0)
        results.append(sim.assign(rule=rule_name, shelf_life_weeks=life))
res = pd.concat(results, ignore_index=True)
res.to_csv("outputs/carryover_rows.csv", index=False)

by = ["window", "method", "rule", "shelf_life_weeks"]
summary = pd.concat([summarize(res, by).assign(population="all meals"),
                     summarize(res[res.is_demo], by).assign(population="demo meals")],
                    ignore_index=True)
summary.to_csv("outputs/carryover_summary.csv", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
for pop in ("demo meals", "all meals"):
    s = summary[summary.population == pop]
    print(f"\n{pop.upper()}: waste (expired only / incl. terminal stock) and unmet rate (%)")
    t = s.pivot_table(index=["method", "rule", "shelf_life_weeks"], columns="window",
                      values=["waste_rate", "waste_rate_with_terminal", "unmet_rate"]) * 100
    print(t.round(1))

# Agreed (6.2): selection on the conservative waste measure; both measures reported.
SELECTION_WASTE = "waste_rate_with_terminal"

# Selection rule (6.2): lowest waste with unmet not above the baseline
# (last, rule a, shelf life 0) in BOTH windows, demo meals.
d = summary[summary.population == "demo meals"].set_index(["window", "method", "rule", "shelf_life_weeks"])
base = {w: d.loc[(w, "last", "a_forecast_minus_leftovers", 0), "unmet_rate"] for w in ("A", "B")}
print(f"\nSELECTION (demo meals, shelf life 1 week, waste metric = {SELECTION_WASTE})")
ok = []
for (method, rule) in sorted({(m, r) for _, m, r, _ in d.index}):
    a = d.loc[("A", method, rule, 1)]
    b = d.loc[("B", method, rule, 1)]
    qualifies = a.unmet_rate <= base["A"] and b.unmet_rate <= base["B"]
    print(f"  {method:6} {rule:28} waste A {a[SELECTION_WASTE]:.1%} B {b[SELECTION_WASTE]:.1%} | "
          f"unmet A {a.unmet_rate:.1%} B {b.unmet_rate:.1%} | {'qualifies' if qualifies else 'fails service floor'}")
    if qualifies:
        ok.append(((a[SELECTION_WASTE] + b[SELECTION_WASTE]) / 2, method, rule))
print("  WINNER:", min(ok)[1:] if ok else "none - keep baseline")
