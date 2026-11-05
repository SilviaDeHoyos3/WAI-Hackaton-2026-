# FreshWise: agreed approach, story and work plan

Owner: Silvia (forecasting) · Team: Ari (decisions), Lan (demo, submission)
Status: Nov 5, 2026. **Approach agreed** (see §0). Development results only; weeks 136–145 are reserved for one final frozen run.
Branch: `forecast-next-week` · PR #2 · Detailed numbers: `docs/FORECAST_FINDINGS_2026-11-05.md`

---

## 0. Agreed approach (Nov 5)

**Main approach: better forecast + use leftovers first, tested on real weekly data.**

1. **Forecast:** next-week orders per centre and meal, using `hgb` (prices and promotions assumed known at planning time). `last` and the 50/50 blend stay as baselines.
2. **Plan around stock:** each week, prepare only what is missing after counting usable leftovers. Leftovers are used first; anything not used within one extra week is waste.
3. **Compare preparation rules on the same cases:** (a) prepare the forecast minus leftovers, and (b) Ari's empirical-quantile rule minus leftovers. Choose with a rule agreed **before** running.
4. **Extension (only if time allows):** Ari's flexible preparation (shared components, delayed allocation) as a small, clearly labelled synthetic demo. Regional stock sharing stays as future work.

Everyone works from this document. Changes to it are agreed in the team chat first.

---

## 1. The story in one paragraph

Meal-prep kitchens decide each week how many portions to prepare before they know demand. Prepare too much and food is wasted; prepare too little and customers go unserved. FreshWise is **a human–AI decision system for meal preparation under uncertainty**. It forecasts next week's orders, shows the uncertainty honestly, and recommends how much to prepare, taking into account **what is already in stock**. A manager can add context (e.g. a local event), and the system explains how the recommendation changes. Our development results show that a better forecast plus **shelf-life-aware planning (use leftovers first)** can bring simulated waste below **5%** without serving fewer customers. That holds only under an explicit assumption that portions or ingredients keep for one extra week.

---

## 2. Context

- **Challenge:** Women in AI Hackathon 2026, Sustainable Food Systems. Abstract due Nov 1, final due Nov 12.
- **Data:** weekly meal orders for 77 fulfilment centres × 51 meals, weeks 1–145 (`train.csv`, about 456k rows), plus meal and centre information and prices/promotions. No real inventory, expiry, recipes or waste data exist, so all decision results are **simulated**.
- **Mentor guidance (Abir):** make the decision variable and objective explicit; generate scenarios from real errors; keep model uncertainty separate from manager adjustments; the assistant should call tools, not compute; evaluate forecast quality **and** decision quality against "prepare the central forecast"; never claim real-world waste reduction without deployment evidence.
- **Goal agreed in the team:** minimise waste while keeping profit and service as high as possible.

---

## 3. What we did (forecasting side)

| Date | Step | Result |
|---|---|---|
| Nov 3 | Setup: VS Code, Git, Python 3.12, data connected | Tests pass |
| Nov 3 | Demo sample chosen using weeks ≤115 only | Centre 13; meals 2306, 2444, 1198, 2664 (`docs/scope.md`) |
| Nov 3 | `forecast_rows` handoff function + PR #2 | Ari and Lan unblocked |
| Nov 4 | Week-by-week evaluation, weeks 116–125 | `last` beats `trailing4` (WAPE 41.5% vs 42.9%), frozen |
| Nov 4 | Mentor feedback: data-based uncertainty range | p10/p90 of real past errors by meal size; ~80% coverage on unseen weeks 126–135 (`docs/forecast.md`) |
| Nov 4 | Ari's decision tests | Equal-weight scenarios and quantile policies trade waste for service; best candidate ≈2% better than baseline |
| Nov 5 | Diagnosis | The bottleneck is the forecast; the naive `last` forecast ignores promotions and prices |
| Nov 5 | New supervised model (`hgb`), evaluated once on two windows | About one third less forecast error |
| Nov 5 | Waste vs profit analysis and the 5% target | Trade-off is a Pareto frontier; 5% is very costly without operational change |
| Nov 5 | New approach: shelf-life-aware planning (carry-over) | Waste under 5% without lower service (simulated, assumption-based) |

Verification: our pipeline reproduces Ari's published numbers exactly (`last` central 1992 / 2023 / 14099; blend q0.55 1950 / 1971 / 13755).

