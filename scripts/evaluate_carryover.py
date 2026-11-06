"""Compare forecasts x preparation rules with "use leftovers first". RUN ONCE (Nov 7),
only after the team has agreed the selection rule (docs/FRESHWISE_FORECASTING_STORY.md 6.2).

Input: outputs/supervised_forecasts.csv (from scripts/evaluate_supervised.py).
Evaluation windows: A = weeks 106-115, B = weeks 126-135. Weeks 136-145 are NOT used.
Start stock 0. Shelf life 1 week (headline), with 0 and 2 weeks as sensitivity.

To add Ari's rule (b): add an entry to RULES with signature (forecast, leftovers, context) -> int.
Context contains the row (centre, meal, target_week, method, window, ...).

Outputs (outputs/, not committed): carryover_rows.csv, carryover_summary.csv
"""
import pandas as pd

from freshwise.carryover import prepare_forecast_minus_leftovers, simulate_carryover, summarize

METHODS = ["last", "blend", "hgb"]
SHELF_LIVES = [0, 1, 2]
RULES = {"a_forecast_minus_leftovers": prepare_forecast_minus_leftovers}

rows = pd.read_csv("outputs/supervised_forecasts.csv")
rows = rows[(rows.role == "evaluation") & rows.method.isin(METHODS)]
assert rows.target_week.max() <= 135, "Final weeks must not be used here"

results = []
for rule_name, fn in RULES.items():
    for life in SHELF_LIVES:
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
    print(f"\n{pop.upper()}: waste rate / unmet rate (%)")
    t = s.pivot_table(index=["method", "rule", "shelf_life_weeks"], columns="window",
                      values=["waste_rate", "unmet_rate"]) * 100
    print(t.round(1))

# Selection rule (6.2): lowest waste with unmet not above the baseline
# (last, rule a, shelf life 0) in BOTH windows, demo meals.
d = summary[summary.population == "demo meals"].set_index(["window", "method", "rule", "shelf_life_weeks"])
base = {w: d.loc[(w, "last", "a_forecast_minus_leftovers", 0), "unmet_rate"] for w in ("A", "B")}
print("\nSELECTION (demo meals, headline shelf life 1 week)")
ok = []
for (method, rule) in {(m, r) for _, m, r, _ in d.index}:
    a = d.loc[("A", method, rule, 1)]
    b = d.loc[("B", method, rule, 1)]
    qualifies = a.unmet_rate <= base["A"] and b.unmet_rate <= base["B"]
    print(f"  {method:6} {rule:28} waste A {a.waste_rate:.1%} B {b.waste_rate:.1%} | "
          f"unmet A {a.unmet_rate:.1%} B {b.unmet_rate:.1%} | {'qualifies' if qualifies else 'fails service floor'}")
    if qualifies:
        ok.append(((a.waste_rate + b.waste_rate) / 2, method, rule))
print("  WINNER:", min(ok)[1:] if ok else "none - keep baseline")
