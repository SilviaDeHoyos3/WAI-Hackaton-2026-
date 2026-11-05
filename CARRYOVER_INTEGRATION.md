# Carry-over integration — working agreement

## Purpose
Compare preparation rules using the same forecasts, cases and stock accounting.
Previous experiments remain unchanged and documented.

## Ari's adapter
Module: freshwise.preparation_rules
Function: empirical_preparation_rule(forecast, leftovers, context)
Returns: integer number of new portions to prepare.

Context requires:
- error_ratios: past calibration ratios for the matching forecast method and size group
- quantile: explicitly chosen preparation quantile

## Proposed comparison
- Start stock: zero for every policy.
- Shelf life: one additional week, explicitly assumed.
- Use older usable stock first.
- Baseline: last forecast, central preparation, no carry-over.
- Compare central and empirical preparation with carry-over.
- Evaluate weeks 106–115 and 126–135 separately.
- Report demo meals and all-meal results separately.
- Preserve earlier fixed-inventory results as historical experiments.

## Selection
Follow the team's agreed rule:
lowest waste rate with unmet rate no higher than the baseline
in BOTH development windows for the demo meals.
Report all-meal results alongside.

Calibration uses each forecast method's own past errors.
Quantile selection must be specified before running comparisons;
do not search for a winning quantile on the evaluation windows.

## Accounting points requiring confirmation
- Missing observations are not zero demand.
- Any removed stock must be recorded explicitly.
- Remaining usable stock at the end must be reported separately.
- Define the waste-rate denominator and penalty accounting consistently.

## Evidence limits
Historical orders are observed data.
Inventory, shelf life, waste and service outcomes are simulated.
The adapter alone does not demonstrate waste reduction.