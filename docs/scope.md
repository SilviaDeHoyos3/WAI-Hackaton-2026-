# Demo scope (proposed)

Owner: Silvia (forecasting). Status: proposed, for team confirmation.

## Selected demo IDs

| center_id | meal_id | weeks observed (1-115) | mean weekly orders (1-115) | volume tier |
|---|---|---|---|---|
| 13 | 2306 | 114 | 173 | low |
| 13 | 2444 | 115 | 304 | mid-low |
| 13 | 1198 | 115 | 639 | mid-high |
| 13 | 2664 | 98 | 920 | high |

## Selection rule

Only weeks 1-115 of `train.csv` were used. No evaluation weeks (116-145) were inspected.

1. Eligible centre-meal pairs: at least 90 observed weeks in weeks 1-115 and an observed row in every week 104-115. 2,296 pairs qualify.
2. Centre: the one with the most eligible meals (centre 13, 45 eligible meals).
3. Meals: within centre 13, eligible meals were sorted by mean weekly orders (weeks 1-115). The meals at the 20th, 40th, 60th and 80th percentiles were taken, to cover low to high volume without picking extremes.

Script: `outputs/find_candidates.py` (local; not committed). Candidate list: `outputs/demo_candidates.csv` (local; not committed).

## Data limitations

- `num_orders` is observed orders, not unconstrained demand.
- A missing centre-meal-week row means unknown availability, assortment or missingness, not confirmed zero demand. Meal 2664 has 17 unobserved weeks in 1-115.
- No inventory, expiry, recipe, waste or lead-time data is supplied.
- Week numbers are anonymous; they are not mapped to real dates or holidays.
