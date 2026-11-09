"""Lan's manager interface. Real teammate tools; no language model connected."""
from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import streamlit as st
from threadpoolctl import threadpool_limits
from freshwise.application_tools import (get_context, invoke, reject_guarantee,
    load_application_data, resolve_data_dir, context_for_meal)
from freshwise.agent_data_tools import menu_tool, evidence_tool

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
    # Avoid OpenMP oversubscription on laptops. Teammate model parameters are unchanged.
    with threadpool_limits(limits=1):
        return context_for_meal(center_id, meal_id, get_data(path, signature))

st.set_page_config(page_title="FreshWise | Preparation planner", page_icon="🌱", layout="wide")
st.html("""<style>
.stApp {background:#FAF8F2;color:#203E32}
.block-container {max-width:1120px;padding-top:4.5rem}
h1,h2,h3 {color:#203E32}
.stButton>button[kind="primary"] {background:#286249;border-color:#286249}
.fw-brand {font-size:30px;font-weight:750;color:#286249;letter-spacing:-1px}
.fw-brand span {color:#758B58}
.fw-tag {font-size:12px;font-weight:650;letter-spacing:1.3px;text-transform:uppercase;color:#53715D;margin-bottom:14px}
.fw-plan {background:#EAF0E4;border:1px solid #D5E0CB;border-radius:22px;padding:32px 36px;margin:18px 0 24px}
.fw-plan h1 {font-size:clamp(30px,5vw,54px);line-height:1.14;margin:0 0 18px;letter-spacing:-1.5px}
.fw-plan p {font-size:18px;line-height:1.6;margin:0;color:#3D5A49}
.fw-plan .fw-note {font-size:14px;margin-top:14px}
@media(max-width:600px){.fw-plan{padding:24px}.block-container{padding-top:4.5rem}}
</style><div class="fw-brand">Fresh<span>Wise</span> 🌱</div>""")
st.caption("A clearer plan for your next preparation.")
with st.expander("Demo and verification settings", expanded=False):
    st.caption("Tool-connected prototype · Explicit inputs · No AI conversation connected")
    mode = st.radio("Data mode", ["Acceptance examples", "Real next-week forecast"], index=1,
                    horizontal=True, key="data_mode")
hero = st.container()
st.session_state["current_response"] = None
context = None
case_id = 1
arguments = {}
tool = "central_preparation_recommendation"
user_message = "How many new portions should I prepare?"
blocked = False
if mode == "Acceptance examples":
    case = st.selectbox("Acceptance scenario", list(CASES), key="case")
    case_id = int(case[0]); user_message = CASES[case]
    context = get_context("acceptance-fixture")
    st.caption("Synthetic test example · Forecast 100. Example 6 uses synthetic calibration and q=5/7.")
    stock_key = f"stock_{case_id}"
    if stock_key not in st.session_state:
        st.session_state[stock_key] = 150 if case_id == 3 else 20
    stock = st.number_input("How many portions do you already have ready to use?", value=None, step=1, key=stock_key)
    arguments = {"usable_stock": stock}
    if case_id == 6:
        tool = "preparation_recommendation"
    adjusted = case_id in (2, 4)
    adjustment_prefix = str(case_id)
else:
    try:
        root = resolve_data_dir()
        signature = tuple((f.name, f.stat().st_size, f.stat().st_mtime_ns) for f in sorted(root.glob("*.csv")))
        data = get_data(str(root), signature)
        centers = sorted(int(c) for c in data.centers.center_id.unique())
        center = st.selectbox("Centre", centers, index=centers.index(13) if 13 in centers else 0, key="center")
        menu = menu_tool(center, data)
        if "error" in menu:
            raise ValueError(menu["error"])
        meals = {r["meal_id"]: r for r in menu["meals"]}
        if not meals:
            raise ValueError("No observed menu is available for this centre.")
        options = list(meals)
        meal = st.selectbox("Meal", options, index=options.index(1198) if 1198 in options else 0,
            format_func=lambda m: f"{m} · {meals[m]['category']} · {meals[m]['cuisine']}", key=f"meal_{center}")
        with st.expander("Centre menu from the data"):
            st.dataframe(menu["meals"], hide_index=True)
        identity = (str(root), signature, center, meal)
        if st.session_state.get("loaded_identity") != identity:
            st.session_state.pop("live_context", None)
        if st.button("Load next-week forecast", key="load_forecast"):
            with st.spinner("Loading Silvia's forecast; first model fit may take about a minute…"):
                st.session_state["live_context"] = get_live_context(str(root), signature, center, meal)
                st.session_state["loaded_identity"] = identity
        context = st.session_state.get("live_context")
        if context is None:
            blocked = True
            st.warning("Load a forecast to calculate a plan. No example values are substituted.")
        else:
            r = context.forecast_record
            if r["is_fallback"]:
                st.warning(f"Forecast fallback used: {r['method']}.")
        stock = st.number_input("How many portions do you already have ready to use?", value=None, step=1, key=f"real_stock_{center}_{meal}")
        arguments = {"usable_stock": stock}
        st.caption("Count only portions you have checked are still safe to use. Enter whole portions.")
        adjusted = st.checkbox("Add your own expected orders", key="real_adjustment")
        adjustment_prefix = f"real_{center}_{meal}"
    except Exception as exc:
        blocked = True; adjusted = False
        st.error(f"Forecast unavailable: {type(exc).__name__}: {exc}")
        st.session_state.pop("live_context", None)

