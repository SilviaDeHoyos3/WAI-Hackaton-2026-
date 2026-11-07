# FreshWise — forecasting findings and shared plan (Nov 5, 2026)

From: Silvia (forecasting) + agent. For: Ari (decisions) + agent, Lan (demo).
Purpose: one shared picture of where we are, so both sides work on the same thing.

All results below are **development results** (weeks 96–135). Weeks 136–145 have not been used (see §7).
Nothing here is measured real-world waste reduction; decision results are simulated.

---

## 1. Shared goal

Minimise waste while keeping profit / service as high as possible. This is a two-objective problem: for one meal-week with prepared portions $S$, demand $D$, price $p$ and unit cost $c$:

$$
\text{Profit} = p\,\min(D,S) - c\,S \qquad \text{Waste} = \max(S-D,\,0)
$$

There is no single $S$ that is best for both, only a **Pareto frontier** of trade-offs. Two standard ways to pick a point:

- **Weighted:** add a waste cost $\lambda$ per leftover portion. The best plan is a demand quantile $q^* = \dfrac{p-c}{p+\lambda}$. A larger $\lambda$ means a lower $q^*$ and less waste.
- **Constrained:** minimise waste subject to service (or profit) not falling below a floor. This is Ari's current selection rule.

**Key point:** the preparation rule only chooses a point on the frontier. **A better forecast moves the whole frontier**, giving less waste at the same service level.

Waste metric used below (share of prepared portions left over):

$$
\text{waste rate} = \frac{\sum \max(S-D,\,0)}{\sum S}
\qquad
\text{unmet rate} = \frac{\sum \max(D-S,\,0)}{\sum D}
$$

---

## 2. Reproducibility check: our pipeline matches Ari's numbers

Under Ari's assumptions (inventory 40 portions, overage 2, underage 5, 1 order = 1 portion, tiers 69 / 230, weeks 126–135, 4 demo meals):

| Policy | Excess | Unmet | Penalty | Ari's file |
|---|---:|---:|---:|---|
| `last`, central forecast | 1992 | 2023 | 14099 | identical |
| 50/50 blend, q0.55 | 1950 | 1971 | 13755 | identical |

---

## 3. Supervised forecast candidate

Code: `src/freshwise/supervised.py`, `scripts/evaluate_supervised.py`, `tests/test_supervised.py` (branch `forecast-next-week`).

- **Model:** one pooled `HistGradientBoostingRegressor` on `log1p(num_orders)`. Fixed settings: learning_rate 0.05, max_iter 300, max_leaf_nodes 63, random_state 0. No tuning.
- **Past-only demand features:** lag-1 and lag-2 observed orders, weeks since lag-1, mean of last 4 / 8 observed rows, std of last 8, history length, meal mean in the previous week, centre op area.
- **Static features:** centre, meal, category, cuisine, centre type, city, region.
- **Planning-time features** (assumed known when planning): target-week checkout price, base price, discount, price vs last observed price, email promotion, homepage featured. The variant `hgb_no_plan` drops these.
- **Leakage rules:** no zero-filling of missing weeks. Each block's model is fit only on weeks ≤ (block start − 1). Lags use completed weeks only.
- **Tests:** future outcomes don't change predictions; shuffled rows give the same results; outputs are finite, non-negative and keyed; duplicate keys are rejected.
- **Evaluation design:** run once, not tuned.

| Fit on weeks | Predict | Role |
|---|---|---|
| ≤95 | 96–105 | calibration A (error ratios) |
| ≤105 | 106–115 | evaluation A (fresh window) |
| ≤115 | 116–125 | calibration B |
| ≤125 | 126–135 | evaluation B |

Each method's quantile policies use **its own** calibration ratios.

### 3.1 Forecast error (WAPE, one-week-ahead)

| Method | A: all pairs | A: demo | B: all pairs | B: demo |
|---|---:|---:|---:|---:|
| `last` | 43.2% | 44.6% | 45.2% | 29.1% |
| `trailing4` | 46.3% | 41.2% | 45.9% | 33.6% |
| 50/50 blend | 41.3% | 40.8% | 41.9% | 28.1% |
| **`hgb`** | **30.2%** | **30.1%** | **29.2%** | **21.5%** |
| `hgb_no_plan` | 38.7% | 39.3% | 39.2% | 33.6% |

About one third less error, consistent across windows. Most of the gain depends on the planning-time price/promotion assumption.

### 3.2 Decisions, demo meals: central-forecast policy

| Window | Method | Excess | Unmet | Penalty |
|---|---|---:|---:|---:|
| A | `last` | 4233 | 5244 | 34686 |
| A | `hgb` | **2676** | **3735** | **24027** |
| B | `last` | **1992** | 2023 | 14099 |
| B | `hgb` | 2186 | **819** | **8467** |

**Pre-registered rule** (hgb must have lower excess AND no higher unmet than `last` on both windows, demo pairs): **FAIL**. Window A passes; window B has +194 excess (+10%), even though unmet falls 60% and penalty falls 40%. The q0.55 policy also fails on B excess (2961 vs 1674).

### 3.3 Decisions, all pairs (≈32,700 cases per window): central policy