---

## 4. Findings

### 4.1 A better forecast exists

One pooled gradient-boosted model (`src/freshwise/supervised.py`) uses past orders, meal and centre information, and **target-week prices and promotions**, which are assumed known at planning time.

| WAPE (one week ahead) | Weeks 106–115 | Weeks 126–135 |
|---|---:|---:|
| `last` (current) | 43.2% | 45.2% |
| 50/50 blend | 41.3% | 41.9% |
| **`hgb`** | **30.2%** | **29.2%** |
| `hgb` without price/promo | 38.7% | 39.2% |

Evaluated once with fixed settings, on two separate windows (weeks 106–115 and 126–135), with leakage tests.

### 4.2 On decisions alone, the forecast helps but does not remove the trade-off

- Across all ≈32,700 cases per window, `hgb` reduces **both** excess and unmet orders versus `last`.
- On the 4 demo meals, `hgb` **failed our pre-registered rule** in one window: +194 excess portions (+10%), even though unmet fell 60% and penalty fell 40%. We report this as is.
- The waste–profit trade-off is a **Pareto frontier**. The preparation rule only picks a point on it; a better forecast moves the whole frontier.

For one meal-week with prepared portions $S$ and demand $D$:

$$
\text{waste rate} = \frac{\sum \max(S-D,0)}{\sum S}
\qquad
\text{unmet rate} = \frac{\sum \max(D-S,0)}{\sum D}
$$

- **5% waste with one-week-ahead planning alone is very costly:** about 58% of demo orders unmet with `last`, and about 28% with `hgb`.

### 4.3 The approach that breaks the trade-off: use leftovers first

Each week the kitchen prepares only what the forecast says is missing after counting usable leftovers:

$$
\text{prepare}_t = \max\!\left(0,\ \lceil \hat{D}_t - L_t \rceil\right)
$$

$L_t$ is the stock carried from last week. Leftovers are used first (FIFO), and anything not used within **one extra week** counts as waste.

| Simulated, prepare = forecast, start stock 0 | Waste 106–115 | Unmet 106–115 | Waste 126–135 | Unmet 126–135 |
|---|---:|---:|---:|---:|
| All meals, `last`, no carry-over | 21.9% | 21.1% | 22.5% | 22.8% |
| All meals, `last` + carry-over | 8.7% | 19.9% | 9.9% | 21.9% |
| All meals, `hgb`, no carry-over | 15.9% | 13.9% | 10.5% | 19.9% |
| **All meals, `hgb` + carry-over** | **3.8%** | **13.8%** | **2.8%** | **19.8%** |
| Demo meals, `last` + carry-over | 8.5% | 24.5% | 4.3% | 14.0% |
| **Demo meals, `hgb` + carry-over** | **4.7%** | **17.4%** | **0.1%** | **5.7%** |

**Reading:** carry-over cuts waste by roughly three quarters with **no loss of service**, reaching the 5% target in both windows. The better forecast adds a further gain on both waste and service.

A second option, **sharing stock between centres in the same region**, cut waste from 10.5% to 5.1% and unmet from 19.9% to 15.2% (`hgb`, weeks 126–135). It is kept as an extension.

**Assumptions and limits (must appear wherever these numbers are used):**

- One-week reuse is realistic for frozen meals, meal kits or prepped ingredients, not for food cooked to serve the same day.
- Week numbers are anonymous; there are no real expiry dates.
- The carry-over and pooling analyses were designed **after** seeing the earlier results, so they are exploratory until the final frozen run.
- All results are simulated orders; `num_orders` is observed orders, not true demand.
- No real-world waste reduction is claimed.

---

## 5. How this fits with Ari's flexible-preparation proposal

Ari's `docs/flexible_preparation_strategy.md` (on `main`, Nov 5) proposes a **different, complementary lever**: keep some preparation as **shared components** and finish specific meals later, once better information arrives (a two-stage plan with non-anticipativity, capacity and expiry rules). It is a **synthetic mechanism experiment**, because the dataset has no recipes, components or within-week timing. Ari's document was written before the `hgb` and carry-over results above.

The three levers fit together:

