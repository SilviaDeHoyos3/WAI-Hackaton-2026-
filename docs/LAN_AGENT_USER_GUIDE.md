# FreshWise AI Conversation Guide

User testing, demonstration and capability boundaries | Prepared by Lan | November 11, 2026

FreshWise is a focused preparation-planning prototype for one selected meal. The assistant collects ready-to-use stock and a manager’s order estimate, requests existing tools, and presents a plan for human review. It does not run a restaurant or send instructions to a kitchen.

### What the assistant does

Select a centre and meal, load the forecast, describe available portions, review the recommendation, add an order estimate if needed, choose its influence, and explicitly confirm the plan. Numerical recommendations come from the decision tools, not the language model.

| Contributor | Contribution |
| --- | --- |
| Lan | Conversation interface, Gemini integration, application-tool dispatch, plan preview and confirmation flow, integration tests and handoff documentation. |
| Silvia | Forecasting model and forecast tools, uncertainty information and forecasting assumptions. |
| Ari | Preparation policies and decision tools. Integration of the conversation module into the updated team demo and final rehearsal was proposed in the team handoff. |

### Reference case

Centre 13, Meal 1198, Week 146: the recorded local forecast was 453.1596995 orders. With 20 ready portions, the tool returned 434 NEW portions. A manager estimate of 600 orders with Small change (25%) returned 470 NEW portions. The change means 36 additional portions to prepare, not 36 additional forecast orders.

These are reference results, not fixed responses. Always compare the chat and manual controls using the same forecast and inputs. A previously observed 453.16 versus 455.0 forecast difference between environments remains unresolved; do not alter values manually to match.

### Evidence and status

The recorded real Gemini flow passed seven acceptance checks using real local forecast and decision tools. The current local test suite contains 127 passing unit tests, and the offline real-data UI check passed with a mocked provider. The live report predates later event-first protection and interface refinements; rehearse the current revision on the presentation laptop.

Model configuration: Gemini API, default model gemini-3.5-flash-lite. Settings: GEMINI_API_KEY and GEMINI_MODEL. Free-tier availability and quotas depend on the account; successful local testing does not guarantee availability during a presentation.

## A complete demonstration conversation

Load Centre 13 and Meal 1198 before starting. Copy the short messages below. Reference quantities assume the recorded local forecast; check the actual tool output if the context changes.

### 1 Request the initial plan

I have 20 portions ready to use. How many more should I make?

Expected result: use 20 ready portions first and prepare 434 NEW portions. The result is a pending preview. Click Confirm and apply plan to make it the active plan in this demo.

### 2 Mention an event without an estimate

There’s a local event.

Expected question: About how many orders do you expect for this dish next week? The assistant must not guess the event’s effect.

### 3 Supply the manager estimate

I think we will get 600 orders for this dish next week.

Expected result: record 600 and ask how strongly to move toward it. Use one of the displayed buttons: Small change (25%), Meet halfway (50%), or Use my estimate (100%).

### 4 Preview a small adjustment

Click Small change

Expected result: 434 → 470 NEW portions, retaining 20 ready portions. The previously confirmed plan must remain unchanged until confirmation.

### 5 Review and apply

Click Confirm and apply plan

The pending recommendation becomes the active plan within the demo. No order, stock deduction or kitchen instruction is sent. Discard preview removes the pending plan and keeps the active plan.

### What to verify

Check that NEW portions and ready portions remain separate. Check Active plan before and after confirmation. Expand Exact tool trace and forecast context to inspect the tool name, inputs and output. Never include an API key in screenshots or shared files.

### Recommended presentation order

Demonstrate the basic recommendation, missing-estimate question, adjustment preview and confirmation. Show the tool trace if asked. Treat untested paraphrases as exploratory tests rather than guaranteed behavior.

## Additional input categories to test

No list can cover every possible sentence. These examples cover the main input categories. They describe expected handling; they are not claims that every exact wording has passed a live API test.

### Zero ready portions

I have 0 portions ready to use. How many more should I make?

Zero is valid. With the reference forecast, the central policy should return 454 new portions after rounding up. This is an expected calculation, not a new live-test result.

### Enough ready stock

I have 500 portions ready to use. How many more should I make?

The central policy should return 0 new portions. The app does not verify that the stated stock exists or is safe to use.

### Missing stock

How many portions should I prepare next week?

Ask how many portions are ready to use. Do not assume zero stock.

### Correcting stock

Actually, I have 30 portions ready to use. How many more should I make?

Request a new tool calculation and create a preview. Check that the trace uses 30; do not rely on conversational wording alone.

