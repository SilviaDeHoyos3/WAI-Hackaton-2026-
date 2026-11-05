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

## Quantile selection — proposal for team approval

This procedure is proposed, not yet agreed or implemented.

- Candidate quantiles: 0.1, 0.2, ..., 0.9.
- Select one quantile per forecast method, shared across the four
  demo meals. Error-ratio distributions may still differ by size group.
- For evaluation A (106–115), use only calibration weeks 96–105
  to select the quantile.
- For evaluation B (126–135), use only calibration weeks 116–125
  to select the quantile.
- Simulate each candidate with the same carry-over accounting.
- On the calibration window, select the candidate with the lowest
  waste rate among those whose unmet rate is no higher than the
  last-forecast central baseline without carry-over.
- Break ties by lower unmet rate, then lower quantile.
- If no candidate qualifies, report this and retain the baseline
  for that window.
- Freeze the selected quantile before evaluating the next window.
- Never change this procedure to improve evaluation results.

These remain development comparisons: these periods have already
been examined. This procedure does not make them untouched test data.
The team must separately freeze the procedure for weeks 136–145.