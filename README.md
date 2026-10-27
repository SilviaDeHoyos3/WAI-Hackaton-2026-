# FreshWise

Weekly prepared-meal order forecasting, followed by explicitly simulated inventory decisions.
The source data do not validate grocery replenishment, observed food waste or actual carbon savings.

## Interactive fixture demo (Lan)

```sh
python -m pip install -e '.[demo]'
python -m streamlit run app.py --server.address 127.0.0.1
```

Activate your project environment first. This one-screen prototype uses synthetic
meals and a forecast-matching baseline; it needs no source CSVs or API keys.
It is not connected to the team's forecast or optimized policy and is not an AI
agent. See [the demo guide](docs/demo.md) for setup, checks and integration steps.

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