### Invalid stock

I have -5 portions ready to use. / I have 2.5 portions ready to use.

Ready stock must be a nonnegative whole number. Invalid values must not produce a valid plan. The manager estimate must also be finite and nonnegative.

### Several requests in one message

I have 20 portions ready and expect 600 orders because of an event.

Split this into two messages: stock first, then the manager estimate. At most one tool call is accepted per message.

### Changing the selected meal

Can you plan Meal 2444 instead?

Use the sidebar meal selector and reload the forecast to reset the conversation context. A chat message does not replace the application selection.

Chinese, typos, long messages and unfamiliar paraphrases can be explored, but have not been comprehensively validated. Messages over 4,000 characters are rejected. Use the short demonstration messages for the main presentation.

## Capability boundaries and failure handling

| Question or request | Current boundary |
| --- | --- |
| Can you guarantee zero waste and no missed orders? | No. Demand is uncertain. A preparation plan is conditional on its inputs and policy. |
| How much waste will we have next week? | No specific next-week waste, shortage or carbon forecast is provided. Use the separately labelled Impact simulations for historical comparisons. |
| Is this leftover food safe to eat? | No food-safety, storage-condition or expiry verification. A person must confirm stock is usable before entering it. |
| Order ingredients and send this to the kitchen. | No purchasing, kitchen orders, real stock deductions or operational execution. |
| Plan every dish and allocate ingredients. | One selected meal at a time. No joint menu optimization, recipes or ingredient-inventory allocation. |
| What events are nearby? | No connected event search, weather feed or other live external context. The manager supplies an estimate. |
| Remember my restaurant next month. | No persistent business memory across sessions. Do not rely on state surviving a restart or refresh. |

### Human control and tool boundaries

The application supplies the selected meal, forecast and planning context. Gemini extracts manager inputs and requests tools. The controller uses freshwise.application_tools.invoke for numerical decisions. Numerical explanations are templates populated from tool results. Input extraction can still fail; validation and human review remain necessary.

Use the adjustment and confirmation buttons. Typing yes or apply it does not replace the confirmation button. Confirmation changes the active plan only inside this prototype.

### Provider or network errors

403 means access was denied; 429 indicates a rate limit; 503 indicates temporary provider unavailability. Network failure or a timeout can also occur. The assistant displays a short error and preserves the active plan. There is no automatic retry. Use the manual app as a fallback, clearly identifying it as a manual workflow.

Scope protection is deliberately conservative: messages mentioning waste, shortages, carbon or guarantees may receive a boundary explanation rather than a new calculation. Separate such questions from stock and estimate inputs.

## Presentation answers and team handoff

### A short introduction

Our assistant helps a manager plan preparation for one selected dish. It collects ready-to-use stock and the manager’s order estimate, then calls our existing tools. The manager reviews and confirms the plan. It does not verify food safety, execute kitchen orders, or guarantee waste reduction.

### What does AI add to the manual interface

The manual interface uses explicit controls. The assistant lets the manager describe stock and an event in everyday language, asks for missing information, and connects those inputs to the same decision tools. The numerical calculation remains in the tools.

### What did Lan build

I built the conversation interface and Gemini integration, connected the assistant to our application tools, and added plan previews, confirmation controls and conversation tests. Silvia built the forecasting component, and Ari built the preparation decision tools.

### How to run and test

Start with AGENT_START_HERE.md in the repository. Configure a personal Gemini API key and the four required local CSVs. Launch the separate chat with:

python -m streamlit run agent_lan_demo.py --server.port 8504

Integration entry points: PreparationAgent(context, GeminiClient(...)), send(message), choose_weight(label), confirm(), and cancel_preview(). The host application must supply the forecast and selected meal context. Detailed integration notes are in docs/LAN_AI_AGENT_HANDOFF.md.

### Branch and pull request

Lan’s source branch is lan/ai-assistant-integration. PR #4 shares those changes for review. A draft PR is already uploaded and can be downloaded and tested; it has not been marked ready to merge. A merge adds changes to the PR’s target branch. The target branch does not change the authors of existing commits.

This integration builds on the existing forecasting and decision components. The previously checked PR target was ari/agent-decision-tools. Component ownership remains as listed on the first page.

### Before the presentation

Run the complete conversation on the presentation machine, verify agreement with manual controls, verify that confirmation is required, and check missing-input and provider-error handling. Keep a clearly labelled manual fallback. Confirm the final integration branch and presentation roles with the team.

PR: https://github.com/SilviaDeHoyos3/WAI-Hackaton-2026-/pull/4