| Window | Method | Excess | Unmet |
|---|---|---:|---:|
| A | `last` | 1,974,727 | 1,792,209 |
| A | `hgb` | **1,459,261** | **1,200,969** |
| B | `last` | 1,990,378 | 1,914,402 |
| B | `hgb` | **852,268** | **1,698,509** |

Across all pairs, `hgb` reduces **both** excess and unmet in both windows.

---

## 4. Follow-up analysis (defined AFTER seeing §3; labelled as post hoc)

**Service-constrained rule:** choose the quantile $q$ that minimises excess subject to unmet ≤ `last` central unmet, **on window A only**, then apply that $q$ unchanged to window B.

| Demo meals, window B | q (chosen on A) | Excess | Unmet |
|---|---:|---:|---:|
| `last` central (today) | — | 1992 | 2023 |
| `last` + rule | 0.60 | 2097 | 1959 |
| blend + rule | 0.52 | 1767 | 2164 ❌ |
| **`hgb` + rule** | **0.35** | **1503 (−25%)** | **1440 (−29%)** |

All pairs, same procedure: `hgb` with q = 0.33 cuts window-B excess by 73% but raises unmet by 16%. The trade-off point is not stable across periods, so this is not a guaranteed win.

At equal service in window A (all pairs), `hgb` wastes about 54% less than `last` (0.90M vs 1.96M portions).

---

## 5. The 5% waste target

Rule: choose the largest $q$ with waste ≤ 5% on window A, then test on window B.

| Population | Method | Waste B | Unmet B |
|---|---|---:|---:|
| Demo | `last`, central (today) | 14.3% | 14.5% |
| Demo | `hgb`, central | 14.3% | 5.9% |
| Demo | `last`, ≤5% rule | 3.0% | 58.5% |
| Demo | blend, ≤5% rule | 4.1% | 44.9% |
| **Demo** | **`hgb`, ≤5% rule** | **3.5%** | **27.9%** |
| All pairs | `last`, central (today) | 22.8% | 22.2% |
| All pairs | `hgb`, central | 10.9% | 19.7% |
| All pairs | `last` | cannot reach 5% (minimum ≈5.4% on A, with 75% unmet) | — |
| All pairs | `hgb`, ≤5% rule (q = 0.11) | 4.0% | 42.8% |

**Reading:** with a one-week-ahead plan and this level of demand noise, 5% waste costs a large share of lost sales. `hgb` roughly halves that cost versus `last`, but it remains high.

---

## 6. Issues found

1. **Fixed inventory of 40 portions creates waste on its own.** 15.5% of cases have demand below 40 (window B, all pairs), so these leftovers are forced by the assumption, not by the forecast. Proposal: scale inventory to each meal's typical volume, or set it to 0, and document the choice.
2. **Week-116 example range:** `forecast_rows` uses a range table calibrated on 116–125, so the range is only out-of-sample for target weeks ≥126. Proposal: label rows for weeks ≤125 as `in_sample_calibration_overlap`.
3. **The range table is `last`-specific.** If the forecast method changes, it must be recalibrated on the new method's own errors.

---

## 7. Weeks 136–145 disclosure

- `python -m freshwise` (default `__main__`) prints `backtest()` results for cutoff 135, i.e. **aggregate 10-week-ahead MAE/WAPE for `last` and `trailing4` over all pairs in weeks 136–145**. These were seen once during setup (WAPE 0.485 / 0.498).
- **Never inspected:** demo-pair rows, one-week-ahead forecasts, `hgb`, ranges, or any decision result for 136–145.
- **Proposal:** remove cutoff 135 from the default `backtest()` call.

---

## 8. Decisions needed (Ari + Silvia, before the Nov 7 freeze)

| # | Decision | Options | Proposed |
|---|---|---|---|
| 1 | Forecast method | `last` / blend / `hgb` | `hgb`, with an honest note that it failed the pre-registered demo-B excess check |
| 2 | Price/promo known at planning? | yes / no | yes, stated as an explicit assumption |
| 3 | Objective | waste cost $\lambda$, or a service floor | service floor (unmet ≤ today), q chosen on window A |
| 4 | 5% waste | hard target / stated goal | stated goal with the trade-off shown honestly |
| 5 | Inventory assumption | fixed 40 / scaled / 0 | scaled or 0 |
| 6 | Next model improvement | — | two-step plan: cautious batch + mid-week top-up |
| 7 | Final run | — | freeze forecast, calibration, policy, assumptions and metrics together, then run 136–145 once |

If `hgb` is adopted, Silvia will: add `scikit-learn` to `pyproject.toml`, add `method="hgb"` to `forecast_rows` (no column changes), recalibrate the range on `hgb` errors (calibration window agreed with Ari), and update `docs/forecast.md`.

---

## 9. How to reproduce

From the repo root, branch `forecast-next-week`:

```
.venv\Scripts\Activate.ps1
python -m pip install scikit-learn
$env:FRESHWISE_DATA_DIR = "<folder with the 7 CSVs>"
python -m unittest discover -s tests
python scripts/evaluate_supervised.py
```

Outputs (local, not committed): `outputs/supervised_summary.csv` and `outputs/supervised_forecasts.csv` (keyed rows: centre, meal, target week, history end week, model fit end, method, forecast, actual, window, role, demo flag).

The §4–§5 follow-up numbers were computed from `outputs/supervised_forecasts.csv` using the same tiers, inventory and `inverted_cdf` quantiles as `empirical.py`.
