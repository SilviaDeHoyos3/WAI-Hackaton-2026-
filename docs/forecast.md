# Forecast component (owner: Silvia)

Status: development results, Nov 4. Final evaluation (weeks 136-145) not yet run.

## What is predicted

Next-week `num_orders` (observed orders, not unconstrained demand) for a known centre-meal pair.
Function: `freshwise.next_week.forecast_rows(train, history_end_week)` returns one row per demo pair for week `history_end_week + 1`.

## Method

`last`: the most recent observed week's orders for that centre-meal pair.
Unseen pairs use the existing fallback (recent meal mean, then recent global mean) and are labelled.

Chosen once on development weeks 116-125 (one-week-ahead, rolling, history strictly before each target week):

| Method | Rows | MAE (orders) | WAPE |
|---|---:|---:|---:|
| last | 32,834 | 105.7 | 41.5% |
| trailing4 | 32,834 | 109.4 | 42.9% |

Demo pairs only (40 rows): last 31.2% WAPE, trailing4 42.0%. The overall difference is small.
WAPE = total absolute error / total actual orders.

## Low / central / high scenarios

- Central = the forecast.
- Low / high = forecast x the 10th / 90th percentile of past `actual / forecast` ratios.
- Ratios come from the one-week-ahead errors on weeks 116-125, all observed pairs, split into three forecast-size tiers (forecast size is known at prediction time).
- Coverage was checked on weeks 126-135, which were not used to calibrate:

| Forecast size | Low x | High x | Calibration rows | Coverage 126-135 |
|---|---:|---:|---:|---:|
| < 69 | 0.48 | 3.93 | 10,492 | 81.8% |
| 69-230 | 0.37 | 1.98 | 11,278 | 80.8% |
| > 230 | 0.40 | 1.41 | 11,064 | 79.4% |

Target coverage is 80%. This is an empirical range, not a parametric confidence interval.

The range represents model uncertainty only. Manager contextual adjustments (e.g. a local event) are applied afterwards in the decision module and must stay separate.

## Limitations

- Weekly orders are volatile; average error is about 40% of actual orders.
- The lower bound stays wide (about x0.4) because sudden drops are common.
- Missing weeks are not treated as zero demand; evaluation uses observed rows only.
- No real-world waste reduction is claimed. Decision results will be simulated.
