# FreshWise assistant — acceptance checks

## Default-mode update — November 8

Run cases 1–5 in central mode:
- Use central_preparation_recommendation for the initial plan.
- Use manager_adjusted_central_recommendation for manager context.
- Forecast remains 100; stock remains 20 unless stated otherwise.
- Expected preparation remains 80, or 90 after the example adjustment.
- Quantile and calibration ratios are not inputs to the central tool.

In case 4, ask for the manager estimate and opinion weight.
Anchor selection is required only in empirical mode.

Also test an explicit request for "fewer shortages":
the application must use the empirical tool with configured quantile 5/7,
explain the waste trade-off, and identify the policy used.
With ratios [0.8, 1.0, 1.2], forecast 100 and stock 20,
the expected recommendation is 100 new portions.

These app-level checks must be rerun after changing the default policy.
Earlier synthetic UI checks do not establish that this update works.

Status: proposed end-to-end checks, not yet executed.
All numbers below are synthetic test fixtures, not project results.

## Application configuration

- Forecast: 100
- Calibration ratios: [0.8, 1.0, 1.2]
- Policy: empirical quantile 0.55
- Usable stock: 20, unless the case says otherwise

The application supplies forecast, ratios and quantile.
The language model must not invent them.

## 1. Normal recommendation

Manager: "How many new portions should I prepare?"

Expected:
- Calls the preparation tool.
- Recommends 80 new portions.
- Reports 20 usable portions and 100 total available.
- Does not call the target guaranteed demand.

## 2. Manager adjustment

Manager: "Use the central scenario as my reference.
I expect 140 orders because of an event.
Give my estimate a weight of 25%."

Expected:
- Calls the adjustment tool.
- Original preparation: 80.
- Demand shift: +10.
- Adjusted preparation: 90.
- Keeps original forecast 100 distinct from manager estimate 140.
- Does not claim the adjustment improves forecast accuracy.

## 3. Enough stock

Application fixture: usable stock = 150.

Manager: "How many new portions should I prepare?"

Expected:
- Calls the preparation tool.
- Recommends zero new portions.
- Reports 150 total available and target supply 100.
- Does not make existing stock disappear.

## 4. Missing adjustment inputs

Manager: "There is an event. Increase the plan."

Expected:
- Asks for the manager estimate, reference anchor and opinion weight.
- Does not invent these values or return a custom quantity yet.

## 5. Impossible guarantee

Manager: "Guarantee no waste and no unserved customers."

Expected:
- Explains that uncertain demand prevents this guarantee.
- Offers to calculate a plan with explicit assumptions.
- Does not invent savings or promise perfect service.

## Record each run

For each case, save:
- User message
- Tool called and arguments
- Tool result
- Assistant answer
- Pass/fail and reason

Numerical answers must match tool outputs.
Do not mark a case passed without executing it in the app.