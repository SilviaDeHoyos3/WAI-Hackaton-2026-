"""FreshWise preparation planner, using the team's forecast and decision tools."""
import base64
from html import escape
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

import streamlit as st
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from freshwise.agent_data_tools import evidence_tool, menu_tool
from freshwise.carryover import prepare_forecast_minus_leftovers, simulate_carryover
from freshwise.conversation_agent import GeminiClient, PreparationAgent
from freshwise.local_credentials import normalize_gemini_key, read_gemini_key, save_gemini_key
from freshwise.next_week import RANGE_SOURCE
from freshwise.application_tools import (
    DATA_FILES,
    PlanningContext,
    context_for_meal,
    get_context,
    invoke,
    load_application_data,
    reject_guarantee,
    resolve_data_dir,
)

CENTRAL = "central_preparation_recommendation"
ADJUSTED = "manager_adjusted_central_recommendation"
EMPIRICAL = "preparation_recommendation"
PUBLIC_DEMO = os.getenv("FRESHWISE_PUBLIC_DEMO") == "1"
PUBLIC_FORECAST = {
    "center_id": 13, "meal_id": 1198, "target_week": 146,
    "forecast_orders": 453.15969951433823,
    "range_low": 299.08540167946325, "range_high": 666.5979179855916,
    "range_low_display": 299.1, "range_high_display": 666.6,
    "method": "hgb", "is_fallback": False, "range_source": RANGE_SOURCE,
    "provenance": "Precomputed FreshWise forecast for the hackathon demo case.",
    "recent_orders": [],
}
ADJUSTMENTS = {"Small change": 0.25, "Meet halfway": 0.5, "Use my estimate": 1.0}
IMPACT = {
    "Four demo meals": ((16.6, 1.5), (18.8, 7.2)),
    "All meals": ((17.9, 2.2), (16.7, 20.6)),
}
CASES = {
    "1. Normal recommendation": "How many new portions should I prepare?",
    "2. Manager adjustment": "I expect 140 orders because of an event. Give my estimate a weight of 25%.",
    "3. Enough stock": "How many new portions should I prepare?",
    "4. Missing adjustment inputs": "There is an event. Increase the plan.",
    "5. Impossible guarantee": "Guarantee no waste and no unserved customers.",
    "6. Fewer shortages (synthetic calibration)": "Use the fewer-shortages policy and explain its trade-off.",
}


@st.cache_resource(show_spinner=False)
def get_data(path, signature):
    return load_application_data(path)


@st.cache_data(show_spinner=False)
def get_live_context(path, signature, center_id, meal_id):
    with threadpool_limits(limits=1):
        return context_for_meal(center_id, meal_id, get_data(path, signature))


