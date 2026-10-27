# Lan's local demo

This source folder was extracted from the team's ZIP at commit
`94df1563fd8163d44d96ba91171d773590d58d71`. It is a local development copy, not a
Git clone. The demo is prepared for review on the `demo-and-submission` branch;
the branch/PR upload status is recorded separately in the development chat.

## Run

From this project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[demo]'
python -m streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed in the terminal. No CSV files, credentials or API keys
are needed for fixture mode. The seven-file research data loader is unchanged.

On Lan's current machine the local environment is already prepared. To restart,
double-click `run_demo.command` in Finder. If port 8501 is already running, use
that existing page or stop the previous server with Ctrl+C before restarting.
The tested Streamlit version is 1.66.1. This machine's environment uses the bundled
Python runtime and existing scientific packages; other machines should follow
the clean-environment installation steps above.

## What to demonstrate

1. Select Demo meal A: the synthetic forecast is 100 orders, stock is 20 portions,
   and forecast-matching preparation is 80 portions.
2. Compare the scenario rows: at demand 70 there are 30 excess portions; at demand
   130 there are 30 unmet orders. These are stress cases, not confidence intervals.
3. Change stock to 120: preparation becomes zero, and excess includes pre-existing stock.
4. Change to Demo meal B: forecast becomes 160 and its independent initial stock is 20.
5. Change the shortage penalty: high-demand scenario loss changes. Preparation
   does not change because this is a forecast-matching baseline, not optimization.
6. Enter a negative value or clear an input and commit the change: an error replaces
   the plan and scenario table. Correct the input to restore the current plan.

## Integration handoff

`app.py` handles the screen; `src/freshwise/demo.py` contains synthetic fixtures
and an explicitly named baseline. Replace the fixture provider with Silvia's
forecast adapter and the baseline call with Ari's decision adapter after agreeing
their contracts. Keep policy and provenance labels accurate. Do not copy this
baseline into a second production decision implementation.

### Proposed contract to agree before integration

Silvia's forecast record should contain `center_id`, `meal_id`, `target_week`,
`history_end_week`, `forecast_orders` and `method`. Use orders as the forecast
unit and require `history_end_week < target_week`. A calibrated interval, if
provided, needs its own coverage/calibration metadata; the fixture stress cases
are not such an interval. Anonymous IDs must retain the dataset's meaning.

Ari's decision function should accept the forecast record, usable inventory in
portions, non-negative overage/underage penalties and explicit demand scenarios.
It should return `preparation`, `baseline_preparation`, scenario results (demand,
total supply, excess, unmet orders, penalty loss), `policy` and
`assumption_version`. Future actual outcomes are evaluation inputs, not decision
inputs. Agree on rounding, cost units and any scenario probabilities explicitly.

These names are proposed handoff fields, not a claim about functions already
implemented by either teammate. An adapter can map their actual names/outputs to
the UI, so they do not need to rewrite their models to match the fixture class.
Ask each owner for a function/import path, a small runnable example, expected
output, dependencies and failure behavior. Add adapter checks for matching IDs,
target week, valid quantities and past-only history before replacing the fixture.
Remove fixture labels only after real integration is verified. If a function
fails, show an unavailable/error state rather than silently substituting examples.

The screen is not an agent. Agree on agent/tool orchestration with the team before
presenting it as one. No real orders are placed. No performance or savings claims
are supported by the fixture.

Run checks with the demo extra installed:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

Before merging into the real repository, compare against the latest team code,
transfer only the reviewed new files and dependency/docs changes, and preserve
teammates' edits. Original forecast/data modules and notebook are unchanged.
