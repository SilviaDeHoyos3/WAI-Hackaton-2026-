# FreshWise — decision module

## Entry point

```python
from freshwise.decision import compare_preparation_plans

result = compare_preparation_plans(
    inventory=20,
    demand_scenarios=[70, 100, 130],
    overage_cost=2,
    underage_cost=5,
    anchor_index=1,
    manager_estimate=140,
    opinion_weight=0.25,
)
```

## Inputs

- inventory: usable portions already available.
- demand_scenarios: low, central and high demand, in this order.
- overage_cost: assumed penalty per excess portion.
- underage_cost: assumed penalty per unfulfilled order.
- anchor_index: selected scenario; 0=low, 1=central, 2=high.
- manager_estimate: manager's demand estimate.
- opinion_weight: manager opinion weight from 0 to 1, not 0 to 100.

The demo assumes one order corresponds to one portion.
The three demand scenarios receive equal weights.

## Outputs

- inputs: inventory, penalties and manager adjustment inputs.
- original_scenarios: original demand scenarios.
- custom_adjustment: weighted anchor, adjustment and updated scenarios.
- original_plan: preparation quantity and average loss on original scenarios.
- custom_plan: preparation quantity and average loss on updated scenarios.
- loss_comparison: both plans evaluated on both scenario sets.

## Expected example

- Updated scenarios: [80, 110, 140].
- Original preparation: 110 new portions.
- Custom preparation: 120 new portions.

| Plan | Loss on original scenarios | Loss on updated scenarios |
|---|---:|---:|
| Original | 60 | 63.3333 |
| Custom | 80 | 60 |

These are simulated penalties, not measured financial savings.

## Interface requirements

- Convert a displayed weight of 25% to 0.25.
- Show which scenario set each loss refers to.
- Keep the manager's reason alongside the calculation;
  the function does not currently receive or store that reason.
- Catch ValueError and show a clear input error.
- Numeric validation rejects negative values, NaN, infinity,
  text, missing values and booleans in the validated fields.
- anchor_index must be an integer; decimal values and booleans
  are rejected. NumPy numeric types are supported.
- Inventory must represent whole portions: 20 and 20.0 are
  accepted; 20.5 is rejected.
- compare_preparation_plans requires exactly three scenarios
  ordered as low <= central <= high. Equal values are accepted.
- The lower-level optimization functions remain general and
  can evaluate a different number of scenarios.
- No forecasting model is called here: scenarios are supplied as inputs.
- The function does not place orders or save results permanently.