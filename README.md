## AI conversation demo by Lan

Run `python -m streamlit run agent_lan_demo.py --server.port 8504` after following
[AGENT_START_HERE.md](AGENT_START_HERE.md). This separate Gemini-powered conversation
prototype reuses the existing forecasting and decision tools, previews manager
adjustments and requires confirmation before updating a demo plan. The manual
`app.py` remains available. Provider key: `GEMINI_API_KEY` or the local password
field; model: `GEMINI_MODEL` (default `gemini-3.5-flash-lite`). No key is included.

Lan: conversation interface and AI integration. Silvia: forecasting model and tools.
Ari: preparation policy and decision tools. See
[the handoff](docs/LAN_AI_AGENT_HANDOFF.md) and
[presentation scope/Q&A](docs/AI_PRESENTATION_GUIDE.md).

Verification: 127 local unit tests and the current mocked-provider real-data UI
flow pass. The recorded real Gemini conversation passed all seven checks on Lan's
machine before the later event-first guard and visual refinements; its source
hashes are preserved in `docs/AGENT_LIVE_ACCEPTANCE.json`. Rehearse the current
revision and teammate-machine setup before presentation. No final evaluation rerun.

## Kitchen-pass update and aligned runtime

The prep ticket shows existing ready-to-use stock alongside new preparation, with
an explicit manager-adjustment delta. Both original logos are included. The relay
is a labelled synthetic two-week example calculated by the shared simulator.
The plate grids use the final simulation percentages **reported by Silvia in the
group update**, with the all-meal service deterioration shown separately. The full
final-run tables/manifest have not been independently imported or verified here.

Use Python **3.12.16** and install the recorded numerical versions in a fresh env:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-demo-repro.txt
export FRESHWISE_DATA_DIR='/absolute/path/to/Data'
python -m streamlit run app.py --server.port 8502
```

Check `python --version` first: `python3.12` may point to another patch release.
The pins are NumPy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1 (UI: Streamlit 1.66.1).
Do not rerun the frozen final-evaluation script to test the interface.

Local reproduction with those four versions still returned **453.15969951433823**
for centre 13 / meal 1198 / week 146. Therefore version alignment alone did not
reproduce Silvia's 455.0 example. The reported difference is about 0.4% for this
case, not a universal bound. Source revision, data hashes and other dependencies
also matter. See `docs/RUNTIME_REPRODUCTION.md` and the trace for the unresolved
comparison. The exact forecast from the same tool call always feeds the decision.

# FreshWise — Lan interface integration

Start with [LAN_START_HERE.md](LAN_START_HERE.md) for the current manager interface,
setup and checks. It connects real forecast and decision tools; no AI model is
connected. Interface/integration: Lan; forecasting: Silvia; decisions: Ari.
Review branch: `lan/ai-assistant-integration`. See LAN_START_HERE.md for launch instructions.

---

# FreshWise

Weekly prepared-meal order forecasting, followed by explicitly simulated inventory decisions.
The source data do not validate grocery replenishment, observed food waste or actual carbon savings.

## Start in VS Code

Open `freshwise.code-workspace`. Install the recommended Python and Jupyter extensions.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Select `.venv` as the notebook kernel and open `notebooks/01_data_and_baselines.ipynb`.
The local machine may already have a prepared environment; use it if present.
Set `FRESHWISE_DATA_DIR` if automatic local data discovery does not find your files.

```sh
python -m freshwise
python -m unittest discover -s tests -v
```

## Structure

- `notebooks/`: exploration and interpretation; reusable logic lives in `src/freshwise/`.
- `src/freshwise/`: read-only source loading, validated joins and chronological baseline backtests.
- `tests/`: checks for leakage, unseen-pair fallback and invalid joins.
- `data/`: documentation only; original CSVs stay outside Git.
- `outputs/`: local generated results, excluded from Git.

## Evaluation contract

Backtests start after weeks 115, 125 and 135, each predicting the next ten weeks.
They compare last-observed orders with a mean of the last four observed rows per pair.
Neither baseline uses held-out outcomes. Unseen pairs use a recent meal mean, then global mean.
Missing rows are not converted to zero. Scores cover observed holdout rows only.
The last window should be reserved for final evaluation once model tuning begins.
WAPE is stored as a fraction. Currency, actual dates and unconstrained demand are not established.

## Next work

1. Inspect sparse histories and subgroup errors; compare a feature-based model using past-only features.
2. Choose a decision horizon consistent with weekly observations.
3. Simulate ordering with clearly labelled inventory, shelf-life, cost and lead-time assumptions.
4. Compare ordering policies on identical held-out outcomes and assumptions.
5. Add recipe-based carbon illustrations only after ingredient masses and compatible factors exist.

FAOSTAT export: Canada, 2013–2023; filter intensity rows and units before use.
Do not pool emissions totals (`kt`) with intensities (`kg CO2eq/kg`).
TPFLW combines methods and supply-chain stages; do not treat its overall mean as a retailer waste rate.
No credentials or raw datasets belong in this repository. No data redistribution licence is assumed.