if adjusted:
    tool = "manager_adjusted_central_recommendation"
    if mode == "Acceptance examples" and case_id == 2:
        for key,value in (("estimate_2",140.0),("weight_2",25.0)):
            if key not in st.session_state: st.session_state[key] = value
    estimate = st.number_input("How many orders do you expect?", value=None, step=1.0, key=f"estimate_{adjustment_prefix}")
    weight = st.number_input("How much weight should your estimate have? (%)", value=None, step=1.0, key=f"weight_{adjustment_prefix}")
    arguments.update(manager_estimate=estimate, opinion_weight=None if weight is None else weight/100)
    if mode != "Acceptance examples":
        user_message = "Apply the manager estimate and confirmed weight to this plan."
response = None
if not blocked:
    try:
        response = reject_guarantee() if mode == "Acceptance examples" and case_id == 5 else invoke(tool, arguments, context=context)
    except Exception as exc:
        response = {"status":"error", "tool_call":None, "result":None,
                    "answer":f"No valid recommendation: {type(exc).__name__}: {exc}"}
    st.session_state["current_response"] = response

if response and response["status"] == "success":
    result = response["result"]
    is_adjusted = "original_plan" in result
    plan = result["adjusted_plan"] if is_adjusted else result
    policy = plan["policy"]
    tag = (f"Week {context.forecast_record['target_week']} · Centre {center} · Meal {meal}"
           if context.forecast_record else "Synthetic acceptance example")
    if is_adjusted:
        old = result["original_plan"]["new_portions_to_prepare"]
        new = plan["new_portions_to_prepare"]
        manager = result["manager_context"]
        heading = f"{old:,} → {new:,} portions"
        sentence = (f"Your estimate of {manager['manager_estimate']:g} orders, given "
                    f"{manager['opinion_weight']:.0%} weight, changes new preparation from {old:,} to {new:,} portions.")
    else:
        heading = f"Prepare {plan['new_portions_to_prepare']:,} new portions"
        sentence = "Use ready-to-use portions first, then prepare the rest."
    hero.html(f'<section class="fw-plan"><div class="fw-tag">{tag}</div>'
              f'<h1>{heading}</h1><p>Expected orders: about {context.forecast:,.0f} · '
              f'Ready to use: {plan["usable_stock"]:,}</p><p class="fw-note">{sentence}</p></section>')
    if is_adjusted:
        st.caption("Your adjustment is a planning input; it was not part of the evaluated policy results.")
    if tool == "preparation_recommendation":
        st.warning("Synthetic fewer-shortages example: preparing more may reduce shortages but increase waste.")
else:
    hero.html('<section class="fw-plan"><div class="fw-tag">Your next preparation</div>'
              '<h1>Let’s make a preparation plan.</h1><p>Choose a meal, load its forecast, and tell us what you already have ready to use.</p></section>')
    if response:
        if response["status"] == "error": st.error(response["answer"])
        else: st.info(response["answer"])

with st.expander("Forecast details, assumptions and evidence", expanded=False):
    st.write("Default policy: forecast minus usable stock, rounded up and lower bounded at zero.")
    if context and context.forecast_record:
        r = context.forecast_record
        st.write(f"Expected orders: {r['forecast_orders_display']} · Model range: {r['range_low_display']}–{r['range_high_display']}.")
        st.caption(f"Observed through week {r['history_end_week']} · Actual method: {r['method']} · Full precision is used in calculations.")
        st.write(r["provenance"])
        st.dataframe(r["recent_orders"], hide_index=True)
        for assumption in r["assumptions"]: st.write("• " + assumption)
    st.caption("One extra week of storage is a simulation assumption. Confirm expiry before entering stock. One order is treated as one portion. These tools do not predict waste or unmet orders for an individual plan.")
    st.caption("Real fewer-shortages mode awaits matching calibration ratios; model-range endpoints are not substitutes.")
    st.write("Development evidence supplied by Silvia")
    st.json(evidence_tool())
    st.caption("This bundled evidence is an older development snapshot, not the newly reported final test. Final-test tables have not yet been imported into this preview. Across all meals, the reported final default reduces simulated waste but increases unmet orders; do not claim service improved everywhere.")

with st.expander("Verification prompts and exact tool trace", expanded=False):
    st.caption("Interface/integration: Lan · Forecasts: Silvia · Decisions: Ari. These prompts and responses use explicit inputs and templates, not an AI conversation.")
    st.chat_message("user").write(user_message)
    if response:
        st.chat_message("assistant").write(response["answer"])
        st.json(response)
        st.download_button("Download current trace", data=json.dumps(
            {"user_message":user_message,"mode":mode,"llm_connected":False,**response},indent=2),
            file_name="freshwise_plan.json",mime="application/json")
st.caption("Planning prototype · Forecasts are estimates, not guaranteed demand.")