| Lever | Question it answers | Evidence base | Owner |
|---|---|---|---|
| Better forecast (`hgb`) | How much demand to expect | Real weekly data, two evaluation windows | Silvia |
| Carry-over / shelf-life-aware planning | How to use what is already in stock across weeks | Real weekly orders + assumed one-week shelf life | Silvia (simulation), Ari (decision rules) |
| Flexible preparation (shared components, delayed allocation) | Which commitments to make now vs later | Synthetic recipes, timing and capacities | Ari |

Story: *better forecast* → *use leftovers first* → *keep commitments flexible where recipes allow*.
Carry-over directly addresses one assumption in Ari's history (inventory "reset for each evaluated case; no carry-over ageing model").

### Joint comparison on real data (carry-over)

Run both teams' preparation rules on exactly the same cases and assumptions, then pick the better one together:

| Item | Proposal |
|---|---|
| Forecasts | Silvia supplies keyed rows (centre, meal, target week, history end week, forecast, method) for `last`, blend and `hgb`, one week ahead |
| Windows | Evaluation A = weeks 106–115, evaluation B = weeks 126–135 (calibration 96–105 / 116–125). Weeks 136–145 untouched |
| Carry-over rules | Shelf life = 1 extra week; FIFO; leftovers dropped if a week has no observed row; start stock = 0 (replaces the fixed 40 portions, which forced waste on 15.5% of cases) |
| Rules to compare | (a) prepare the forecast minus leftovers; (b) Ari's empirical-quantile rule (`empirical.py`) minus leftovers, with quantiles recalibrated on each method's own errors |
| Metrics | Waste rate, unmet rate, total penalty (overage 2, underage 5), per meal and per week, demo meals and all meals |
| Selection rule | Agreed before running: lowest waste with unmet not higher than today's baseline, on **both** windows |
| Run | Once each, then freeze together on **Nov 7** |

### Silvia's input to Ari's synthetic experiment

Ari's Gate 1 asks Silvia to specify joint demand cases and to separate **total-volume** uncertainty from **menu-mix** uncertainty. Proposal: estimate both from real one-week-ahead errors for the centre-13 demo meals (how much total demand moves vs how much the split between meals moves), and use those as the synthetic scenario settings. The scenarios are then grounded in data rather than chosen freely, and are labelled as data-informed synthetic inputs.

## 6. Work plan: who does what

### 6.1 Shared simulation contract (build once, used by everyone)

One function runs every preparation rule on the same cases, so results are comparable:

```python
simulate_carryover(rows, prepare_fn, shelf_life_weeks=1, start_stock=0)
```

- `rows`: keyed forecast rows (`center_id, meal_id, target_week, history_end_week, forecast_orders, method, actual_orders`), from Silvia.
- `prepare_fn(forecast, leftovers, context) -> int`: the preparation rule. Rule (a) is `max(0, ceil(forecast - leftovers))`; rule (b) wraps Ari's `recommend_empirical_preparation` with `inventory = leftovers`.
- Stock rules: FIFO; leftovers older than `shelf_life_weeks` become waste; leftovers are dropped if the next week has no observed row; start stock 0.
- Output per row: `leftovers_in, prepared, supply, sold, unmet, expired` (expired = waste), plus totals per window, per meal and per week.
- Metrics: waste rate, unmet rate, penalty (overage 2, underage 5).

### 6.2 Selection rule (agreed before running)

> Choose the forecast + rule combination with the **lowest waste rate** whose **unmet rate is not higher than today's baseline** (`last`, prepare the forecast, no carry-over) on **both** evaluation windows (106–115 and 126–135), for the demo meals. Report all-meals results alongside. If nothing qualifies, keep the baseline and say so.

Quantiles for rule (b) are calibrated on each forecast's own errors (weeks 96–105 for window A, 116–125 for window B). No tuning on the evaluation windows.

### 6.3 Tasks and dates

