# Lan — FreshWise interface and tool integration

## Public hackathon deployment

Deploy `app.py` from `ari/mockup-demo` with Python 3.12. In Streamlit
Community Cloud, add the following top-level setting under **Secrets** before
starting the app:

```toml
FRESHWISE_PUBLIC_DEMO = "1"
```

The public app uses the recorded forecast for centre 13, dish 1198, week 146.
It runs the same preparation and adjustment tools without raw CSVs or Gemini.
To check the deployment, enter 20 ready portions and make the plan. It should
recommend 434 new portions. Preview 600 expected orders with **Small change**
and check that the recommendation moves to 470.

Updated November 9. Real teammate tools are connected using explicit controls
and response templates. No language model, API key or paid API is used.

## Sources and contribution

- Ari's decision-tool archive: `525a9a8b501169daa8a2c785b03edd135e98cf09`.
- Silvia's forecast archive: `b16d4517055027e4034970830b3dea4495198ed1`.
  Its updated `agent_data_tools.py` and tests replace the earlier copy on Ari's branch.
  Other shared Python modules are identical between the supplied archives.
- Lan: Streamlit interface, application adapter, application tests and handoff.

Review branch: `lan/ai-assistant-integration` (based on Ari commit above).
The old `demo-and-submission` branch shows a different preview. A local backup preserves the previous integration.

## Open on Lan's machine

Double-click `run_preview.command`, then open http://localhost:8502.
Choose **Real next-week forecast**, centre **13**, meal **1198**, then
**Load next-week forecast**. First model fitting takes longer; later requests
for the same centre reuse the teammate cache.

Enter usable stock after checking expiry. Check **Include manager adjustment**
to supply an estimate and explicit percentage weight. Download the JSON trace
to review exact forecasts, arguments and answers with Ari and Silvia.

## Install elsewhere

From the project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[demo]'
export FRESHWISE_DATA_DIR='/absolute/path/to/Data'
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

Required CSVs: `train.csv`, `test.csv`, `meal_info.csv`,
`fulfilment_center_info.csv`. Data files are not included in the code package.
The UI uses Silvia's `context_from_tables` for these four files, preserving the
shared research loader unchanged. Without the environment variable it checks
project `data/`, project `Data/`, then sibling `Data/`.

## What works and what remains

- Central default: full-precision forecast minus usable stock, rounded up,
  lower bounded at zero. Rounded display values never enter the calculations.
- Manager adjustment uses the original forecast as reference and requires only
  manager estimate and weight. Original and adjusted quantities remain separate.
- Live planning uses history through week 145 and week-146 prices/promotions.
  This is not a final-evaluation run. The actual method and fallback provenance show.
- Missing inputs request information; errors and meal changes clear stale plans.
- Fewer-shortages q=5/7 works only in the labelled synthetic acceptance example.
  Real use requires matching calibration ratios. Forecast-range endpoints are
  not substituted for calibration ratios.
- Development evidence comes unchanged from Silvia's tool. Its supplied snapshot
  still says final evaluation is pending. No final-results claim is added.
- One extra week of storage remains an assumption. Current stock is a manager
  input. The UI does not check expiry, run the stock simulator, optimize capacity
  or predict individual-plan waste/unmet orders.
- AI orchestration and real conversation acceptance remain to be implemented;
  confirm ownership with Ari/Silvia. The current preview does not parse free text.

## Run checks

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 python -m unittest discover -s tests -v
PYTHONPATH=src OMP_NUM_THREADS=1 python scripts/check_application_acceptance.py
PYTHONPATH=src OMP_NUM_THREADS=1 python scripts/check_live_application.py
```

The scripted UI check covers five central cases, synthetic fewer-shortages, and
invalid/missing stock. The live UI check loads the real menu and forecast,
verifies central and adjusted quantities, and invalidates the plan on meal change.
Reports are saved in `outputs/`. These are tool/UI tests, not AI conversations.
Do not rerun or tune the frozen final evaluation as part of UI work.
