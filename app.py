"""Lan's manager interface. Real teammate tools; no language model connected."""
from pathlib import Path
import sys
import json
import base64
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import streamlit as st
from threadpoolctl import threadpool_limits
from freshwise.application_tools import (get_context, invoke, reject_guarantee,
    load_application_data, resolve_data_dir, context_for_meal)
from freshwise.agent_data_tools import menu_tool, evidence_tool
from freshwise.carryover import simulate_carryover, prepare_forecast_minus_leftovers

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

def image_data(name):
    raw = (Path(__file__).parent / "assets" / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def plates(rate, label):
    # One hundred illustrative icons, rounded to a whole icon; the percentage stays exact.
    count = int(rate + 0.5)
    icons = "".join(f'<span class="plate {"waste" if i < count else "kept"}"></span>' for i in range(100))
    return f'<div><div class="fw-tag">{label}</div><div class="plate-grid" role="img" aria-label="Approximately {count} of 100 plate icons highlighted">{icons}</div><p class="plate-rate">{rate:g}%</p></div>'


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

.fw-plan {background:#FFFDF7;border:1px solid #D7DDCE;border-top:7px solid #286249;box-shadow:0 9px 25px #203e3209}
.ticket-top {display:flex;justify-content:space-between;gap:15px;border-bottom:1px dashed #B8C4B0;padding-bottom:12px;margin-bottom:18px}
.ticket-top .fw-tag {margin:0}
.ticket-trays,.plate-panels,.relay {display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px}
.tray {border:2px solid #88A36B;border-radius:12px;background:#EFF3E8;padding:17px 20px;box-shadow:inset 0 0 0 5px #fff8}
.tray.new {border-color:#D7B987;background:#FAF1E2}
.tray b {display:block;font-size:34px;color:#203E32;line-height:1.25}
.tray span {font-size:14px;color:#45614F}
.first-tag {display:inline-block;background:#286249;color:white!important;border-radius:5px;padding:3px 8px;font-size:11px!important;margin-top:7px}
.extra {display:inline-block;background:#E9D9B7;border-radius:7px;padding:7px 12px;font-weight:650;margin-top:12px}
.plate-grid {display:grid;grid-template-columns:repeat(10,1fr);gap:5px;max-width:300px}
.plate {display:block;aspect-ratio:1;border:2px solid #C3D1B8;border-radius:50%;background:#EEF3E7;box-shadow:inset 0 0 0 3px #FAF8F2}
.plate.waste {background:#BD875C;border-color:#BD875C;box-shadow:inset 0 0 0 3px #F4E2D2}
.plate-rate {font-size:26px;font-weight:700;color:#203E32;margin:8px 0}
.relay-note {text-align:center;color:#286249;font-weight:650;margin:12px 0}
.team-signature {display:flex;align-items:center;gap:10px;color:#58715C;font-size:12px;margin-top:30px}
@media(max-width:600px){.ticket-trays,.relay{grid-template-columns:1fr}.tray b{font-size:30px}.plate-grid{gap:3px}}
</style>""")
st.html(f'<img src="{image_data("freshwise-logo.png")}" alt="FreshWise original logo" style="width:330px;max-width:100%;height:auto;border-radius:10px">')
st.caption("Your kitchen pass · Use what is ready. Prepare what is next.")
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
        delta = new - old
        change_badge = f'<div class="extra">{abs(delta):,} {"extra" if delta >= 0 else "fewer"} portions to prepare</div>' 
        sentence = (f"Your estimate of {manager['manager_estimate']:g} orders, given "
                    f"{manager['opinion_weight']:.0%} weight, changes new preparation from {old:,} to {new:,} portions.")
    else:
        change_badge = ""
        heading = f"Prepare {plan['new_portions_to_prepare']:,} new portions"
        sentence = "Use ready-to-use portions first, then prepare the rest."
    hero.html(f'<section class="fw-plan"><div class="ticket-top"><div class="fw-tag">Prep ticket</div><div class="fw-tag">{tag}</div></div>'
              f'<h1>{heading}</h1><p>Expected orders: about {context.forecast:,.0f} · '
              f'Ready to use: {plan["usable_stock"]:,}</p>{change_badge}'
              f'<div class="ticket-trays"><div class="tray"><b>{plan["usable_stock"]:,}</b><span>ready to use</span><br><span class="first-tag">Use these first</span></div>'
              f'<div class="tray new"><b>{plan["new_portions_to_prepare"]:,}</b><span>new portions to prepare</span></div></div>'
              f'<p class="fw-note">{sentence}</p></section>')
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

with st.expander("The leftover relay — a two-week illustration", expanded=False):
    toy = pd.DataFrame({"center_id":[13,13],"meal_id":[1198,1198],"target_week":[1,2],
                        "forecast_orders":[100,100],"actual_orders":[80,100]})
    relay = simulate_carryover(toy, prepare_forecast_minus_leftovers, shelf_life_weeks=1, start_stock=0)
    first, second = relay.iloc[0], relay.iloc[1]
    st.caption("Synthetic illustration calculated by Silvia's simulator. These are not this meal's historical outcomes. One extra week of usability is assumed, not a food-safety recommendation.")
    st.html(f'<div class="relay"><div class="tray"><div class="fw-tag">This week</div><b>{int(first.prepared)} prepared</b><span>{int(first.sold)} portions served</span></div>'
            f'<div class="tray"><div class="fw-tag">Next week</div><b>{int(second.leftovers_in)} reused + {int(second.prepared)} new</b><span>{int(second.sold)} portions served</span></div></div>'
            f'<div class="relay-note">{int(second.leftovers_in)} usable portions → carry forward → use these first</div>')
    with st.expander("Two-week calculation trace"):
        st.dataframe(relay, hide_index=True)

with st.expander("Simulated impact — demo meals and the wider trade-off", expanded=False):
    st.caption("Team-reported final simulation: Silvia's group update, commit 7eefc42, weeks 136–145, training cutoff 135. Full §4.5 tables/manifest have not yet been imported or independently checked here. These results are separate from the current prep ticket.")
    st.write("Four demo meals at centre 13")
    st.html('<div class="plate-panels">' + plates(16.6,"Baseline · no carry-over") + plates(1.5,"Default · includes terminal stock") + '</div>')
    st.caption("Each grid has 100 illustrative plate icons; 17 and 2 are highlighted after rounding. Exact reported waste rates: 16.6% → 1.5%. Rates are portions divided by prepared portions, not measured physical plates or food weight.")
    st.write("Missed orders, shown separately: **18.8% → 7.2%** (unmet / actual orders).")
    st.info("Across all meals: reported waste 17.9% → 2.2%, but missed orders 16.7% → 20.6%. The default does not meet the no-worse-service floor across all meals.")
    st.caption("Default waste: expired plus usable end-of-horizon stock. Expired-only default rates: 1.1% for demo meals, 0.8% for all meals. Simulated with zero starting stock, oldest usable portions first and one extra week of shelf life. Manager adjustments were not evaluated in this comparison.")

with st.expander("Technical details", expanded=False):
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
st.html(f'<div class="team-signature"><span>A project by</span><img src="{image_data("sallas-logo.png")}" alt="SALLAS original team logo" style="width:130px;height:auto"></div>')
st.caption("Planning prototype · Forecasts are estimates, not guaranteed demand. No AI conversation connected.")