| Date | Silvia (forecast + simulator) | Ari (decision rules) | Lan (demo + submission) |
|---|---|---|---|
| **Nov 6** | Build `src/freshwise/carryover.py` (`simulate_carryover`) + tests; `scripts/evaluate_carryover.py` producing keyed rows and metrics for `last`, blend, `hgb` with rule (a). Add `method="hgb"` to `forecast_rows`; recalibrate the range on `hgb` errors; add `scikit-learn` to `pyproject.toml` | Review and merge PR #2. Wrap `empirical.py` as rule (b) for `prepare_fn`. Confirm the stock assumptions (start 0, 1-week shelf life, FIFO, penalties 2/5) | Check official rules and formats. Draft the demo screen for meal 1198: forecast → stock → recommendation → manager adjustment → explanation |
| **Nov 6 (evening)** | Team agrees the selection rule (§6.2) in writing | ← same | ← same |
| **Nov 7** | Run the comparison **once** (rules a and b, all forecasts, both windows); share the table | Review the results and the rule (b) behaviour per meal | Plug the real functions into the screen (no numbers computed in the UI) |
| **Nov 7** | **Freeze together:** forecast, shelf life, rule, assumptions, metrics | ← same | ← same |
| **Nov 8** | Buffer / fix broken paths only. Optional: data-informed demand scenarios (total volume vs menu mix) for Ari's extension | Optional: minimal flexible-preparation demo (two meals, one shared base), labelled synthetic | Assistant explanation text that calls tools; label observed vs simulated vs synthetic |
| **Nov 9** | Run weeks 136–145 **once** with the frozen setup; save all rows | Check the final decision numbers | Insert final numbers into slides |
| **Nov 10** | Fix README or dependency gaps found by Lan | Review the final evidence wording | Reproduce from the README on a clean setup; rehearse |
| **Nov 11** | Approve forecasting claims | Approve decision claims | Submit; save the receipt |
| **Nov 12** | Buffer: submission blockers only | ← same | ← same |

### 6.4 Still open (decide by Nov 6 evening)

1. Are FreshWise meals storable for one extra week (frozen, kits, prepped ingredients)? This must be stated as the core assumption.
2. Shelf life: 1 week only, or also show 0 and 2 weeks as a sensitivity check?
3. Does Ari's flexible-preparation extension go into the demo, or stay as future work?

### 6.5 Rules for working together

- One owner per file; agree before editing someone else's core file.
- Small pull requests; Ari reviews forecast/simulator PRs, Silvia reviews decision-rule PRs, Lan confirms what the screen shows.
- End every session with: "Done / Next / Blocked by / Handoff file".
- No raw data, credentials or large outputs in Git. Weeks 136–145 are opened only on Nov 9.

---

## 7. Demo story (for Lan)

1. **One case:** centre 13, meal 1198 (stable, mid-volume).
2. **Forecast:** next week's orders, with the data-based range ("actual orders fell inside this range about 80% of the time").
3. **Stock check:** FreshWise subtracts usable leftovers from last week.
4. **Recommendation:** how many portions to prepare, with expected leftovers and expected shortages.
5. **Manager adjustment:** "local event next week" raises demand; the recommendation is recalculated, and the change is explained. Model uncertainty and the manager's input are shown separately.
6. **Evidence slide:** simulated waste falls from about 22% to under 5% with no loss of service, under the stated shelf-life assumption.

---

## 8. Honesty notes

- **Weeks 136–145:** only aggregate 10-week-ahead baseline scores (all pairs) were printed once during setup. No choice used them. They are reserved for one final frozen run.
- The new model's demo-meal result failed one pre-registered check; this is reported, not hidden.
- Post-hoc analyses (service-constrained quantile, 5% target, carry-over, pooling) are labelled as such.
- All decision results are simulations; no measured waste, carbon or profit savings are claimed.

---

## 9. Files

| File | What it is |
|---|---|
| `docs/scope.md` | Demo meals and selection rule |
| `docs/forecast.md` | Forecast method, range and limits |
| `docs/FORECAST_FINDINGS_2026-11-05.md` | Detailed results tables |
| `docs/flexible_preparation_strategy.md` (on `main`) | Ari's flexible-preparation proposal |
| `src/freshwise/carryover.py`, `scripts/evaluate_carryover.py` | Shared simulator and comparison (to build Nov 6) |
| `src/freshwise/next_week.py` | `forecast_rows`, rolling forecasts, error summary, range |
| `src/freshwise/supervised.py` | `hgb` model (experimental) |
| `scripts/evaluate_supervised.py` | One-shot comparison, weeks 106–115 and 126–135 |
| `tests/test_supervised.py` | Leakage, shuffle, output and duplicate-key tests |

Reproduce: activate `.venv`, `pip install scikit-learn`, set `FRESHWISE_DATA_DIR` to the folder with the 7 CSVs, then run `python -m unittest discover -s tests` and `python scripts/evaluate_supervised.py`.
