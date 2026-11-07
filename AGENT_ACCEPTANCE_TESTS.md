# FreshWise assistant — acceptance checks

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