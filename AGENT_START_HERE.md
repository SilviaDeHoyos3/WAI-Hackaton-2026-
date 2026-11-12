# Lan's FreshWise AI conversation review package

Start the independent conversation screen; Ari can integrate the controller later.
This package contains source code and tests, not API keys or raw datasets.

## On your own machine

1. Unzip the package, then open a terminal inside `FreshWise_Lan_Agent_Review`.
2. Use Python 3.12 (3.12.16 for the recorded forecast runtime).
3. Install into a virtual environment:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements-demo-repro.txt
```

On Windows activate with `.venv\Scripts\activate` instead.

4. Put your existing four CSVs (`train.csv`, `test.csv`, `meal_info.csv`,
   `fulfilment_center_info.csv`) in a local `Data` folder here, or set
   `FRESHWISE_DATA_DIR` to their existing folder.
5. Launch:

```sh
python -m streamlit run agent_lan_demo.py --server.address 127.0.0.1 --server.port 8504
```

6. Open `http://127.0.0.1:8504`, enter your Gemini API key in the sidebar, and
   click **Load forecast and start**. API must be enabled for the key's project.
   The default model is `gemini-3.5-flash-lite`; no paid tier is required by the code.
   Actual free access depends on your project's current eligibility/quota.
7. Send "I have 20 portions ready to use. How many more should I make?"
8. Review and confirm. Then send "There's a local event. I think we'll get 600 orders."
9. Choose **Small change**, check the pending change, then confirm to apply.
10. Download the trace and share it for review. It contains no API key.

An initial key/connection error does not change your active plan. The key is kept
in the running local session only. Do not publish the test server or put the key
in messages, screenshots, files, or commits.

## Contributions and evidence

**Lan:** Gemini API integration, conversation controller, existing-tool dispatch,
confirmation state, this test interface and integration tests.
**Silvia:** forecasting model and forecasting tool.
**Ari:** preparation policy and decision tools.

Verified: live Gemini synthetic tool-call smoke test (forecast 100, stock 20,
prepare 80); 127 local unit tests; real forecast and tools with mocked provider
(453.1596995, 434 -> 470); full UI flow with mocked AI responses.
Verified live multi-turn: all seven acceptance checks passed on Lan’s machine; see
`docs/AGENT_LIVE_ACCEPTANCE.json`. Pending: teammate-machine testing and integration
into Ari’s latest interface.
The first live smoke test and the mocked full-flow checks are different evidence.

See `docs/LAN_AI_AGENT_HANDOFF.md` for the importable function, environment names,
limits and acceptance checklist. Prior UI documentation describes the earlier
manual screen in `app.py`; the new agent screen is `agent_lan_demo.py`.

## Faster live verification

Instead of manually repeating the flow, run `python scripts/check_agent_live.py`.
Enter the key once; it runs up to four real Gemini requests and saves a no-key
report in `outputs/agent_live_acceptance.json`. An error stops it without retry.
The user has already shown a successful live initial recommendation and confirmation;
this automated test checks the remaining multi-turn path as well.

See `docs/AI_PRESENTATION_GUIDE.md` for capability boundaries and presentation Q&A.

## Branded review revision

The current screen includes both original logos, warm cream/green styling,
confirmed/pending plan cards, separate connection settings and contribution credit.
The event-first clarification guard and stale-session reset were added after the
recorded live report. Current local tests and the mocked-provider full UI flow pass.
The included live report records the preceding controller source hashes; it is not
a claim that every revised UI state has been tested live. Rehearse the new screen
on the presentation laptop.
