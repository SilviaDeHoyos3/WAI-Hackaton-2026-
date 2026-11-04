# Decision evaluation — development example

## Setup

- Centre: 13.
- Meals: 2306, 2444, 1198, 2664.
- Target week: 126; forecasting history through week 125.
- Forecast method: last.
- Scenario ranges: empirical, calibrated on weeks 116–125.
- Scenario weights: equal, explicitly assumed.
- Simulated usable inventory: 40 portions per meal.
- Overage penalty: 2; underage penalty: 5.
- One order is assumed to correspond to one portion.
- No manager adjustment was applied.

## Results

| Policy | Excess portions | Unmet orders | Total penalty |
|---|---:|---:|---:|
| Central-forecast baseline | 107 | 217 | 1299 |
| Scenario optimization | 571 | 0 | 1142 |

Scenario optimization reduced simulated penalty by 157
(approximately 12.1%), while increasing excess by 464 portions.

The aggregate benefit was driven by meal 2664.
The scenario policy had higher penalties for the other three meals.

## Limits and next evaluation

This is one development week, not the final evaluation.
It does not establish real-world waste reduction or general superiority.

Next: evaluate weeks 126–135 with the same four meals,
inventory rule and penalties. Keep weeks 136–145 reserved
for the frozen final evaluation.

## Development evaluation: weeks 126–135

Same four meals at centre 13; 40 observed cases per policy.
No missing outcomes. Inventory=40, overage penalty=2,
underage penalty=5. No manager adjustment.

| Policy | Excess | Unmet | Total penalty |
|---|---:|---:|---:|
| Central-forecast baseline | 1992 | 2023 | 14099 |
| Equal-weight scenario optimization | 7339 | 597 | 17663 |

The scenario policy increased total penalty by approximately
25.3%, despite reducing unmet orders by approximately 70.5%.

It had higher aggregate penalties for every meal and lower
penalties in only four of ten weeks.

The week-126 result alone was not representative of the
full development window. No general improvement is established.

## Interpretation and next investigation

The optimizer minimizes loss under its supplied discrete
scenarios, not under an established true demand distribution.

Equal weights on empirical lower bound, central forecast
and upper bound are an approximation, not estimated probabilities.

Keep the baseline as the current lower-penalty benchmark.
Investigate a demand representation based on historical
forecast errors rather than assuming equal mass at three points.

Do not change penalties merely to obtain an improvement.
Weeks 136–145 remain reserved for final frozen evaluation.
Any revised method must be documented as developed after
inspecting weeks 126–135.

## Revised empirical policy — development results

The revised policy uses historical actual/forecast ratios
from weeks 116–125, grouped into the same forecast-size tiers
as Silvia's range model.

Each historical ratio generates one demand scenario.
Preparation minimizes empirical mean penalty using the
newsvendor critical fraction and integer candidate comparison.

Evaluation: the same 40 cases in weeks 126–135.
Inventory=40, overage penalty=2, underage penalty=5.

| Policy | Excess | Unmet | Penalty |
|---|---:|---:|---:|
| Baseline | 1992 | 2023 | 14099 |
| Empirical | 3173 | 1456 | 13626 |
| Three equal-weight scenarios | 7339 | 597 | 17663 |

Empirical penalty was approximately 3.4% below baseline,
with approximately 28% fewer unmet orders and 59% more excess.

It won in six of ten weeks and three of four meal aggregates.
Meal 1198 contributed 488 penalty units of improvement;
the remaining three meals combined worsened by 15.

This method was developed after inspecting this evaluation
window. These are development results, not independent
final-test evidence or measured waste reduction.

Candidate next step: freeze the empirical specification,
implement and test its reusable function, and coordinate
the change with Silvia and Lan before final evaluation.

## Sustainability and service trade-off

Development sample: 40 cases, 13,951 observed orders.

| Policy | Excess | Unmet | Simulated orders fulfilled |
|---|---:|---:|---:|
| Baseline | 1992 | 2023 | 85.50% |
| Empirical 50th percentile | 1412 | 2567 | 81.60% |
| Empirical 60th percentile | 2097 | 1959 | 85.96% |

The 50th-percentile policy reduced excess by 29.1% but
reduced fulfilled-order share by 3.90 percentage points,
leaving 544 additional orders unmet.

None of the nine tested quantile policies reduced excess
without increasing unmet orders relative to baseline.

No acceptable service threshold has yet been agreed.
These results do not establish waste reduction at maintained
service, or real-world deployment benefits.

Next investigation: forecast quality and the relevance of
pooled historical errors, coordinated with Silvia.
Do not choose a finer quantile solely to fit these 40 cases.