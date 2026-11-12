# FreshWise conversation integration by Lan

Lan implemented the Gemini provider connection, separate conversation controller,
plain test screen, confirmation state, and integration checks. Silvia owns the
forecasting tool and Ari owns the preparation decision tools. The controller reuses
`freshwise.application_tools.invoke`; it does not replace their numerical functions.

## Current verification status

The user executed the first live synthetic test successfully: Gemini 3.5 Flash Lite
requested `central_preparation_recommendation(usable_stock=20)`, the real adapter
used the synthetic forecast 100 and returned 80 new portions, and the model
replied: "Use your 20 existing portions first, then prepare 80 new portions."

The complete controller has 12 additional offline tests (127 project tests pass).
These mock provider responses and test actual tool calculations and state changes.
They are not evidence of a completed live multi-turn conversation. The real-data forecast and manual-versus-controller comparison are checked separately.
The user has now executed the full live acceptance: all seven checks passed;
see `docs/AGENT_LIVE_ACCEPTANCE.json` in the review ZIP.
No final evaluation is rerun or modified by this integration.

## Setup

Use the numerical runtime in `requirements-demo-repro.txt`, Python 3.12.16.
Install the project, then the demo requirements in your own virtual environment:

```sh
python -m pip install -e .
python -m pip install -r requirements-demo-repro.txt
export FRESHWISE_DATA_DIR='/absolute/path/to/Data'
export GEMINI_MODEL='gemini-3.5-flash-lite'
python -m streamlit run agent_lan_demo.py --server.address 127.0.0.1 --server.port 8504
```

Provider variables: `GEMINI_API_KEY`, `GEMINI_MODEL`. Enter the key in the local
password field instead of setting the environment variable if preferred. The
controller also accepts an explicit key. Never commit keys. The localhost test
screen does not save the key to a file or put it in downloadable traces. It holds
the key in server memory for that conversation. Raw order CSVs stay local.

## Entry points for Ari's updated interface

```python
from freshwise.conversation_agent import PreparationAgent, GeminiClient

# context is the selected dish's existing PlanningContext, from forecast_tool
# through application_tools.context_for_meal; it is not supplied by the model.
agent = PreparationAgent(context, GeminiClient())
reply = agent.send(manager_message)
preview = agent.choose_weight('Small change')  # 25%; also 50% and 100% choices
applied = agent.confirm()  # only a separate explicit confirmation applies a plan
```

Retain one agent per session and selected dish. Create a new agent when the dish,
forecast or planning context changes. Replies contain `answer`, `active_plan`,
`pending_plan`, and `weight_choices`. Exact calls and tool results are in
`agent.trace`. An error response leaves the active plan unchanged; the manager can
retry. Apply confirmation from a real UI control, never from a model tool call.

The model extracts stock or records an explicit manager estimate. Adjustment
weight comes from the manager's selected button, not model-generated numbers.
The central and adjusted results use the same stored full-precision forecast.
The controller generates its numerical explanation from exact tool outputs using
templates, conserving requests and avoiding another LLM arithmetic step.

## First live acceptance flow

1. Start the screen, enter key, select Centre 13 / Meal 1198 and load forecast.
2. Send: "I have 20 portions ready to use. How many more should I make?"
3. Check the central tool trace; review and confirm the initial plan.
4. Send: "There's a local event. I think we'll get 600 orders."
5. Select **Small change**. Compare the pending quantity with the manual adapter
   for stock 20 / manager estimate 600 / weight .25 using this exact forecast.
   434 -> 470 was the prior local example, not a hard-coded acceptance value.
6. Confirm that the active plan remains unchanged until **Confirm and apply plan**.
7. Download the no-key trace for joint review.
8. In a new session send "There's an event" without an estimate. Check that it
   asks "About how many orders do you expect for this dish next week?" and makes
   no numerical recommendation. Also test missing stock, 0 stock and API failure.

## Limits

This is an early prototype, not a public deployment. The full live multi-turn acceptance passed on Lan’s machine. Free-provider limits and availability still apply. Each
message uses at most one provider request and one local tool call; no automatic
retry is performed. No inventory is deducted and no external kitchen action is
sent. Initial and adjusted plans both need confirmation. This screen has no
imported, verified simulation impact table, so it cannot provide specific waste
comparisons; use the separately labelled Impact screen. Next-week waste/shortage
quantities and guarantees are not supported. Model compliance on arbitrary text
is not established by the mocked tests.

## Final local review additions

See `docs/AI_PRESENTATION_GUIDE.md` for capabilities, limitations and judge Q&A.
The updated UI can discard a preview, exposes safe error categories, and explicitly
labels confirmation as an update inside the demo. Scope guards refuse waste/shortage
forecasts and guarantees without using the model. The original manual `app.py` is
the network-independent fallback; switching to it is a deliberate user action.

Run `python scripts/check_agent_live.py` to perform the four-request live acceptance
with one hidden-key prompt. It writes `outputs/agent_live_acceptance.json` and
records checks even when a step fails. Do not claim a complete live pass unless
`all_checks_pass` is true. `python scripts/check_agent_offline.py` uses a mocked
provider and is separately labelled. No current public deployment is included.

## Branded review revision

The current screen includes both original logos, warm cream/green styling,
confirmed/pending plan cards, separate connection settings and contribution credit.
The event-first clarification guard and stale-session reset were added after the
recorded live report. Current local tests and the mocked-provider full UI flow pass.
The included live report records the preceding controller source hashes; it is not
a claim that every revised UI state has been tested live. Rehearse the new screen
on the presentation laptop.
