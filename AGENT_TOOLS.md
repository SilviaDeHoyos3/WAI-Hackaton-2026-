# FreshWise decision tools — integration contract

Status: decision functions implemented; AI connection not yet implemented.
The empirical policy is supported, but the final policy is still pending
the agreed comparison. Do not silently use it if another policy is selected.

## Python functions

Module: freshwise.agent_tools

### preparation_recommendation
Inputs:
- forecast
- usable_stock
- error_ratios
- quantile

Returns:
- forecast_orders
- usable_stock
- new_portions_to_prepare
- total_available
- target_supply
- quantile
- calibration_sample_count
- policy
- manager_adjustment_applied
- assumptions

### manager_adjusted_recommendation
Same inputs, plus:
- anchor: "low", "central" or "high"
- manager_estimate: non-negative expected orders
- opinion_weight: number between 0 and 1

Returns:
- original_plan
- adjusted_plan
- manager_context
- adjustment_method

Low / central / high refer to empirical p10 / p50 / p90.
The adjustment shifts all empirical scenarios and clips demand at zero.
This is a contextual adjustment, not a newly trained forecast.

## Application-owned inputs

The application supplies:
- forecast from the forecasting tool
- calibration ratios matching the forecast method, window and size group
- explicitly configured policy quantile

Do not expose calibration ratios as arguments for the language model
to invent or populate. Wrap the Python functions with an application
lookup before registering them as AI tools.

## Manager inputs

The manager supplies or confirms:
- usable stock, unless available from a verified stock source
- chosen anchor, estimate and opinion weight for a custom adjustment

Missing adjustment inputs must be requested.
Do not silently assume an opinion weight.

## Assistant behaviour

- Call tools for calculations.
- Explain returned values without changing them.
- Keep original forecast and manager adjustment distinct.
- Target supply is a policy target, not guaranteed demand.
- Do not promise zero waste or zero unmet demand.
- Do not invent shelf life, savings, prices or stock.
- On validation or missing-calibration errors, explain the problem
  and request correction; do not fabricate a recommendation.

## Evidence boundary

These tools do not establish measured waste reduction.
Shelf life is a stated simulation assumption.
Tests of Python tools do not replace end-to-end conversation tests.