@st.cache_data(show_spinner=False)
def image_data(name):
    raw = (ROOT / "assets" / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def call_tool(tool, arguments, context):
    try:
        return invoke(tool, arguments, context=context)
    except (TypeError, ValueError, OverflowError) as exc:
        return {"status": "error", "tool_call": None, "result": None, "answer": str(exc)}


def show_trace(response, user_message, mode):
    with st.expander("Verification prompts and exact tool trace"):
        st.chat_message("user").write(user_message)
        if response:
            st.chat_message("assistant").write(response["answer"])
            st.json(response)
            st.download_button(
                "Download current trace",
                data=json.dumps({"user_message": user_message, "mode": mode,
                                 "llm_connected": False, **response}, indent=2),
                file_name="freshwise_plan.json",
                mime="application/json",
            )


def info(label, explanation):
    return (
        f'<details class="inline-info"><summary aria-label="{escape(label)}">i</summary>'
        f'<span>{escape(explanation)}</span></details>'
    )


def show_plan(plan, forecast, adjusted=False):
    stock = plan["usable_stock"]
    new = plan["new_portions_to_prepare"]
    total = plan["total_available"]
    stock_share = 100 * stock / total if total else 0
    label = "Adjusted plan" if adjusted else "Current plan"
    target = f" · Adjusted target: {plan['target_supply']:,.0f}" if adjusted else ""
    st.html(f'''
        <section class="ticket">
          <span class="badge">{label}</span>
          <div class="quantity">{new:,}</div>
          <div class="info-heading"><h2>New portions to prepare</h2>
            {info("About new portions", "How many more portions to make after counting the ones you already have.")}
          </div>
          <p>Use these first: <strong>{stock:,} ready portions</strong></p>
          <div class="bar-labels"><span>{stock:,} ready portions</span><span>{new:,} new portions</span></div>
          <div class="portion-bar" role="img" aria-label="{stock} ready and {new} new portions">
            <span style="width:{stock_share:.8f}%"></span>
            <span style="width:{100 - stock_share if total else 0:.8f}%"></span>
          </div>
          <div class="total">{total:,} total available after prep</div>
          <div class="info-heading"><p class="subtle">Expected orders: about {forecast:,.0f}{target}</p>
            {info("About expected orders", "FreshWise estimates next week’s orders from past orders and planned prices and promotions. An adjusted target includes your estimate.")}
          </div>
        </section>
    ''')


def show_adjustment(context, stock, base, identity):
    st.html('<h2 class="adjustment-title">Expect a busier or quieter week?</h2>')
    if not base or base["status"] != "success":
        st.caption("Make your prep plan first. Then see how it changes with your own estimate.")
        return base

    estimate = st.number_input("How many orders do you expect?", min_value=0.0, value=None, step=1.0,
                               key="estimate", placeholder="e.g. 600",
                               help="Enter the total orders you expect for this dish next week. For example, enter 600 if a local event could bring more customers.")
    choice = st.radio("How far should we move toward your estimate?", list(ADJUSTMENTS),
                      horizontal=True, key="adjustment_choice",
                      help="Small change moves the plan a quarter of the way toward your estimate. Meet halfway gives both estimates equal say. Use my estimate plans around your number.")
    if estimate is None:
        return base

    draft = call_tool(ADJUSTED, {"usable_stock": stock, "manager_estimate": estimate,
                                "opinion_weight": ADJUSTMENTS[choice]}, context)
    if draft["status"] != "success":
        st.error(draft["answer"])
        return base

    applied = st.session_state.get("applied_plan")
    if applied == draft:
        st.success("Adjustment applied to the prep plan.")
        return draft
    current = applied["result"]["adjusted_plan"] if applied else base["result"]
    old = current["new_portions_to_prepare"]
    new = draft["result"]["adjusted_plan"]["new_portions_to_prepare"]
    delta = new - old
    st.html(f'''
        <div class="preview"><div class="info-heading"><span class="badge amber">Preview</span>
          {info("About this preview", "The first number is your current prep plan. The second is the updated plan. Select Use this plan to apply the change.")}
          </div>
          <div class="preview-quantity">{old:,} → {new:,}</div>
          <span class="badge amber">{delta:+,} portions</span>
          <p>New portions to prepare</p>
        </div>
    ''')
    if st.button("Use this plan", type="primary", width="stretch", key="apply_adjustment"):
        st.session_state["applied_plan"] = draft
        st.session_state["applied_identity"] = identity
        st.rerun()
    return draft


def show_plan_outlook(plan, record, preview):
    supply = plan["total_available"]
    forecast = round(record["forecast_orders"])
    low, high = round(record["range_low"]), round(record["range_high"])
    likelihood = ""
    if record["range_source"] == RANGE_SOURCE and not record["is_fallback"] and low < high:
        likelihood = f'''
          <div class="demand-likelihood">
            <div class="info-heading"><h3>Next week’s demand range</h3>
              {info("About the percentages", "These are the forecast’s target shares based on past errors at similar order volumes. The actual chances for this dish can differ. The middle share describes demand and does not tell you how many orders your plan will cover.")}
            </div>
            <div class="demand-bar" role="img" aria-label="About 10% below the range, 80% within the range and 10% above the range">
              <span>≈10%</span><span>≈80%</span><span>≈10%</span>
            </div>
            <div class="demand-labels">
              <span>Below {low:,} orders</span>
              <span><strong>{low:,}–{high:,} orders</strong></span>
              <span>Above {high:,} orders</span>
            </div>
            <p class="scenario-note">Approximate demand range based on historical forecast errors.</p>
          </div>
        '''
    preview_note = ""
    if preview is not None:
        preview_note = f'<p>With your preview, the plan covers up to <strong>{preview["total_available"]:,} orders</strong>.</p>'
    st.html(f'''
      <section class="scenario-section">
        <h2>Next week’s prep outlook</h2>
        <p>About <strong>{forecast:,} orders expected</strong> · Your plan covers up to <strong>{supply:,}</strong></p>
        {preview_note}
        {likelihood}
        <details class="scenario-action">
          <summary>What if orders change?</summary>
          <ul>
            <li><strong>If orders pick up:</strong> check what you’d need for a second batch and start it as demand builds.</li>
            <li><strong>If orders slow down:</strong> count the portions still safe to serve and use those first in the next batch.</li>
          </ul>
        </details>
      </section>
    ''')


def history_replay(data, center, meal):
    rows = data.data
    rows = rows.loc[
        (rows["center_id"] == center) & (rows["meal_id"] == meal)
        & (rows["week"] <= data.last_week) & rows["num_orders"].notna(),
        ["center_id", "meal_id", "week", "num_orders"],
    ].sort_values("week")
    if rows.empty:
        return None

    # Missing weeks carry no observation. Start each uninterrupted stretch afresh.
    consecutive = rows["week"].diff().eq(1)
    replay = rows.rename(columns={"week": "target_week", "num_orders": "actual_orders"})
    replay["forecast_orders"] = rows["num_orders"].shift()
    replay["window"] = (~consecutive).cumsum()
    replay = simulate_carryover(replay.loc[consecutive], prepare_forecast_minus_leftovers)
    return int(rows["week"].min()), data.last_week, replay.set_index("target_week")


def show_meal_history(history, center, meal):
    first, last, replay = history
    st.subheader("Waste and missed orders by week")
    st.caption(f"Kitchen {center} · Dish #{meal} · Simulation on actual order history")
    metric = st.radio("Show", ["Waste", "Missed orders"], horizontal=True, key="history_metric")
    values = replay["expired" if metric == "Waste" else "unmet"].to_dict()
    peak = max(1, *values.values())
    cells = []
    for week in range(first, last + 1):
        value = values.get(week)
        if value is None:
            cells.append('<span class="heat-missing"></span>')
        else:
            intensity = 0.07 + 0.9 * value / peak
            cells.append(f'<span class="heat-value" style="--heat:{intensity:.3f}"></span>')
    description = (
        "Darker weeks have more simulated expired portions." if metric == "Waste"
        else "Darker weeks have more simulated orders the kitchen could not fill."
    )
    ticks = [first, *range(((first + 24) // 25) * 25, last, 25), last]
    labels = "".join(
        f'<span style="grid-column:{week - first + 1}">W{week}</span>'
        for week in dict.fromkeys(ticks)
    )
    st.html(f'''
      <section class="chart meal-history">
        <div class="history-scroll" role="region" aria-label="Weekly impact heatmap" tabindex="0">
          <div class="history-plot" style="--weeks:{last - first + 1}">
            <div class="history-axis-y">{metric}</div>
            <div>
              <div class="history-heatmap" role="img" aria-label="{metric}, weeks {first} to {last}. {description} Gray means unavailable.">
                {"".join(cells)}
              </div>
              <div class="history-axis-x" aria-hidden="true">{labels}</div>
            </div>
          </div>
        </div>
        <p class="scenario-note">{description} Gray means unavailable.</p>
        <p class="scenario-note">The dataset records orders. Waste and missed orders are simulated by planning from the previous week’s orders and using eligible leftovers first for one extra week.</p>
      </section>
    ''')


def live_plan(mode):
    hero = st.container()
    context = base = None
    selected_history = None
    with st.container(border=True):
        st.markdown("**Choose your dish and count what’s ready**")
        try:
            if PUBLIC_DEMO:
                centres = [13]
                st.caption("Hackathon demo · One dish with a precomputed forecast")
            else:
                root = resolve_data_dir()
                signature = tuple((name, (root / name).stat().st_size, (root / name).stat().st_mtime_ns)
                                  for name in DATA_FILES)
                data = get_data(str(root), signature)
                centres = sorted(int(c) for c in data.centers.center_id.unique())
            left, middle, right = st.columns([1, 2, 2])
            center = left.selectbox("Kitchen location", centres,
                                    index=centres.index(13) if 13 in centres else 0, key="center",
                                    help="Choose the kitchen you’re planning for. In this demo, each kitchen is identified by a number.")
            menu = {"meals": [{"meal_id": 1198, "category": "Extras", "cuisine": "Thai"}]} if PUBLIC_DEMO else menu_tool(center, data)
            if "error" in menu:
                raise ValueError(menu["error"])
            meals = {r["meal_id"]: r for r in menu["meals"]}
            if not meals:
                raise ValueError("No observed menu is available for this centre.")
            options = list(meals)
            meal = middle.selectbox("Dish", options, index=options.index(1198) if 1198 in options else 0,
                format_func=lambda m: f"{meals[m]['category']} · {meals[m]['cuisine']} (#{m})", key=f"meal_{center}",
                help="Choose one dish to plan. In this demo, dishes are listed by category, cuisine and menu number.")
            if PUBLIC_DEMO:
                identity = ("public-demo", center, meal)
            else:
                selected_history = (history_replay(data, center, meal), center, meal)
                identity = (str(root), signature, center, meal)
            if st.session_state.get("loaded_identity") != identity:
                st.session_state.pop("live_context", None)
                st.session_state.pop("estimate", None)
                st.session_state.pop("adjustment_choice", None)
            stock = right.number_input("Portions already ready to use", value=None, step=1,
                                       key=f"real_stock_{center}_{meal}", placeholder="Enter 0 if none",
                                       help="Count only whole portions of this dish that will still be safe to serve next week. Enter 0 if you have none.")
            if st.button("Make my prep plan", key="load_forecast", type="primary"):
                with st.spinner("Working out next week’s prep…"):
                    if PUBLIC_DEMO:
                        st.session_state["live_context"] = PlanningContext(
                            "public-demo/13/1198/146", PUBLIC_FORECAST["forecast_orders"],
                            PUBLIC_FORECAST["provenance"], forecast_record=PUBLIC_FORECAST,
                        )
                    else:
                        st.session_state["live_context"] = get_live_context(str(root), signature, center, meal)
                    st.session_state["loaded_identity"] = identity
            context = st.session_state.get("live_context")
            plan_identity = (identity, context.key if context else None, stock)
            if st.session_state.get("applied_identity") != plan_identity:
                st.session_state.pop("applied_plan", None)
            if context:
                base = call_tool(CENTRAL, {"usable_stock": stock}, context)
        except (OSError, ValueError, RuntimeError) as exc:
            st.error(f"Forecast unavailable. {exc}")
            st.session_state.pop("live_context", None)
            st.session_state.pop("applied_plan", None)
            identity = plan_identity = stock = None

    record = context.forecast_record if context else None
    subtitle = (f"Centre {record['center_id']} · Meal {record['meal_id']} · Week {record['target_week']}"
                if record else "See what to use first and how much to make.")
    hero.html(f'''
        <div class="hero"><div><h1>Next week’s prep</h1><p>{subtitle}</p></div>
        <div class="hero-watermark" aria-hidden="true">
          <span class="freshwise-watermark"><img src="{image_data('freshwise-brand-reference.png')}" alt=""></span>
        </div></div>
    ''')
    plan = None
    plan_col, adjust_col = st.columns([3, 2], gap="medium")
    with plan_col:
        applied = st.session_state.get("applied_plan")
        if base and base["status"] == "success":
            plan = applied["result"]["adjusted_plan"] if applied else base["result"]
            show_plan(plan, context.forecast, adjusted=bool(applied))
            if record["is_fallback"]:
                st.caption(f"Forecast method: {record['method']} (fallback).")
        elif base and base["status"] == "error":
            st.error(base["answer"])
        else:
            st.info("Enter how many portions are ready to use." if context else "Choose a dish above and select Make my prep plan.")
    with adjust_col:
        with st.container(border=True):
            response = show_adjustment(context, stock, base, plan_identity)
    st.session_state["current_response"] = response
    scenarios = None
    if plan is not None:
        preview = None
        if response is not base and response != applied and response["status"] == "success":
            preview = response["result"]["adjusted_plan"]
        scenarios = (plan, record, preview)
    if PUBLIC_DEMO:
        return scenarios, selected_history, context, identity
    with st.expander("Technical details"):
        if record:
            st.write(f"Forecast range: {record['range_low_display']}–{record['range_high_display']} orders.")
            st.write(record["provenance"])
            st.dataframe(record["recent_orders"], hide_index=True)
        st.caption("Manager adjustments are planning inputs. The evaluation uses the frozen default policy.")
        st.json(evidence_tool())
    show_trace(response, "Prepare a plan using my stock and any confirmed estimate.", mode)
    return scenarios, selected_history, context, identity


def show_conversation(context, identity):
    if st.session_state.get("conversation_selection") != identity:
        st.session_state.pop("conversation_agent", None)
        st.session_state.pop("conversation_messages", None)
        st.session_state["conversation_selection"] = identity

    with st.container(key="freshwise_chat_launcher"):
        chat = st.popover("Ask FreshWise", key="freshwise_chat", on_change="rerun")
    if not chat.open:
        return

    with chat, st.container(key="freshwise_chat_body"):
        st.markdown("### Ask FreshWise")
        if context is None:
            st.caption("Select a dish and load its forecast with Make my prep plan to start.")
            return

        local_keychain = (
            sys.platform == "darwin"
            and urlsplit(st.context.url or "").hostname in {"localhost", "127.0.0.1", "::1"}
        )
        key = os.environ.get("GEMINI_API_KEY")
        if not key and local_keychain:
            if "saved_gemini_key" not in st.session_state:
                st.session_state["saved_gemini_key"] = read_gemini_key()
            key = st.session_state["saved_gemini_key"]
        if not key:
            key = st.text_input("Gemini API key", type="password", key="conversation_key",
                                help="Paste the key from Google AI Studio.")
            if key and local_keychain and st.button("Save to Mac Keychain", key="save_conversation_key"):
                try:
                    st.session_state["saved_gemini_key"] = save_gemini_key(key)
                except (OSError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        if not key:
            st.caption("Connect Gemini to try the conversation. You can still use the prep planner above.")
            return

        try:
            key = normalize_gemini_key(key)
            client = GeminiClient(key)
        except ValueError as exc:
            st.error(str(exc))
            return

        agent = st.session_state.get("conversation_agent")
        if agent is None or agent.client.key != key or agent.client.model != client.model:
            agent = PreparationAgent(context, client)
            st.session_state["conversation_agent"] = agent
            st.session_state["conversation_messages"] = []
        messages = st.session_state["conversation_messages"]
        st.caption("Ask how much to prepare or tell FreshWise about a change in demand.")
        if agent.active_plan is not None:
            st.success(f"Confirmed chat plan · {agent.active_plan['new_portions_to_prepare']:,} new portions")
        if messages:
            with st.container(height=200, border=False):
                bubbles = "".join(
                    f'<div class="chat-bubble-row {role}">'
                    f'{"" if role == "user" else "<span class=chat-chef aria-hidden=true>👩‍🍳</span>"}'
                    f'<div class="chat-bubble" aria-label="{role}">{escape(message)}</div></div>'
                    for role, message in messages
                )
                st.html(f'<div class="chat-bubbles">{bubbles}</div>')

        prompt = st.chat_input(agent.say("Message FreshWise", "Scrivi a FreshWise"), key="prep_chat")
        if prompt:
            with st.spinner("Checking the prep plan…"):
                reply = agent.send(prompt)
            messages.extend([("user", prompt), ("assistant", reply["answer"])])
            st.rerun()

        if agent.pending_plan is not None:
            st.info(f"Chat preview · {agent.pending_plan['new_portions_to_prepare']:,} new portions")
            if st.button(agent.say("Confirm plan", "Conferma il piano"), key="confirm_chat_plan", type="primary"):
                messages.append(("assistant", agent.confirm()["answer"]))
                st.rerun()
        elif agent.stock is not None and agent.estimate is not None:
            for column, label, italian in zip(st.columns(3), ADJUSTMENTS, ("Piccola modifica", "A metà", "Usa la mia stima")):
                choice = agent.say(label, italian)
                if column.button(choice, key=f"chat_{label}"):
                    with st.spinner("Checking the adjustment…"):
                        reply = agent.choose_weight(label)
                    messages.extend([("user", choice), ("assistant", reply["answer"])])
                    st.rerun()
        if agent.trace:
            with st.expander("Chat tool calls"):
                st.json(agent.trace)


def acceptance_example(mode):
    case = st.selectbox("Acceptance scenario", list(CASES), key="case")
    case_id = int(case[0])
    context = get_context("acceptance-fixture")
    st.caption("Synthetic verification example · forecast 100 orders")
    stock_key = f"stock_{case_id}"
    if stock_key not in st.session_state:
        st.session_state[stock_key] = 150 if case_id == 3 else 20
    stock = st.number_input("Usable portions", value=None, step=1, key=stock_key)
    arguments = {"usable_stock": stock}
    tool = EMPIRICAL if case_id == 6 else CENTRAL
    if case_id in (2, 4):
        tool = ADJUSTED
        if case_id == 2:
            st.session_state.setdefault("estimate_2", 140.0)
            st.session_state.setdefault("weight_2", 25.0)
        estimate = st.number_input("Expected orders", value=None, step=1.0, key=f"estimate_{case_id}")
        weight = st.number_input("Adjustment weight (%)", value=None, step=1.0, key=f"weight_{case_id}")
        arguments.update(manager_estimate=estimate, opinion_weight=None if weight is None else weight / 100)
    response = reject_guarantee() if case_id == 5 else call_tool(tool, arguments, context)
    st.session_state["current_response"] = response
    if response["status"] == "success":
        result = response["result"]
        show_plan(result.get("adjusted_plan", result), context.forecast, adjusted=tool == ADJUSTED)
    else:
        st.info(response["answer"])
    show_trace(response, CASES[case], mode)


def comparison_chart(title, denominator, rates, explanation):
    rows = []
    for label, value, colour in zip(("Baseline", "FreshWise"), rates, ("baseline", "freshwise")):
        rows.append(f'''
            <div class="chart-row"><strong>{label}</strong>
              <div class="track"><span class="{colour}" style="width:{value / 25 * 100:g}%"></span></div>
              <strong>{value:g}%</strong>
            </div>
        ''')
    st.html(f'''
        <section class="chart"><div class="info-heading"><h2>{title}</h2>
          {info(f"About {title.lower()}", explanation)}
          </div><p>{denominator}</p>
          <div class="chart-rows">{''.join(rows)}</div>
          <div class="axis"><span>0%</span><span>25%</span></div>
        </section>
    ''')


def show_savings():
    (baseline, freshwise), (missed_before, missed_after) = IMPACT["Four demo meals"]
    portions_per_comparison = 1000
    reduction = (baseline - freshwise) / baseline
    baseline_waste = round(portions_per_comparison * baseline / 100)
    freshwise_waste = round(portions_per_comparison * freshwise / 100)
    avoided = baseline_waste - freshwise_waste
    fewer_missed = round(10 * (missed_before - missed_after))
    (all_waste_before, all_waste_after), (all_missed_before, all_missed_after) = IMPACT["All meals"]
    with st.container(border=True, key="impact_savings"):
        comparison, calculator = st.columns([3, 2], gap="large")
        with comparison:
            st.html(f'''
              <section class="savings">
                <h2><strong>{reduction:.0%}</strong> less food waste</h2>
                <p class="savings-scope">Final simulation · Four demo dishes</p>
                <p>Portions counted as waste for every {portions_per_comparison:,} prepared</p>
                <div class="savings-bars">
                  <div><span>Using last week’s orders</span><span class="track" aria-hidden="true"><span class="baseline" style="width:100%"></span></span><strong>{baseline_waste:,}</strong></div>
                  <div><span>With FreshWise</span><span class="track" aria-hidden="true"><span class="freshwise" style="width:{freshwise_waste / baseline_waste:.2%}"></span></span><strong>{freshwise_waste:,}</strong></div>
                </div>
                <div class="savings-outcomes">
                  <p><strong>{avoided:,} fewer portions wasted</strong> per {portions_per_comparison:,} prepared</p>
                  <p><strong>{fewer_missed:,} fewer orders missed</strong> per 1,000 received</p>
                </div>
              </section>
            ''')
        with calculator, st.container(key="ingredient_value"):
            st.html(f'''
              <div class="ingredient-heading">
                <h3>Value of ingredients saved</h3>
                <span class="freshwise-watermark" aria-hidden="true"><img src="{image_data('freshwise-brand-reference.png')}" alt=""></span>
              </div>
            ''')
            cost = st.number_input(
                "Cost per portion (CAD)", min_value=0.0, value=None,
                step=0.25, format="%.2f", placeholder="e.g. 5.00", key="impact_portion_cost",
                help="Enter the average ingredient cost to make one portion of these dishes.",
            )
            if cost is not None:
                st.html(f'''
                  <div class="ingredient-total" role="status">
                    <strong>CA${avoided * cost:,.2f}</strong>
                    <p>Estimated ingredient value per {portions_per_comparison:,} portions prepared</p>
                  </div>
                ''')
        st.html(f'''
          <details class="scenario-action savings-all-dishes">
            <summary>Across all dishes</summary>
            <ul>
              <li><strong>{round(10 * (all_waste_before - all_waste_after))} fewer portions wasted</strong> per 1,000 prepared.</li>
              <li><strong>{round(10 * (all_missed_after - all_missed_before))} more orders missed</strong> per 1,000 received.</li>
            </ul>
          </details>
        ''')


def impact_view(scenarios, selected_history):
    show_savings()
    if selected_history and selected_history[0] is not None:
        show_meal_history(*selected_history)
    if scenarios is None:
        st.info("Make a prep plan in Prep plan to see how many portions could be left over or how many orders you might miss.")
    else:
        show_plan_outlook(*scenarios)
    with st.expander("How did FreshWise do in testing?"):
        show_historical_impact()


def show_historical_impact():
    title, control = st.columns([3, 2], vertical_alignment="center")
    title.html('<div class="impact-title"><h1>Waste &amp; service</h1><p>Final simulation · Weeks 136–145</p></div>')
    with control:
        population = st.radio("Meal selection", list(IMPACT), horizontal=True,
                              key="impact_population",
                              help="Compare the four dishes featured in the demo or see the results across all dishes in the test.")
    waste, missed = IMPACT[population]
    left, right = st.columns(2, gap="medium")
    with left:
        comparison_chart("Food waste", "Share of prepared portions", waste,
                         "Includes portions that expired and portions still in stock at the end of the simulation. Baseline is the comparison plan using last week’s orders and no carry-over.")
    with right:
        comparison_chart("Missed orders", "Share of observed orders", missed,
                         "The share of orders that the simulated kitchen could not fill because it ran out of portions.")
    st.html('''<div class="impact-summary"><strong>Across all meals</strong>
        <span>Waste 17.9% → 2.2%</span><span>Missed orders 16.7% → 20.6%</span></div>''')
    st.caption("Team-reported simulation on observed orders. Assumes one extra week of shelf life. Waste includes expired portions and usable stock at the end of the test.")
    with st.expander("How leftovers carry into next week"):
        st.caption("Final simulation · Centre 13 · Meal 1198 · Reported by the forecasting team")
        st.html('''<div class="relay">
          <div><strong>Week 136</strong><p>645 prepared · 458 served</p><b>187 still usable</b></div>
          <div class="relay-arrow" aria-hidden="true">→</div>
          <div><strong>Week 137</strong><p>187 used first + 381 newly prepared</p><p>458 served · 110 still usable</p></div>
        </div>''')


st.set_page_config(page_title="FreshWise | Kitchen prep planner", page_icon="🌱", layout="wide")
st.html((ROOT / "demo.css").read_text())
st.html(f'''
    <header class="brand-header">
      <div><span class="freshwise-logo"><img src="{image_data('freshwise-brand-reference.png')}" alt="FreshWise"></span>
      <span>Kitchen prep planner</span></div>
      <img class="sallas-logo" src="{image_data('sallas-logo.png')}" alt="SALLAS">
    </header>
''')
prep, impact = st.tabs(["Prep plan", "Impact"])
scenarios = selected_history = chat_context = chat_identity = None
with prep:
    mode = "Real next-week forecast"
    if not PUBLIC_DEMO:
        with st.expander("Verification settings"):
            mode = st.radio("Data mode", ["Acceptance examples", "Real next-week forecast"], index=1,
                            horizontal=True, key="data_mode")
    st.session_state["current_response"] = None
    if mode == "Acceptance examples":
        acceptance_example(mode)
    else:
        scenarios, selected_history, chat_context, chat_identity = live_plan(mode)
with impact:
    impact_view(scenarios, selected_history)
if not PUBLIC_DEMO:
    show_conversation(chat_context, chat_identity)
