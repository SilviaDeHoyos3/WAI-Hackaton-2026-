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
st.title("FreshWise · Preparation planner")
st.caption("Interface and integration: Lan · Decision tools: Ari · Forecast and menu tools: Silvia")
st.info("Tool-connected preview · Explicit controls and response templates · No AI model connected")
mode = st.radio("Data mode", ["Acceptance examples", "Real next-week forecast"], horizontal=True, key="data_mode")
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
    st.caption("Synthetic forecast: 100 orders. Central is the default. Example 6 alone uses synthetic ratios [0.8, 1.0, 1.2] and q=5/7.")
    stock_key = f"stock_{case_id}"
    if stock_key not in st.session_state:
        st.session_state[stock_key] = 150 if case_id == 3 else 20
    stock = st.number_input("Usable stock (whole portions)", value=None, step=1, key=stock_key)
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
            a,b,c = st.columns(3)
            a.metric(f"Week {r['target_week']} forecast", r["forecast_orders_display"])
            b.metric("Range low", r["range_low_display"])
            c.metric("Range high", r["range_high_display"])
            st.caption(f"Observed through week {r['history_end_week']} · Method used: {r['method']} · Full precision is used for preparation.")
            if r["is_fallback"]:
                st.warning(f"Requested {r['method_requested']}; fallback used: {r['method']}.")
            st.write(r["provenance"])
            with st.expander("Recent orders and forecast assumptions"):
                st.dataframe(r["recent_orders"], hide_index=True)
                for assumption in r["assumptions"]:
                    st.write("• " + assumption)
        stock = st.number_input("Usable stock (whole portions, confirm after expiry check)", value=None, step=1, key=f"real_stock_{center}_{meal}")
        arguments = {"usable_stock": stock}
        adjusted = st.checkbox("Include manager adjustment", key="real_adjustment")
        adjustment_prefix = f"real_{center}_{meal}"
        st.caption("Default: forecast minus usable stock, rounded up. Stock is a manager input, not an observed inventory field.")
        st.caption("Fewer-shortages mode is unavailable for real forecasts until matching calibration ratios are provided. Forecast-range endpoints are not substitutes.")
        with st.expander("Development evidence supplied by Silvia"):
            st.json(evidence_tool())
            st.caption("Historical development simulations only; these are not predictions of waste or shortages for this plan. The supplied evidence snapshot still labels the final test as pending.")
    except Exception as exc:
        blocked = True; adjusted = False
        st.error(f"Forecast unavailable: {type(exc).__name__}: {exc}")
        st.session_state.pop("live_context", None)

if adjusted:
    tool = "manager_adjusted_central_recommendation"
    if mode == "Acceptance examples" and case_id == 2:
        for key,value in (("estimate_2",140.0),("weight_2",25.0)):
            if key not in st.session_state: st.session_state[key] = value
    estimate = st.number_input("Manager expected orders", value=None, step=1.0, key=f"estimate_{adjustment_prefix}")
    weight = st.number_input("Opinion weight (%) — please confirm", value=None, step=1.0, key=f"weight_{adjustment_prefix}")
    arguments.update(manager_estimate=estimate, opinion_weight=None if weight is None else weight/100)
    if mode != "Acceptance examples":
        user_message = "Apply the manager estimate and confirmed weight to this plan."
st.chat_message("user").write(user_message)
st.caption("This is a scripted prompt paired with explicit inputs; it is not a free-text AI conversation.")
if not blocked:
    try:
        response = reject_guarantee() if mode == "Acceptance examples" and case_id == 5 else invoke(tool, arguments, context=context)
    except Exception as exc:
        response = {"status":"error", "tool_call":None, "result":None,
                    "answer":f"No valid recommendation: {type(exc).__name__}: {exc}"}
    st.session_state["current_response"] = response
    st.subheader("Preparation recommendation")
    if response["status"] == "success":
        st.chat_message("assistant").write(response["answer"])
        result = response["result"]
        if "original_plan" in result:
            a,b,c = st.columns(3)
            a.metric("Original preparation", result["original_plan"]["new_portions_to_prepare"])
            b.metric("Adjusted preparation", result["adjusted_plan"]["new_portions_to_prepare"])
            c.metric("Target change", f"{result['manager_context']['demand_shift']:+g}")
            policy = result["adjusted_plan"]["policy"]
        else:
            a,b,c = st.columns(3)
            a.metric("New portions to prepare", result["new_portions_to_prepare"])
            b.metric("Total available", result["total_available"])
            c.metric("Policy target supply", f"{result['target_supply']:g}")
            policy = result["policy"]
        st.caption("Policy used: " + policy)
    elif response["status"] == "error": st.error(response["answer"])
    else: st.warning(response["answer"])
    with st.expander("Exact tool call and result"):
        st.json(response)
    st.download_button("Download current trace", data=json.dumps(
        {"user_message":user_message,"mode":mode,"llm_connected":False,**response},indent=2),
        file_name="freshwise_plan.json",mime="application/json")
st.warning("Storage assumption: one additional week; use usable leftovers first. Confirm expiry before entering stock. One order is treated as one portion. The tools do not calculate expected waste or unmet orders for an individual plan.")
