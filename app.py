"""Run from the project root: python -m streamlit run app.py."""

from pathlib import Path
import sys

# Support a source archive before the package has been installed in editable mode.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st
from freshwise.demo import FIXTURES, baseline_plan


st.set_page_config(page_title="FreshWise | Weekly preparation", page_icon="🌱", layout="wide")
st.title("FreshWise")
st.write("A clearer plan for next week's meal preparation.")
st.info("Prototype · Synthetic examples only · Forecast-matching baseline · Human review required")

st.subheader("1. Choose a meal")
left, middle, right = st.columns(3)
left.selectbox("Fulfilment centre", ["DEMO_CENTER"], key="center")
meal = middle.selectbox("Meal", list(FIXTURES), key="meal")
forecast = FIXTURES[meal]
right.metric("Target dataset week", str(forecast.target_week))
st.caption(f"Selection: {forecast.center_id} / {forecast.meal_id}. Dataset weeks are indices, not calendar dates.")

st.subheader("2. Review the forecast")
st.metric("Example forecast (orders)", f"{forecast.forecast_orders:,.0f}")
st.caption("Model forecast: synthetic placeholder; Silvia's forecast function is not connected.")
st.caption("Historical orders: not loaded in this fixture demo. These meal identifiers are synthetic.")

st.subheader("3. Set planning assumptions")
st.write("Simulated stock and penalties. For this simulation, one order is assumed to equal one portion.")
a, b, c = st.columns(3)
stock_key = f"stock_{forecast.meal_id}"
for key, default in ((stock_key, 20), ("overage", 1.0), ("underage", 3.0)):
    if key not in st.session_state:
        st.session_state[key] = default
stock = a.number_input("Usable stock (portions)", value=None, step=1, key=stock_key)
overage = b.number_input("Excess penalty (cost units / portion)", value=None, step=0.5, key="overage")
underage = c.number_input("Shortage penalty (cost units / unmet order)", value=None, step=0.5, key="underage")
st.caption("Each meal has its own stock input. Penalties apply to the current simulation and are not verified monetary costs.")

try:
    plan = baseline_plan(forecast, stock, overage, underage)
except (ValueError, ArithmeticError) as exc:
    st.error(f"No valid plan: {exc}")
    st.stop()

st.subheader("4. Review your baseline plan")
x, y, z = st.columns(3)
x.metric("Baseline preparation (portions)", f"{plan['preparation']:,}")
y.metric("Total available supply (portions)", f"{plan['supply']:,}")
z.metric("Usable stock (portions)", f"{stock:,}")
st.write(f"For {forecast.meal_id} in week {forecast.target_week}, the example forecast is "
         f"{forecast.forecast_orders:,.0f} orders and usable stock is {stock:,} portions. "
         f"The baseline prepares {plan['preparation']:,} additional portions. "
         "Preparation is rounded up to whole portions and cannot be negative.")

st.subheader("5. Explore the trade-offs")
st.caption("Low / base / high = 70% / 100% / 130% of the example forecast, rounded up. These are assumed stress cases, not a confidence interval.")
st.dataframe(plan["scenarios"], hide_index=True, width="stretch")
st.write("Changing a penalty updates scenario losses immediately. This simple baseline always matches the forecast; "
         "penalties do not change its preparation quantity. Ari's decision function is not connected yet.")
st.warning("Results describe simulated excess and unmet orders. They do not establish observed waste reduction, profit or carbon savings.")

with st.expander("Assumptions and integration status"):
    st.write("Policy: forecast-matching baseline. Assumption version: demo-v1. No lead time, capacity limit, expiry or carry-over is modelled.")
    st.write("Implemented: meal selection, per-meal stock, penalties, baseline scenarios and validation. "
             "Pending: Silvia's forecast, Ari's recommendation, evaluation results and the team-agreed agent workflow. "
             "This screen is not an implemented AI agent and does not place orders.")
    st.write("All values are recalculated on input changes; no prior recommendation is stored as a valid result.")
